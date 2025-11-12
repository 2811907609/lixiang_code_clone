
## rag_ingest
本项目主要是将代码库(目录)的代码文件切片，然后调用 embedding api 进行向量化，然后存储在向量数据库中，
后续可以根据文本(以后或许可以有图片等)进行检索。

### embedding 服务
可以使用 codebuddy 项目的远程的，也可以使用本地的 ollama。

### 向量数据库
目前支持 pgvector, 如果需要使用其他 db，参考 `rag_ingest/stores/pgvector.py` 实现相应的方法即可。

### dev
你在安装 psycopg2 包的时候可能会碰到一些麻烦，你需要安装postgres的开发包，然后将postgres的bin目录添加到环境变量中。
比如下面是我的路径和环境变量设置，你需要按需修改成你的。

    $ export PATH="/opt/local/lib/postgresql12/bin:$PATH"
    $ uv sync

然后你可以尝试运行单元测试.

    ```bash
    source .env  &&  RAG_LANG=go  RAG_DIR=<Code_DIR>  RAG_FILE=<A_CODE_FILE>  poetry run pytest -vv -s -k test_dir_to_ch
    ```

#### 使用本地的ollama embedding api

```bash
ollama pull bge-m3
ollama serve

# curl to test if it is OK
curl http://localhost:11434/api/embeddings -d '{ "model": "bge-m3", "prompt": "hello!" }'
```
