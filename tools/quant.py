'''
https://github.com/casper-hansen/AutoAWQ
'''
import fire
from transformers import AutoTokenizer


def awq(source_dir, target_dir):
    from awq import AutoAWQForCausalLM

    quant_config = {
        "zero_point": True,
        "q_group_size": 128,
        "w_bit": 4,
        "version": "GEMM"
    }

    model = AutoAWQForCausalLM.from_pretrained(
        source_dir, **{
            "use_cache": False,
            "low_cpu_mem_usage": True
        })
    tokenizer = AutoTokenizer.from_pretrained(source_dir,
                                              trust_remote_code=True)

    # Quantize
    model.quantize(
        tokenizer,
        quant_config=quant_config,
        calib_data=
        '/lpai/volumes/zxd-code-complete/data/database/pile-val-backup',
        split='validation')

    # Save quantized model
    model.save_quantized(target_dir)
    tokenizer.save_pretrained(target_dir)


def fp8(source_dir, target_dir):
    from auto_fp8 import AutoFP8ForCausalLM, BaseQuantizeConfig

    tokenizer = AutoTokenizer.from_pretrained(source_dir, use_fast=True)
    tokenizer.pad_token = tokenizer.eos_token
    examples = ['auto_fp8 is an easy-to-use model quantization library']
    examples = tokenizer(examples, return_tensors="pt").to("cuda")

    quantize_config = BaseQuantizeConfig(quant_method='fp8',
                                         activation_scheme='dynamic')

    model = AutoFP8ForCausalLM.from_pretrained(
        source_dir,
        quantize_config=quantize_config,
        trust_remote_code=True,
    )
    model.quantize(examples)
    model.save_quantized(target_dir)


if __name__ == '__main__':
    cmds = {
        'awq': awq,
        'fp8': fp8,
    }
    fire.Fire(cmds)
