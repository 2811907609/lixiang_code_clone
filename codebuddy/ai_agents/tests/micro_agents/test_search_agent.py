import pytest
import os
import logging

from ai_agents.micro_agents.search_agent import SearchAgent
from ai_agents.config import config
from tests.test_config import skip_if_no_llm_config

# Silence debug logs from markdown_it and other verbose libraries
logging.getLogger('markdown_it').setLevel(logging.WARNING)
logging.getLogger('smolagents').setLevel(logging.WARNING)
logging.getLogger('openai').setLevel(logging.WARNING)


@pytest.mark.llm
class TestSearchAgentRun:
    """Test the SearchAgent run method with real LLM and search functionality"""

    def setup_method(self):
        """Setup test environment before each test"""
        # Skip tests if no API configuration is available
        skip_if_no_llm_config()

        # Get repository path from environment variable
        self.test_repo_path = os.getenv("TEST_REPO_PATH", os.getcwd())

    def test_search_agent_initialization(self):
        """Test SearchAgent can be initialized using model manager"""
        # Create SearchAgent using model manager (default behavior)
        agent = SearchAgent()

        # Verify initialization
        assert agent._model is not None
        assert agent._agent is not None
        assert hasattr(agent, 'run')

        # Verify tools are available
        tools = agent.toolsets()
        assert len(tools) == 2  # search_keyword_in_directory, search_keyword_with_context

    def test_search_agent_without_model_manager(self):
        """Test SearchAgent can be initialized without model manager"""
        agent = SearchAgent()

        # Verify initialization
        assert agent._model is None
        assert agent._agent is not None
        assert hasattr(agent, 'run')

        # Verify tools are available
        tools = agent.toolsets()
        assert len(tools) == 2

    def test_run_method_basic_search(self):
        """Test the run method with a basic search task"""
        agent = SearchAgent()  # Use model manager

        task = f"Search for the word 'SearchAgent' in the directory {self.test_repo_path}"

        try:
            result = agent.run(task)

            # Verify we got a response
            assert isinstance(result, str)
            assert len(result) > 0

            # The result should mention finding SearchAgent or searching
            result_lower = result.lower()
            assert any(keyword in result_lower for keyword in ['search', 'found', 'file', 'directory'])

        except Exception as e:
            pytest.fail(f"SearchAgent run method failed: {e}")

    def test_run_method_search_with_context(self):
        """Test the run method with a context search task"""
        agent = SearchAgent()  # Use model manager

        task = f"Search for Python function definitions (keyword 'def') in {self.test_repo_path} and show me some context around the matches"

        try:
            result = agent.run(task)

            # Verify we got a response
            assert isinstance(result, str)
            assert len(result) > 0

            # The result should mention functions or definitions
            result_lower = result.lower()
            assert any(keyword in result_lower for keyword in ['def', 'function', 'found', 'context'])

        except Exception as e:
            pytest.fail(f"SearchAgent context search failed: {e}")

    def test_run_method_file_extension_filter(self):
        """Test the run method with file extension filtering"""
        agent = SearchAgent()  # Use model manager

        task = f"Search for 'import' statements only in Python files (.py) in the directory {self.test_repo_path}"

        try:
            result = agent.run(task)

            # Verify we got a response
            assert isinstance(result, str)
            assert len(result) > 0

            # The result should mention imports or Python files
            result_lower = result.lower()
            assert any(keyword in result_lower for keyword in ['import', 'python', '.py', 'found'])

        except Exception as e:
            pytest.fail(f"SearchAgent file extension search failed: {e}")

    def test_run_method_no_matches(self):
        """Test the run method when no matches are found"""
        agent = SearchAgent()  # Use model manager

        # Search for something that likely doesn't exist
        task = f"Search for the word 'ThisShouldNotExistAnywhere12345' in the directory {self.test_repo_path}"

        try:
            result = agent.run(task)

            # Verify we got a response
            assert isinstance(result, str)
            assert len(result) > 0

            # The result should indicate no matches were found
            result_lower = result.lower()
            assert any(keyword in result_lower for keyword in ['no matches', 'not found', 'no results', 'nothing found'])

        except Exception as e:
            pytest.fail(f"SearchAgent no matches test failed: {e}")

    def test_run_method_without_model(self):
        """Test that run method fails gracefully without a model"""
        agent = SearchAgent()  # No model provided

        task = f"Search for 'test' in {self.test_repo_path}"

        # Without a model, the agent should raise an error or handle it gracefully
        with pytest.raises((AttributeError, ValueError, TypeError, RuntimeError)):
            agent.run(task)




@pytest.mark.llm
class TestSearchAgentRunAdvanced:
    """Advanced tests for SearchAgent run method"""

    def setup_method(self):
        """Setup test environment"""
        # Skip tests if no API configuration is available
        skip_if_no_llm_config()

        self.test_repo_path = os.getenv("TEST_REPO_PATH", os.getcwd())

    @pytest.mark.slow
    def test_run_method_complex_task(self):
        """Test the run method with a complex search task"""
        agent = SearchAgent()  # Use model manager

        task = f"""
        Please help me analyze the codebase in {self.test_repo_path}:
        1. Search for all Python class definitions
        2. Find any TODO comments
        3. Look for import statements
        Provide a summary of what you find.
        """

        try:
            result = agent.run(task)

            # Verify we got a response
            assert isinstance(result, str)
            assert len(result) > 0

            # The result should mention classes, TODOs, or imports
            result_lower = result.lower()
            assert any(keyword in result_lower for keyword in ['class', 'todo', 'import', 'found', 'search'])

        except Exception as e:
            pytest.fail(f"Complex search task failed: {e}")

    @pytest.mark.slow
    def test_run_method_multiple_calls(self):
        """Test calling the run method multiple times with the same agent"""
        agent = SearchAgent()  # Use model manager

        tasks = [
            f"Search for 'def' in {self.test_repo_path}",
            f"Search for 'class' in {self.test_repo_path}",
            f"Search for 'import' in {self.test_repo_path}"
        ]

        results = []
        for task in tasks:
            try:
                result = agent.run(task)
                assert isinstance(result, str)
                assert len(result) > 0
                results.append(result)
            except Exception as e:
                pytest.fail(f"Multiple calls test failed on task '{task}': {e}")

        # Verify we got different results for different searches
        assert len(results) == 3
        assert all(isinstance(r, str) and len(r) > 0 for r in results)

    @pytest.mark.slow
    def test_run_method_error_handling(self):
        """Test run method error handling with invalid directory"""
        agent = SearchAgent()  # Use model manager

        task = "Search for 'test' in /this/directory/does/not/exist"

        try:
            result = agent.run(task)

            # The agent should handle the error gracefully and report it
            assert isinstance(result, str)
            assert len(result) > 0

            # The result should indicate an error or problem
            result_lower = result.lower()
            assert any(keyword in result_lower for keyword in ['error', 'not found', 'does not exist', 'invalid', 'failed'])

        except Exception as e:
            # It's also acceptable for the method to raise an exception
            assert "does not exist" in str(e).lower() or "not found" in str(e).lower()

    def test_run_method_return_type(self):
        """Test that run method returns the correct type"""
        agent = SearchAgent()  # Use model manager

        # Test with a simple task
        task = f"Search for 'test' in {self.test_repo_path}"

        try:
            result = agent.run(task)

            # Should return a string
            assert isinstance(result, str)

        except Exception as e:
            pytest.fail(f"Run method type test failed: {e}")

    @pytest.mark.parametrize("search_term", ["def", "class", "import", "pytest"])
    @pytest.mark.slow
    def test_run_method_different_search_terms(self, search_term):
        """Test run method with different search terms"""
        agent = SearchAgent()  # Use model manager

        task = f"Search for '{search_term}' in Python files in {self.test_repo_path}"

        try:
            result = agent.run(task)

            assert isinstance(result, str)
            assert len(result) > 0

            # Result should mention the search term or searching
            result_lower = result.lower()
            assert search_term.lower() in result_lower or 'search' in result_lower

        except Exception as e:
            pytest.fail(f"Parameterized search test failed for '{search_term}': {e}")

    @pytest.mark.slow
    def test_run_method_file_creation(self):
        """Test the run method with file creation task"""
        agent = SearchAgent()  # Use model manager

        # Use a temporary directory for file creation
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            task = f"Create a new Python file called 'example.py' in {temp_dir} with a simple hello world function"

            try:
                result = agent.run(task)

                # Verify we got a response
                assert isinstance(result, str)
                assert len(result) > 0

                # The result should mention file creation
                result_lower = result.lower()
                assert any(keyword in result_lower for keyword in ['created', 'file', 'example.py', 'python'])

            except Exception as e:
                pytest.fail(f"File creation test failed: {e}")

    @pytest.mark.slow
    def test_run_method_search_and_create(self):
        """Test the run method with both search and file creation"""
        agent = SearchAgent()  # Use model manager

        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            task = f"""
            Please help me:
            1. Search for Python class definitions in {self.test_repo_path}
            2. Create a summary file called 'classes_found.txt' in {temp_dir} with the results
            """

            try:
                result = agent.run(task)

                # Verify we got a response
                assert isinstance(result, str)
                assert len(result) > 0

                # The result should mention both searching and creating
                result_lower = result.lower()
                assert any(keyword in result_lower for keyword in ['search', 'class', 'found'])
                assert any(keyword in result_lower for keyword in ['created', 'file', 'summary'])

            except Exception as e:
                pytest.fail(f"Search and create test failed: {e}")


@pytest.mark.unit
class TestSearchAgentUnit:
    """Unit tests for SearchAgent (no LLM calls)"""

    def test_config_values(self):
        """Test that config provides the necessary values"""
        # Test that config has the required attributes
        assert hasattr(config, 'LLM_API_BASE')
        assert hasattr(config, 'LLM_API_KEY')

        # Test that values are strings
        assert isinstance(config.LLM_API_BASE, str)
        assert isinstance(config.LLM_API_KEY, str)

    def test_environment_repo_path(self):
        """Test that we can get repository path from environment"""
        repo_path = os.getenv("TEST_REPO_PATH", os.getcwd())

        # Should be a valid directory path
        assert isinstance(repo_path, str)
        assert len(repo_path) > 0

        # Should be an existing directory
        assert os.path.isdir(repo_path)

    def test_search_agent_toolsets(self):
        """Test that _get_tools returns actual working functions"""
        agent = SearchAgent()  # No model needed for toolsets
        tools = agent._get_tools()

        # Verify we have the expected number of tools
        assert len(tools) == 7  # Updated count based on actual tools

        # Verify tools are callable
        for tool in tools:
            assert callable(tool)

        # Verify tools have the expected names
        tool_names = []
        for tool in tools:
            tool_names.append(tool.name)

        assert "search_keyword_in_directory" in tool_names
        assert "search_keyword_with_context" in tool_names
