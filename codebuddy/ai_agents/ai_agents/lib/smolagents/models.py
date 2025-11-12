
"""
Extended LiteLLM model implementation with custom header support.

This module provides an enhanced version of the smolagents LiteLLMModel that allows
passing custom HTTP headers to the underlying LLM API calls. This is particularly
useful for authentication, request tracking, or other API-specific requirements.
"""

from smolagents import LiteLLMModel


class LiteLLMModelV2(LiteLLMModel):
    """
    Enhanced LiteLLM model with support for custom HTTP headers.

    This class extends the base LiteLLMModel to allow passing custom headers
    to the underlying LLM API requests. This is useful for scenarios where
    you need to:
    - Add custom authentication headers
    - Include request tracking headers
    - Pass API-specific metadata
    - Implement custom rate limiting or monitoring

    The custom headers are preserved and passed through to all completion
    requests made by this model instance.
    """
    def __init__(self, *args, **kwargs):
        # Extract custom headers before passing kwargs to parent
        # This prevents the parent class from receiving unknown parameters
        extra_headers = kwargs.pop("extra_headers", None)
        self._extra_headers = extra_headers
        super().__init__(*args, **kwargs)

    def _prepare_completion_kwargs(self, *args, **kwargs):
        completion_kwargs = super()._prepare_completion_kwargs(*args, **kwargs)

        # Only add extra_headers if they were provided during initialization
        # This avoids passing None or empty dict to the API
        if self._extra_headers:
            completion_kwargs["extra_headers"] = self._extra_headers

        return completion_kwargs
