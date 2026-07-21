import csv
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

from src.automation.automation_engine import normalize_expression, PowerAutomateAutomationEngine
from src.automation.cli import register_subcommand

def test_normalize_expression():
    """Verifies that expressions are correctly stripped/unwrapped for the formula editor."""
    assert normalize_expression("@triggerBody()?['Title']") == "triggerBody()?['Title']"
    assert normalize_expression("@{items('Apply_to_each_1')?['Title']}") == "items('Apply_to_each_1')?['Title']"
    assert normalize_expression("variables('var')") == "variables('var')"
    assert normalize_expression("  @variables('var')  ") == "variables('var')"
    assert normalize_expression("") == ""
    assert normalize_expression(None) == ""

def test_load_expressions_csv(tmp_path):
    """Verifies that the CSV expression mapping database is parsed correctly."""
    csv_file = tmp_path / "expressions.csv"
    
    # Write a test CSV structure
    headers = [
        "List Name",
        "Internal Field Name",
        "Display Name",
        "Normalized Field Type",
        "Direct Trigger Expression",
        "Foreach Expression"
    ]
    rows = [
        ["ListA", "Field1", "Field One", "Text", "@triggerBody()?['F1']", "@items('A')?['F1']"],
        ["ListA", "Field2", "Field Two", "Choice", "@triggerBody()?['F2']", ""],
        ["ListB", "Title", "Title", "Text", "@triggerBody()?['Title']", "@items('B')?['Title']"]
    ]
    
    with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
        
    engine = PowerAutomateAutomationEngine(expressions_file=str(csv_file))
    db = engine.load_expressions()
    
    # Check ListA field mapping
    assert "ListA" in db
    assert "Field One" in db["ListA"]
    assert db["ListA"]["Field One"]["direct_trigger"] == "@triggerBody()?['F1']"
    assert db["ListA"]["Field One"]["foreach"] == "@items('A')?['F1']"
    
    # Check empty expressions are preserved
    assert db["ListA"]["Field Two"]["foreach"] == ""
    
    # Check ListB mapping
    assert "ListB" in db
    assert "Title" in db["ListB"]



def test_cli_subcommand_registration():
    """Verifies that the automate subcommand is registered correctly with all arguments."""
    import argparse
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    
    sub_parser = register_subcommand(subparsers)
    assert sub_parser is not None
    
    # Test parsing arguments with optional parameters omitted
    args = parser.parse_args(["automate"])
    assert args.command == "automate"
    assert args.flow_url is None
    assert args.list_name is None
    assert args.mode == "foreach"
    assert args.headless is False

def test_run_automation_interactive_prompts():
    """Verifies that run_automation prompts for flow-url and list-name if they are omitted."""
    from src.automation.cli import run_automation
    import argparse
    
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    register_subcommand(subparsers)
    args = parser.parse_args(["automate"])
    
    with patch("builtins.input", side_effect=["http://prompt-flow.com", "LIST_Prompted"]), \
         patch("src.automation.automation_engine.PowerAutomateAutomationEngine") as mock_engine_class, \
         patch("sys.exit") as mock_exit:
         
        mock_engine = mock_engine_class.return_value
        mock_engine.run.return_value = True
        
        run_automation(args)
        
        # Verify engine was initialized with parsed values
        mock_engine_class.assert_called_once()
        # Verify engine.run was called with prompted URL and List name
        mock_engine.run.assert_called_once_with(
            flow_url="http://prompt-flow.com",
            list_name="LIST_Prompted",
            mode="foreach"
        )
        mock_exit.assert_called_once_with(0)

def test_run_automation_config_file():
    """Verifies that run_automation reads flow-url and list-name from config.json if omitted on CLI."""
    from src.automation.cli import run_automation
    import argparse
    import json
    from pathlib import Path
    
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    register_subcommand(subparsers)
    args = parser.parse_args(["automate"])
    
    config_data = {
        "flow_url": "http://config-flow.com",
        "list_name": "LIST_ConfigJson"
    }
    
    with patch.object(Path, "exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=json.dumps(config_data))), \
         patch("builtins.input") as mock_input, \
         patch("src.automation.automation_engine.PowerAutomateAutomationEngine") as mock_engine_class, \
         patch("sys.exit") as mock_exit:
         
        mock_engine = mock_engine_class.return_value
        mock_engine.run.return_value = True
        
        run_automation(args)
        
        # Verify no interactive prompts were called since config.json was used
        mock_input.assert_not_called()
        
        # Verify engine was initialized and run was called with config.json values
        mock_engine_class.assert_called_once()
        mock_engine.run.assert_called_once_with(
            flow_url="http://config-flow.com",
            list_name="LIST_ConfigJson",
            mode="foreach"
        )
        mock_exit.assert_called_once_with(0)

def test_find_action_card():
    """Verifies that find_action_card tries cascading selectors and returns first visible locator."""
    engine = PowerAutomateAutomationEngine()
    mock_page = MagicMock()
    mock_locator = MagicMock()
    mock_locator.count.return_value = 2
    
    mock_visible_loc = MagicMock()
    mock_visible_loc.is_visible.return_value = True
    
    mock_locator.nth.side_effect = [MagicMock(is_visible=lambda: False), mock_visible_loc]
    mock_page.locator.return_value = mock_locator
    
    card = engine.find_action_card(mock_page, "Get items")
    assert card == mock_visible_loc
    assert mock_page.locator.call_count == 1

def test_set_property_value_success():
    """Verifies set_property_value locates label/input, interacts, and returns True."""
    engine = PowerAutomateAutomationEngine()
    mock_page = MagicMock()
    
    # Create simple mock structure for label and control
    mock_label = MagicMock()
    mock_label.first.is_visible.return_value = True
    
    mock_control = MagicMock()
    mock_control.is_visible.return_value = True
    mock_control.first.is_visible.return_value = True
    mock_control.get_attribute.return_value = "combobox"
    
    # Make locator calls on mock_label.first return the mock control locator
    mock_label.first.locator.return_value = mock_control
    
    # Mock options list
    mock_option = MagicMock()
    mock_option.first.is_visible.return_value = True
    mock_option.count.return_value = 1
    
    # Make locator calls on mock_page return label, option lists, and custom items
    mock_page.locator.side_effect = lambda selector: (
        mock_label if "List Name" in selector or "label" in selector else (
            mock_option if "option" in selector else MagicMock()
        )
    )
    
    mock_page.keyboard = MagicMock()
    
    success = engine.set_property_value(mock_page, "List Name", "REG_InformationSystems")
    assert success is True
    # We click the control itself
    assert mock_control.first.click.call_count == 1
    # We click the target option found in page.locator('[role="option"]...')
    assert mock_option.first.click.call_count == 1

def test_full_run_execution():
    """Verifies that the run method goes through all Phase 1 and Phase 2 edits, and saves successfully."""
    engine = PowerAutomateAutomationEngine()
    
    mock_db = {
        "ListA": {
            "Title": {
                "direct_trigger": "@triggerBody()?['Title']",
                "foreach": "@items('Apply_to_each_1')?['Title']"
            }
        }
    }
    
    mock_page = MagicMock()
    mock_page.url = "https://make.powerautomate.com/environments/env/flows/flow"
    mock_page.title.return_value = "Powerflow - ListA | Power Automate"
    
    # Mock locator visibility checks
    mock_page.locator.return_value.first.is_visible.return_value = True
    mock_page.locator.return_value.count.return_value = 1
    
    with patch.object(engine, "load_expressions", return_value=mock_db), \
         patch.object(engine, "find_action_card") as mock_find_card, \
         patch.object(engine, "select_excel_file_from_picker", return_value=True) as mock_select_picker, \
         patch.object(engine, "expand_canvas_containers") as mock_expand, \
         patch.object(engine, "click_show_all_parameters") as mock_show_all, \
         patch.object(engine, "set_property_value", return_value=True) as mock_set_prop, \
         patch.object(engine, "wait_for_any_visible", return_value=True), \
         patch("builtins.input", return_value=""), \
         patch("src.automation.automation_engine.sync_playwright") as mock_play:
         
        mock_context = mock_play.return_value.__enter__.return_value.chromium.launch_persistent_context.return_value
        mock_context.pages = [mock_page]
        
        # Define mock cards returned by find_action_card
        mock_card = MagicMock()
        mock_find_card.return_value = mock_card
        
        # Run the full automation loop
        success = engine.run(
            flow_url="https://make.powerautomate.com/environments/env/flows/flow",
            list_name="ListA",
            mode="foreach"
        )
        
        # Verify execution
        assert success is True
        
        # Verify canvas operations are skipped
        assert mock_find_card.call_count == 0
        assert mock_select_picker.call_count == 0
        assert mock_set_prop.call_count == 0
        assert mock_expand.call_count == 0
        assert mock_show_all.call_count == 0
        
        # Verify page save button was searched for
        called_selectors = [args[0][0] for args in mock_page.locator.call_args_list]
        save_selectors = [
            'button:has-text("Save draft")',
            'button:has-text("Save")',
            'button[aria-label="Save"]',
            'button[aria-label*="Save"]',
            '#save-flow-button'
        ]
        assert any(sel in called_selectors for sel in save_selectors)

def test_auto_detect_mode_and_extra_fields():
    """Verifies that flow name auto-detection changes the mode to direct_trigger and maps extra fields."""
    engine = PowerAutomateAutomationEngine(expressions_file="dummy.csv")
    mock_db = {
        "LIST_Environments": {
            "Title": {"direct_trigger": "@triggerBody()?['Title']", "foreach": "@items('A')?['Title']"}
        }
    }
    
    mock_page = MagicMock()
    mock_page.url = "https://make.powerautomate.com/environments/env/flows/flow"
    
    # Mock header label returning the flow name with "sync add update" in it
    mock_header = MagicMock()
    mock_header.is_visible.return_value = True
    mock_header.first = mock_header
    mock_header.get_attribute.return_value = "The flow name is LIST_Environments - Sync Add Update. Press enter to edit."
    
    # Configure page locator side-effects
    mock_page.locator.side_effect = lambda selector: (
        mock_header if selector == '[aria-label^="The flow name is"]' else MagicMock()
    )
    
    with patch.object(engine, "load_expressions", return_value=mock_db), \
         patch.object(engine, "find_action_card"), \
         patch.object(engine, "select_excel_file_from_picker", return_value=True), \
         patch.object(engine, "expand_canvas_containers"), \
         patch.object(engine, "click_show_all_parameters"), \
         patch.object(engine, "set_property_value", return_value=True), \
         patch.object(engine, "wait_for_any_visible", return_value=True), \
         patch("builtins.input", return_value=""), \
         patch("src.automation.automation_engine.sync_playwright") as mock_play:
         
        mock_context = mock_play.return_value.__enter__.return_value.chromium.launch_persistent_context.return_value
        mock_context.pages = [mock_page]
        
        # We will spy on the mapping loop to see which values get filled
        filled_values = []
        
        # We intercept calls to input_box.fill and input_box.type
        mock_input = MagicMock()
        mock_input.is_visible.return_value = True
        mock_input.first = mock_input
        
        # Replace locators for fields to return our mock input
        mock_page.locator.side_effect = lambda selector: (
            mock_header if selector == '[aria-label^="The flow name is"]' else mock_input
        )
        
        mock_input.fill.side_effect = lambda val: filled_values.append(val)
        mock_input.type.side_effect = lambda val: filled_values.append(val)
        
        success = engine.run(
            flow_url="https://make.powerautomate.com/environments/env/flows/flow",
            list_name="LIST_Environments",
            mode="foreach" # Initially foreach, but should auto-detect to direct_trigger
        )
        
        assert success is True
        
        # Extract values filled via mock_input.evaluate
        for call in mock_input.evaluate.call_args_list:
            args = call[0]
            if len(args) > 1:
                filled_values.append(args[1])
                
        # Verify direct_trigger values were filled instead of foreach:
        assert "@triggerBody()?['Title']" in filled_values
        assert "@triggerBody()?['ID']" in filled_values
        assert "LIST_Environments" in filled_values
        assert "Governance" in filled_values
        assert "@formatDateTime(convertTimeZone(utcNow(),'UTC','GMT Standard Time'),'yyyy-MM-dd HH:mm')" in filled_values
        # Ensure the foreach version of SharePointItemID was NOT used
        assert "@items('Apply_to_each_1')?['ID']" not in filled_values
