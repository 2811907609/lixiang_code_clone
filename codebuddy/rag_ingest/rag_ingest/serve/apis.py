import json
import logging
from dataclasses import asdict

from aiohttp import web
from rag_ingest.ingest import get_ns_from_repo_url, ingest_repos
from rag_ingest.query import query
from rag_ingest.state import STORE

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def run_server(port=8080):
    routes = web.RouteTableDef()

    @routes.route('*', '/v1/health')
    async def health(request):
        return web.Response(text='ok')

    @routes.route("POST", "/v1/query")
    async def query_api(request):
        req = await request.json()
        git_remote_url = req.get('git_remote_url', '')
        namespace = req.get('namespace', '')
        if not namespace:
            if git_remote_url:
                try:
                    namespace = get_ns_from_repo_url(git_remote_url)
                except Exception as e:
                    return web.Response(
                        status=400,
                        text=f'get namespace from git_remote_url error: {e}')
            if not namespace:
                return web.Response(status=400, text='namespace is required')

        input = req.get('input')
        n = req.get('n', 3)
        if n > 10:
            n = 10
        recall_n = req.get('recall_n', 10)
        if recall_n > 20:
            recall_n = 20
        records, stat = query(input,
                              namespace=namespace,
                              recall_limit=recall_n,
                              rerank_limit=n)
        logger.info(
            f'query ns: {namespace}, n_result: {n}, recall_n: {recall_n}')
        logger.info(f'query input: {input[:40]}')
        response = {
            'namespace': namespace,
            'records': [r.output() for r in records],
            'stat': asdict(stat),
        }
        return web.Response(body=json.dumps(response))

    @routes.route("POST", "/v1/ingest-repo")
    async def ingest_repo(request):
        req = await request.json()
        repos = req.get('repos', [])
        if not repos:
            return web.Response(status=400, text='repos is required')
        ssh_key_filepath = req.get('ssh_key_filepath', '')
        username = req.get('username', '')
        await ingest_repos(repos,
                           ssh_key_filepath=ssh_key_filepath,
                           username=username)
        return web.Response(body=json.dumps({}))

    @routes.route("GET", "/v1/repo-ingested")
    async def repo_ingested(request):
        git_remote_url = request.query.get('git_remote_url', '')
        try:
            namespace = get_ns_from_repo_url(git_remote_url)
        except Exception as e:
            return web.Response(
                status=400,
                text=f'get namespace from git_remote_url error: {e}')
        existed = STORE.namespace_existed(namespace)
        result = dict(existed=existed)
        return web.Response(body=json.dumps(result))

    app = web.Application()
    app.add_routes(routes)
    web.run_app(app,
                host='0.0.0.0',
                port=int(port),
                reuse_address=True,
                reuse_port=True)


if __name__ == '__main__':
    run_server()
