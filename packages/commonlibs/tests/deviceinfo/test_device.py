import time
import unittest
from unittest.mock import patch

from commonlibs.deviceinfo.device import (
    get_cpu_brand,
    get_device_brand,
    get_device_info,
)


class TestDeviceInfoCache(unittest.TestCase):
    """测试设备信息缓存功能"""

    def setUp(self):
        """清理缓存"""
        # 清理函数缓存
        get_cpu_brand.cache_clear()
        get_device_brand.cache_clear()
        get_device_info.cache_clear()

    def test_cpu_brand_cache(self):
        """测试CPU品牌信息缓存"""
        with patch('commonlibs.deviceinfo.device.platform.processor') as mock_processor:
            mock_processor.return_value = "Intel(R) Core(TM) i7-9750H CPU @ 2.60GHz"

            # 第一次调用
            result1 = get_cpu_brand()
            self.assertEqual(result1, "Intel(R) Core(TM) i7-9750H CPU @ 2.60GHz")
            self.assertEqual(mock_processor.call_count, 1)

            # 第二次调用应该使用缓存
            result2 = get_cpu_brand()
            self.assertEqual(result2, "Intel(R) Core(TM) i7-9750H CPU @ 2.60GHz")
            self.assertEqual(result1, result2)
            # mock 应该只被调用一次，证明使用了缓存
            self.assertEqual(mock_processor.call_count, 1)

    def test_device_brand_cache(self):
        """测试设备品牌信息缓存"""
        with patch('commonlibs.deviceinfo.device.platform.system') as mock_system:
            mock_system.return_value = "Darwin"

            # 第一次调用
            result1 = get_device_brand()
            self.assertEqual(result1, "Apple")
            self.assertEqual(mock_system.call_count, 1)

            # 第二次调用应该使用缓存
            result2 = get_device_brand()
            self.assertEqual(result2, "Apple")
            self.assertEqual(result1, result2)
            # mock 应该只被调用一次，证明使用了缓存
            self.assertEqual(mock_system.call_count, 1)

    def test_device_info_cache(self):
        """测试综合设备信息缓存"""
        with patch('commonlibs.deviceinfo.device.platform.release') as mock_release, \
             patch('commonlibs.deviceinfo.device.platform.machine') as mock_machine, \
             patch('commonlibs.deviceinfo.device.platform.system') as mock_system, \
             patch('commonlibs.deviceinfo.device.platform.mac_ver') as mock_mac_ver, \
             patch('commonlibs.deviceinfo.device.get_device_brand') as mock_device_brand, \
             patch('commonlibs.deviceinfo.device.get_cpu_brand') as mock_cpu_brand, \
             patch('commonlibs.deviceinfo.device.psutil.cpu_count') as mock_cpu_count:

            # 设置 mock 返回值
            mock_release.return_value = "21.6.0"
            mock_machine.return_value = "x86_64"
            mock_system.return_value = "Darwin"
            mock_mac_ver.return_value = ("12.5", "", "")  # macOS version tuple
            mock_device_brand.return_value = "Apple"
            mock_cpu_brand.return_value = "Intel Core i7"
            mock_cpu_count.return_value = 8

            # 第一次调用
            result1 = get_device_info()
            expected_info = {
                "os_version": "12.5",  # 使用 mac_ver 返回的版本
                "os_arch": "x86_64",
                "os_family": "Darwin",
                "brand": "Apple",
                "cpu_brand": "Intel Core i7",
                "cpu_cores": 8
            }

            # 验证结果包含预期字段
            for key, value in expected_info.items():
                self.assertEqual(result1[key], value)

            # 验证函数被调用
            self.assertEqual(mock_release.call_count, 1)
            self.assertEqual(mock_machine.call_count, 1)
            self.assertEqual(mock_system.call_count, 2)  # system() 被调用两次（一次获取系统类型，一次判断是否为Darwin）
            self.assertEqual(mock_mac_ver.call_count, 1)

            # 第二次调用应该使用缓存
            result2 = get_device_info()
            self.assertEqual(result1, result2)

            # mock 函数调用次数不应该增加，证明使用了缓存
            self.assertEqual(mock_release.call_count, 1)
            self.assertEqual(mock_machine.call_count, 1)
            self.assertEqual(mock_system.call_count, 2)
            self.assertEqual(mock_mac_ver.call_count, 1)

    def test_cache_performance(self):
        """测试缓存性能提升"""
        # 模拟慢速操作
        with patch('commonlibs.deviceinfo.device.platform.processor') as mock_processor:
            def slow_processor():
                time.sleep(0.01)  # 模拟10ms延迟
                return "Test CPU"

            mock_processor.side_effect = slow_processor

            # 测量第一次调用时间（包含慢速操作）
            start_time = time.time()
            result1 = get_cpu_brand()
            first_call_time = time.time() - start_time

            # 测量第二次调用时间（使用缓存）
            start_time = time.time()
            result2 = get_cpu_brand()
            second_call_time = time.time() - start_time

            # 验证结果一致
            self.assertEqual(result1, result2)
            self.assertEqual(result1, "Test CPU")

            # 第二次调用应该明显更快（缓存的好处）
            self.assertLess(second_call_time, first_call_time)
            self.assertLess(second_call_time, 0.005)  # 缓存调用应该小于5ms

    def test_cache_info(self):
        """测试缓存统计信息"""
        # 清理缓存
        get_cpu_brand.cache_clear()

        # 检查初始缓存状态
        cache_info = get_cpu_brand.cache_info()
        self.assertEqual(cache_info.hits, 0)
        self.assertEqual(cache_info.misses, 0)

        # 第一次调用 - 应该是 cache miss
        get_cpu_brand()
        cache_info = get_cpu_brand.cache_info()
        self.assertEqual(cache_info.hits, 0)
        self.assertEqual(cache_info.misses, 1)

        # 第二次调用 - 应该是 cache hit
        get_cpu_brand()
        cache_info = get_cpu_brand.cache_info()
        self.assertEqual(cache_info.hits, 1)
        self.assertEqual(cache_info.misses, 1)

        # 第三次调用 - 应该又是 cache hit
        get_cpu_brand()
        cache_info = get_cpu_brand.cache_info()
        self.assertEqual(cache_info.hits, 2)
        self.assertEqual(cache_info.misses, 1)
