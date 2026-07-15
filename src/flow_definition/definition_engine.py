from pathlib import Path
from typing import List, Optional

from src.powerautomate.expression import ExpressionContext
from src.template_engine.template_engine import TemplateEngine
from src.flow_definition.models import FlowDefinition, FlowContext
from src.flow_definition.template_loader import TemplateLoader
from src.flow_definition.placeholder_resolver import PlaceholderResolver
from src.flow_definition.serializers import FlowDefinitionSerializer

class FlowDefinitionEngine:
    """
    Combines template definition files with generated mapping templates
    to compile full, valid Power Automate flow definitions.
    """

    def __init__(self, inventory_path: str = "Inventory/inventory.json", template_path: Optional[str] = None):
        self.inventory_path = Path(inventory_path)
        self.template_loader = TemplateLoader()
        self.template_path = template_path

    def generate_definitions(
        self,
        output_dir: str = "flow_definitions",
        context: Optional[ExpressionContext] = None,
        flow_ctx: Optional[FlowContext] = None
    ) -> List[FlowDefinition]:
        """
        Loads the SharePoint list mapping templates and builds a flow definition
        for each list, exporting resolved files to output_dir.
        """
        if flow_ctx is None:
            flow_ctx = FlowContext()

        # Load the flow definition template
        template_str = self.template_loader.load_template(self.template_path)

        # 1. Fetch filtered templates from the Template Engine.
        # Responsibilities are separate: TemplateEngine does all filtering.
        temp_engine = TemplateEngine(inventory_path=str(self.inventory_path))
        mapping_templates = temp_engine.load_templates(context)

        definitions = []

        for m in mapping_templates:
            list_name = m.list_name
            excel_file = flow_ctx.excel_file_pattern.format(list_name=list_name)
            excel_table = flow_ctx.excel_table_pattern.format(list_name=list_name)
            
            # Resolve placeholders using the PlaceholderResolver (isolated replacement)
            definition_dict = PlaceholderResolver.resolve(
                template_str=template_str,
                list_name=list_name,
                excel_file=excel_file,
                excel_table=excel_table,
                value_object=m.mappings,
                trigger_name=flow_ctx.trigger_name,
                site_url=flow_ctx.site_url
            )
            
            definitions.append(FlowDefinition(list_name=list_name, definition=definition_dict))

        # 2. Serialize outputs
        out_dir = Path(output_dir)
        FlowDefinitionSerializer.serialize(definitions, out_dir)

        return definitions
