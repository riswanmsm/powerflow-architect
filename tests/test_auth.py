import datetime
from unittest.mock import MagicMock, patch
import pytest

from src.auth.models import AccessToken, SessionState
from src.auth.session_manager import AuthenticationProvider
from src.auth.token_provider import BaseTokenProvider
from src.auth.playwright_provider import PlaywrightTokenProvider

def test_access_token_expiration():
    # Not expired
    future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)
    token = AccessToken(token_value="test_token", expires_on=future)
    assert not token.is_expired()

    # Expired (within 5-minute buffer)
    near_future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=3)
    token_near = AccessToken(token_value="test_token", expires_on=near_future)
    assert token_near.is_expired()

    # Fully expired
    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=10)
    token_expired = AccessToken(token_value="test_token", expires_on=past)
    assert token_expired.is_expired()

def test_auth_provider_caching():
    # Setup mock return values
    token1 = AccessToken(
        token_value="token1", 
        expires_on=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)
    )
    token2 = AccessToken(
        token_value="token2", 
        expires_on=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)
    )
    
    provider = PlaywrightTokenProvider()
    
    with patch.object(provider, "_capture_session") as mock_capture:
        mock_capture.side_effect = [(token1, SessionState()), (token2, SessionState())]
        
        auth_manager = AuthenticationProvider(provider=provider)
        
        # First fetch should call _capture_session
        t1 = auth_manager.get_access_token()
        assert t1 == "token1"
        assert mock_capture.call_count == 1
        
        # Second fetch should use cached token from provider
        t2 = auth_manager.get_access_token()
        assert t2 == "token1"
        assert mock_capture.call_count == 1
        
        # Forced refresh should bypass cache
        t3 = auth_manager.get_access_token(force_refresh=True)
        assert t3 == "token2"
        assert mock_capture.call_count == 2

def test_session_decoration():
    mock_provider = MagicMock(spec=BaseTokenProvider)
    session_state = SessionState(
        headers={"Authorization": "Bearer abc", "X-Custom": "123"},
        cookies={"CookieKey": "CookieVal"}
    )
    mock_provider.get_session_state.return_value = session_state
    
    auth_manager = AuthenticationProvider(provider=mock_provider)
    session = auth_manager.get_session()
    
    assert session.headers.get("Authorization") == "Bearer abc"
    assert session.headers.get("X-Custom") == "123"
    assert session.cookies.get("CookieKey") == "CookieVal"
