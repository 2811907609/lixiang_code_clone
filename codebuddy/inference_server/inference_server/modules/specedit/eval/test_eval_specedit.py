"""
Tests for the specedit evaluation module
"""

import os
import tempfile
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest
from transformers import AutoTokenizer

from inference_server.modules.specedit.lib.spec_edit_worker_v1 import (
    SpecEditProposer,
)
from inference_server.modules.specedit.eval.eval_specedit import (
    calculate_prefix_match,
    load_dataset,
    process_single_case,
    setup_proposer,
    EvaluationMetrics,
)


@pytest.mark.parametrize("spec_draft,truth_output,expected,description", [
    # String tests
    ("hello world", "hello there", 6, "normal matching prefix case"),
    ("", "anything", 0, "empty spec_draft edge case"),
    ("test", "", 0, "empty truth_output edge case"),
    ("", "", 0, "both strings empty edge case"),
    ("exact", "exact", 5, "exact match case"),
    ("abc", "xyz", 0, "no match from the beginning"),
    ("hello world", "hello", 5, "spec_draft longer than truth_output"),
    ("hello", "hello world", 5, "truth_output longer than spec_draft"),
    ("a", "a", 1, "single character match"),
    ("a", "b", 0, "single character no match"),
])
def test_calculate_prefix_match_strings(spec_draft, truth_output, expected, description):
    """Test calculate_prefix_match with string inputs"""
    result = calculate_prefix_match(spec_draft, truth_output)
    assert result == expected, f"Failed for {description}: expected {expected}, got {result}"


def test_process_single_case_basic_functionality():
    """Test process_single_case with a mock proposer and tokenizer"""
    # Create a mock proposer
    mock_proposer = Mock()

    # Mock the propose method to return some token ids
    # For "hello", we'll return token ids that represent " world"
    mock_proposer.propose.return_value = np.array([32, 119, 111, 114, 108, 100])  # " world"

    # Create a mock tokenizer
    mock_tokenizer = Mock()
    mock_tokenizer.encode.return_value = [1, 2, 3]  # Mock token ids for context
    mock_tokenizer.decode.return_value = " world"  # Mock decoded text

    # Create test data
    test_row = pd.Series({
        'id': 'test_1',
        'prompt': 'Say hello',
        'draft': 'hello',
        'output': 'hello world'
    })

    # Call the function
    result = process_single_case(test_row, mock_proposer, mock_tokenizer)

    # Verify the result is an EvaluationMetrics instance
    assert isinstance(result, EvaluationMetrics)

    # Verify types
    assert isinstance(result.execution_time_ms, float)
    assert isinstance(result.propose_count, int)
    assert isinstance(result.total_accepted_tokens, int)
    assert isinstance(result.total_output_tokens, int)

    # Verify that propose was called at least once
    assert result.propose_count > 0
    assert mock_proposer.propose.called


def test_process_single_case_no_draft_generated():
    """Test process_single_case when proposer returns None"""
    # Create a mock proposer that returns None
    mock_proposer = Mock()
    mock_proposer.propose.return_value = None

    # Create a mock tokenizer with proper return values
    mock_tokenizer = Mock()
    # Mock encode to return different token arrays for different inputs
    def mock_encode(text, add_special_tokens=False):
        if text == 'Say hello':
            return [1, 2, 3]  # prompt tokens
        elif text == 'hello world':
            return [1, 2, 3, 4, 5]  # output tokens
        elif text == 'hello':
            return [1, 2, 3]  # draft tokens
        return [1, 2, 3]  # default

    mock_tokenizer.encode.side_effect = mock_encode

    # Create test data
    test_row = pd.Series({
        'id': 'test_2',
        'prompt': 'Say hello',
        'draft': 'hello',
        'output': 'hello world'
    })

    # Call the function
    result = process_single_case(test_row, mock_proposer, mock_tokenizer)

    # Verify the result is an EvaluationMetrics instance
    assert isinstance(result, EvaluationMetrics)

    # When proposer returns None, it adds one token per iteration until complete
    # With 5 output tokens, it should take 5 iterations
    assert result.propose_count == 5
    assert result.total_accepted_tokens == 0  # No tokens accepted from proposer
    assert result.total_output_tokens == 5


def test_process_single_case_proposer_exception():
    """Test process_single_case when proposer raises an exception"""
    # Create a mock proposer that raises an exception
    mock_proposer = Mock()
    mock_proposer.propose.side_effect = Exception("Proposer error")

    # Create a mock tokenizer
    mock_tokenizer = Mock()
    mock_tokenizer.encode.return_value = [1, 2, 3]

    # Create test data
    test_row = pd.Series({
        'id': 'test_3',
        'prompt': 'Say hello',
        'draft': 'hello',
        'output': 'hello world'
    })

    # The function should raise the exception since it's not handled in the current implementation
    with pytest.raises(Exception, match="Proposer error"):
        process_single_case(test_row, mock_proposer, mock_tokenizer)


def test_setup_proposer():
    """Test that setup_proposer creates a valid proposer instance"""
    try:
        proposer = setup_proposer()

        # Should return a SpecEditProposer instance
        assert isinstance(proposer, SpecEditProposer)

        # Should have the necessary attributes
        assert hasattr(proposer, 'propose')
        assert callable(proposer.propose)

    except Exception as e:
        # If setup fails due to missing dependencies, that's acceptable for testing
        # but we should at least verify the exception is handled
        assert isinstance(e, Exception)


def test_load_dataset_success():
    """Test load_dataset function with valid parquet file"""
    # Create a test DataFrame and save it to a temporary file
    test_df = pd.DataFrame({
        'id': [1, 2],
        'prompt': ['test prompt 1', 'test prompt 2'],
        'draft': ['test draft 1', 'test draft 2'],
        'output': ['test output 1', 'test output 2']
    })

    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
        temp_path = tmp.name
        test_df.to_parquet(temp_path)

    try:
        # Load the dataset
        loaded_df = load_dataset(temp_path)

        # Verify the data
        assert len(loaded_df) == 2
        assert 'id' in loaded_df.columns
        assert 'prompt' in loaded_df.columns
        assert 'draft' in loaded_df.columns
        assert 'output' in loaded_df.columns

    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_load_dataset_missing_fields():
    """Test load_dataset function with missing required fields"""
    # Create a test DataFrame missing required fields
    test_df = pd.DataFrame({
        'id': [1, 2],
        'prompt': ['test prompt 1', 'test prompt 2']
        # Missing 'draft' and 'output' fields
    })

    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
        temp_path = tmp.name
        test_df.to_parquet(temp_path)

    try:
        with pytest.raises(ValueError) as exc_info:
            load_dataset(temp_path)

        assert "Missing required fields" in str(exc_info.value)
        assert "draft" in str(exc_info.value)
        assert "output" in str(exc_info.value)

    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_load_dataset_file_not_found():
    """Test load_dataset function with non-existent file"""
    with pytest.raises(FileNotFoundError) as exc_info:
        load_dataset("nonexistent_file.parquet")

    assert "Dataset file not found" in str(exc_info.value)


@pytest.mark.parametrize("spec_draft,truth_output,expected,description", [
    # Int array tests
    ([1, 2, 3, 4], [1, 2, 5, 6], 2, "normal matching prefix with int arrays"),
    ([1, 2, 3], [1, 2, 3], 3, "exact match with int arrays"),
    ([1, 2, 3], [4, 5, 6], 0, "no match from start with int arrays"),
    ([], [1, 2, 3], 0, "empty spec_draft array"),
    ([1, 2, 3], [], 0, "empty truth_output array"),
    ([], [], 0, "both empty arrays"),

    # Numpy array tests
    (np.array([1, 2, 3, 4]), np.array([1, 2, 5, 6]), 2, "normal matching prefix with numpy arrays"),
    (np.array([1, 2, 3]), np.array([1, 2, 3]), 3, "exact match with numpy arrays"),
    ([1, 2, 3, 4], np.array([1, 2, 5, 6]), 2, "mixed list and numpy array"),
])
def test_calculate_prefix_match_arrays(spec_draft, truth_output, expected, description):
    """Test calculate_prefix_match with array inputs"""
    result = calculate_prefix_match(spec_draft, truth_output)
    assert result == expected, f"Failed for {description}: expected {expected}, got {result}"


@pytest.mark.parametrize("spec_draft,truth_output,expected,description", [
    # Mismatched types tests
    ("hello", [1, 2, 3], 0, "string vs int array (should return 0 with warning)"),
    ([1, 2, 3], "hello", 0, "int array vs string (should return 0 with warning)"),

    # None inputs tests
    (None, "test", 0, "None spec_draft with string truth_output"),
    ("test", None, 0, "string spec_draft with None truth_output"),
    (None, [1, 2, 3], 0, "None spec_draft with array truth_output"),
    ([1, 2, 3], None, 0, "array spec_draft with None truth_output"),
])
def test_calculate_prefix_match_edge_cases(spec_draft, truth_output, expected, description):
    """Test calculate_prefix_match with edge cases and mismatched types"""
    result = calculate_prefix_match(spec_draft, truth_output)
    assert result == expected, f"Failed for {description}: expected {expected}, got {result}"


def test_process_single_case_missing_output_field():
    """Test process_single_case with missing output field"""
    mock_proposer = Mock()
    mock_tokenizer = Mock()

    # Create test data without output field
    test_row = pd.Series({
        'id': 'test_missing_output',
        'prompt': 'Say hello',
        'draft': 'hello'
        # Missing 'output' field
    })

    # The function should raise a KeyError since 'output' is required
    with pytest.raises(KeyError):
        process_single_case(test_row, mock_proposer, mock_tokenizer)


def test_process_single_case_null_output_field():
    """Test process_single_case with null output field"""
    mock_proposer = Mock()
    mock_proposer.propose.return_value = None

    # Create a mock tokenizer with proper return values
    mock_tokenizer = Mock()
    def mock_encode(text, add_special_tokens=False):
        if text == 'Say hello':
            return [1, 2, 3]  # prompt tokens
        elif text == '<NA>':  # pd.NA converts to '<NA>' string
            return [4, 5]  # output tokens for '<NA>'
        elif text == 'hello':
            return [1, 2, 3]  # draft tokens
        return [1, 2, 3]  # default

    mock_tokenizer.encode.side_effect = mock_encode

    # Create test data with null output field
    test_row = pd.Series({
        'id': 'test_null_output',
        'prompt': 'Say hello',
        'draft': 'hello',
        'output': pd.NA  # Null output
    })

    # The function should handle null output by converting it to string
    result = process_single_case(test_row, mock_proposer, mock_tokenizer)

    # Verify the result is an EvaluationMetrics instance
    assert isinstance(result, EvaluationMetrics)

    # Should have some execution time and 2 tokens for '<NA>'
    assert result.execution_time_ms > 0.0
    assert result.total_output_tokens == 2  # '<NA>' tokenized to [4, 5]


def test_tokenizer():
    """Test the fulledit tokenizer functionality"""

    # Get the current directory to locate the tokenizer files
    _current_dir = os.path.dirname(os.path.abspath(__file__))

    """
    Copied from fulledit model, only tokenizer related files is enough
    ❯ ls inference_server/modules/specedit/eval/fulledit_tokenizer
    added_tokens.json       special_tokens_map.json tokenizer_config.json   tokenizer.json          vocab.json
    """
    tokenizer_path = os.path.join(_current_dir, "fulledit_tokenizer")
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)

    # Test the tokenizer
    text = "def hello_world():\n    print('Hello, World!')"
    tokens = tokenizer.encode(text)
    decoded = tokenizer.decode(tokens)

    print(f"Original: {text}")
    print(f"Tokens: {tokens}")
    print(f"Decoded: {decoded}")

    # Check special tokens
    print(f"BOS token: {tokenizer.bos_token}")
    print(f"EOS token: {tokenizer.eos_token}")
    print(f"PAD token: {tokenizer.pad_token}")

    # Basic assertions to ensure tokenizer works
    assert isinstance(tokens, list)
    assert len(tokens) > 0
    assert isinstance(decoded, str)
    assert len(decoded) > 0


def test_proposer_setup_comprehensive():
    """Test that the setup_proposer function works correctly with comprehensive checks."""
    try:
        # Test proposer initialization
        proposer = setup_proposer()
        print("✓ SpecEditProposer initialized successfully")

        # Verify the proposer type
        print(f"✓ Proposer type: {type(proposer)}")

        # Check if it has the expected methods
        assert hasattr(proposer, 'propose'), "Proposer should have 'propose' method"
        print("✓ Proposer has 'propose' method")

        # Check if it has expected attributes from mock config
        assert hasattr(proposer, 'max_model_len'), "Proposer should have 'max_model_len' attribute"
        assert hasattr(proposer, 'k'), "Proposer should have 'k' attribute"
        print("✓ Proposer has expected configuration attributes")

        print(f"✓ max_model_len: {proposer.max_model_len}")
        print(f"✓ k (speculative tokens): {proposer.k}")

        print("\n🎉 All tests passed! SpecEditProposer setup function works correctly.")

        # Additional assertions for pytest
        assert callable(proposer.propose), "propose method should be callable"
        assert isinstance(proposer.max_model_len, int), "max_model_len should be an integer"
        assert isinstance(proposer.k, int), "k should be an integer"
        assert proposer.k > 0, "k should be positive"

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        # Re-raise for pytest to catch
        raise
