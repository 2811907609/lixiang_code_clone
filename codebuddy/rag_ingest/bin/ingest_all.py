import logging

from rag_ingest.ingest import ingest_repos

logging.basicConfig(level=logging.DEBUG)

_repo_list = [
    # gerrit
    'gerrit.it.chehejia.com:29418/ep/web/ep-services',  # ssh://user@gerrit/project_path
    'gerrit.it.chehejia.com:29418/cpd/fsd/thor/drive-system',
    'gerrit.it.chehejia.com:29418/srdg/ssdk/firmware/scp-firmware',
    'gerrit.it.chehejia.com:29418/srdg/ssdk/multimedia/isp_control_tool',

    # gitlab CE
    'git@gitlab.chehejia.com:ep/ep-portal-fe.git',
    'git@gitlab.chehejia.com:ep/buildfarm/buildfarm-admin-server.git',
    'git@gitlab.chehejia.com:ep/ai/data-processing.git',
    'git@gitlab.chehejia.com:liware/limq-examples.git',
    'git@gitlab.chehejia.com:liware-devops/liware-devops-test.git',
    'git@gitlab.chehejia.com:schumacher_framework/dataflow_net.git',
    'git@gitlab.chehejia.com:lihal/libsys_diag.git',
    'git@gitlab.chehejia.com:lihal/camera_manager.git',
    'git@gitlab.chehejia.com:lihal/diag_service.git',
    'git@gitlab.chehejia.com:lihal/lihal_eol.git',
    'git@gitlab.chehejia.com:metrics/os-metrics-front.git',
    'git@gitlab.chehejia.com:cd_cristal121_118878/wxt-treesitter-test.git',

    # gitlab EE
    'git@gitlabee.chehejia.com:ep/integration/codebuddy-agent.git',
    'git@gitlabee.chehejia.com:ep/sre/openresty-conf.git',
    'git@gitlabee.chehejia.com:lianshan/livis.git',
    'git@gitlabee.chehejia.com:ep/integration/codebuddy-webview-panels.git',
]

_default_repo_tmp_dir = '/tmp/rag_ingest'


async def run(tmp_dir=_default_repo_tmp_dir,
              repos: str = None,
              ssh_key_filepath: str = None,
              username: str = None):
    if not repos:
        repos = _repo_list
    else:
        repos = repos.split(',')
        repos = [repo.strip() for repo in repos]
    await ingest_repos(repos,
                       tmp_dir=tmp_dir,
                       ssh_key_filepath=ssh_key_filepath,
                       username=username)


if __name__ == '__main__':
    import fire
    cmds = dict(run=run)
    fire.Fire(cmds)
