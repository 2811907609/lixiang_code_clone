from inference_server.types import PromptComposeInfo, CompletionResponse, CompletionResponseChoice

from .fixes import fix_output


def test_online_cases():
    # comp_id, prompt, output, expected
    testcases = [
        ('cmpl-0051fe02-265d-4416-a6b4-821308eeecf1', '''
        vbox({
          window(text("存储I/O性能")| hcenter, io_performance | flex) | flex,
          window(text("脏页比例"), canvas(std::move(canvas_dirty_page_)) | hcenter |flex) |flex,
        }) | flex,
      }) | flex,
      hbox({
║  canvas(std::move(canvas_io_latency_)) | hcenter | flex,
          separator(),
          canvas(std::move(canvas_queue_depth_avg_)) | hcenter | flex,
          separator()''',
         '''window(text("读请求最长响应时间") | hcenter, canvas(std::move(canvas_io_latency_max_)) | hcenter | flex) | flex,
          separator(),
          window(text("读请求最短响应时间") | hcenter, canvas(std::move(canvas_io_latency_min_)) | hcenter | flex) | flex,
          separator(),
          window(text("最大队列长度") | hcenter, canvas(std::move(canvas_queue_depth_max_)) | hcenter | flex) | flex,
''', ''),
    ]
    for comp_id, prompt, output, expected in testcases:
        prefix, suffix = prompt.split('║')
        prompt_info = PromptComposeInfo(used_prefix=prefix, used_suffix=suffix)
        choice = CompletionResponseChoice(index=0, text=output)
        completion = CompletionResponse(choices=[choice], model='')
        fix_output(prompt_info, completion)
        assert choice.text == expected, comp_id
