import os

import requests


def getConfiguration(category, key):
    base_url = os.getenv("PORTAL_BASE_URL","https://portal-k8s-staging.ep.chehejia.com")
    url = f"""{base_url}/api/v2/public/configuration?category={category}&key={key}"""
    resp = requests.get(url, timeout=10)
    return resp.json()
