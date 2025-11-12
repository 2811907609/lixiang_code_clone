
## specedit eval

### create dataset

```bash

# create datasets from a repo
uv run inference_server/modules/specedit/dataset.py \
    create_dataset ~/code/li/ep-service-clean \
    --exts=go --min_lines 200 --max_lines 500 \
    --outfile dataset_spec_edit.parquet

# create from repo yaml
uv run inference_server/modules/specedit/dataset.py \
    create_dataset yamltask

# create from instructcoder datasets
# https://huggingface.co/datasets/likaixin/InstructCoder

uv run inference_server/modules/specedit/dataset.py \
    create_dataset instructcoder

```

### run eval
Offline eval

```bash

# base line no spec
uv run inference_server/modules/specedit/eval.py run dataset_spec_edit.parquet \
        --config_path conf/test.json \
        --instance 'test.qwen25-7B-awq' \
        --model_path '/mnt/volumes/zxd-code-complete/data/models/qwen/qwen__qwen2_5-coder-14b-instruct-awq' \
        --num_speculative_tokens 80 \
        --outfile out_qwen7b-ngram-lookup-5-tokens.parquet \
        --spec_edit False


uv run inference_server/modules/specedit/eval.py run dataset_spec_edit.parquet \
        --config_path conf/test.json \
        --instance 'test.qwen25-7B-awq' \
        --outfile out_qwen7b-ngram-lookup-5-tokens.parquet \
        --spec_edit False \
        --limit 40


# small model as draft baseline
uv run inference_server/modules/specedit/eval.py run dataset_spec_edit.parquet \
        --config_path conf/test.json \
        --instance 'test.qwen25-7B-awq' \
        --model_path '/mnt/volumes/zxd-code-complete/data/models/qwen/qwen__qwen2_5-coder-14b-instruct-awq' \
        --num_speculative_tokens 80 \
        --outfile out_20250515_qwen25_14b-awq_small_model_draft_0_5b.parquet \
        --speculative_model /mnt/volumes/zxd-code-complete/data/models/qwen/qwen__qwen2_5-coder-0_5b-instruct/24-11-18-1252 \
        --spec_edit False \
        --limit 2

```

### analyze
Offline

```bash

uv run inference_server/modules/specedit/eval.py \
    analyze out_spec_edit_max_10k.parquet,out_qwen7b-spec-edit.parquet \
    --limit 40


```
