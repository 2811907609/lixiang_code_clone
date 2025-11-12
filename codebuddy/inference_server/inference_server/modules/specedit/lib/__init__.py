from .constant import (
    disable_ngram_spec,
    disable_spec_edit,
    enable_ngram_spec,
    enable_spec_edit,
)
from .patch import patch_spec_edit

__all__ = [
    'patch_spec_edit',
    'disable_spec_edit',
    'enable_spec_edit',
    'disable_ngram_spec',
    'enable_ngram_spec',
]
