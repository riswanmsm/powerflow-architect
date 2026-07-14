import pytest
from src.sharepoint.classifier import FieldClassifier

def test_classify_lookup_single():
    col = {
        "id": "col1",
        "name": "Project",
        "displayName": "Project Lookup",
        "lookup": {
            "allowMultipleValues": False,
            "listId": "some-list-id"
        }
    }
    f = FieldClassifier.classify(col)
    assert f.field_type == "Lookup"
    assert f.is_system is False

def test_classify_lookup_multi():
    col = {
        "id": "col2",
        "name": "Projects",
        "displayName": "Projects Lookup Multi",
        "lookup": {
            "allowMultipleValues": True,
            "listId": "some-list-id"
        }
    }
    f = FieldClassifier.classify(col)
    assert f.field_type == "LookupMulti"
    assert f.is_system is False

def test_classify_choice_single():
    col = {
        "id": "col3",
        "name": "Status",
        "displayName": "Status Choice",
        "choice": {
            "choices": ["Open", "Closed"],
            "displayAs": "dropDownMenu"
        }
    }
    f = FieldClassifier.classify(col)
    assert f.field_type == "Choice"
    assert f.is_system is False

def test_classify_choice_multi():
    col = {
        "id": "col4",
        "name": "Tags",
        "displayName": "Tags Choice Multi",
        "choice": {
            "choices": ["A", "B"],
            "displayAs": "checkBoxes"
        }
    }
    f = FieldClassifier.classify(col)
    assert f.field_type == "ChoiceMulti"
    assert f.is_system is False

def test_classify_person_single():
    col = {
        "id": "col5",
        "name": "Manager",
        "displayName": "Manager Person",
        "personOrGroup": {
            "allowMultipleSelection": False
        }
    }
    f = FieldClassifier.classify(col)
    assert f.field_type == "Person"
    assert f.is_system is False

def test_classify_person_multi():
    col = {
        "id": "col6",
        "name": "TeamMembers",
        "displayName": "Team Members Person Multi",
        "personOrGroup": {
            "allowMultipleSelection": True
        }
    }
    f = FieldClassifier.classify(col)
    assert f.field_type == "PersonMulti"
    assert f.is_system is False

def test_classify_managed_metadata():
    col = {
        "id": "col7",
        "name": "Department",
        "displayName": "Department Managed Metadata",
        "term": {
            "allowMultipleValues": False
        }
    }
    f = FieldClassifier.classify(col)
    assert f.field_type == "Managed Metadata"
    assert f.is_system is False

def test_classify_calculated():
    col = {
        "id": "col8",
        "name": "TotalPrice",
        "displayName": "Total Price",
        "calculated": {
            "outputType": "currency",
            "formula": "=[Quantity]*[UnitPrice]"
        }
    }
    f = FieldClassifier.classify(col)
    assert f.field_type == "Calculated"
    assert f.is_system is False

def test_classify_system_and_attributes():
    col = {
        "id": "col9",
        "name": "Created",
        "displayName": "Created Date",
        "required": True,
        "readOnly": True,
        "hidden": False,
        "dateTime": {}
    }
    f = FieldClassifier.classify(col)
    assert f.field_type == "DateTime"
    assert f.is_system is True
    assert f.is_required is True
    assert f.is_read_only is True
    assert f.is_hidden is False
