
# llminfer_rs

This is a rust toolchain for copilot projects. We use rust to make some critical components of the project to improve performance and safety.

## Build

```bash
# 开发模式构建
maturin develop

# 生产构建
maturin build --release

# 运行测试
uv run pytest tests/
```

## crates/python

This is python bindings so that we can use the rust code in python. It uses pyo3 to generate the bindings.
