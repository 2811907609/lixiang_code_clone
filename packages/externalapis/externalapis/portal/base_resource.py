class BaseResource:

    def __init__(self, client):
        self.client = client

    @property
    def base_url(self):
        return self.client.base_url
