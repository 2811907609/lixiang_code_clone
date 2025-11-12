
from inference_server.backend.models.deepseek_model import DeepseekCoder

def test_force_fim():
    class TestDeepseekCoder(DeepseekCoder):
        _enable_monitor = False
    m = TestDeepseekCoder(None, None)
    prompt, _ = m.gen_prompt_no_cutoff('python', prompt='def hello()')
    assert prompt == '<｜fim▁begin｜># this is python code\n\ndef hello()<｜fim▁hole｜><｜fim▁end｜>'
