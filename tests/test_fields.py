from unittest.mock import MagicMock
import pytest

from src.sharepoint.client import SharePointClient
from src.sharepoint.field_service import FieldService

def test_get_fields():
    mock_client = MagicMock(spec=SharePointClient)
    
    # Mock payload returned by fetch_columns
    mock_payload = [
        {
            "id": "col-id-1",
            "name": "Title",
            "displayName": "Title",
            "required": True,
            "readOnly": False,
            "hidden": False,
            "text": {}
        },
        {
            "id": "col-id-2",
            "name": "AssignedTo",
            "displayName": "Assigned To",
            "required": False,
            "readOnly": False,
            "hidden": False,
            "personOrGroup": {
                "allowMultipleSelection": True
            }
        }
    ]
    mock_client.fetch_columns.return_value = mock_payload
    
    field_service = FieldService(mock_client)
    fields = field_service.get_fields("site-id", "list-id")
    
    assert len(fields) == 2
    
    assert fields[0].id == "col-id-1"
    assert fields[0].name == "Title"
    assert fields[0].display_name == "Title"
    assert fields[0].field_type == "Text"
    assert fields[0].is_required is True
    assert fields[0].is_read_only is False
    assert fields[0].is_hidden is False
    assert fields[0].is_system is False  # 'Title' is treated as a user/custom column


    
    assert fields[1].id == "col-id-2"
    assert fields[1].name == "AssignedTo"
    assert fields[1].display_name == "Assigned To"
    assert fields[1].field_type == "PersonMulti"
    assert fields[1].is_required is False
    assert fields[1].is_read_only is False
    assert fields[1].is_hidden is False
    assert fields[1].is_system is False  # Custom
    
    mock_client.fetch_columns.assert_called_once_with("site-id", "list-id")
