import hashlib
import unittest
from unittest.mock import patch

from commonlibs.deviceinfo.fingerprint import get_machine_fingerprint


class TestMachineFingerprint(unittest.TestCase):
    """测试机器指纹生成功能"""

    def test_fingerprint_generation(self):
        """测试正常的指纹生成"""
        with patch('commonlibs.deviceinfo.fingerprint.platform.machine') as mock_machine, \
             patch('commonlibs.deviceinfo.fingerprint.platform.processor') as mock_processor, \
             patch('commonlibs.deviceinfo.fingerprint.platform.system') as mock_system, \
             patch('commonlibs.deviceinfo.fingerprint.platform.release') as mock_release, \
             patch('commonlibs.deviceinfo.fingerprint.platform.node') as mock_node, \
             patch('commonlibs.deviceinfo.fingerprint.platform.platform') as mock_platform, \
             patch('commonlibs.deviceinfo.fingerprint.uuid.getnode') as mock_getnode:

            # 设置固定的 mock 返回值
            mock_machine.return_value = "x86_64"
            mock_processor.return_value = "Intel(R) Core(TM) i7-9750H"
            mock_system.return_value = "Darwin"
            mock_release.return_value = "21.6.0"
            mock_node.return_value = "MacBook-Pro.local"
            mock_platform.return_value = "macOS-12.5-x86_64-i386-64bit"
            mock_getnode.return_value = 0x1234567890ab

            # 生成指纹
            fingerprint = get_machine_fingerprint()

            # 验证指纹格式
            self.assertIsInstance(fingerprint, str)
            self.assertEqual(len(fingerprint), 16)  # 应该是16个字符
            self.assertTrue(all(c in '0123456789abcdef' for c in fingerprint))  # 应该是十六进制

            # 验证所有 mock 函数都被调用
            mock_machine.assert_called_once()
            mock_processor.assert_called_once()
            mock_system.assert_called_once()
            mock_release.assert_called_once()
            mock_node.assert_called_once()
            mock_platform.assert_called_once()
            mock_getnode.assert_called_once()

    def test_fingerprint_consistency(self):
        """测试指纹的一致性 - 相同输入应该产生相同指纹"""
        with patch('commonlibs.deviceinfo.fingerprint.platform.machine') as mock_machine, \
             patch('commonlibs.deviceinfo.fingerprint.platform.processor') as mock_processor, \
             patch('commonlibs.deviceinfo.fingerprint.platform.system') as mock_system, \
             patch('commonlibs.deviceinfo.fingerprint.platform.release') as mock_release, \
             patch('commonlibs.deviceinfo.fingerprint.platform.node') as mock_node, \
             patch('commonlibs.deviceinfo.fingerprint.platform.platform') as mock_platform, \
             patch('commonlibs.deviceinfo.fingerprint.uuid.getnode') as mock_getnode:

            # 设置固定的返回值
            mock_machine.return_value = "x86_64"
            mock_processor.return_value = "Intel Core i7"
            mock_system.return_value = "Darwin"
            mock_release.return_value = "21.6.0"
            mock_node.return_value = "test-machine"
            mock_platform.return_value = "macOS-12.5"
            mock_getnode.return_value = 0xaabbccddeeff

            # 多次生成指纹
            fingerprint1 = get_machine_fingerprint()
            fingerprint2 = get_machine_fingerprint()
            fingerprint3 = get_machine_fingerprint()

            # 验证一致性
            self.assertEqual(fingerprint1, fingerprint2)
            self.assertEqual(fingerprint2, fingerprint3)

    def test_fingerprint_uniqueness(self):
        """测试不同系统应该产生不同的指纹"""
        # 第一组系统信息
        with patch('commonlibs.deviceinfo.fingerprint.platform.machine') as mock_machine, \
             patch('commonlibs.deviceinfo.fingerprint.platform.processor') as mock_processor, \
             patch('commonlibs.deviceinfo.fingerprint.platform.system') as mock_system, \
             patch('commonlibs.deviceinfo.fingerprint.platform.release') as mock_release, \
             patch('commonlibs.deviceinfo.fingerprint.platform.node') as mock_node, \
             patch('commonlibs.deviceinfo.fingerprint.platform.platform') as mock_platform, \
             patch('commonlibs.deviceinfo.fingerprint.uuid.getnode') as mock_getnode:

            mock_machine.return_value = "x86_64"
            mock_processor.return_value = "Intel Core i7"
            mock_system.return_value = "Darwin"
            mock_release.return_value = "21.6.0"
            mock_node.return_value = "machine1"
            mock_platform.return_value = "macOS-12.5"
            mock_getnode.return_value = 0x111111111111

            fingerprint1 = get_machine_fingerprint()

        # 第二组系统信息（不同的机器）
        with patch('commonlibs.deviceinfo.fingerprint.platform.machine') as mock_machine, \
             patch('commonlibs.deviceinfo.fingerprint.platform.processor') as mock_processor, \
             patch('commonlibs.deviceinfo.fingerprint.platform.system') as mock_system, \
             patch('commonlibs.deviceinfo.fingerprint.platform.release') as mock_release, \
             patch('commonlibs.deviceinfo.fingerprint.platform.node') as mock_node, \
             patch('commonlibs.deviceinfo.fingerprint.platform.platform') as mock_platform, \
             patch('commonlibs.deviceinfo.fingerprint.uuid.getnode') as mock_getnode:

            mock_machine.return_value = "aarch64"
            mock_processor.return_value = "Apple M1"
            mock_system.return_value = "Darwin"
            mock_release.return_value = "22.1.0"
            mock_node.return_value = "machine2"
            mock_platform.return_value = "macOS-13.0"
            mock_getnode.return_value = 0x222222222222

            fingerprint2 = get_machine_fingerprint()

        # 验证不同系统产生不同指纹
        self.assertNotEqual(fingerprint1, fingerprint2)

    def test_fingerprint_with_exception_fallback(self):
        """测试异常情况下的回退机制"""
        with patch('commonlibs.deviceinfo.fingerprint.platform.machine') as mock_machine, \
             patch('commonlibs.deviceinfo.fingerprint.platform.system') as mock_system, \
             patch('commonlibs.deviceinfo.fingerprint.uuid.getnode') as mock_getnode:

            # 模拟大部分函数抛出异常
            mock_machine.side_effect = Exception("Machine info not available")
            mock_system.return_value = "Linux"  # 这个不会抛异常
            mock_getnode.return_value = 0xffffffffffff

            # 应该能正常生成指纹（使用回退机制）
            fingerprint = get_machine_fingerprint()

            # 验证指纹格式
            self.assertIsInstance(fingerprint, str)
            self.assertEqual(len(fingerprint), 16)
            self.assertTrue(all(c in '0123456789abcdef' for c in fingerprint))

    def test_fingerprint_algorithm_correctness(self):
        """测试指纹算法的正确性"""
        with patch('commonlibs.deviceinfo.fingerprint.platform.machine') as mock_machine, \
             patch('commonlibs.deviceinfo.fingerprint.platform.processor') as mock_processor, \
             patch('commonlibs.deviceinfo.fingerprint.platform.system') as mock_system, \
             patch('commonlibs.deviceinfo.fingerprint.platform.release') as mock_release, \
             patch('commonlibs.deviceinfo.fingerprint.platform.node') as mock_node, \
             patch('commonlibs.deviceinfo.fingerprint.platform.platform') as mock_platform, \
             patch('commonlibs.deviceinfo.fingerprint.uuid.getnode') as mock_getnode:

            # 设置已知的输入值
            mock_machine.return_value = "test_machine"
            mock_processor.return_value = "test_processor"
            mock_system.return_value = "test_system"
            mock_release.return_value = "test_release"
            mock_node.return_value = "test_node"
            mock_platform.return_value = "test_platform"
            mock_getnode.return_value = 0x123456789abc

            # 生成指纹
            fingerprint = get_machine_fingerprint()

            # 手动计算期望的指纹来验证算法
            expected_data = [
                "test_machine",
                "test_processor",
                "test_system",
                "test_release",
                "0x123456789abc",  # hex(0x123456789abc)
                "test_node",
                "test_platform"
            ]
            expected_string = "|".join(expected_data)
            expected_hash = hashlib.sha256(expected_string.encode()).hexdigest()
            expected_fingerprint = expected_hash[:16]

            # 验证算法正确性
            self.assertEqual(fingerprint, expected_fingerprint)

    def test_mac_address_inclusion(self):
        """测试MAC地址确实被包含在指纹中"""
        with patch('commonlibs.deviceinfo.fingerprint.platform.machine') as mock_machine, \
             patch('commonlibs.deviceinfo.fingerprint.platform.processor') as mock_processor, \
             patch('commonlibs.deviceinfo.fingerprint.platform.system') as mock_system, \
             patch('commonlibs.deviceinfo.fingerprint.platform.release') as mock_release, \
             patch('commonlibs.deviceinfo.fingerprint.platform.node') as mock_node, \
             patch('commonlibs.deviceinfo.fingerprint.platform.platform') as mock_platform, \
             patch('commonlibs.deviceinfo.fingerprint.uuid.getnode') as mock_getnode:

            # 设置固定值，除了MAC地址
            mock_machine.return_value = "x86_64"
            mock_processor.return_value = "Intel Core i7"
            mock_system.return_value = "Darwin"
            mock_release.return_value = "21.6.0"
            mock_node.return_value = "test-machine"
            mock_platform.return_value = "macOS-12.5"

            # 测试不同的MAC地址
            mock_getnode.return_value = 0x111111111111
            fingerprint1 = get_machine_fingerprint()

            mock_getnode.return_value = 0x222222222222
            fingerprint2 = get_machine_fingerprint()

            # MAC地址不同应该产生不同的指纹
            self.assertNotEqual(fingerprint1, fingerprint2)

    def test_empty_values_handling(self):
        """测试空值或None值的处理"""
        with patch('commonlibs.deviceinfo.fingerprint.platform.machine') as mock_machine, \
             patch('commonlibs.deviceinfo.fingerprint.platform.processor') as mock_processor, \
             patch('commonlibs.deviceinfo.fingerprint.platform.system') as mock_system, \
             patch('commonlibs.deviceinfo.fingerprint.platform.release') as mock_release, \
             patch('commonlibs.deviceinfo.fingerprint.platform.node') as mock_node, \
             patch('commonlibs.deviceinfo.fingerprint.platform.platform') as mock_platform, \
             patch('commonlibs.deviceinfo.fingerprint.uuid.getnode') as mock_getnode:

            # 设置一些空值
            mock_machine.return_value = ""
            mock_processor.return_value = None
            mock_system.return_value = "Linux"
            mock_release.return_value = ""
            mock_node.return_value = "hostname"
            mock_platform.return_value = "Linux-5.4.0"
            mock_getnode.return_value = 0x123456789abc

            # 应该能正常生成指纹
            fingerprint = get_machine_fingerprint()

            # 验证指纹格式
            self.assertIsInstance(fingerprint, str)
            self.assertEqual(len(fingerprint), 16)
            self.assertTrue(all(c in '0123456789abcdef' for c in fingerprint))
