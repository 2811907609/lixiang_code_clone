

## how to develop a new app
Read `./docs/add_new_agent_app.md` to develop a new app.

## publish
1. run `uv run build_wheel.py` to build packages, output in `dist`.
2. run `uv publish --index liauto --username ep-portal-rt-svc --password xxx`` to publish to artifactory.
3. run `uv tool run  --default-index "https://artifactory.ep.chehejia.com/artifactory/api/pypi/pypi-remote/simple" --index "https://artifactory.ep.chehejia.com/artifactory/api/pypi/liauto-pypi-l5/simple" --from "ai_agents[simple]"  ept_simple_cli -h` to run the cli.
