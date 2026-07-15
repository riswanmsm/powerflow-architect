import os
from pathlib import Path
from typing import Optional

class TemplateLoader:
    """ Loads Power Automate logicflow template definitions. """

    def __init__(self, default_path: str = "templates/default_flow.json"):
        self.default_path = Path(default_path)

    def load_template(self, path: Optional[str] = None) -> str:
        """
        Loads the template string from the given file path.
        If no path is provided, falls back to the default path.
        """
        target_path = Path(path) if path else self.default_path
        
        if not target_path.exists():
            raise FileNotFoundError(f"Flow template file not found at: {target_path}")

        with open(target_path, "r", encoding="utf-8") as f:
            return f.read()
