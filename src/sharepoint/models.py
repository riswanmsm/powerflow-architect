from dataclasses import dataclass, field
from typing import Dict, Any, List as TypeList, Optional

@dataclass
class Field:
    id: str
    name: str
    display_name: str
    field_type: str        # e.g., 'Lookup', 'LookupMulti', 'Choice', 'ChoiceMulti', 'Person', 'PersonMulti', 'Managed Metadata', 'Calculated', 'Text', 'Number', etc.
    is_required: bool
    is_read_only: bool
    is_hidden: bool
    is_system: bool        # Flag indicating whether this is a default SharePoint system field
    raw_definition: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ListModel:
    id: str
    name: str
    display_name: str
    web_url: str
    fields: TypeList[Field] = field(default_factory=list)

@dataclass
class Site:
    id: str
    name: str
    web_url: str
    hostname: str
    path: str
    lists: TypeList[ListModel] = field(default_factory=list)
