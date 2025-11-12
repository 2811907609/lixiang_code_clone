import vllm
from packaging.version import Version

from inference_server.modules.specedit.lib.spec_edit_worker_v1 import (
    patch_spec_edit_v1,
)
from inference_server.utils import getLogger

logger = getLogger(__name__)


def general_patch():
    from vllm.v1.sample import rejection_sampler
    # default is 32, for specedit, we may use very large spec num tokens, like 80
    rejection_sampler.MAX_SPEC_LEN = 128


def patch_spec_edit():
    vllm_version = vllm.__version__
    if Version(vllm_version) < Version('0.9.2'):
        from inference_server.modules.specedit.lib.spec_edit_worker_v0 import (
            patch_spec_edit_v0,
        )
        logger.info("will patch spec edit v0")
        patch_spec_edit_v0()
    else:
        logger.info("will patch spec edit v1")
        general_patch()
        patch_spec_edit_v1()
