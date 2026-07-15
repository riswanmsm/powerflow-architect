import json
import pytest
from pathlib import Path

from src.flow_definition.models import FlowContext
from src.flow_definition.placeholder_resolver import PlaceholderResolver
from src.flow_definition.template_loader import TemplateLoader
from src.flow_definition.definition_engine import FlowDefinitionEngine

@pytest.fixture
def sample_template_str():
    return """{
        "flow_name": "Sync_${LIST_NAME}",
        "site": "${SITE_URL}",
        "trigger": "${TRIGGER_NAME}",
        "excel_path": "${EXCEL_FILE}",
        "excel_table": "${EXCEL_TABLE}",
        "mapping": ${VALUE_OBJECT}
    }"""

def test_placeholder_resolver_success(sample_template_str):
    value_obj = {"Title": "@items('Apply_to_each_1')?['Title']"}
    
    resolved = PlaceholderResolver.resolve(
        template_str=sample_template_str,
        list_name="REG_Risks",
        excel_file="Risks.xlsx",
        excel_table="RisksTable",
        value_object=value_obj,
        trigger_name="OnNewItem",
        site_url="https://mysite.com"
    )
    
    assert resolved["flow_name"] == "Sync_REG_Risks"
    assert resolved["site"] == "https://mysite.com"
    assert resolved["trigger"] == "OnNewItem"
    assert resolved["excel_path"] == "Risks.xlsx"
    assert resolved["excel_table"] == "RisksTable"
    assert resolved["mapping"] == value_obj

def test_placeholder_resolver_unresolved_placeholder_raises_error(sample_template_str):
    value_obj = {"Title": "@items('Apply_to_each_1')?['Title']"}
    # Leave out one placeholder in the template to test detection
    broken_template = sample_template_str + '\n, "extra": "${MISSING_FIELD}"'
    
    with pytest.raises(ValueError) as excinfo:
        PlaceholderResolver.resolve(
            template_str=broken_template,
            list_name="REG_Risks",
            excel_file="Risks.xlsx",
            excel_table="RisksTable",
            value_object=value_obj,
            trigger_name="OnNewItem",
            site_url="https://mysite.com"
        )
    assert "Unresolved placeholders found in template: ${MISSING_FIELD}" in str(excinfo.value)

def test_placeholder_resolver_invalid_json_raises_error(sample_template_str):
    value_obj = {"Title": "@items('Apply_to_each_1')?['Title']"}
    # Make the template structurally invalid JSON
    broken_template = sample_template_str + "\ninvalid_syntax"
    
    with pytest.raises(ValueError) as excinfo:
        PlaceholderResolver.resolve(
            template_str=broken_template,
            list_name="REG_Risks",
            excel_file="Risks.xlsx",
            excel_table="RisksTable",
            value_object=value_obj,
            trigger_name="OnNewItem",
            site_url="https://mysite.com"
        )
    assert "Resolved flow template is not valid JSON" in str(excinfo.value)

@pytest.fixture
def mock_inventory_for_flows(tmp_path):
    inventory_data = {
        "site_id": "site-id",
        "site_name": "Test Site",
        "lists": [
            {
                "list_id": "lst-risks",
                "list_name": "REG_Risks",
                "list_display_name": "REG_Risks",
                "fields": [
                    {
                        "field_id": "f1",
                        "name": "Title",
                        "display_name": "Title",
                        "is_system": True,
                        "field_type": "Text"
                    }
                ]
            }
        ]
    }
    input_path = tmp_path / "inventory.json"
    with open(input_path, "w", encoding="utf-8") as f:
        json.dump(inventory_data, f)
    return input_path

def test_definition_engine_generates_outputs(tmp_path, mock_inventory_for_flows, sample_template_str):
    # Write sample template to a file
    template_path = tmp_path / "flow_template.json"
    with open(template_path, "w", encoding="utf-8") as f:
        f.write(sample_template_str)
        
    output_dir = tmp_path / "flow_definitions"
    
    engine = FlowDefinitionEngine(
        inventory_path=str(mock_inventory_for_flows),
        template_path=str(template_path)
    )
    
    flow_ctx = FlowContext(
        excel_file_pattern="Sync_{list_name}.xlsx",
        excel_table_pattern="tbl_{list_name}",
        trigger_name="WhenNewItemCreated",
        site_url="https://sharepoint.com/site"
    )
    
    definitions = engine.generate_definitions(
        output_dir=str(output_dir),
        flow_ctx=flow_ctx
    )
    
    assert len(definitions) == 1
    d = definitions[0]
    assert d.list_name == "REG_Risks"
    
    # Verify file is written
    out_file = output_dir / "REG_Risks.json"
    assert out_file.exists()
    
    with open(out_file, "r", encoding="utf-8") as f:
        saved_json = json.load(f)
        
    assert saved_json["flow_name"] == "Sync_REG_Risks"
    assert saved_json["site"] == "https://sharepoint.com/site"
    assert saved_json["trigger"] == "WhenNewItemCreated"
    assert saved_json["excel_path"] == "Sync_REG_Risks.xlsx"
    assert saved_json["excel_table"] == "tbl_REG_Risks"
    assert saved_json["mapping"] == {"Title": "@items('Apply_to_each_1')?['Title']"}
