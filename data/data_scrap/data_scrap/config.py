import os
from dataclasses import dataclass, field


@dataclass
class Config:
    # 研发区域，比如 fsd 智驾红区，chip 芯片红区，默认None表示公共区
    RD_ZONE: str = field(
        default_factory=lambda: os.getenv("RD_ZONE", ""))

    # GitLab configuration
    GITLAB_URL: str = field(
        default_factory=lambda: os.getenv("GITLAB_URL", ""))
    GITLAB_TOKEN: str = field(
        default_factory=lambda: os.getenv("GITLAB_TOKEN", ""))

    # Event receiver configuration
    EVENT_RECEIVER_URL: str = field(
        default_factory=lambda: os.getenv("EVENT_RECEIVER_URL", ""))

    # Kafka configuration
    KAFKA_BOOTSTRAP_SERVERS: str = field(
        default_factory=lambda: os.getenv("KAFKA_BOOTSTRAP_SERVERS", "10.134.11.122:9092,10.134.11.121:9092,10.134.11.120:9092"))
    TARGET_TOPIC: str = field(
        default_factory=lambda: os.getenv("TARGET_TOPIC", ""))

    # Database configuration
    REPO_DB_PATH: str = field(
        default_factory=lambda: os.getenv("REPO_DB_PATH", "repo_status.duckdb"))

    # Scraping configuration
    BATCH_SIZE: int = field(
        default_factory=lambda: int(os.getenv("BATCH_SIZE", "10")))
    MAX_SIZE_BYTES: int = field(
        default_factory=lambda: int(os.getenv("MAX_SIZE_BYTES", "1024000")))
    NO_SSL_VERIFY: bool = field(
        default_factory=lambda: os.getenv("NO_SSL_VERIFY", "true").lower() == "true")

    # Date range configuration (defaults to last 30 days if not specified)
    START_DATE: str = field(
        default_factory=lambda: os.getenv("START_DATE", ""))
    END_DATE: str = field(
        default_factory=lambda: os.getenv("END_DATE", ""))

    # Retry configuration
    RETRY_DELAY_HOURS: int = field(
        default_factory=lambda: int(os.getenv("RETRY_DELAY_HOURS", "1")))
    NEXT_COLLECT_HOURS: int = field(
        default_factory=lambda: int(os.getenv("NEXT_COLLECT_HOURS", "24")))
    STUCK_THRESHOLD_HOURS: int = field(
        default_factory=lambda: int(os.getenv("STUCK_THRESHOLD_HOURS", "2")))


config = Config()
