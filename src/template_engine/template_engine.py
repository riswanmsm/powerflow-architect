import json
from pathlib import Path
from typing import List, Optional

from src.sharepoint.normalized_types import NormalizedFieldType
from src.powerautomate.expression import ExpressionContext, ExpressionEngine
from src.template_engine.models import MappingTemplate
from src.template_engine.serializers import JSONSerializer, ExcelSerializer

class TemplateEngine:
    """
    Template Engine that loads SharePoint inventory metadata and generates
    value-object mapping templates suitable for Excel Online Power Automate actions.
    """

    def __init__(self, inventory_path: str = "Inventory/inventory.json"):
        self.inventory_path = Path(inventory_path)

    def load_templates(self, context: Optional[ExpressionContext] = None) -> List[MappingTemplate]:
        """
        Loads the list inventory offline, filters out system and unsupported (UNKNOWN) columns,
        and constructs mapping templates using field Display Names as keys.
        """
        if context is None:
            context = ExpressionContext()

        if not self.inventory_path.exists():
            raise FileNotFoundError(f"Inventory file not found at: {self.inventory_path}")

        with open(self.inventory_path, "r", encoding="utf-8") as f:
            inventory = json.load(f)

        lists = inventory.get("lists", [])
        templates = []

        for lst in lists:
            list_name = lst.get("list_display_name") or lst.get("list_name") or "Unknown List"
            fields = lst.get("fields", [])
            
            mappings = {}
            for field in fields:
                field_name = field.get("name") or ""
                is_system = field.get("is_system") is True
                
                # Exclude read-only system columns (except Title)
                if is_system and field_name.lower() != "title":
                    continue
                
                # Exclude unsupported columns (UNKNOWN)
                field_type_enum = ExpressionEngine.get_normalized_type(field)
                if field_type_enum == NormalizedFieldType.UNKNOWN:
                    continue
                
                display_name = field.get("display_name") or ""
                expr = ExpressionEngine.generate(field, context)
                
                mappings[display_name] = expr
                
            templates.append(MappingTemplate(list_name=list_name, mappings=mappings))

        return templates

    def generate_outputs(self, output_dir: str = "output", context: Optional[ExpressionContext] = None) -> List[MappingTemplate]:
        """
        Generates mapping templates and writes them out to JSON and XLSX formats under output_dir.
        """
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        
        templates = self.load_templates(context)
        
        # Serialize to templates.json
        json_path = out_path / "templates.json"
        JSONSerializer.serialize(templates, json_path)
        
        # Serialize to templates.xlsx
        xlsx_path = out_path / "templates.xlsx"
        ExcelSerializer.serialize(templates, xlsx_path)
        
        return templates
