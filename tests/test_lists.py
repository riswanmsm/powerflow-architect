from unittest.mock import MagicMock
import pytest

from src.sharepoint.client import SharePointClient
from src.sharepoint.list_service import ListService

def test_get_lists():
    mock_client = MagicMock(spec=SharePointClient)
    
    # Mock payload returned by fetch_lists
    mock_payload = [
        {
            "id": "list-id-1",
            "name": "documents",
            "displayName": "Documents",
            "webUrl": "https://tenant.sharepoint.com/sites/site/Shared Documents"
        },
        {
            "id": "list-id-2",
            "name": "custom_list",
            "displayName": "Custom List",
            "webUrl": "https://tenant.sharepoint.com/sites/site/Lists/CustomList"
        }
    ]
    mock_client.fetch_lists.return_value = mock_payload
    
    list_service = ListService(mock_client)
    lists = list_service.get_lists("site-id-xyz")
    
    # Assertions
    assert len(lists) == 2
    
    assert lists[0].id == "list-id-1"
    assert lists[0].name == "documents"
    assert lists[0].display_name == "Documents"
    assert lists[0].web_url == "https://tenant.sharepoint.com/sites/site/Shared Documents"
    assert lists[0].fields == []
    
    assert lists[1].id == "list-id-2"
    assert lists[1].name == "custom_list"
    assert lists[1].display_name == "Custom List"
    assert lists[1].web_url == "https://tenant.sharepoint.com/sites/site/Lists/CustomList"
    assert lists[1].fields == []
    
    mock_client.fetch_lists.assert_called_once_with("site-id-xyz")
