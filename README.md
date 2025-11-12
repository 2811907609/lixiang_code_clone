# code-complete

这是 codebuddy 相关的 monorepo 代码库，多个不同的项目都放在 codebuddy/ 目录下面。

所有项目都使用 [uv](https://docs.astral.sh/uv/) 管理 python 版本、依赖以及环境。


## 开发指南
* 需要 (uv)[https://github.com/astral-sh/uv/] 来管理 python 版本和环境
* 需要 安装 (pre-commit)[https://pre-commit.com/] 进行提交检查
* 需要安装 nbstripout 来去掉 jupyter notebook 的输出，保持比较好看的git记录

## 项目列表
### codebuddy/inference_server
LLM 推理后端，部署在 lpai 平台。

### codebuddy/rag_ingest
RAG 数据处理工具，用于 ingest repo 以及提供向量化检索服务。

### codebuddy/repotools
对代码库进行处理的工具库。

### codebuddy/copilot_dashboard_analysis
copilot 项目相关的数据看板建设，比如周报信息提取。


## 工具包/库列表
### packages/sysutils
系统工具包，该包通常是对系统库的封装，或者一些常规的utils，提供更方便的接口。
该包没有任何第三方依赖。

### packages/commonlibs
通常是对第三方包的进一步封装，该包可以使用 sysutils 包。但是不应该用 packages 下面的其他包
（其他包可以引用它）。

### packages/repoutils
gerrit，gitlab，github 等代码库处理工具包，提供了一些常用的代码库处理工具。

### packages/datautils
数据处理工具包，提供了一些常用的数据处理工具，包括对 starrocks 的访问以及数据缓存；包括
 pandas 的封装之类的。
