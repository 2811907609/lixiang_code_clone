import json
import os
from collections import defaultdict
from typing import Any, Dict, List

# Global variable to store classified data
CLASSIFIED_CASES: Dict[str, List[Dict[str, Any]]] = {}


def get_data_file_path() -> str:
    """
    Get the correct path to data.json file, compatible with different working directories

    Returns:
        str: Path to the data.json file
    """
    # Get the directory where this module is located
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Construct the absolute path to data.json in the same directory
    data_file_path = os.path.join(current_dir, 'data.json')

    # Check if data.json exists in the same directory as this module
    if os.path.exists(data_file_path):
        return data_file_path

    # Fallback: Check if data.json exists in current working directory
    if os.path.exists('data.json'):
        return os.path.abspath('data.json')

    # Fallback: Check workspace root relative path
    workspace_relative_path = 'ai_agents/modules/codedoggy/benchmark/data.json'
    if os.path.exists(workspace_relative_path):
        return os.path.abspath(workspace_relative_path)

    # If no path works, raise an error with detailed information
    raise FileNotFoundError(
        f"data.json file not found. Searched in:\n"
        f"1. Module directory: {data_file_path}\n"
        f"2. Current directory: {os.path.abspath('data.json')}\n"
        f"3. Workspace relative: {os.path.abspath(workspace_relative_path)}"
    )


def load_and_store_global_data(file_path: str) -> None:
    """
    Load JSON data and store it in global variable for access by other methods

    Args:
        file_path: Path to the JSON file
    """
    global CLASSIFIED_CASES
    CLASSIFIED_CASES = read_json_and_classify_by_repo(file_path)


def get_case_by_web_url(web_url: str) -> Dict[str, Any]:
    """
    Get a specific case by web_url from global data

    Args:
        web_url: The web_url to search for

    Returns:
        The case data if found, empty dict otherwise
    """
    for _, case_list in CLASSIFIED_CASES.items():
        for case in case_list:
            if case.get('input_context', {}).get('web_url') == web_url:
                return case
    return {}


def get_cases_by_repo(repo_name: str) -> List[Dict[str, Any]]:
    """
    Get all cases for a specific repo from global data

    Args:
        repo_name: The repository name

    Returns:
        List of cases for the repo
    """
    return CLASSIFIED_CASES.get(repo_name, [])


def read_json_and_classify_by_repo(file_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Read JSON file and classify data by repo_name

    Args:
        file_path: Path to the JSON file

    Returns:
        Dict classified by repo_name, key is repo_name, value is list of cases for that repo

    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file is not valid JSON
        ValueError: If the data structure is invalid
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Data file not found: {file_path}") from e
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON format in {file_path}: {e.msg}", e.doc, e.pos) from e
    except Exception as e:
        raise ValueError(f"Error reading data file {file_path}: {str(e)}") from e

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array in {file_path}, got {type(data).__name__}")

    classified_data = defaultdict(list)

    try:
        for i, case in enumerate(data):
            if not isinstance(case, dict):
                print(f"Warning: Skipping invalid case at index {i}: expected dict, got {type(case).__name__}")
                continue

            repo_name = case.get('input_context', {}).get('repo_name', 'unknown')
            classified_data[repo_name].append(case)
    except Exception as e:
        raise ValueError(f"Error processing data structure: {str(e)}") from e

    return dict(classified_data)
