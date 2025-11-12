# deprecated, we use langfuse
from phoenix.otel import register
from openinference.instrumentation.smolagents import SmolagentsInstrumentor

from ai_agents.config import config

if config.PHOENIX_ENDPOINT:
    register(endpoint=config.PHOENIX_ENDPOINT,)
    SmolagentsInstrumentor().instrument()
