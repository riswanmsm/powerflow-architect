from typing import Dict, Any, List as TypeList
from urllib.parse import urlparse
import requests

from src.auth import AuthenticationProvider

class SharePointClient:
    """
    HTTP client for Microsoft Graph API queries related to SharePoint sites,
    lists, and columns, using requests.Session with captured auth state.
    """

    def __init__(self, provider: AuthenticationProvider):
        self.provider = provider

    def _get_session(self) -> requests.Session:
        return self.provider.get_session()

    def resolve_site(self, site_url: str) -> Dict[str, Any]:
        """
        Resolve site URL to its Graph API metadata, containing the Site ID.
        Supports root sites and sub-sites.
        """
        # Clean site URL
        site_url = site_url.strip()
        if not site_url.startswith("http://") and not site_url.startswith("https://"):
            site_url = f"https://{site_url}"

        parsed = urlparse(site_url)
        hostname = parsed.netloc
        path = parsed.path.strip("/")

        # Root site vs subsite path resolution
        if path:
            url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:/{path}"
        else:
            url = f"https://graph.microsoft.com/v1.0/sites/{hostname}"

        session = self._get_session()
        response = session.get(url)
        
        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to resolve SharePoint site '{site_url}'. "
                f"Status code: {response.status_code}. Response: {response.text}"
            )

        return response.json()

    def fetch_lists(self, site_id: str) -> TypeList[Dict[str, Any]]:
        """
        Retrieve all lists in a given SharePoint site.
        """
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists"
        session = self._get_session()
        
        all_lists = []
        next_url = url

        # Handle pagination if a site contains many lists
        while next_url:
            response = session.get(next_url)
            if response.status_code != 200:
                raise RuntimeError(
                    f"Failed to fetch lists for site ID '{site_id}'. "
                    f"Status code: {response.status_code}. Response: {response.text}"
                )
            
            payload = response.json()
            all_lists.extend(payload.get("value", []))
            next_url = payload.get("@odata.nextLink")

        return all_lists

    def fetch_columns(self, site_id: str, list_id: str) -> TypeList[Dict[str, Any]]:
        """
        Retrieve all columns (fields) in a given SharePoint list.
        """
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/columns"
        session = self._get_session()
        
        all_columns = []
        next_url = url

        # Handle pagination for column definitions
        while next_url:
            response = session.get(next_url)
            if response.status_code != 200:
                raise RuntimeError(
                    f"Failed to fetch columns for list ID '{list_id}'. "
                    f"Status code: {response.status_code}. Response: {response.text}"
                )
            
            payload = response.json()
            all_columns.extend(payload.get("value", []))
            next_url = payload.get("@odata.nextLink")

        return all_columns
