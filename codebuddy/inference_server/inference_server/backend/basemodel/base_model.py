import asyncio
import sys
from typing import Optional

import arrow
from fastapi import FastAPI

from sysutils.heartbeat import HeartbeatMonitor
from sysutils.xhttp import post_json
from sysutils.xtypes import Renewable

from inference_server.envs import config
from inference_server.lang import get_language_comment_mark
from inference_server.types import PromptComposeInfo, RuntimeInfo
from inference_server.processor.preprocess import split_rag_prefix_lines, trim_head_lines, trim_tail_lines
from inference_server.utils import getLogger

logger = getLogger(__name__)


async def notify():
    time = arrow.now().format('HH:mm:ss')
    text = f'推理服务 {config.INSTANCE_NAME} 心跳检测失败 @{time}'
    url = 'https://open.feishu.cn/open-apis/bot/v2/hook/fafb035b-7090-48db-b2b9-7a3817000ce2'
    body = {'msg_type': 'text', 'content': {'text': text}}
    post_json(url, body)
    sys.exit('heartbeat failed')


class MonitorBase(Renewable):

    def __init__(self):
        self._heartbeat_monitor = HeartbeatMonitor(self.heartbeat, notify)
        self._is_closed = False

    async def heartbeat(self):
        raise NotImplementedError("子类必须实现 heartbeat 方法")

    async def start_monitor(self):
        await self._heartbeat_monitor.start(10)

    async def cleanup(self):
        """清理资源，停止心跳监控"""
        if not self._is_closed:
            logger.info("正在停止心跳监控...")
            await self._heartbeat_monitor.stop()
            self._is_closed = True

    def sync_cleanup(self):
        """同步方法，用于清理资源"""
        if not self._is_closed:
            try:
                # 创建一个新的事件循环来运行异步清理方法
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.cleanup())
                loop.close()
            except Exception as e:
                logger.error(f"清理资源时发生错误: {e}")

    def __del__(self):
        """对象被垃圾回收时调用"""
        if not self._is_closed:
            logger.warning(
                "BaseModel 实例被垃圾回收，但 cleanup 方法未被显式调用。"
                "建议在不再需要 BaseModel 实例时显式调用 cleanup 或 sync_cleanup 方法。")
            try:
                self.sync_cleanup()
            except Exception as e:
                logger.error(f"在 __del__ 中清理资源时发生错误: {e}")


class BaseModel(MonitorBase):
    force_fim = False  # force use fim even if there is no suffix, default False

    @classmethod
    def runtime_info(cls) -> RuntimeInfo:
        import torch
        device = torch.cuda.get_device_name()
        torch_version = torch.version.__version__
        cuda_version = torch.version.cuda.title()

        return RuntimeInfo(
            device=device,
            torch_version=torch_version,
            cuda_version=cuda_version,
        )

    def subapp(self) -> Optional[FastAPI]:
        '''You can return a FastAPI app instance'''
        return None

    def instance_params(self, model_name=None):
        ''' 从配置里根据model名字来获取配置的该model的默认参数'''
        if not model_name:
            return {}
        c = self.instance_config
        if not c:
            return {}
        model_config = c.get('models', {}).get(model_name)
        if not model_config:
            return {}
        return model_config.get('params', {}).copy()

    def default_chat_params(self):
        return {}

    def stop_words(self):
        return []

    def gen_prompt_header(self, lang: str) -> str:
        comment = get_language_comment_mark(lang)
        if not (lang and comment):
            return ''
        return f'{comment} this is {lang} code\n\n'


    def gen_prompt_no_cutoff(self,
                   lang: str,
                   prompt: str,
                   suffix: str = '') -> tuple[str, PromptComposeInfo]:
        prompt_info = PromptComposeInfo(used_suffix=suffix,
                                        suffix_length=len(suffix),
                                        no_prompt_cutoff=True)
        language_line = self.gen_prompt_header(lang)
        if language_line:
            prompt_info.language_header_length = len(language_line)

        rag_lines, prefix_lines = split_rag_prefix_lines(lang, prompt)

        prefix = '\n'.join(prefix_lines)
        prompt_info.prefix_length = len(prefix)
        prompt_info.prefix_used_length = len(prefix)

        rag_content = '\n'.join(rag_lines)
        if rag_content:
            rag_content += '\n'
        prompt_info.rag_length = len(rag_content)
        prompt_info.rag_used_length = len(rag_content)
        prompt_info.used_rag = rag_content

        prompt = language_line + prompt

        prompt_info.used_prefix = prompt

        if self.force_fim or (suffix and hasattr(self, 'fim_prompt')):
            prompt_info.used_suffix = suffix
            prompt_info.suffix_used_length = len(suffix)
            prompt = self.fim_prompt(prompt, suffix, lang=lang)
        return prompt, prompt_info

    def gen_prompt(self,
                   lang: str,
                   prompt: str,
                   suffix: str = None,
                   no_prompt_cutoff: bool = False,
                   prefix_limit: int = 2900,
                   rag_min_length: int = 800,
                   suffix_limit: int = 400) -> tuple[str, PromptComposeInfo]:
        if suffix is None:
            suffix = '' # change to None so that len(suffix) won't panic
        if no_prompt_cutoff:
            return self.gen_prompt_no_cutoff(lang, prompt, suffix=suffix)

        prompt_info = PromptComposeInfo(used_suffix=suffix,
                                        suffix_length=len(suffix))
        language_line = self.gen_prompt_header(lang)
        if language_line:
            prompt_info.language_header_length = len(language_line)
            prefix_limit -= len(language_line)

        rag_lines, prefix_lines = split_rag_prefix_lines(lang, prompt)

        prefix = '\n'.join(prefix_lines)
        prompt_info.prefix_length = len(prefix)

        prefix_content = trim_head_lines(prefix_lines, prefix_limit)
        prompt_info.prefix_used_length = len(prefix_content)

        rag_length = len(prompt) - len(prefix)
        prompt_info.rag_length = rag_length

        rag_length_budget = prefix_limit - len(prefix_content)
        if rag_length_budget < rag_min_length:
            rag_length_budget = rag_min_length

        rag_content = trim_tail_lines(rag_lines, rag_length_budget)
        if rag_content:
            rag_content += '\n'
        prompt_info.rag_used_length = len(rag_content)
        prompt_info.used_rag = rag_content

        prompt = language_line + rag_content + prefix_content

        prompt_info.used_prefix = prompt

        if self.force_fim or (suffix and hasattr(self, 'fim_prompt')):
            suffix = suffix[:suffix_limit]
            prompt_info.used_suffix = suffix
            prompt_info.suffix_used_length = len(suffix)
            prompt = self.fim_prompt(prompt, suffix, lang=lang)
        return prompt, prompt_info

    # def decode(self, token_ids, **kwargs):
    #     pass
    # you add this method to decode token_ids by yourself
