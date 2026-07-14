import os
import time
import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs

from playwright.sync_api import sync_playwright, Request, TimeoutError as PlaywrightTimeoutError

from .token_provider import BaseTokenProvider
from .models import AccessToken, SessionState

class PlaywrightTokenProvider(BaseTokenProvider):
    """
    Acquires and maintains OAuth2 sessions and access tokens by reusing
    persistent authenticated browser sessions via Playwright.
    """

    def __init__(
        self,
        profile_dir: Optional[str] = None,
        validation_url: str = "https://make.powerautomate.com/",
        headless: bool = False,
        timeout_seconds: int = 300,
    ):
        """
        Initialize the PlaywrightTokenProvider.

        Args:
            profile_dir (str, optional): Path to the persistent browser profile directory.
            validation_url (str): Target URL used to trigger authentication capture.
            headless (bool): Run Playwright in headless mode.
            timeout_seconds (int): Maximum seconds to wait for authentication headers.
        """
        if profile_dir is None:
            # Default to a folder inside the current working directory.
            profile_dir = os.path.join(os.getcwd(), "playwright-profile")

        self.profile_dir = Path(profile_dir)
        self.validation_url = validation_url
        self.headless = headless
        self.timeout_seconds = timeout_seconds

        self._cached_token: Optional[AccessToken] = None
        self._cached_state: Optional[SessionState] = None

    def _is_target_request(self, request: Request) -> bool:
        """
        Evaluate if the captured request contains valid token credentials.
        We look for standard API endpoints such as /powerautomate/flows or
        Graph requests with an Authorization header.
        """
        url_lower = request.url.lower()
        
        # Capture Power Automate management or Graph API calls
        is_target_endpoint = (
            "/powerautomate/flows" in url_lower
            or "/providers/microsoft.powerapps" in url_lower
            or "graph.microsoft.com" in url_lower
        )
        
        if not is_target_endpoint:
            return False

        try:
            headers = request.all_headers()
        except Exception:
            headers = request.headers

        # Must contain authorization token
        has_auth = any(name.lower() == "authorization" for name in headers)
        return has_auth

    def _capture_session(self) -> tuple[AccessToken, SessionState]:
        """
        Launch Playwright, perform browser interaction, and capture headers/cookies.
        """
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        captured: Dict[str, Any] = {}

        def on_request(request: Request) -> None:
            if captured:
                return

            if not self._is_target_request(request):
                return

            try:
                headers = request.all_headers()
            except Exception:
                headers = request.headers

            auth_header = next(
                (v for k, v in headers.items() if k.lower() == "authorization"), 
                None
            )
            if not auth_header or not auth_header.startswith("Bearer "):
                return

            # Capture only relevant headers to avoid polluting subsequent client calls
            allowed_headers = {
                "authorization",
                "accept",
                "accept-language",
                "user-agent",
                "x-ms-client-session-id",
                "x-ms-client-request-id",
                "x-ms-user-agent",
                "x-ms-request-id",
            }
            clean_headers = {k: v for k, v in headers.items() if k.lower() in allowed_headers}

            captured["headers"] = clean_headers
            captured["token"] = auth_header.split(" ")[1]

        with sync_playwright() as playwright:
            # Configure launch arguments to be consistent with normal browser profiles
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=self.headless,
                viewport={"width": 1440, "height": 900},
                args=["--start-maximized"],
            )

            try:
                context.on("request", on_request)
                page = context.pages[0] if context.pages else context.new_page()

                # Navigate to the validation page
                page.goto(self.validation_url, wait_until="domcontentloaded", timeout=120_000)

                deadline = time.monotonic() + self.timeout_seconds
                while time.monotonic() < deadline:
                    if captured:
                        # Capture browser cookies from context
                        cookies = {c["name"]: c["value"] for c in context.cookies()}
                        captured["cookies"] = cookies
                        break
                    
                    try:
                        page.wait_for_timeout(500)
                    except PlaywrightTimeoutError:
                        pass

                if not captured:
                    raise TimeoutError(
                        f"Authentication capture timed out after {self.timeout_seconds} seconds."
                    )

            finally:
                context.close()

        # Parse token expiration (default to 50 minutes from now as typical Entra tokens last 1 hour)
        expires_on = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=50)
        
        token = AccessToken(
            token_value=captured["token"],
            token_type="Bearer",
            expires_on=expires_on
        )
        
        state = SessionState(
            headers=captured["headers"],
            cookies=captured["cookies"]
        )

        return token, state

    def get_token(self, force_refresh: bool = False) -> AccessToken:
        """Retrieve the cached token or trigger browser interaction if expired."""
        if force_refresh or not self._cached_token or self._cached_token.is_expired():
            token, state = self._capture_session()
            self._cached_token = token
            self._cached_state = state

        return self._cached_token

    def get_session_state(self, force_refresh: bool = False) -> SessionState:
        """Retrieve cached session state or trigger browser interaction if expired."""
        if force_refresh or not self._cached_state or (self._cached_token and self._cached_token.is_expired()):
            token, state = self._capture_session()
            self._cached_token = token
            self._cached_state = state

        return self._cached_state
