import os
import secrets
from dataclasses import dataclass, field

@dataclass
class Settings:
    database_url: str = field(default_factory=lambda: os.getenv('DATABASE_URL', 'sqlite:///./yatharth.db'))
    jwt_secret: str = field(default_factory=lambda: os.getenv('JWT_SECRET') or secrets.token_urlsafe(48))
    token_minutes: int = 60
    high_threshold: int = field(default_factory=lambda: int(os.getenv('HIGH_THRESHOLD', '60')))
    critical_threshold: int = field(default_factory=lambda: int(os.getenv('CRITICAL_THRESHOLD', '80')))
    medium_threshold: int = 30
    retention_days: int = field(default_factory=lambda: int(os.getenv('RETENTION_DAYS', '30')))
    llm_enabled: bool = field(default_factory=lambda: os.getenv('LLM_ENABLED', 'false').lower() == 'true')
    openworker_enabled: bool = field(default_factory=lambda: os.getenv('OPENWORKER_ENABLED', 'false').lower() == 'true')
    llm_url: str = field(default_factory=lambda: os.getenv('LLM_URL', ''))
    llm_key: str = field(default_factory=lambda: os.getenv('LLM_API_KEY', ''))
    llm_model: str = field(default_factory=lambda: os.getenv('LLM_MODEL', ''))
    cors_origins: list[str] = field(default_factory=lambda: [x for x in os.getenv('CORS_ORIGINS', '').split(',') if x])

    def __post_init__(self):
        if not 0 < self.medium_threshold < self.high_threshold < self.critical_threshold <= 100:
            raise ValueError('Risk thresholds must be strictly increasing and <=100')
        if self.retention_days < 1 or len(self.jwt_secret) < 32:
            raise ValueError('Retention must be positive; JWT secret must be at least 32 characters')
