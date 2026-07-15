from typing import Dict, Any, Optional, List, Callable
from .normalized_types import NormalizedFieldType

# Rule 1: SharePoint REST API properties rule
def rest_properties_rule(raw_col: Dict[str, Any]) -> Optional[NormalizedFieldType]:
    type_as_string = raw_col.get("TypeAsString")
    if not type_as_string:
        return None
        
    allow_multi = bool(raw_col.get("AllowMultipleValues", False))
    t_lower = type_as_string.lower()
    
    if t_lower in ("text", "note"):
        return NormalizedFieldType.TEXT
    elif t_lower in ("number", "integer", "counter", "currency"):
        return NormalizedFieldType.NUMBER
    elif t_lower == "datetime":
        return NormalizedFieldType.DATE
    elif t_lower == "boolean":
        return NormalizedFieldType.BOOLEAN
    elif t_lower in ("lookup", "lookupmulti"):
        return NormalizedFieldType.LOOKUP_MULTI if (t_lower == "lookupmulti" or allow_multi) else NormalizedFieldType.LOOKUP
    elif t_lower in ("user", "usermulti"):
        return NormalizedFieldType.PERSON_MULTI if (t_lower == "usermulti" or allow_multi) else NormalizedFieldType.PERSON
    elif t_lower in ("choice", "multichoice"):
        return NormalizedFieldType.CHOICE_MULTI if (t_lower == "multichoice" or allow_multi) else NormalizedFieldType.CHOICE
    elif t_lower in ("taxonomyfieldtype", "taxonomyfieldtypemulti"):
        return NormalizedFieldType.MANAGED_METADATA_MULTI if (t_lower == "taxonomyfieldtypemulti" or allow_multi) else NormalizedFieldType.MANAGED_METADATA
    elif t_lower == "calculated":
        return NormalizedFieldType.CALCULATED
    elif t_lower == "url":
        return NormalizedFieldType.HYPERLINK
    elif t_lower in ("thumbnail", "image"):
        return NormalizedFieldType.IMAGE
    elif t_lower in ("file", "attachments"):
        return NormalizedFieldType.FILE
        
    return None

# Rule 2: Graph Lookup rule
def lookup_rule(raw_col: Dict[str, Any]) -> Optional[NormalizedFieldType]:
    if "lookup" in raw_col:
        lookup_cfg = raw_col.get("lookup") or {}
        if lookup_cfg.get("allowMultipleValues") is True:
            return NormalizedFieldType.LOOKUP_MULTI
        return NormalizedFieldType.LOOKUP
    return None

# Rule 3: Graph Choice rule
def choice_rule(raw_col: Dict[str, Any]) -> Optional[NormalizedFieldType]:
    if "choice" in raw_col:
        choice_cfg = raw_col.get("choice") or {}
        if choice_cfg.get("displayAs") == "checkBoxes":
            return NormalizedFieldType.CHOICE_MULTI
        return NormalizedFieldType.CHOICE
    return None

# Rule 4: Graph Person/Group rule
def person_rule(raw_col: Dict[str, Any]) -> Optional[NormalizedFieldType]:
    if "personOrGroup" in raw_col:
        person_cfg = raw_col.get("personOrGroup") or {}
        if person_cfg.get("allowMultipleSelection") is True:
            return NormalizedFieldType.PERSON_MULTI
        return NormalizedFieldType.PERSON
    return None

# Rule 5: Graph Taxonomy/Term rule
def term_rule(raw_col: Dict[str, Any]) -> Optional[NormalizedFieldType]:
    if "term" in raw_col:
        term_cfg = raw_col.get("term") or {}
        if term_cfg.get("allowMultipleValues") is True:
            return NormalizedFieldType.MANAGED_METADATA_MULTI
        return NormalizedFieldType.MANAGED_METADATA
    return None

# Rule 6: Graph Calculated rule
def calculated_rule(raw_col: Dict[str, Any]) -> Optional[NormalizedFieldType]:
    if "calculated" in raw_col:
        return NormalizedFieldType.CALCULATED
    return None

# Rule 7: Graph Boolean rule
def boolean_rule(raw_col: Dict[str, Any]) -> Optional[NormalizedFieldType]:
    if "boolean" in raw_col:
        return NormalizedFieldType.BOOLEAN
    return None

# Rule 8: Graph Currency rule
def currency_rule(raw_col: Dict[str, Any]) -> Optional[NormalizedFieldType]:
    if "currency" in raw_col:
        return NormalizedFieldType.NUMBER
    return None

# Rule 9: Graph DateTime rule
def datetime_rule(raw_col: Dict[str, Any]) -> Optional[NormalizedFieldType]:
    if "dateTime" in raw_col:
        return NormalizedFieldType.DATE
    return None

# Rule 10: Graph Number rule
def number_rule(raw_col: Dict[str, Any]) -> Optional[NormalizedFieldType]:
    if "number" in raw_col:
        return NormalizedFieldType.NUMBER
    return None

# Rule 11: Graph Text rule
def text_rule(raw_col: Dict[str, Any]) -> Optional[NormalizedFieldType]:
    if "text" in raw_col:
        return NormalizedFieldType.TEXT
    return None

# Rule 12: Graph Thumbnail/Image rule
def thumbnail_rule(raw_col: Dict[str, Any]) -> Optional[NormalizedFieldType]:
    if "thumbnail" in raw_col:
        return NormalizedFieldType.IMAGE
    return None

# Rule 13: Graph Hyperlink/URL rule
def hyperlink_rule(raw_col: Dict[str, Any]) -> Optional[NormalizedFieldType]:
    if "hyperlink" in raw_col or "url" in raw_col:
        return NormalizedFieldType.HYPERLINK
    return None

# Rule 14: Graph File rule
def file_rule(raw_col: Dict[str, Any]) -> Optional[NormalizedFieldType]:
    if "file" in raw_col:
        return NormalizedFieldType.FILE
    return None

# Sequential list of registered classification rules
CLASSIFICATION_RULES: List[Callable[[Dict[str, Any]], Optional[NormalizedFieldType]]] = [
    rest_properties_rule,
    lookup_rule,
    choice_rule,
    person_rule,
    term_rule,
    calculated_rule,
    boolean_rule,
    currency_rule,
    datetime_rule,
    number_rule,
    text_rule,
    thumbnail_rule,
    hyperlink_rule,
    file_rule,
]

class FieldClassifierRules:
    """
    Evaluates raw SharePoint column payloads against registered classification
    rules sequentially. Returns the first matched NormalizedFieldType, or
    NormalizedFieldType.UNKNOWN if no rules match.
    """
    
    @staticmethod
    def evaluate(raw_col: Dict[str, Any]) -> NormalizedFieldType:
        for rule in CLASSIFICATION_RULES:
            result = rule(raw_col)
            if result is not None:
                return result
        return NormalizedFieldType.UNKNOWN
