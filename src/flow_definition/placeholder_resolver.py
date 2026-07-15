import json
import re
from typing import Dict, Any

class PlaceholderResolver:
    """
    Isolates all placeholder replacement logic. Combines mapping templates
    with flow templates to produce fully resolved configurations.
    """

    @staticmethod
    def resolve(
        template_str: str,
        list_name: str,
        excel_file: str,
        excel_table: str,
        value_object: Dict[str, str],
        trigger_name: str,
        site_url: str
    ) -> Dict[str, Any]:
        """
        Replaces placeholders in the flow template string and validates the resulting JSON.
        Raises ValueError if there are missing/unresolved placeholders or if the output is invalid JSON.
        """
        resolved = template_str
        
        # 1. Replace Value Object placeholder (convert dict to JSON string block)
        # Note: we need to replace it as a raw JSON block.
        val_obj_json = json.dumps(value_object, indent=4, ensure_ascii=False)
        resolved = resolved.replace("${VALUE_OBJECT}", val_obj_json)
        
        # 2. Replace other standard string placeholders
        replacements = {
            "${LIST_NAME}": list_name,
            "${EXCEL_FILE}": excel_file,
            "${EXCEL_TABLE}": excel_table,
            "${TRIGGER_NAME}": trigger_name,
            "${SITE_URL}": site_url,
        }
        
        for placeholder, value in replacements.items():
            resolved = resolved.replace(placeholder, value)

        # 3. Check for any remaining unresolved ${...} placeholders
        unresolved = re.findall(r"\$\{[A-Za-z0-9_]+\}", resolved)
        if unresolved:
            raise ValueError(f"Unresolved placeholders found in template: {', '.join(set(unresolved))}")

        # 4. Attempt to parse the completed string to JSON to ensure it is valid
        try:
            return json.loads(resolved)
        except json.JSONDecodeError as e:
            raise ValueError(f"Resolved flow template is not valid JSON: {e}")
