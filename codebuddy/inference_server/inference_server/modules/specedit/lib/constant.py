from dataclasses import dataclass

original_worker_key = '_ep_original_ngram_worker'
original_ngram_proposer_key = "_ep_ngram_proposer_key"


@dataclass
class Features:
    spec_edit = True
    ngram_spec = True


features = Features()


def enable_spec_edit():
    """启用 spec_edit 功能"""
    features.spec_edit = True

def disable_spec_edit():
    """禁用 spec_edit 功能"""
    features.spec_edit = False

def enable_ngram_spec():
    """启用 ngram_spec 功能"""
    features.ngram_spec = True

def disable_ngram_spec():
    """禁用 ngram_spec 功能"""
    features.ngram_spec = False

def is_spec_edit_enabled() -> bool:
    """检查 spec_edit 功能是否启用"""
    return features.spec_edit

def is_ngram_spec_enabled() -> bool:
    """检查 ngram_spec 功能是否启用"""
    return features.ngram_spec
