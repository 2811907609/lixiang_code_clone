
import logging

from inference_server.backend import get_llm
from inference_server.backend.common import is_fim_llm

logger = logging.getLogger(__name__)

async def prestart_check():
    llm = get_llm()
    if not llm:
        logger.error("no llm found")
        raise Exception("no llm found")
    if is_fim_llm(llm):
        await fim_check(llm)


async def fim_check(llm):
    result = await llm.code_complete_v2(
        "", "hello ", "",
        max_tokens=5, logprobs=5)
    assert len(result.usage.output_stat.logprobs) > 0, "fim llm check failed"
    assert result.usage.output_stat.topk_mean_prob > 0, "bad topk_mean_prob"
    return result
