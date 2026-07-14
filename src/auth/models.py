from dataclasses import dataclass, field
from typing import Dict, Optional
import datetime

@dataclass
class AccessToken:
    """Represents an OAuth2 access token with value and expiration metadata."""
    token_value: str
    token_type: str = "Bearer"
    expires_on: Optional[datetime.datetime] = None

    def is_expired(self) -> bool:
        """Check if the token is expired or close to expiration (5-minute buffer)."""
        if not self.expires_on:
            return False
        
        # Ensure comparison is timezone-aware if expires_on is timezone-aware
        now = datetime.datetime.now(self.expires_on.tzinfo or datetime.timezone.utc)
        buffer = datetime.timedelta(minutes=5)
        return now >= (self.expires_on - buffer)

@dataclass
class SessionState:
    """Represents HTTP session parameters including headers and cookies."""
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
