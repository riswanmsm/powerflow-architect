import json
from pathlib import Path
from typing import List

from src.flow_definition.models import FlowDefinition

class FlowDefinitionSerializer:
    """ Serializes compiled flow definition objects to files. """

    @staticmethod
    def serialize(definitions: List[FlowDefinition], output_dir: Path) -> None:
        """
        Writes each FlowDefinition JSON out to files under output_dir,
        naming each file after the list.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for d in definitions:
            # Replace spaces or clean list name for safe filesystem usage
            clean_name = d.list_name.replace(" ", "_")
            out_file = output_dir / f"{clean_name}.json"
            
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(d.definition, f, indent=2, ensure_ascii=False)
