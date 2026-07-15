import argparse
import os
import sys
import yaml
from pathlib import Path

from src.auth import AuthenticationProvider
from src.sharepoint import (
    SharePointClient,
    ListService,
    FieldService,
    Site,
    Exporter
)
from src.generator import ExpressionGenerator
from src.template_engine import TemplateEngine
from src.flow_definition import FlowDefinitionEngine, FlowContext

def load_config() -> str:
    """Load default site URL from config.yaml if present."""
    config_path = Path("config.yaml")
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
                return config.get("sharepoint", {}).get("site_url", "")
        except Exception:
            pass
    return ""

def run_inventory(site_url: str):
    """Orchestrates SharePoint site, lists, and field inventory capture."""
    if not site_url:
        print("Error: No SharePoint site URL provided. Specify via --site or config.yaml.", file=sys.stderr)
        sys.exit(1)

    # Initialize Auth & Client
    auth_provider = AuthenticationProvider()
    client = SharePointClient(auth_provider)
    
    # Initialize Services
    list_service = ListService(client)
    field_service = FieldService(client)

    print(f"Resolving SharePoint site URL: {site_url}...")
    try:
        site_meta = client.resolve_site(site_url)
    except Exception as e:
        print(f"Error resolving site: {e}", file=sys.stderr)
        sys.exit(1)

    site_id = site_meta.get("id", "")
    site_name = site_meta.get("displayName") or site_meta.get("name", "Unknown Site")
    web_url = site_meta.get("webUrl", "")
    
    # Split hostname and path from resolved data
    from urllib.parse import urlparse
    parsed = urlparse(web_url)
    hostname = parsed.netloc
    path = parsed.path.strip("/")

    print("Fetching lists...")
    lists = list_service.get_lists(site_id)
    
    # Track statistics
    total_fields = 0
    classifications = {
        "Lookup": 0,
        "LookupMulti": 0,
        "Choice": 0,
        "ChoiceMulti": 0,
        "Person": 0,
        "PersonMulti": 0,
        "Managed Metadata": 0,
        "Calculated": 0,
        "Hidden": 0,
        "Required": 0,
        "ReadOnly": 0,
    }

    # Fetch fields for each list
    site_lists = []
    print(f"Discovered {len(lists)} lists. Fetching fields for each...")
    for idx, lst in enumerate(lists, 1):
        print(f"[{idx}/{len(lists)}] Fetching columns for list: {lst.display_name}...")
        try:
            fields = field_service.get_fields(site_id, lst.id)
            lst.fields = fields
            site_lists.append(lst)
            
            # Aggregate stats
            total_fields += len(fields)
            for f in fields:
                # Count specific classifications (Note: multiple flags can apply e.g. a Required Choice column)
                if f.field_type in classifications:
                    classifications[f.field_type] += 1
                
                # Check additional binary attribute classifications
                if f.is_required:
                    classifications["Required"] += 1
                if f.is_read_only:
                    classifications["ReadOnly"] += 1
                if f.is_hidden:
                    classifications["Hidden"] += 1
        except Exception as e:
            print(f"Warning: Failed to fetch fields for list '{lst.display_name}': {e}", file=sys.stderr)

    # Construct complete Site model
    site = Site(
        id=site_id,
        name=site_name,
        web_url=web_url,
        hostname=hostname,
        path=path,
        lists=site_lists
    )

    # Export to outputs
    exporter = Exporter(output_dir="Inventory")
    exports = exporter.export(site)

    # Print output matching deliverable requirements
    print("\nSite:")
    print(site.name)

    print("\nLists:")
    print(len(site.lists))

    print("\nFields:")
    print(f"{total_fields:,}")

    print("\nLookup:")
    print(classifications["Lookup"])

    print("\nLookup Multi:")
    print(classifications["LookupMulti"])

    print("\nChoice:")
    print(classifications["Choice"])

    print("\nChoice Multi:")
    print(classifications["ChoiceMulti"])

    print("\nPerson:")
    print(classifications["Person"])

    print("\nPerson Multi:")
    print(classifications["PersonMulti"])

    print("\nManaged Metadata:")
    print(classifications["Managed Metadata"])

    print("\nExport:")
    print(os.path.basename(exports["xlsx"]))
    print()
def main():
    parser = argparse.ArgumentParser(description="SharePoint Flow & List Architect CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # inventory sub-command
    parser_inventory = subparsers.add_parser("inventory", help="Generate SharePoint list & field inventory")
    parser_inventory.add_argument(
        "--site",
        type=str,
        help="Target SharePoint site URL (overrides site_url config in config.yaml)"
    )

    # expressions sub-command
    parser_expressions = subparsers.add_parser("expressions", help="Generate Power Automate expressions from inventory JSON")
    parser_expressions.add_argument(
        "--input",
        type=str,
        default="Inventory/inventory.json",
        help="Path to input inventory.json file (default: Inventory/inventory.json)"
    )
    parser_expressions.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Path to output directory (default: output)"
    )

    # templates sub-command
    parser_templates = subparsers.add_parser("templates", help="Generate Excel action templates from inventory JSON")
    parser_templates.add_argument(
        "--input",
        type=str,
        default="Inventory/inventory.json",
        help="Path to input inventory.json file (default: Inventory/inventory.json)"
    )
    parser_templates.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Path to output directory (default: output)"
    )

    # flows sub-command
    parser_flows = subparsers.add_parser("flows", help="Generate Power Automate flow definitions from templates")
    parser_flows.add_argument(
        "--input",
        type=str,
        default="Inventory/inventory.json",
        help="Path to input inventory.json file (default: Inventory/inventory.json)"
    )
    parser_flows.add_argument(
        "--template",
        type=str,
        default="templates/default_flow.json",
        help="Path to the flow JSON template (default: templates/default_flow.json)"
    )
    parser_flows.add_argument(
        "--output-dir",
        type=str,
        default="flow_definitions",
        help="Path to output directory for flow definitions (default: flow_definitions)"
    )

    args = parser.parse_args()

    if args.command == "inventory":
        site_url = args.site or load_config()
        run_inventory(site_url)
    elif args.command == "expressions":
        generator = ExpressionGenerator(input_json_path=args.input, output_dir=args.output_dir)
        print(f"Generating expressions from {args.input}...")
        try:
            generator.generate()
            print(f"Expressions generated successfully. Outputs saved in '{args.output_dir}/'")
        except Exception as e:
            print(f"Error generating expressions: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "templates":
        engine = TemplateEngine(inventory_path=args.input)
        print(f"Generating templates from {args.input}...")
        try:
            engine.generate_outputs(output_dir=args.output_dir)
            print(f"Templates generated successfully. Outputs saved in '{args.output_dir}/'")
        except Exception as e:
            print(f"Error generating templates: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "flows":
        engine = FlowDefinitionEngine(inventory_path=args.input, template_path=args.template)
        print(f"Generating flow definitions from {args.input} using template {args.template}...")
        try:
            engine.generate_definitions(output_dir=args.output_dir)
            print(f"Flow definitions generated successfully. Outputs saved in '{args.output_dir}/'")
        except Exception as e:
            print(f"Error generating flows: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
