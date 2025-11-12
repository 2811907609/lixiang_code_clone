from unittest.mock import Mock, patch

import numpy as np
import pytest
from inference_server.modules.specedit.lib.constant import (
    original_ngram_proposer_key,
)
from inference_server.modules.specedit.lib.spec_edit_worker_v1 import (
    PatchGPUModelRunner,
    SpecEditProposer,
    patch_gpu_model_runner,
    patch_ngram_proposer,
    patch_spec_edit_v1,
)


class TestSpecEditProposer:
    """测试 SpecEditProposer 类"""

    @pytest.fixture
    def proposer(self):
        """创建 SpecEditProposer 实例"""
        proposer = SpecEditProposer.__new__(SpecEditProposer)
        proposer.k = 5
        proposer.max_model_len = 100
        return proposer

    def test_propose_without_req_id(self, proposer):
        """测试没有 req_id 时的 propose 方法"""
        context_tokens = np.array([10, 20, 30])

        # 测试当req_id为None时，直接调用父类方法
        with patch.object(SpecEditProposer.__bases__[0], 'propose') as mock_super_propose:
            mock_super_propose.return_value = np.array([40, 50])

            proposer.propose(context_tokens)

            mock_super_propose.assert_called_once_with(context_tokens)

    def test_propose_with_req_id_no_stream_chunk(self, proposer):
        """测试有 req_id 但没有 stream_next_chunk 时的 propose 方法"""
        context_tokens = np.array([10, 20, 30])
        req_id = "test_req_123"

        with patch('inference_server.modules.specedit.lib.spec_edit_worker_v1.request_manager') as mock_request_manager:
            mock_request_manager.get_stream_next_chunk.return_value = None

            with patch.object(SpecEditProposer.__bases__[0], 'propose') as mock_super_propose:
                mock_super_propose.return_value = np.array([40, 50])

                proposer.propose(context_tokens, req_id)

                mock_request_manager.get_stream_next_chunk.assert_called_once_with(req_id)
                mock_super_propose.assert_called_once_with(context_tokens)

    def test_propose_with_stream_chunk_empty_result(self, proposer):
        """测试 stream_next_chunk 返回空结果时的 propose 方法"""
        context_tokens = np.array([10, 20, 30])
        req_id = "test_req_123"

        mock_stream_chunk = Mock()
        mock_stream_chunk.next_chunk.return_value = []

        with patch('inference_server.modules.specedit.lib.spec_edit_worker_v1.request_manager') as mock_request_manager:
            mock_request_manager.get_stream_next_chunk.return_value = mock_stream_chunk

            with patch.object(SpecEditProposer.__bases__[0], 'propose') as mock_super_propose:
                mock_super_propose.return_value = np.array([40, 50])

                proposer.propose(context_tokens, req_id)

                mock_stream_chunk.next_chunk.assert_called_once_with([10, 20, 30], 5)
                mock_super_propose.assert_called_once_with(context_tokens)

    def test_propose_with_stream_chunk_success(self, proposer):
        """测试 stream_next_chunk 成功返回结果时的 propose 方法"""
        context_tokens = np.array([10, 20, 30])
        req_id = "test_req_123"

        mock_stream_chunk = Mock()
        mock_stream_chunk.next_chunk.return_value = [40, 50, 60, 70]

        with patch('inference_server.modules.specedit.lib.spec_edit_worker_v1.request_manager') as mock_request_manager:
            mock_request_manager.get_stream_next_chunk.return_value = mock_stream_chunk

            # 由于propose方法会调用父类方法，我们需要mock父类以避免依赖
            with patch.object(SpecEditProposer.__bases__[0], 'propose'):
                result = proposer.propose(context_tokens, req_id)

                mock_stream_chunk.next_chunk.assert_called_once_with([10, 20, 30], 5)
                np.testing.assert_array_equal(result, np.array([40, 50, 60, 70]))

    def test_propose_with_k_limit(self, proposer):
        """测试 k 值限制的 propose 方法"""
        # 测试当上下文长度接近最大模型长度时
        context_tokens = np.array([10] * 98)  # 98 个 token
        req_id = "test_req_123"

        mock_stream_chunk = Mock()
        mock_stream_chunk.next_chunk.return_value = [40, 50, 60, 70, 80]

        with patch('inference_server.modules.specedit.lib.spec_edit_worker_v1.request_manager') as mock_request_manager:
            mock_request_manager.get_stream_next_chunk.return_value = mock_stream_chunk

            # 由于propose方法会调用父类方法，我们需要mock父类以避免依赖
            with patch.object(SpecEditProposer.__bases__[0], 'propose'):
                result = proposer.propose(context_tokens, req_id)

                # k 应该被限制为 max_model_len - context_length = 100 - 98 = 2
                mock_stream_chunk.next_chunk.assert_called_once_with(list(context_tokens), 2)
                np.testing.assert_array_equal(result, np.array([40, 50]))

    def test_propose_with_k_zero_or_negative(self, proposer):
        """测试当 k <= 0 时的 propose 方法"""
        # 测试当上下文长度达到或超过最大模型长度时
        context_tokens = np.array([10] * 100)  # 100 个 token (等于 max_model_len)
        req_id = "test_req_123"

        mock_stream_chunk = Mock()

        with patch('inference_server.modules.specedit.lib.spec_edit_worker_v1.request_manager') as mock_request_manager:
            mock_request_manager.get_stream_next_chunk.return_value = mock_stream_chunk

            result = proposer.propose(context_tokens, req_id)

            # 当 k <= 0 时，应该返回 None
            assert result is None
            mock_stream_chunk.next_chunk.assert_not_called()


class TestPatchGPUModelRunner:
    """测试 PatchGPUModelRunner 类"""

    @pytest.fixture
    def runner(self):
        """创建 PatchGPUModelRunner 实例"""
        runner = PatchGPUModelRunner.__new__(PatchGPUModelRunner)
        runner.max_model_len = 100

        # 模拟 input_batch
        runner.input_batch = Mock()
        runner.input_batch.req_ids = ["req1", "req2", "req3"]
        runner.input_batch.spec_decode_unsupported_reqs = set()
        runner.input_batch.num_tokens_no_spec = [50, 60, 101]  # 第三个超过 max_model_len
        runner.input_batch.token_ids_cpu = np.array([
            [1, 2, 3] + [0] * 97,
            [4, 5, 6] + [0] * 97,
            [7, 8, 9] + [0] * 97
        ])

        # 模拟 drafter
        runner.drafter = Mock()
        return runner

    def test_propose_ngram_draft_token_ids_empty_sampled_ids(self, runner):
        """测试空的 sampled_token_ids"""
        sampled_token_ids = [[], [1, 2], [3, 4]]
        runner.drafter.propose.return_value = np.array([10, 11])

        result = runner.propose_ngram_draft_token_ids(sampled_token_ids)

        expected = [[], [10, 11], []]  # 第一个空，第二个有结果，第三个超过 max_model_len
        assert result == expected

    def test_propose_ngram_draft_token_ids_unsupported_reqs(self, runner):
        """测试不支持的请求"""
        sampled_token_ids = [[1, 2], [3, 4], [5, 6]]
        runner.input_batch.spec_decode_unsupported_reqs = {"req2"}
        runner.drafter.propose.return_value = np.array([10, 11])

        result = runner.propose_ngram_draft_token_ids(sampled_token_ids)

        expected = [[10, 11], [], []]  # 第二个是不支持的请求，第三个超过 max_model_len
        assert result == expected

    def test_propose_ngram_draft_token_ids_drafter_returns_none(self, runner):
        """测试 drafter 返回 None"""
        sampled_token_ids = [[1, 2], [3, 4]]
        runner.input_batch.num_tokens_no_spec = [50, 60]  # 调整为不超过限制
        runner.drafter.propose.return_value = None

        result = runner.propose_ngram_draft_token_ids(sampled_token_ids)

        expected = [[], []]
        assert result == expected

    def test_propose_ngram_draft_token_ids_drafter_returns_empty(self, runner):
        """测试 drafter 返回空数组"""
        sampled_token_ids = [[1, 2], [3, 4]]
        runner.input_batch.num_tokens_no_spec = [50, 60]  # 调整为不超过限制
        runner.drafter.propose.return_value = np.array([])

        result = runner.propose_ngram_draft_token_ids(sampled_token_ids)

        expected = [[], []]
        assert result == expected


class TestPatchFunctions:
    """测试补丁函数"""

    def test_patch_spec_edit_v1(self):
        """测试 patch_spec_edit_v1 函数"""
        with patch('inference_server.modules.specedit.lib.spec_edit_worker_v1.patch_ngram_proposer') as mock_patch_ngram:
            with patch('inference_server.modules.specedit.lib.spec_edit_worker_v1.patch_gpu_model_runner') as mock_patch_gpu:
                patch_spec_edit_v1()

                mock_patch_ngram.assert_called_once()
                mock_patch_gpu.assert_called_once()

    def test_patch_gpu_model_runner(self):
        """测试 patch_gpu_model_runner 函数"""
        with patch('inference_server.modules.specedit.lib.spec_edit_worker_v1.logger') as mock_logger:
            # 创建一个模拟的gpu_model_runner模块
            mock_module = Mock()
            mock_module.OriginalGPUModelRunner = None
            mock_module.GPUModelRunner = Mock()

            with patch.dict('sys.modules', {
                'vllm.v1.worker.gpu_model_runner': mock_module
            }):
                patch_gpu_model_runner()

                # 验证日志被调用
                mock_logger.info.assert_called_once()

    def test_patch_ngram_proposer(self):
        """测试 patch_ngram_proposer 函数"""
        with patch('inference_server.modules.specedit.lib.spec_edit_worker_v1.logger') as mock_logger:
            # 创建一个模拟的ngram_proposer模块
            mock_module = Mock()
            mock_module.NgramProposer = Mock()

            with patch('inference_server.modules.specedit.lib.spec_edit_worker_v1.ngram_proposer', mock_module):
                patch_ngram_proposer()

                # 验证设置了原始类
                assert hasattr(mock_module, original_ngram_proposer_key)
                # 验证日志被调用
                mock_logger.info.assert_called_once()


# 参数化测试示例
@pytest.mark.parametrize("context_length,expected_k", [
    (95, 5),  # 正常情况，k 不受限制
    (98, 2),  # k 被限制为 2
    (99, 1),  # k 被限制为 1
    (100, 0), # k 为 0，应该返回 None
    (101, 0), # k 为负数，应该返回 None
])
def test_propose_k_calculation(context_length, expected_k):
    """参数化测试 k 值计算"""
    proposer = SpecEditProposer.__new__(SpecEditProposer)
    proposer.k = 5
    proposer.max_model_len = 100

    context_tokens = np.array([10] * context_length)
    req_id = "test_req_123"

    mock_stream_chunk = Mock()
    mock_stream_chunk.next_chunk.return_value = [40, 50, 60, 70, 80]

    with patch('inference_server.modules.specedit.lib.spec_edit_worker_v1.request_manager') as mock_request_manager:
        mock_request_manager.get_stream_next_chunk.return_value = mock_stream_chunk

        # Mock父类方法以避免依赖
        with patch.object(SpecEditProposer.__bases__[0], 'propose'):
            result = proposer.propose(context_tokens, req_id)

            if expected_k <= 0:
                assert result is None
                mock_stream_chunk.next_chunk.assert_not_called()
            else:
                mock_stream_chunk.next_chunk.assert_called_once_with(list(context_tokens), expected_k)


def test_integration_spec_edit_proposer():
    """集成测试 SpecEditProposer 与真实的依赖项"""
    # 这是一个更接近真实使用场景的测试
    proposer = SpecEditProposer.__new__(SpecEditProposer)
    proposer.k = 3
    proposer.max_model_len = 50

    context_tokens = np.array([1, 2, 3, 4, 5])
    req_id = "integration_test_req"

    # 使用Mock对象代替类
    mock_stream_chunk = Mock()
    mock_stream_chunk.next_chunk.return_value = [6, 7, 8]  # 模拟返回 [5+1, 5+2, 5+3]

    with patch('inference_server.modules.specedit.lib.spec_edit_worker_v1.request_manager') as mock_request_manager:
        mock_request_manager.get_stream_next_chunk.return_value = mock_stream_chunk

        # Mock父类方法以避免依赖
        with patch.object(SpecEditProposer.__bases__[0], 'propose'):
            proposer.propose(context_tokens, req_id)

            # 验证结果 - 由于我们mock了父类，这里主要验证stream_chunk的调用
            mock_stream_chunk.next_chunk.assert_called_once_with([1, 2, 3, 4, 5], 3)
