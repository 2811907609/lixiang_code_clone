
## Data Scrap Project


## Tools
### tools/gerrit
* scrap-changes.py
A tool to consume event from gerrit kafka topic and fetch change details and
 send to another topic. While a postgres table is used to record consuming
 progress and status.

### tools/gitcommits
A tool to scrape git commit data from repositories and send to Kafka topics.

## Deploy

To build the gerrit change scraper Docker image, run the following command at the git root:

```bash
docker build -t artifactory.ep.chehejia.com/ep-docker-test-local/portal/data_scrap_gerrit:v1 -f data/data_scrap/deploy/Dockerfile-gerrit-scrap .
```

To build the gitcommits scraper Docker image, run the following command at the git root:

```bash
docker build -t artifactory.ep.chehejia.com/ep-docker-test-local/portal/data_scrap_gitcommits:v1 -f data/data_scrap/deploy/Dockerfile-gerrit-scrap .
```
