from dataclasses import dataclass
from typing import Dict, Any

@dataclass(frozen=True)
class FlowDefinition:
    """
    Represents a compiled Power Automate flow definition JSON for a SharePoint list.
    """
    list_name: str
    definition: Dict[str, Any]

@dataclass(frozen=True)
class FlowContext:
    """
    Configurable parameters for resolving templates in the Flow Definition Engine.
    """
    excel_file_pattern: str = "{list_name}.xlsx"
    excel_table_pattern: str = "{list_name}"
    trigger_name: str = "When_an_item_is_created"
    site_url: str = "https://runedigitaluk.sharepoint.com/sites/RuneManagementSystem"
