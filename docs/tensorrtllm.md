
### references

https://github.com/NVIDIA/TensorRT-LLM/blob/main/examples/llama/README.md

### model convert
When running in LPAI, the ENVs of ssh shell is different from ENVs of the docker
 container. You may need to copy ENVs from container to ssh shell.

```shell
export PYTORCH_HOME=/opt/pytorch/pytorch
export LD_LIBRARY_PATH=/usr/local/lib/python3.10/dist-packages/torch/lib:/usr/local/lib/python3.10/dist-packages/torch_tensorrt/lib:/usr/local/cuda/compat/lib:/usr/local/nvidia/lib:/usr/local/nvidia/lib64:/usr/local/cuda/lib64:/usr/local/tensorrt/lib:/usr/local/cuda/lib64:/usr/local/tensorrt/lib
export PATH=/usr/local/nvm/versions/node/v16.20.2/bin:/usr/local/lib/python3.10/dist-packages/torch_tensorrt/bin:/usr/local/mpi/bin:/usr/local/nvidia/bin:/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/local/ucx/bin:/opt/tensorrt/bin:/usr/local/cmake/bin:/usr/local/cmake/bin
export OPAL_PREFIX=/opt/hpcx/ompi
export OMPI_MCA_coll_hcoll_enable=0
```

    $ python3 convert_checkpoint.py --model_dir /lpai/volumes/zxd-code-complete/data/models/hf-codellama-7b-instruct_v4.34/ --output_dir /lpai/volumes/zxd-code-complete/data/models/tensorrtllm/tllm_checkpoint_codellama7binstruct --dtype float16 --rotary_base 1000000 --vocab_size 32016

Attention: set max_input_len ad max_output_len since the default is not so large.

    $ trtllm-build --checkpoint_dir /lpai/volumes/zxd-code-complete/data/models/tensorrtllm/tllm_checkpoint_codellama7binstruct --output_dir /lpai/volumes/zxd-code-complete/data/models/tensorrtllm/tllm_codellama7binstruct_fp16 --gemm_plugin float16 --max_input_len 6200 --max_output_len 1024

    $ python3 ../run.py --max_output_len=100 --tokenizer_dir /lpai/volumes/zxd-code-complete/data/models/hf-codellama-7b-instruct_v4.34/ --engine_dir /lpai/volumes/zxd-code-complete/data/models/tensorrtllm/tllm_codellama7binstruct_fp16  --input_text 'In Bash, how do I list all text files?'
