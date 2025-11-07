"""
Data models for QueueCTL job queue system.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
import json


class JobState:
    """Job state constants."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD = "dead"


@dataclass
class Job:
    """Represents a job in the queue."""
    id: str
    command: str
    state: str = JobState.PENDING
    attempts: int = 0
    max_retries: int = 3
    created_at: str = None
    updated_at: str = None
    next_retry_at: Optional[str] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """Initialize timestamps if not provided."""
        now = datetime.utcnow().isoformat() + "Z"
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now
    
    def to_dict(self) -> dict:
        """Convert job to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert job to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Job':
        """Create job from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Job':
        """Create job from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class Config:
    """System configuration."""
    max_retries: int = 3
    backoff_base: int = 2
    worker_poll_interval: float = 1.0
    job_timeout: int = 300  # 5 minutes
    
    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Config':
        """Create config from dictionary."""
        return cls(**data)
