
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Union
import difflib

import numpy as np
import pandas as pd
import Levenshtein

import inference_server.utils.ipython  # noqa: F401
from transformers import AutoTokenizer

from datautils.pandas import df_to_parquet, parquet_to_df

from inference_server.backend.state import request_manager
from inference_server.utils import random_uuid, setup_logging, getLogger
from inference_server.modules.specedit.lib.spec_edit_worker_v1 import (
    MockVllmConfig,
    SpecEditProposer,
)


logger = getLogger(__name__)

_script_model = bool(globals().get('__file__'))


@dataclass
class EvaluationMetrics:
    """Metrics collected during speculative inference evaluation."""
    execution_time_ms: float
    propose_count: int
    total_accepted_tokens: int
    total_output_tokens: int

    def is_failed_case(self) -> bool:
        """Check if this represents a failed case (all metrics are zero)."""
        return (self.execution_time_ms == 0.0 and
                self.propose_count == 0 and
                self.total_accepted_tokens == 0 and
                self.total_output_tokens == 0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary format."""
        return {
            'execution_time_ms': self.execution_time_ms,
            'propose_count': self.propose_count,
            'total_accepted_tokens': self.total_accepted_tokens,
            'total_output_tokens': self.total_output_tokens
        }


def load_dataset(file_path: str) -> pd.DataFrame:
    """
    Load dataset from parquet file using parquet_to_df utility.

    Args:
        file_path: Path to the parquet dataset file

    Returns:
        DataFrame with dataset contents
    """
    try:
        df = parquet_to_df(file_path)

        # Validate that required fields are present
        required_fields = ['id', 'prompt', 'draft', 'output']
        missing_fields = [field for field in required_fields if field not in df.columns]

        if missing_fields:
            raise ValueError(f"Missing required fields in dataset: {missing_fields}")

        return df

    except FileNotFoundError:
        raise FileNotFoundError(f"Dataset file not found: {file_path}")
    except ValueError:
        # Re-raise ValueError as-is (for missing fields)
        raise
    except Exception as e:
        raise Exception(f"Error loading dataset from {file_path}: {str(e)}")


def calculate_prefix_match(spec_draft: Union[str, List[int], np.ndarray], truth_output: Union[str, List[int], np.ndarray]) -> int:
    """
    Calculate the number of accepted elements from spec_draft that match truth_output.

    Performs element-by-element prefix comparison and returns the count of
    accepted elements before the first mismatch occurs. Works with both strings
    (character-by-character) and int arrays (element-by-element).

    Args:
        spec_draft: The speculative draft (str or int array) to compare
        truth_output: The ground truth output (str or int array) to compare against

    Returns:
        int: Number of accepted elements before first mismatch

    Examples:
        >>> calculate_prefix_match("hello world", "hello there")
        6  # "hello " matches
        >>> calculate_prefix_match([1, 2, 3, 4], [1, 2, 5, 6])
        2  # [1, 2] matches
        >>> calculate_prefix_match("", "anything")
        0  # Empty draft
        >>> calculate_prefix_match([], [1, 2, 3])
        0  # Empty draft array
    """
    try:
        # Handle edge cases with empty inputs or None values
        if spec_draft is None or truth_output is None:
            return 0

        # Handle empty inputs
        if (isinstance(spec_draft, (str, list, tuple, np.ndarray)) and len(spec_draft) == 0) or \
           (isinstance(truth_output, (str, list, tuple, np.ndarray)) and len(truth_output) == 0):
            return 0

        # Ensure both inputs are the same type (both strings or both arrays)
        spec_is_string = isinstance(spec_draft, str)
        truth_is_string = isinstance(truth_output, str)
        spec_is_array = isinstance(spec_draft, (list, tuple, np.ndarray))
        truth_is_array = isinstance(truth_output, (list, tuple, np.ndarray))

        if spec_is_string and truth_is_string:
            # String comparison (original behavior)
            pass
        elif spec_is_array and truth_is_array:
            # Array comparison - convert to numpy arrays for easier handling
            spec_draft = np.array(spec_draft)
            truth_output = np.array(truth_output)
        else:
            # Mismatched types
            logger.warning(f"Mismatched input types to prefix matching: spec_draft={type(spec_draft)}, truth_output={type(truth_output)}")
            return 0

        # Find the minimum length to avoid index out of bounds
        min_length = min(len(spec_draft), len(truth_output))

        # Count matching elements from the beginning
        accepted_elements = 0
        for i in range(min_length):
            if spec_draft[i] == truth_output[i]:
                accepted_elements += 1
            else:
                # Stop at first mismatch
                break

        return accepted_elements

    except Exception as e:
        logger.error(f"Error in prefix matching: {str(e)}")
        return 0



def setup_proposer(num_speculative_tokens: int = 5) -> SpecEditProposer:
    mock_config = MockVllmConfig(
        min_n=1,  # Minimum n-gram length
        max_n=5,  # Maximum n-gram length
        num_speculative_tokens=num_speculative_tokens,  # Number of speculative tokens (k)
        max_model_len=8192  # Maximum model length
    )
    spec_edit_proposer = SpecEditProposer(mock_config)

    return spec_edit_proposer


def setup_tokenizer(tokenizer_path: str = None):
    if tokenizer_path is None:
        # Get the path to the fulledit_tokenizer directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        tokenizer_path = os.path.join(current_dir, "fulledit_tokenizer")

    # Load the tokenizer
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)

    return tokenizer


def process_single_case(
        row: pd.Series,
        proposer: SpecEditProposer,
        tokenizer: AutoTokenizer,
        mode: str="ngram") -> EvaluationMetrics:
    """
    Process a single dataset case using the SpecEditProposer to simulate speculative inference.

    This function simulates the speculative inference loop by:
    1. Measuring execution time for the entire process
    2. Tracking the number of propose method calls
    3. Simulating the iterative process of proposing drafts and accepting tokens
    4. Accumulating the total number of accepted tokens and output tokens

    Args:
        row: DataFrame row containing 'id', 'prompt', 'draft', 'output' fields
        proposer: Configured SpecEditProposer instance for generating proposals
        tokenizer: AutoTokenizer instance for proper text-to-token conversion
        model: ngram or specedit, default is ngram

    Returns:
        EvaluationMetrics containing:
            - execution_time_ms: Total execution time in milliseconds
            - propose_count: Number of times the propose method was called
            - total_accepted_tokens: Total tokens accepted from all proposals
            - total_output_tokens: Total tokens in the expected output
    """
    case_id = row.get('id', random_uuid())
    req_id = str(case_id)
    start_time = time.time()

    # Initialize counters
    propose_count = 0
    total_accepted_tokens = 0
    total_output_tokens = 0

    # Get the prompt and truth output for comparison
    prompt = str(row['prompt'])
    truth_output = str(row['output'])
    draft = str(row['draft'])

    if mode == "specedit":
        draft_tokens = tokenizer.encode(draft, add_special_tokens=False)
        request_manager.set_stream_next_chunk(req_id, draft_tokens)

    # Tokenize prompt and truth_output once at the beginning
    prompt_tokens = np.array(tokenizer.encode(prompt, add_special_tokens=False), dtype=np.int32)
    truth_output_tokens = np.array(tokenizer.encode(truth_output, add_special_tokens=False), dtype=np.int32)
    total_output_tokens = len(truth_output_tokens)

    # Simulate the speculative inference loop
    # Start with the current output being empty (beginning of generation)
    cur_output_tokens = np.array([], dtype=np.int32)

    max_iterations = 20000  # Prevent infinite loops
    iteration = 0

    while (iteration < max_iterations and
            len(cur_output_tokens) < len(truth_output_tokens)):

        # Call the proposer to get a draft using current token array
        propose_count += 1

        # The proposer.propose method expects context_token_ids and optional req_id
        # For evaluation, we'll use the row id as req_id
        # Context should be prompt_tokens + current_output_tokens
        context_tokens = np.concatenate([prompt_tokens, cur_output_tokens])
        _req_id = req_id
        if mode == "ngram":
            _req_id = None
        draft_token_ids = proposer.propose(context_tokens, output_token_ids=cur_output_tokens.tolist(), req_id=_req_id)

        if draft_token_ids is None or len(draft_token_ids) == 0:
            logger.debug(f"Case {case_id}: No draft generated at iteration {iteration}")
            # Add the next correct token from truth_output_tokens and continue
            if len(cur_output_tokens) < len(truth_output_tokens):
                next_token = truth_output_tokens[len(cur_output_tokens)]
                logger.debug(f"no draft and get next token {next_token}")
                cur_output_tokens = np.concatenate([cur_output_tokens, [next_token]])
                logger.debug(f"Case {case_id}: Added next truth token at iteration {iteration}")
            iteration += 1
            continue

        # Calculate how many tokens from the draft match the remaining truth output
        remaining_truth_tokens = truth_output_tokens[len(cur_output_tokens):]

        # Use token-based prefix matching
        accepted_tokens = calculate_prefix_match(draft_token_ids, remaining_truth_tokens)

        if accepted_tokens == 0:
            logger.debug(f"Case {case_id}: No tokens accepted at iteration {iteration}")
            # Add the next correct token from truth_output_tokens and continue
            if len(cur_output_tokens) < len(truth_output_tokens):
                next_token = truth_output_tokens[len(cur_output_tokens)]
                cur_output_tokens = np.concatenate([cur_output_tokens, [next_token]])
                logger.debug(f"Case {case_id}: Added next truth token at iteration {iteration}")
        else:
            # Update counters and current output tokens
            total_accepted_tokens += accepted_tokens
            # Extend current output tokens with accepted tokens
            accepted_token_ids = remaining_truth_tokens[:accepted_tokens]
            cur_output_tokens = np.concatenate([cur_output_tokens, accepted_token_ids])
            logger.debug(f"Case {case_id}: Accepted {accepted_tokens} tokens at iteration {iteration}")

        iteration += 1

    # Log completion status
    if iteration >= max_iterations:
        logger.debug(f"Case {case_id}: Stopped due to max iterations ({max_iterations})")

    if mode == "specedit":
        request_manager.remove_request(req_id)

    # Calculate execution time
    end_time = time.time()
    execution_time_ms = (end_time - start_time) * 1000

    return EvaluationMetrics(
        execution_time_ms=execution_time_ms,
        propose_count=propose_count,
        total_accepted_tokens=total_accepted_tokens,
        total_output_tokens=total_output_tokens
    )


def run(
        dataset_file: str = None,
        tokenizer_path: str = None,
        num_speculative_tokens: int=40,
        limit: int = None,
        max_change_ratio: float = None,
        debug: bool = False):
    """
    Run evaluation with both ngram and specedit modes and compare results.
    """
    setup_logging(debug)

    if dataset_file is None:
        raise ValueError("dataset_file parameter is required")

    # Load dataset
    df = load_dataset(dataset_file)
    if limit:
        df = df.head(limit)

    proposer = setup_proposer(num_speculative_tokens=num_speculative_tokens)
    tokenizer = setup_tokenizer(tokenizer_path=tokenizer_path)

    # Run both modes
    results = {}
    for current_mode in ['ngram', 'specedit']:
        logger.info(f"Running {current_mode} mode...")
        metrics_list = []

        for idx, row in df.iterrows():
            metrics = process_single_case(row, proposer, tokenizer, mode=current_mode)
            metrics_list.append(metrics)

        # Add metrics to dataframe
        df_result = df.copy()
        df_result[f'execution_time_ms_{current_mode}'] = [m.execution_time_ms for m in metrics_list]
        df_result[f'propose_count_{current_mode}'] = [m.propose_count for m in metrics_list]
        df_result[f'total_accepted_tokens_{current_mode}'] = [m.total_accepted_tokens for m in metrics_list]
        df_result[f'total_output_tokens_{current_mode}'] = [m.total_output_tokens for m in metrics_list]

        results[current_mode] = df_result

    # Compare results
    timestamp = time.strftime("%Y-%m-%d_%H-%M")
    df_comparison = results['ngram'][['id', 'prompt', 'draft', 'output']].copy()

    # Calculate change ratio once (it's the same for both modes)
    draft_output_change_ratios = []
    for _, row in df_comparison.iterrows():
        draft_tokens = tokenizer.encode(row['draft'])
        output_tokens = tokenizer.encode(row['output'])
        distance = Levenshtein.distance(draft_tokens, output_tokens)
        change_ratio = distance / len(draft_tokens) if len(draft_tokens) > 0 else 0.0
        draft_output_change_ratios.append(change_ratio)
    df_comparison['draft_output_change_ratio'] = draft_output_change_ratios

    for mode_name in ['ngram', 'specedit']:
        for metric in ['execution_time_ms', 'propose_count', 'total_accepted_tokens', 'total_output_tokens']:
            df_comparison[f'{metric}_{mode_name}'] = results[mode_name][f'{metric}_{mode_name}']

    # Save comparison results to parquet file
    comparison_file = f"eval_comparison_{timestamp}.parquet"
    df_to_parquet(df_comparison, comparison_file)
    logger.info(f"Saved comparison results to {comparison_file}")

    # Analyze and print results
    analyze_results(df_comparison, max_change_ratio=max_change_ratio)
    return df_comparison


def analyze_results(df_comparison: pd.DataFrame, max_change_ratio: float=None):
    """
    Analyze and print comparison results from evaluation data.

    Args:
        df_comparison: DataFrame with comparison results containing metrics for both modes
    """
    successful = df_comparison[
        (df_comparison['execution_time_ms_ngram'] > 0) &
        (df_comparison['execution_time_ms_specedit'] > 0)
    ]

    if max_change_ratio:
        successful = successful[successful.draft_output_change_ratio <= max_change_ratio]

    print(f"\nComparison Results ({len(successful)} successful cases):")

    # Print change ratio once (same for both modes)
    change_ratio_values = successful['draft_output_change_ratio']
    print("\nDRAFT-OUTPUT CHANGE RATIO:")
    print(f"  draft_output_change_ratio: P50={change_ratio_values.quantile(0.5):.2f}, P80={change_ratio_values.quantile(0.8):.2f}, P90={change_ratio_values.quantile(0.9):.2f}")

    for mode in ['ngram', 'specedit']:
        print(f"\n{mode.upper()}:")
        for metric in ['execution_time_ms', 'propose_count', 'total_accepted_tokens']:
            values = successful[f'{metric}_{mode}']
            print(f"  {metric}: P50={values.quantile(0.5):.2f}, P80={values.quantile(0.8):.2f}, P90={values.quantile(0.9):.2f}")


def analyze_single_case(df: pd.DataFrame, case_id: str):
    """
    Analyze a single case by ID and show a pretty diff between draft and output.

    Args:
        df: DataFrame containing 'id', 'draft', 'output' columns
        case_id: The ID of the case to analyze
    """
    # Find the row with matching ID
    matching_rows = df[df['id'] == case_id]
    if matching_rows.empty:
        print(f"Case ID '{case_id}' not found in dataset")
        return

    row = matching_rows.iloc[0]
    draft = str(row['draft'])
    output = str(row['output'])

    # Calculate basic statistics
    draft_len = len(draft)
    output_len = len(output)
    change_ratio = Levenshtein.distance(draft, output) / draft_len if draft_len > 0 else 0.0

    print(f"Case ID: {case_id}")
    print(f"Draft length: {draft_len} characters")
    print(f"Output length: {output_len} characters")
    print(f"Change ratio: {change_ratio:.3f}")
    print()

    # Generate unified diff
    draft_lines = draft.splitlines(keepends=True)
    output_lines = output.splitlines(keepends=True)

    diff = difflib.unified_diff(
        draft_lines,
        output_lines,
        fromfile='draft',
        tofile='output',
        lineterm=''
    )

    print("DIFF:")
    diff_lines = list(diff)
    if not diff_lines:
        print("  No differences found")
    else:
        for line in diff_lines:
            print(f"  {line}")


def analyze(comparison_file: str):
    """
    Load and analyze results from a saved comparison parquet file.

    Args:
        comparison_file: Path to the comparison parquet file
    """
    df_comparison = parquet_to_df(comparison_file)
    logger.info(f"Loaded comparison data from {comparison_file}")
    analyze_results(df_comparison)


if __name__ == '__main__' and _script_model:
    import fire

    cmds = dict(run=run, analyze=analyze, analyze_single_case=analyze_single_case)
    fire.Fire(cmds)
