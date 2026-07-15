import json
import csv
from pathlib import Path

def test_sample_inventory_json():
    json_path = Path("examples/sample_inventory.json")
    assert json_path.exists()
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert "site_id" in data
    assert "site_name" in data
    assert "web_url" in data
    assert "hostname" in data
    assert "path" in data
    assert "lists" in data
    
    assert len(data["lists"]) > 0
    for lst in data["lists"]:
        assert "list_id" in lst
        assert "list_name" in lst
        assert "list_display_name" in lst
        assert "web_url" in lst
        assert "fields" in lst
        assert "fields_count" in lst
        assert lst["fields_count"] == len(lst["fields"])
        
        for fld in lst["fields"]:
            assert "field_id" in fld
            assert "name" in fld
            assert "display_name" in fld
            assert "field_type" in fld
            assert isinstance(fld["is_required"], bool)
            assert isinstance(fld["is_read_only"], bool)
            assert isinstance(fld["is_hidden"], bool)
            assert isinstance(fld["is_system"], bool)

def test_sample_inventory_csv():
    csv_path = Path("examples/sample_inventory.csv")
    assert csv_path.exists()
    
    expected_headers = [
        "List Name",
        "List ID",
        "Field Name",
        "Field Display Name",
        "Field ID",
        "Field Type",
        "Is Required",
        "Is Read Only",
        "Is Hidden",
        "Is System",
    ]
    
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        assert headers == expected_headers
        
        rows = list(reader)
        assert len(rows) > 0
        for row in rows:
            assert len(row) == len(expected_headers)
            # Boolean values should be serialized as string representations of bools
            assert row[6] in ("True", "False")
            assert row[7] in ("True", "False")
            assert row[8] in ("True", "False")
            assert row[9] in ("True", "False")
