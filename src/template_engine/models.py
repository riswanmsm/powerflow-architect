from dataclasses import dataclass
from typing import Dict

@dataclass(frozen=True)
class MappingTemplate:
    """
    Represents a complete field-to-expression mapping template for a SharePoint list,
    suitable for Excel Online actions in Power Automate.
    """
    list_name: str
    mappings: Dict[str, str]  # { display_name: expression }
