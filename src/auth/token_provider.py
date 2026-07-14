from abc import ABC, abstractmethod
from .models import AccessToken, SessionState

class BaseTokenProvider(ABC):
    """Abstract base class defining interface for token and session extraction."""

    @abstractmethod
    def get_token(self, force_refresh: bool = False) -> AccessToken:
        """
        Retrieve a valid access token.
        
        Args:
            force_refresh (bool): Skip local cache and acquire a fresh token.
            
        Returns:
            AccessToken: The active oauth2 access token.
        """
        pass

    @abstractmethod
    def get_session_state(self, force_refresh: bool = False) -> SessionState:
        """
        Retrieve HTTP headers and cookies for request decoration.
        
        Args:
            force_refresh (bool): Skip local cache and acquire fresh session parameters.
            
        Returns:
            SessionState: Object containing request headers and cookies.
        """
        pass
