from typing import Optional

from .gitlab_provider import GitLabProvider
from .provider import RepoProvider


class ProviderFactory:

    @staticmethod
    def create_provider(provider_type: str, base_url: str, token: str) -> Optional[RepoProvider]:
        provider_type = provider_type.lower()

        if provider_type == 'gitlab':
            return GitLabProvider(base_url, token)
        elif provider_type == 'gerrit':
            raise NotImplementedError("Gerrit provider not implemented yet")
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")

    @staticmethod
    def auto_detect_provider(base_url: str) -> str:
        if 'gitlab' in base_url.lower():
            return 'gitlab'
        elif 'gerrit' in base_url.lower():
            return 'gerrit'
        else:
            raise ValueError(f"Cannot auto-detect provider type from URL: {base_url}")
