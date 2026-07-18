from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from src.sharepoint.normalized_types import NormalizedFieldType

@dataclass(frozen=True)
class ExpressionContext:
    loop_name: str = "Apply_to_each_1"
    delimiter: str = " | "
    lookup_property: str = "Value"
    person_property: str = "Email"
    use_trigger: bool = False

    def get_base_source(self) -> str:
        return "triggerBody()" if self.use_trigger else f"items('{self.loop_name}')"

class ExpressionStrategy(ABC):
    @abstractmethod
    def generate(self, field_name: str, context: ExpressionContext) -> str:
        pass

class StandardStrategy(ExpressionStrategy):
    def generate(self, field_name: str, context: ExpressionContext) -> str:
        return f"@{context.get_base_source()}?['{field_name}']"

class LookupStrategy(ExpressionStrategy):
    def generate(self, field_name: str, context: ExpressionContext) -> str:
        return f"@{context.get_base_source()}?['{field_name}/{context.lookup_property}']"

class LookupMultiStrategy(ExpressionStrategy):
    def generate(self, field_name: str, context: ExpressionContext) -> str:
        return (
            f"@join(xpath(xml(json(concat('{{\"items\":{{\"item\":',string({context.get_base_source()}?['{field_name}']),'}}}}'))),"
            f"'//{context.lookup_property}/text()'),'{context.delimiter}')"
        )

class PersonStrategy(ExpressionStrategy):
    def generate(self, field_name: str, context: ExpressionContext) -> str:
        return f"@{context.get_base_source()}?['{field_name}/{context.person_property}']"

class PersonMultiStrategy(ExpressionStrategy):
    def generate(self, field_name: str, context: ExpressionContext) -> str:
        return (
            f"@join(xpath(xml(json(concat('{{\"items\":{{\"item\":',string({context.get_base_source()}?['{field_name}']),'}}}}'))),"
            f"'//{context.person_property}/text()'),'{context.delimiter}')"
        )

class ChoiceStrategy(ExpressionStrategy):
    def generate(self, field_name: str, context: ExpressionContext) -> str:
        return f"@{context.get_base_source()}?['{field_name}/Value']"

class ChoiceMultiStrategy(ExpressionStrategy):
    def generate(self, field_name: str, context: ExpressionContext) -> str:
        return (
            f"@join(xpath(xml(json(concat('{{\"items\":{{\"item\":',string({context.get_base_source()}?['{field_name}']),'}}}}'))),"
            f"'//Value/text()'),'{context.delimiter}')"
        )

class ManagedMetadataStrategy(ExpressionStrategy):
    def generate(self, field_name: str, context: ExpressionContext) -> str:
        return f"@{context.get_base_source()}?['{field_name}/Label']"

class ManagedMetadataMultiStrategy(ExpressionStrategy):
    def generate(self, field_name: str, context: ExpressionContext) -> str:
        return (
            f"@join(xpath(xml(json(concat('{{\"items\":{{\"item\":',string({context.get_base_source()}?['{field_name}']),'}}}}'))),"
            f"'//Label/text()'),'{context.delimiter}')"
        )

# Map NormalizedFieldType to its respective generator strategy
STRATEGIES = {
    NormalizedFieldType.TEXT: StandardStrategy(),
    NormalizedFieldType.NUMBER: StandardStrategy(),
    NormalizedFieldType.DATE: StandardStrategy(),
    NormalizedFieldType.BOOLEAN: StandardStrategy(),
    NormalizedFieldType.CALCULATED: StandardStrategy(),
    NormalizedFieldType.HYPERLINK: StandardStrategy(),
    NormalizedFieldType.IMAGE: StandardStrategy(),
    NormalizedFieldType.FILE: StandardStrategy(),
    NormalizedFieldType.UNKNOWN: StandardStrategy(),
    
    NormalizedFieldType.LOOKUP: LookupStrategy(),
    NormalizedFieldType.LOOKUP_MULTI: LookupMultiStrategy(),
    
    NormalizedFieldType.PERSON: PersonStrategy(),
    NormalizedFieldType.PERSON_MULTI: PersonMultiStrategy(),
    
    NormalizedFieldType.CHOICE: ChoiceStrategy(),
    NormalizedFieldType.CHOICE_MULTI: ChoiceMultiStrategy(),
    
    NormalizedFieldType.MANAGED_METADATA: ManagedMetadataStrategy(),
    NormalizedFieldType.MANAGED_METADATA_MULTI: ManagedMetadataMultiStrategy(),
}

def generate_expression(field_name: str, field_type: NormalizedFieldType, context: Optional[ExpressionContext] = None) -> str:
    """
    Generates a production-ready Power Automate expression for the given field.
    """
    if context is None:
        context = ExpressionContext()
        
    strategy = STRATEGIES.get(field_type, StandardStrategy())
    return strategy.generate(field_name, context)

class ExpressionEngine:
    """
    Wrapper interface that parses a field metadata dictionary and delegates
    expression generation to generate_expression.
    """
    @staticmethod
    def get_normalized_type(field: dict) -> NormalizedFieldType:
        type_str = field.get("NormalizedFieldType")
        if type_str:
            try:
                return NormalizedFieldType(type_str)
            except ValueError:
                pass
        
        orig_type = field.get("field_type")
        if orig_type:
            mapping = {
                "text": NormalizedFieldType.TEXT,
                "note": NormalizedFieldType.TEXT,
                "string": NormalizedFieldType.TEXT,
                "number": NormalizedFieldType.NUMBER,
                "integer": NormalizedFieldType.NUMBER,
                "counter": NormalizedFieldType.NUMBER,
                "currency": NormalizedFieldType.NUMBER,
                "datetime": NormalizedFieldType.DATE,
                "date": NormalizedFieldType.DATE,
                "boolean": NormalizedFieldType.BOOLEAN,
                "lookup": NormalizedFieldType.LOOKUP,
                "lookupmulti": NormalizedFieldType.LOOKUP_MULTI,
                "person": NormalizedFieldType.PERSON,
                "personmulti": NormalizedFieldType.PERSON_MULTI,
                "user": NormalizedFieldType.PERSON,
                "usermulti": NormalizedFieldType.PERSON_MULTI,
                "choice": NormalizedFieldType.CHOICE,
                "choicemulti": NormalizedFieldType.CHOICE_MULTI,
                "multichoice": NormalizedFieldType.CHOICE_MULTI,
                "managed metadata": NormalizedFieldType.MANAGED_METADATA,
                "managed metadata_multi": NormalizedFieldType.MANAGED_METADATA_MULTI,
                "managedmetadata": NormalizedFieldType.MANAGED_METADATA,
                "managedmetadatamulti": NormalizedFieldType.MANAGED_METADATA_MULTI,
                "taxonomyfieldtype": NormalizedFieldType.MANAGED_METADATA,
                "taxonomyfieldtypemulti": NormalizedFieldType.MANAGED_METADATA_MULTI,
                "calculated": NormalizedFieldType.CALCULATED,
                "url": NormalizedFieldType.HYPERLINK,
                "hyperlink": NormalizedFieldType.HYPERLINK,
                "thumbnail": NormalizedFieldType.IMAGE,
                "image": NormalizedFieldType.IMAGE,
                "file": NormalizedFieldType.FILE,
                "attachments": NormalizedFieldType.FILE,
                "geolocation": NormalizedFieldType.UNKNOWN,
            }
            return mapping.get(orig_type.lower(), NormalizedFieldType.UNKNOWN)
        return NormalizedFieldType.UNKNOWN

    @staticmethod
    def generate(field: dict, context: Optional[ExpressionContext] = None) -> str:
        field_name = field.get("name") or field.get("FieldName") or ""
        field_type = ExpressionEngine.get_normalized_type(field)
        return generate_expression(field_name, field_type, context)
