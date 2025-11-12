import json
import re
from typing import Any, Dict

import fire
import pandas as pd
from commonlibs.encoding import yaml_dump
from datasets import load_dataset


def load_swebench_data() -> pd.DataFrame:
    """Load SWE-bench Verified dataset and convert to DataFrame."""
    ds = load_dataset("princeton-nlp/SWE-bench_Verified")
    return pd.DataFrame(ds['test'])


def analyze_repo_distribution(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze repository distribution in the dataset."""
    repo_counts = df['repo'].value_counts()

    analysis = {
        'total_repos': len(repo_counts),
        'total_instances': len(df),
        'repo_distribution': repo_counts.to_dict(),
        'top_10_repos': repo_counts.head(10).to_dict(),
        'avg_instances_per_repo': repo_counts.mean(),
        'median_instances_per_repo': repo_counts.median(),
    }

    return analysis


def analyze_date_distribution(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze date patterns in the dataset."""
    df['created_at_parsed'] = pd.to_datetime(df['created_at'])
    df['year'] = df['created_at_parsed'].dt.year
    df['month'] = df['created_at_parsed'].dt.month
    df['day_of_week'] = df['created_at_parsed'].dt.day_name()

    analysis = {
        'date_range': {
            'earliest': df['created_at_parsed'].min(),
            'latest': df['created_at_parsed'].max()
        },
        'year_distribution': df['year'].value_counts().sort_index().to_dict(),
        'month_distribution': df['month'].value_counts().sort_index().to_dict(),
        'day_of_week_distribution': df['day_of_week'].value_counts().to_dict(),
        'instances_per_year': df.groupby('year').size().to_dict()
    }

    return analysis


def analyze_problem_complexity(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze problem complexity indicators."""
    analysis = {
        'problem_statement_lengths': {
            'avg_length': df['problem_statement'].str.len().mean(),
            'median_length': df['problem_statement'].str.len().median(),
            'max_length': df['problem_statement'].str.len().max(),
            'min_length': df['problem_statement'].str.len().min()
        },
        'patch_lengths': {
            'avg_length': df['patch'].str.len().mean(),
            'median_length': df['patch'].str.len().median(),
            'max_length': df['patch'].str.len().max(),
            'min_length': df['patch'].str.len().min()
        }
    }

    return analysis


def analyze_test_characteristics(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze test-related characteristics."""
    analysis = {
        'test_patch_lengths': {
            'avg_length': df['test_patch'].str.len().mean(),
            'median_length': df['test_patch'].str.len().median(),
            'max_length': df['test_patch'].str.len().max(),
            'min_length': df['test_patch'].str.len().min()
        },
        'files_modified': {
            'avg_files': df['patch'].apply(lambda x: len(re.findall(r'diff --git', x))).mean(),
            'median_files': df['patch'].apply(lambda x: len(re.findall(r'diff --git', x))).median(),
            'max_files': df['patch'].apply(lambda x: len(re.findall(r'diff --git', x))).max()
        }
    }

    return analysis


def analyze_language_patterns(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze programming language patterns based on repo names and patches."""
    language_indicators = {
        'python': ['.py', 'python', 'django', 'flask', 'pytest'],
        'javascript': ['.js', '.ts', 'node', 'npm', 'jest'],
        'java': ['.java', 'maven', 'gradle', 'junit'],
        'c++': ['.cpp', '.hpp', '.cc', 'cmake'],
        'go': ['.go', 'golang'],
        'rust': ['.rs', 'cargo'],
        'ruby': ['.rb', 'gem', 'rails']
    }

    language_counts = {}
    for lang, indicators in language_indicators.items():
        count = 0
        for indicator in indicators:
            count += df['patch'].str.contains(indicator, case=False).sum()
            count += df['repo'].str.contains(indicator, case=False).sum()
        language_counts[lang] = count

    return {
        'language_distribution': language_counts,
        'most_common_language': max(language_counts, key=language_counts.get)
    }


def analyze_issue_types(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze types of issues based on problem statements."""
    issue_keywords = {
        'bug_fix': ['bug', 'fix', 'error', 'issue', 'problem', 'broken'],
        'feature': ['feature', 'add', 'implement', 'new'],
        'performance': ['performance', 'speed', 'optimize', 'slow', 'fast'],
        'refactor': ['refactor', 'clean', 'reorganize', 'restructure'],
        'documentation': ['doc', 'documentation', 'readme', 'comment'],
        'test': ['test', 'testing', 'unittest', 'pytest']
    }

    issue_counts = {}
    for issue_type, keywords in issue_keywords.items():
        count = 0
        for keyword in keywords:
            count += df['problem_statement'].str.contains(keyword, case=False).sum()
        issue_counts[issue_type] = count

    return {
        'issue_type_distribution': issue_counts,
        'most_common_issue_type': max(issue_counts, key=issue_counts.get)
    }


def generate_comprehensive_report(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate a comprehensive analysis report."""
    report = {
        'dataset_overview': {
            'total_instances': len(df),
            'unique_repos': df['repo'].nunique(),
            'unique_instances': df['instance_id'].nunique()
        },
        'repo_analysis': analyze_repo_distribution(df),
        'date_analysis': analyze_date_distribution(df),
        'complexity_analysis': analyze_problem_complexity(df),
        'test_analysis': analyze_test_characteristics(df),
        'language_analysis': analyze_language_patterns(df),
        'issue_type_analysis': analyze_issue_types(df)
    }

    return report




class SWEBenchAnalyzer:
    """SWE-bench Verified dataset analyzer CLI tool."""

    def __init__(self):
        self._df = None

    def _load_data(self) -> pd.DataFrame:
        """Lazy load the dataset."""
        if self._df is None:
            print("Loading SWE-bench Verified dataset...")
            self._df = load_swebench_data()
        return self._df

    def analyze(self, output_file: str = None):
        """
        Run comprehensive analysis on SWE-bench Verified dataset.

        Args:
            output_file: Optional file path to save the report (JSON format)
        """
        df = self._load_data()

        print("Generating comprehensive analysis...")
        report = generate_comprehensive_report(df)

        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"Report saved to {output_file}")
        else:
            print("\n" + "="*50)
            print("SWE-BENCH VERIFIED ANALYSIS REPORT")
            print("="*50)
            print(json.dumps(report, indent=2, default=str))

        print("Analysis complete!")

    def recent_items(self, repo: str=None, n: int = 10, output_file: str = None, random_seed: int = None):
        """
        Get recent N items from a specific repository, or random N items if random_seed is provided.

        Args:
            repo: Repository name (e.g., 'django/django')
            n: Number of items to retrieve (default: 10)
            output_file: Optional file path to save the items (YAML format)
            random_seed: If provided, select random items instead of recent items.
                         Using the same seed will produce the same results. (default: None)
        """
        df = self._load_data()

        # Filter by repository
        if repo:
            original_df = df.copy()  # Keep reference to original data
            df = df[df['repo'] == repo].copy()

        if df.empty:
            print(f"No items found for repository: {repo}")
            available_repos = original_df['repo'].unique()[:10]
            print(f"Available repositories (first 10): {list(available_repos)}")
            return

        # Select items based on whether random_seed is provided
        if random_seed is not None:
            # Random selection with fixed seed for reproducibility
            repo_df_sampled = df.sample(n=min(n, len(df)), random_state=random_seed)
            selected_df = repo_df_sampled
        else:
            # Sort by created_at and get recent N items
            df['created_at_parsed'] = pd.to_datetime(df['created_at'])
            selected_df = df.sort_values('created_at_parsed', ascending=False).head(n)

        # Convert to YAML-friendly format, including all original fields
        items = []
        for _, row in selected_df.iterrows():
            item = row.to_dict()
            # Convert datetime objects to strings for YAML serialization
            for key, value in item.items():
                if pd.api.types.is_datetime64_any_dtype(type(value)) or hasattr(value, 'strftime'):
                    item[key] = str(value)
            # Add computed metadata
            item['_metadata'] = {
                'patch_length': len(row['patch']),
                'test_patch_length': len(row['test_patch']),
                'files_modified': len(re.findall(r'diff --git', row['patch'])),
                'problem_statement_length': len(row['problem_statement']),
                'hints_length': len(row['hints_text']) if pd.notna(row['hints_text']) else 0
            }
            items.append(item)

        result = {
            'repository': repo,
            'total_items_in_repo': len(df),
            'requested_items': n,
            'returned_items': len(items),
            'items': items
        }

        if output_file:
            with open(output_file, 'w') as f:
                yaml_dump(result, f)
            print(f"Selected {len(items)} items from {repo} saved to {output_file}")
        else:
            print(f"\n{'-'*60}")
            mode = "RANDOM" if random_seed is not None else "RECENT"
            print(f"{mode} {len(items)} ITEMS FROM {repo}")
            print(f"{'-'*60}")
            print(yaml_dump(result))

    def list_repos(self, limit: int = 20):
        """
        List available repositories with their instance counts.

        Args:
            limit: Number of repositories to show (default: 20)
        """
        df = self._load_data()

        repo_counts = df['repo'].value_counts().head(limit)

        print(f"\nTop {limit} repositories by instance count:")
        print("-" * 50)
        for repo, count in repo_counts.items():
            print(f"{repo:<40} {count:>8}")

        print(f"\nTotal repositories: {df['repo'].nunique()}")
        print(f"Total instances: {len(df)}")

    def get_item(self, instance_id: str = None, index: int = None, repo: str = None):
        """
        Get and pretty print a single item from the dataset.

        Args:
            instance_id: Specific instance ID to retrieve
            index: Row index to retrieve (0-based)
            repo: If provided with index, get the Nth item from this repo
        """
        df = self._load_data()

        if instance_id:
            # Get by instance_id
            item_df = df[df['instance_id'] == instance_id]
            if item_df.empty:
                print(f"No item found with instance_id: {instance_id}")
                return
            row = item_df.iloc[0]
        elif repo and index is not None:
            # Get Nth item from specific repo
            repo_df = df[df['repo'] == repo]
            if repo_df.empty:
                print(f"No items found for repository: {repo}")
                return
            if index >= len(repo_df):
                print(f"Index {index} out of range. Repository {repo} has {len(repo_df)} items.")
                return
            row = repo_df.iloc[index]
        elif index is not None:
            # Get by global index
            if index >= len(df):
                print(f"Index {index} out of range. Dataset has {len(df)} items.")
                return
            row = df.iloc[index]
        else:
            # Get random item
            row = df.sample(1).iloc[0]
            print("(Showing random item since no specific item was requested)")

        # Convert pandas Series to dict with all original keys
        item_dict = row.to_dict()

        # Add metadata without modifying original data
        metadata = {
            'patch_length': len(row['patch']),
            'test_patch_length': len(row['test_patch']),
            'files_modified': len(re.findall(r'diff --git', row['patch'])),
            'problem_statement_length': len(row['problem_statement']),
            'hints_length': len(row['hints_text']) if pd.notna(row['hints_text']) else 0
        }
        item_dict['_metadata'] = metadata

        print(f"\n{'='*80}")
        print(f"SWE-BENCH ITEM: {row['instance_id']}")
        print(f"{'='*80}")
        print(yaml_dump(item_dict))


if __name__ == "__main__":
    fire.Fire(SWEBenchAnalyzer)
