import random
from typing import Dict, List, Optional

import numpy as np
from pydantic import BaseModel

from inference_server.utils import xfloat


class Logprob(BaseModel):
    '''Infos for supporting OpenAI compatible logprobs and token ranks.

    Attributes:
        p: logprob: The logprob of chosen token
        r: rank: The vocab rank of chosen token (>=1)
        t: decoded_token: The decoded chosen token index
    '''
    p: float | str = None
    r: Optional[int] = None
    t: Optional[str] = None


SampleLogprobs = List[Dict[int | str, Logprob]]


class OutputStat(BaseModel):
    output_token_length: int = 0
    first_token_latency: Optional[float] = None  # in ms
    per_token_time: Optional[float] = None  # in ms
    cumulative_logprob: Optional[float] = None

    logprobs: SampleLogprobs = None
    first_token_logprob: Optional[float] = None
    logprob_lt1_idx: Optional[int] = None
    logprob_lt3_idx: Optional[int] = None

    topk_mean_token_num: Optional[int] = 3
    topk_mean_prob: Optional[float] = None
    topk_mean_threshold: Optional[float] = None
    # 如果该值不为None，那么随机一个数，如果<=topk_mean_active_ratio, 则active
    # 如果active了,则根据topk_mean_prob和topk_mean_threshold确定要不要返回空字符串
    topk_mean_active_ratio: Optional[float] = None
    topk_mean_activated: Optional[bool] = None

    def should_drop_due_to_logprob(self):
        if self.topk_mean_activated and self.topk_mean_prob:
            return self.topk_mean_prob <= self.topk_mean_threshold


def attach_logprobs(stat: OutputStat, logprobs):
    result = []
    for p in (logprobs or []):
        new_p = {}
        for k, log in p.items():
            # if topk_num:
            #     # rank序号是从1开始的，取前 N(topk_num) 个token的logprob
            #     if i < topk_num and log.rank == 1:
            #         topk.append(log.logprob)

            new_p[k] = Logprob(
                p=xfloat(log.logprob),
                r=log.rank,
                t=log.decoded_token,
            )
        result.append(new_p)
    stat.logprobs = result

    attach_logprobs_v2(stat)


def attach_logprobs_v2(stat: OutputStat):

    topk = []
    topk_num = stat.topk_mean_token_num or 0
    topk_logprobs = stat.logprobs[:topk_num]
    for token_logprobs in topk_logprobs:
        for _, logprob in token_logprobs.items():
            if logprob.r == 1:
                topk.append(logprob.p)

    # https://li.feishu.cn/docx/JRywdKg7loak96xnzkBcgOnxncg
    # 计算topk的平均prob
    if len(topk) == topk_num:
        topk = np.array(topk, dtype=float)
        topk_filtered = topk[~np.isnan(topk) & ~np.isinf(topk)]
        # 确认topk的logprob是有效的
        if len(topk_filtered) == topk_num:
            topk_exp = np.exp(topk_filtered)
            topk_mean = np.mean(topk_exp)
            stat.topk_mean_prob = topk_mean

    # 根据上面的值确定是否要修改返回的结果
    if stat.topk_mean_threshold and stat.topk_mean_active_ratio:
        p = random.random()
        should_active = p <= stat.topk_mean_active_ratio
        stat.topk_mean_activated = should_active
