from typing import Dict, Any
from .models import Field

# A set of standard default/system SharePoint column names (lowercased)
SHAREPOINT_SYSTEM_COLUMNS = {
    "id",
    "created",
    "modified",
    "author",
    "editor",
    "contenttype",
    "attachments",
    "guid",
    "edit",
    "linktitle",
    "linktitlenomenu",
    "docicon",
    "itemchildcount",
    "folderchildcount",
    "appauthor",
    "appeditor",
    "_copysource",
    "_hascopydestinations",
    "_moderationstatus",
    "_moderationcomments",
    "complianceassetid",
    "thumbnail",
}

class FieldClassifier:
    """
    Evaluates Microsoft Graph API ColumnDefinition JSON and maps it to
    a classified Field model with type, required, read-only, hidden, and system flags.
    """

    @staticmethod
    def classify(raw_col: Dict[str, Any]) -> Field:
        """
        Classifies a raw Microsoft Graph column definition.
        """
        col_id = raw_col.get("id", "")
        name = raw_col.get("name", "")
        display_name = raw_col.get("displayName", "")
        
        # Get basic boolean flags
        is_required = bool(raw_col.get("required", False))
        is_read_only = bool(raw_col.get("readOnly", False))
        is_hidden = bool(raw_col.get("hidden", False))

        # Check system column
        name_lower = name.lower()
        is_system = name_lower in SHAREPOINT_SYSTEM_COLUMNS or name_lower.startswith("_")

        # Determine type classification
        field_type = "Unknown"

        if "lookup" in raw_col:
            lookup_cfg = raw_col.get("lookup") or {}
            if lookup_cfg.get("allowMultipleValues") is True:
                field_type = "LookupMulti"
            else:
                field_type = "Lookup"
        elif "choice" in raw_col:
            choice_cfg = raw_col.get("choice") or {}
            if choice_cfg.get("displayAs") == "checkBoxes":
                field_type = "ChoiceMulti"
            else:
                field_type = "Choice"
        elif "personOrGroup" in raw_col:
            person_cfg = raw_col.get("personOrGroup") or {}
            if person_cfg.get("allowMultipleSelection") is True:
                field_type = "PersonMulti"
            else:
                field_type = "Person"
        elif "term" in raw_col:
            field_type = "Managed Metadata"
        elif "calculated" in raw_col:
            field_type = "Calculated"
        elif "boolean" in raw_col:
            field_type = "Boolean"
        elif "currency" in raw_col:
            field_type = "Currency"
        elif "dateTime" in raw_col:
            field_type = "DateTime"
        elif "number" in raw_col:
            field_type = "Number"
        elif "text" in raw_col:
            field_type = "Text"
        elif "thumbnail" in raw_col:
            field_type = "Thumbnail"
        elif "geolocation" in raw_col:
            field_type = "Geolocation"

        return Field(
            id=col_id,
            name=name,
            display_name=display_name,
            field_type=field_type,
            is_required=is_required,
            is_read_only=is_read_only,
            is_hidden=is_hidden,
            is_system=is_system,
            raw_definition=raw_col,
        )
