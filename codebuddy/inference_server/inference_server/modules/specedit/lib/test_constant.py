from inference_server.modules.specedit.lib.constant import (
    Features,
    disable_ngram_spec,
    disable_spec_edit,
    enable_ngram_spec,
    enable_spec_edit,
    features,
    is_ngram_spec_enabled,
    is_spec_edit_enabled,
)


class TestFeatures:
    """测试 Features 类"""

    def test_features_initialization(self):
        """测试 Features 类的初始状态"""
        test_features = Features()
        assert test_features.spec_edit is True
        assert test_features.ngram_spec is True

    def test_features_instance_attributes(self):
        """测试 Features 实例属性"""
        assert hasattr(features, 'spec_edit')
        assert hasattr(features, 'ngram_spec')
        assert isinstance(features.spec_edit, bool)
        assert isinstance(features.ngram_spec, bool)


class TestFeatureFunctions:
    """测试功能开关函数"""

    def setup_method(self):
        """在每个测试方法前重置features状态"""
        features.spec_edit = True
        features.ngram_spec = True

    def test_enable_spec_edit(self):
        """测试启用 spec_edit 功能"""
        features.spec_edit = False
        enable_spec_edit()
        assert features.spec_edit is True

    def test_disable_spec_edit(self):
        """测试禁用 spec_edit 功能"""
        features.spec_edit = True
        disable_spec_edit()
        assert features.spec_edit is False

    def test_enable_ngram_spec(self):
        """测试启用 ngram_spec 功能"""
        features.ngram_spec = False
        enable_ngram_spec()
        assert features.ngram_spec is True

    def test_disable_ngram_spec(self):
        """测试禁用 ngram_spec 功能"""
        features.ngram_spec = True
        disable_ngram_spec()
        assert features.ngram_spec is False

    def test_is_spec_edit_enabled(self):
        """测试检查 spec_edit 功能状态"""
        features.spec_edit = True
        assert is_spec_edit_enabled() is True

        features.spec_edit = False
        assert is_spec_edit_enabled() is False

    def test_is_ngram_spec_enabled(self):
        """测试检查 ngram_spec 功能状态"""
        features.ngram_spec = True
        assert is_ngram_spec_enabled() is True

        features.ngram_spec = False
        assert is_ngram_spec_enabled() is False

    def test_toggle_features(self):
        """测试功能开关的切换"""
        # 初始状态
        assert is_spec_edit_enabled() is True
        assert is_ngram_spec_enabled() is True

        # 禁用两个功能
        disable_spec_edit()
        disable_ngram_spec()
        assert is_spec_edit_enabled() is False
        assert is_ngram_spec_enabled() is False

        # 重新启用
        enable_spec_edit()
        enable_ngram_spec()
        assert is_spec_edit_enabled() is True
        assert is_ngram_spec_enabled() is True


class TestIntegration:
    """集成测试"""

    def test_features_global_instance(self):
        """测试全局 features 实例的行为"""
        # 确保使用的是同一个实例
        from inference_server.modules.specedit.lib.constant import (
            features as global_features,
        )

        # 修改全局实例
        original_spec_edit = global_features.spec_edit
        original_ngram_spec = global_features.ngram_spec

        disable_spec_edit()
        disable_ngram_spec()

        assert global_features.spec_edit is False
        assert global_features.ngram_spec is False

        # 恢复原始状态
        if original_spec_edit:
            enable_spec_edit()
        if original_ngram_spec:
            enable_ngram_spec()

    def test_function_consistency(self):
        """测试函数行为的一致性"""
        # 测试多次调用的一致性
        for _ in range(5):
            enable_spec_edit()
            assert is_spec_edit_enabled() is True

            disable_spec_edit()
            assert is_spec_edit_enabled() is False

            enable_ngram_spec()
            assert is_ngram_spec_enabled() is True

            disable_ngram_spec()
            assert is_ngram_spec_enabled() is False
