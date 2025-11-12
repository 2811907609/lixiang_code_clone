#! /bin/bash

export TARGET_TOPIC=gerritprod-perceval-gerrit-review
export SCRAP_DB_URI="postgres://app_datascrap:$DATA_SCRAP_PG_PASSWD@ep-portal-pg.rdsgrlkfekaocya.rds.bj.baidubce.com:3306/datascrap_prod"
export GERRIT_USER=chjscm

cd "$(dirname "$0")"
uv run scrap_changes.py main
