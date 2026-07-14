import requests
from typing import Optional

from .token_provider import BaseTokenProvider
from .playwright_provider import PlaywrightTokenProvider
from .models import AccessToken, SessionState

class AuthenticationProvider:
    """
    Main authentication manager exposing a provider-independent interface
    for obtaining sessions and access tokens.
    """

    def __init__(self, provider: Optional[BaseTokenProvider] = None):
        """
        Initialize the AuthenticationProvider.

        Args:
            provider (BaseTokenProvider, optional): Authentication provider instance.
                Defaults to PlaywrightTokenProvider.
        """
        if provider is None:
            provider = PlaywrightTokenProvider()
        self.provider = provider

    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Retrieve a valid access token string.

        Args:
            force_refresh (bool): Skip local cache and acquire a fresh token.

        Returns:
            str: Raw access token value.
        """
        token: AccessToken = self.provider.get_token(force_refresh=force_refresh)
        return token.token_value

    def get_session(self, force_refresh: bool = False) -> requests.Session:
        """
        Retrieve a pre-configured requests.Session containing session cookies
        and headers.

        Args:
            force_refresh (bool): Skip local cache and acquire fresh session parameters.

        Returns:
            requests.Session: Configured session for HTTP client calls.
        """
        state: SessionState = self.provider.get_session_state(force_refresh=force_refresh)
        
        session = requests.Session()
        session.headers.update(state.headers)
        
        # Load captured cookies into session cookiejar
        for name, value in state.cookies.items():
            session.cookies.set(name, value)
            
        return session
