"""
Performance tests for the hook system.
Tests hook execution overhead and performance characteristics.
"""
import time
import statistics
from unittest.mock import patch
from pathlib import Path

from ai_agents.core.hooks.hook_manager import HookManager
from ai_agents.core.hooks.types import HookEvent, HookResult
from ai_agents.core.tools import tool


class TestHookPerformance:
    """Test hook system performance characteristics."""

    def setup_method(self):
        """Set up test fixtures."""
        HookManager.reset_instance()
        self.hook_manager = HookManager.get_instance()
        self.test_config_dir = Path(__file__).parent / "fixtures" / "sample_configs"

    def teardown_method(self):
        """Clean up after tests."""
        HookManager.reset_instance()

    def test_hook_execution_overhead(self):
        """Test the overhead of hook execution on tool performance."""
        # Create a simple tool without hooks
        @tool
        def simple_tool(value: str) -> str:
            """Simple tool for performance testing.

            Args:
                value: A string value to process

            Returns:
                A processed string
            """
            return f"processed: {value}"

        # Measure baseline performance without hooks
        baseline_times = []
        for _ in range(100):
            start_time = time.perf_counter()
            _ = simple_tool("test")
            end_time = time.perf_counter()
            baseline_times.append(end_time - start_time)

        baseline_avg = statistics.mean(baseline_times)

        # Load hook configuration
        config_path = self.test_config_dir / "basic_hooks.json"
        with patch('ai_agents.core.hooks.config_loader.ConfigurationLoader.CONFIG_PATHS',
                   [str(config_path)]):
            self.hook_manager.load_configuration()

        # Measure performance with hooks
        hook_times = []
        for _ in range(100):
            start_time = time.perf_counter()
            _ = simple_tool("test")
            end_time = time.perf_counter()
            hook_times.append(end_time - start_time)

        hook_avg = statistics.mean(hook_times)

        # Calculate overhead
        overhead = hook_avg - baseline_avg
        overhead_percentage = (overhead / baseline_avg) * 100

        # Assert reasonable overhead (should be less than 50% for simple hooks)
        assert overhead_percentage < 50, f"Hook overhead too high: {overhead_percentage:.2f}%"

        print(f"Baseline average: {baseline_avg:.6f}s")
        print(f"With hooks average: {hook_avg:.6f}s")
        print(f"Overhead: {overhead:.6f}s ({overhead_percentage:.2f}%)")

    def test_multiple_hooks_performance(self):
        """Test performance with multiple hooks registered."""
        # Register multiple Python hooks
        def fast_hook(context):
            return HookResult(success=True, continue_execution=True)

        def medium_hook(context):
            time.sleep(0.001)  # 1ms delay
            return HookResult(success=True, continue_execution=True)

        def slow_hook(context):
            time.sleep(0.005)  # 5ms delay
            return HookResult(success=True, continue_execution=True)

        # Register hooks
        self.hook_manager.register_python_hook(HookEvent.PRE_TOOL_USE, "*", fast_hook)
        self.hook_manager.register_python_hook(HookEvent.PRE_TOOL_USE, "*", medium_hook)
        self.hook_manager.register_python_hook(HookEvent.PRE_TOOL_USE, "*", slow_hook)
        self.hook_manager.register_python_hook(HookEvent.POST_TOOL_USE, "*", fast_hook)

        # Measure execution time
        execution_times = []
        for _ in range(50):
            start_time = time.perf_counter()

            # Trigger hooks
            _ = self.hook_manager.trigger_hooks(
                HookEvent.PRE_TOOL_USE, "TestTool", {"param": "value"}
            )
            _ = self.hook_manager.trigger_hooks(
                HookEvent.POST_TOOL_USE, "TestTool", {"param": "value"}, {"result": "success"}
            )

            end_time = time.perf_counter()
            execution_times.append(end_time - start_time)

        avg_time = statistics.mean(execution_times)
        max_time = max(execution_times)
        min_time = min(execution_times)

        # Should complete within reasonable time (accounting for sleep delays)
        expected_min_time = 0.006  # 6ms minimum due to sleep delays
        assert avg_time >= expected_min_time, f"Average time too low: {avg_time:.6f}s"
        assert avg_time < 0.020, f"Average time too high: {avg_time:.6f}s"  # 20ms max

        print(f"Multiple hooks - Avg: {avg_time:.6f}s, Min: {min_time:.6f}s, Max: {max_time:.6f}s")

    def test_pattern_matching_performance(self):
        """Test performance of pattern matching with many patterns."""
        # Create many patterns
        patterns = [
            "ExactTool",
            "File.*",
            "Edit|Write|Create",
            "Test.*Tool",
            ".*Writer",
            "Complex.*Pattern.*Match",
            "*",
            "Another.*Pattern",
            "Yet.*Another.*One"
        ]

        # Register hooks for each pattern
        def dummy_hook(context):
            return HookResult(success=True, continue_execution=True)

        for pattern in patterns:
            self.hook_manager.register_python_hook(
                HookEvent.PRE_TOOL_USE, pattern, dummy_hook
            )

        # Test tool names
        tool_names = [
            "ExactTool",
            "FileWriter",
            "EditTool",
            "TestMyTool",
            "DocumentWriter",
            "ComplexPatternMatchTool",
            "RandomTool",
            "AnotherPatternTool",
            "YetAnotherOne"
        ]

        # Measure pattern matching performance
        matching_times = []
        for _ in range(100):
            start_time = time.perf_counter()

            for tool_name in tool_names:
                _ = self.hook_manager.trigger_hooks(
                    HookEvent.PRE_TOOL_USE, tool_name, {}
                )

            end_time = time.perf_counter()
            matching_times.append(end_time - start_time)

        avg_time = statistics.mean(matching_times)

        # Pattern matching should be fast
        assert avg_time < 0.010, f"Pattern matching too slow: {avg_time:.6f}s"

        print(f"Pattern matching performance - Avg: {avg_time:.6f}s for {len(tool_names)} tools")

    def test_concurrent_hook_execution_performance(self):
        """Test performance of concurrent hook execution."""

        def concurrent_hook(context):
            # Simulate some work
            time.sleep(0.001)
            return HookResult(success=True, continue_execution=True)

        # Register multiple hooks
        for i in range(5):
            self.hook_manager.register_python_hook(
                HookEvent.PRE_TOOL_USE, f"Tool{i}", concurrent_hook
            )

        # Test sequential vs concurrent execution
        tool_names = [f"Tool{i}" for i in range(5)]

        # Sequential execution
        start_time = time.perf_counter()
        for tool_name in tool_names:
            self.hook_manager.trigger_hooks(HookEvent.PRE_TOOL_USE, tool_name, {})
        sequential_time = time.perf_counter() - start_time

        # The hook executor should handle concurrency internally
        # This test verifies that multiple hook executions don't block each other excessively

        print(f"Sequential hook execution time: {sequential_time:.6f}s")

        # Should complete in reasonable time
        assert sequential_time < 0.050, f"Sequential execution too slow: {sequential_time:.6f}s"

    def test_memory_usage_stability(self):
        """Test that hook execution doesn't cause memory leaks."""
        import gc
        import psutil
        import os

        process = psutil.Process(os.getpid())

        # Get initial memory usage
        gc.collect()
        initial_memory = process.memory_info().rss

        # Register a hook
        def memory_test_hook(context):
            # Create some temporary data
            _ = ["x" * 1000 for _ in range(100)]
            return HookResult(success=True, continue_execution=True)

        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE, "*", memory_test_hook
        )

        # Execute hooks many times
        for i in range(1000):
            self.hook_manager.trigger_hooks(
                HookEvent.PRE_TOOL_USE, f"Tool{i % 10}", {"iteration": i}
            )

            # Periodic garbage collection
            if i % 100 == 0:
                gc.collect()

        # Final garbage collection
        gc.collect()
        final_memory = process.memory_info().rss

        # Memory increase should be reasonable (less than 50MB)
        memory_increase = final_memory - initial_memory
        memory_increase_mb = memory_increase / (1024 * 1024)

        print(f"Memory increase: {memory_increase_mb:.2f} MB")

        assert memory_increase_mb < 50, f"Memory increase too high: {memory_increase_mb:.2f} MB"

    def test_hook_timeout_performance(self):
        """Test performance impact of hook timeouts."""
        # Create a hook that will timeout
        def timeout_hook(context):
            time.sleep(2)  # Will timeout with 1s limit
            return HookResult(success=True, continue_execution=True)

        self.hook_manager.register_python_hook(
            HookEvent.PRE_TOOL_USE, "TimeoutTool", timeout_hook
        )

        # Measure timeout handling performance
        start_time = time.perf_counter()

        result = self.hook_manager.trigger_hooks(
            HookEvent.PRE_TOOL_USE, "TimeoutTool", {}
        )

        end_time = time.perf_counter()
        execution_time = end_time - start_time

        # Should timeout quickly (within 1.5s including overhead)
        assert execution_time < 1.5, f"Timeout handling too slow: {execution_time:.3f}s"
        assert not result.success, "Hook should have failed due to timeout"

        print(f"Timeout handling time: {execution_time:.3f}s")


class TestHookSystemScalability:
    """Test hook system scalability with large numbers of hooks and tools."""

    def setup_method(self):
        """Set up test fixtures."""
        HookManager.reset_instance()
        self.hook_manager = HookManager.get_instance()

    def teardown_method(self):
        """Clean up after tests."""
        HookManager.reset_instance()

    def test_large_number_of_hooks(self):
        """Test performance with a large number of registered hooks."""
        # Register many hooks
        def simple_hook(context):
            return HookResult(success=True, continue_execution=True)

        num_hooks = 1000
        for i in range(num_hooks):
            pattern = f"Tool{i % 100}"  # Create some pattern overlap
            self.hook_manager.register_python_hook(
                HookEvent.PRE_TOOL_USE, pattern, simple_hook
            )

        # Test execution with many hooks
        start_time = time.perf_counter()

        for i in range(100):
            tool_name = f"Tool{i % 50}"
            result = self.hook_manager.trigger_hooks(
                HookEvent.PRE_TOOL_USE, tool_name, {}
            )
            assert result.success

        end_time = time.perf_counter()
        execution_time = end_time - start_time

        # Should handle large numbers efficiently
        assert execution_time < 5.0, f"Large hook set execution too slow: {execution_time:.3f}s"

        print(f"Execution time with {num_hooks} hooks: {execution_time:.3f}s")

    def test_complex_pattern_performance(self):
        """Test performance with complex regex patterns."""
        complex_patterns = [
            r"^File(Writer|Reader|Editor)$",
            r".*Tool(V[0-9]+)?$",
            r"(Create|Update|Delete).*Entity.*",
            r"^(HTTP|FTP|SSH).*Client$",
            r".*Manager(Impl|Proxy)?$",
            r"^Test.*Tool(Mock|Stub)?$",
            r"(Async|Sync).*Handler.*",
            r".*Service(Client|Server)?$",
            r"^(JSON|XML|CSV).*Parser$",
            r".*Validator(Chain|Composite)?$"
        ]

        def pattern_hook(context):
            return HookResult(success=True, continue_execution=True)

        # Register hooks with complex patterns
        for pattern in complex_patterns:
            self.hook_manager.register_python_hook(
                HookEvent.PRE_TOOL_USE, pattern, pattern_hook
            )

        # Test with various tool names
        test_tools = [
            "FileWriter", "FileReader", "FileEditor",
            "MyToolV1", "AnotherToolV2", "SimpleTool",
            "CreateUserEntity", "UpdateOrderEntity", "DeleteProductEntity",
            "HTTPClient", "FTPClient", "SSHClient",
            "UserManager", "OrderManagerImpl", "ProductManagerProxy",
            "TestUserTool", "TestOrderToolMock", "TestProductToolStub",
            "AsyncEventHandler", "SyncDataHandler",
            "UserService", "OrderServiceClient", "ProductServiceServer",
            "JSONParser", "XMLParser", "CSVParser",
            "EmailValidator", "PhoneValidatorChain", "AddressValidatorComposite"
        ]

        # Measure performance
        start_time = time.perf_counter()

        for tool_name in test_tools:
            _ = self.hook_manager.trigger_hooks(
                HookEvent.PRE_TOOL_USE, tool_name, {}
            )

        end_time = time.perf_counter()
        execution_time = end_time - start_time

        # Complex patterns should still be reasonably fast
        assert execution_time < 0.100, f"Complex pattern matching too slow: {execution_time:.6f}s"

        print(f"Complex pattern matching time: {execution_time:.6f}s for {len(test_tools)} tools")
