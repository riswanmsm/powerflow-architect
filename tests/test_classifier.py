import pytest
from src.sharepoint.classifier import FieldClassifier
from src.sharepoint.normalized_types import NormalizedFieldType
from src.sharepoint.mapping_capabilities import get_mapping_capability

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
    assert f.normalized_field_type == NormalizedFieldType.LOOKUP
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
    assert f.normalized_field_type == NormalizedFieldType.LOOKUP_MULTI
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
    assert f.normalized_field_type == NormalizedFieldType.CHOICE
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
    assert f.normalized_field_type == NormalizedFieldType.CHOICE_MULTI
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
    assert f.normalized_field_type == NormalizedFieldType.PERSON
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
    assert f.normalized_field_type == NormalizedFieldType.PERSON_MULTI
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
    assert f.normalized_field_type == NormalizedFieldType.MANAGED_METADATA
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
    assert f.normalized_field_type == NormalizedFieldType.CALCULATED
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
    assert f.normalized_field_type == NormalizedFieldType.DATE
    assert f.is_system is True
    assert f.is_required is True
    assert f.is_read_only is True
    assert f.is_hidden is False

def test_classify_rest_properties():
    # Choice with allow multi
    col_choice_multi = {
        "id": "col10",
        "name": "Categories",
        "displayName": "Categories Choice Multi",
        "TypeAsString": "Choice",
        "AllowMultipleValues": True
    }
    f1 = FieldClassifier.classify(col_choice_multi)
    assert f1.normalized_field_type == NormalizedFieldType.CHOICE_MULTI

    # User without allow multi
    col_user_single = {
        "id": "col11",
        "name": "Approver",
        "displayName": "Approver User",
        "TypeAsString": "User",
        "AllowMultipleValues": False
    }
    f2 = FieldClassifier.classify(col_user_single)
    assert f2.normalized_field_type == NormalizedFieldType.PERSON

    # Taxonomy field (Managed Metadata)
    col_term = {
        "id": "col12",
        "name": "Location",
        "displayName": "Location MM",
        "TypeAsString": "TaxonomyFieldType",
        "AllowMultipleValues": False
    }
    f3 = FieldClassifier.classify(col_term)
    assert f3.normalized_field_type == NormalizedFieldType.MANAGED_METADATA

def test_classify_unknown_fallback():
    col_unknown = {
        "id": "col13",
        "name": "UnsupportedCol",
        "displayName": "Unsupported Field",
        "customNonExistentFieldType": {}
    }
    f = FieldClassifier.classify(col_unknown)
    assert f.field_type == "Unknown"
    assert f.normalized_field_type == NormalizedFieldType.UNKNOWN

def test_mapping_capabilities():
    # Text mapping capability
    cap_text = get_mapping_capability(NormalizedFieldType.TEXT)
    assert cap_text.is_mappable is True
    assert cap_text.supports_join is False

    # LookupMulti mapping capability
    cap_lm = get_mapping_capability(NormalizedFieldType.LOOKUP_MULTI)
    assert cap_lm.is_mappable is True
    assert cap_lm.supports_join is True

    # Image mapping capability
    cap_img = get_mapping_capability(NormalizedFieldType.IMAGE)
    assert cap_img.is_mappable is False
    assert cap_img.supports_join is False

    # Unknown mapping capability
    cap_unk = get_mapping_capability(NormalizedFieldType.UNKNOWN)
    assert cap_unk.is_mappable is False
    assert cap_unk.supports_join is False
