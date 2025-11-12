import logging
import os
import shutil

from repoutils.repo import Repo

from rag_ingest.ingest import ingest_dir

from .utils import get_ns_from_repo

logger = logging.getLogger(__name__)

_default_repo_tmp_dir = '/tmp/rag_ingest'


async def ingest_repo(repo_url,
                      tmp_dir=_default_repo_tmp_dir,
                      ssh_key_filepath: str = None,
                      keep_repo: bool = False,
                      username: str = None):
    repo = Repo.repo_from(repo_url)
    cloned_dir = repo.clone_repo(tmp_dir,
                                 remove_if_exists=True,
                                 depth=1,
                                 ssh_key_filepath=ssh_key_filepath,
                                 username=username)
    namespace = get_ns_from_repo(repo)
    categories = ['split=customized_text_slide']
    async for _c in ingest_dir(cloned_dir,
                               namespace=namespace,
                               categories=categories):
        pass
    logging.info(f'cloned dir {cloned_dir} ingested, will removed')
    if keep_repo:
        shutil.rmtree(cloned_dir)


async def ingest_repos(repo_list,
                       tmp_dir=_default_repo_tmp_dir,
                       ssh_key_filepath: str = None,
                       keep_repo: bool = False,
                       username: str = None):
    if not os.path.isabs(tmp_dir):
        raise Exception(f'tmp_dir must be absolute path, got {tmp_dir}')
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    for repo_url in repo_list:
        logger.info(f'ingesting repo: {repo_url}')
        await ingest_repo(repo_url,
                          tmp_dir=tmp_dir,
                          ssh_key_filepath=ssh_key_filepath,
                          keep_repo=keep_repo,
                          username=username)
