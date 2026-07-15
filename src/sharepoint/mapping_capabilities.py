from dataclasses import dataclass
from .normalized_types import NormalizedFieldType

@dataclass(frozen=True)
class MappingCapability:
    is_mappable: bool
    supports_join: bool

CAPABILITIES = {
    NormalizedFieldType.TEXT: MappingCapability(is_mappable=True, supports_join=False),
    NormalizedFieldType.NUMBER: MappingCapability(is_mappable=True, supports_join=False),
    NormalizedFieldType.DATE: MappingCapability(is_mappable=True, supports_join=False),
    NormalizedFieldType.BOOLEAN: MappingCapability(is_mappable=True, supports_join=False),
    NormalizedFieldType.LOOKUP: MappingCapability(is_mappable=True, supports_join=False),
    NormalizedFieldType.LOOKUP_MULTI: MappingCapability(is_mappable=True, supports_join=True),
    NormalizedFieldType.PERSON: MappingCapability(is_mappable=True, supports_join=False),
    NormalizedFieldType.PERSON_MULTI: MappingCapability(is_mappable=True, supports_join=True),
    NormalizedFieldType.CHOICE: MappingCapability(is_mappable=True, supports_join=False),
    NormalizedFieldType.CHOICE_MULTI: MappingCapability(is_mappable=True, supports_join=True),
    NormalizedFieldType.MANAGED_METADATA: MappingCapability(is_mappable=True, supports_join=False),
    NormalizedFieldType.MANAGED_METADATA_MULTI: MappingCapability(is_mappable=True, supports_join=True),
    NormalizedFieldType.CALCULATED: MappingCapability(is_mappable=True, supports_join=False),
    NormalizedFieldType.HYPERLINK: MappingCapability(is_mappable=True, supports_join=False),
    NormalizedFieldType.IMAGE: MappingCapability(is_mappable=False, supports_join=False),
    NormalizedFieldType.FILE: MappingCapability(is_mappable=False, supports_join=False),
    NormalizedFieldType.UNKNOWN: MappingCapability(is_mappable=False, supports_join=False),
}

def get_mapping_capability(field_type: NormalizedFieldType) -> MappingCapability:
    """Retrieve mapping capability details for a given normalized field type."""
    return CAPABILITIES.get(field_type, MappingCapability(is_mappable=False, supports_join=False))
