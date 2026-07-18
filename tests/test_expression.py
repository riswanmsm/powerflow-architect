import pytest
from pathlib import Path
from src.sharepoint.normalized_types import NormalizedFieldType
from src.powerautomate.expression import ExpressionContext, generate_expression

# Mapping of field type to (fixture_filename, test_field_name)
FIXTURE_MAP = {
    NormalizedFieldType.TEXT: ("text.txt", "Title"),
    NormalizedFieldType.NUMBER: ("number.txt", "EstimatedHours"),
    NormalizedFieldType.DATE: ("date.txt", "DueDate"),
    NormalizedFieldType.BOOLEAN: ("boolean.txt", "IsMilestone"),
    NormalizedFieldType.LOOKUP: ("lookup.txt", "Project"),
    NormalizedFieldType.LOOKUP_MULTI: ("lookup_multi.txt", "RelatedTask"),
    NormalizedFieldType.PERSON: ("person.txt", "ProjectManager"),
    NormalizedFieldType.PERSON_MULTI: ("person_multi.txt", "AssignedTo"),
    NormalizedFieldType.CHOICE: ("choice.txt", "Status"),
    NormalizedFieldType.CHOICE_MULTI: ("choice_multi.txt", "Tags"),
    NormalizedFieldType.MANAGED_METADATA: ("managed_metadata.txt", "Category"),
    NormalizedFieldType.MANAGED_METADATA_MULTI: ("managed_metadata_multi.txt", "MetadataTags"),
    NormalizedFieldType.CALCULATED: ("calculated.txt", "TaskSummary"),
    NormalizedFieldType.HYPERLINK: ("hyperlink.txt", "WebLink"),
    NormalizedFieldType.IMAGE: ("image.txt", "ProjectIcon"),
    NormalizedFieldType.FILE: ("file.txt", "DocumentFile"),
    NormalizedFieldType.UNKNOWN: ("unknown.txt", "UnsupportedField"),
}

@pytest.mark.parametrize("field_type, fixture_info", FIXTURE_MAP.items())
def test_expression_generation_against_fixtures(field_type, fixture_info):
    filename, field_name = fixture_info
    fixture_path = Path("tests/expression_samples") / filename
    
    assert fixture_path.exists(), f"Fixture file {filename} does not exist"
    
    with open(fixture_path, "r", encoding="utf-8") as f:
        expected_expression = f.read().strip()
        
    generated = generate_expression(field_name, field_type)
    assert generated == expected_expression

def test_expression_context_customization():
    context = ExpressionContext(
        loop_name="Apply_to_each_row_sync",
        delimiter="; ",
        lookup_property="Title",
        person_property="Claims"
    )
    
    # 1. Custom Loop Name on Standard field
    expr_text = generate_expression("Title", NormalizedFieldType.TEXT, context)
    assert expr_text == "@items('Apply_to_each_row_sync')?['Title']"
    
    # 2. Custom Loop Name and Lookup Property on single Lookup field
    expr_lookup = generate_expression("Project", NormalizedFieldType.LOOKUP, context)
    assert expr_lookup == "@items('Apply_to_each_row_sync')?['Project/Title']"
    
    # 3. Custom Loop Name and Person Property on single Person field
    expr_person = generate_expression("Manager", NormalizedFieldType.PERSON, context)
    assert expr_person == "@items('Apply_to_each_row_sync')?['Manager/Claims']"
    
    # 4. Custom properties, loop, and delimiter on multi-lookup field
    expr_lm = generate_expression("RelatedProjects", NormalizedFieldType.LOOKUP_MULTI, context)
    assert expr_lm == (
        "@join(xpath(xml(json(concat('{\"items\":{\"item\":',string(items('Apply_to_each_row_sync')?['RelatedProjects']),'}}'))),'//Title/text()'),'; ')"
    )
    
    # 5. Custom properties, loop, and delimiter on multi-person field
    expr_pm = generate_expression("Coordinators", NormalizedFieldType.PERSON_MULTI, context)
    assert expr_pm == (
        "@join(xpath(xml(json(concat('{\"items\":{\"item\":',string(items('Apply_to_each_row_sync')?['Coordinators']),'}}'))),'//Claims/text()'),'; ')"
    )

def test_expression_generation_direct_trigger():
    context_trigger = ExpressionContext(use_trigger=True)
    
    # 1. Standard field
    expr_text = generate_expression("Title", NormalizedFieldType.TEXT, context_trigger)
    assert expr_text == "@triggerBody()?['Title']"
    
    # 2. Lookup field
    expr_lookup = generate_expression("Project", NormalizedFieldType.LOOKUP, context_trigger)
    assert expr_lookup == "@triggerBody()?['Project/Value']"
    
    # 3. ChoiceMulti field (nested XPath with triggerBody)
    expr_cm = generate_expression("Tags", NormalizedFieldType.CHOICE_MULTI, context_trigger)
    assert expr_cm == (
        "@join(xpath(xml(json(concat('{\"items\":{\"item\":',string(triggerBody()?['Tags']),'}}'))),'//Value/text()'),' | ')"
    )
