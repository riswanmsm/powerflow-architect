import argparse
from pathlib import Path
import sys

def register_subcommand(subparsers):
    """Registers the 'automate' subcommand and its arguments."""
    parser = subparsers.add_parser(
        "automate",
        help="Automate populating a Power Automate flow with generated expressions"
    )
    
    parser.add_argument(
        "--flow-url",
        type=str,
        required=False,
        help="The edit canvas URL of the target Power Automate flow"
    )
    
    parser.add_argument(
        "--list-name",
        type=str,
        required=False,
        help="Target SharePoint list name (e.g. REG_InformationSystems)."
    )
    
    parser.add_argument(
        "--expressions-file",
        type=str,
        default="output/expressions.csv",
        help="Path to the expressions mapping CSV file (default: output/expressions.csv)"
    )
    
    parser.add_argument(
        "--mode",
        choices=["foreach", "direct_trigger"],
        default="foreach",
        help="The expression scope/mode to populate: 'foreach' or 'direct_trigger' (default: foreach)"
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run the browser in headless mode (default: False / headful, which allows MFA interaction)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout in seconds for browser operations (default: 30)"
    )
    
    parser.add_argument(
        "--profile-dir",
        type=str,
        default="playwright-profile",
        help="Path to the persistent browser profile directory (default: playwright-profile)"
    )
    
    return parser

def run_automation(args):
    """Execution wrapper invoked when the 'automate' command is run."""
    import json
    
    # Load JSON configuration if present
    config_data = {}
    config_path = Path("config.json")
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except Exception:
            pass

    # Retrieve arguments, prompting interactively if omitted on command line and JSON config
    flow_url = args.flow_url or config_data.get("flow_url")
    if not flow_url:
        flow_url = input("Please enter the Flow Edit URL: ").strip()
        while not flow_url:
            flow_url = input("Flow URL cannot be empty. Please enter the Flow Edit URL: ").strip()

    list_name = args.list_name or config_data.get("list_name")
    if not list_name:
        list_name = input("Please enter the SharePoint List Name (e.g. LIST_Environments): ").strip()
        while not list_name:
            list_name = input("List Name cannot be empty. Please enter the SharePoint List Name: ").strip()

    from .automation_engine import PowerAutomateAutomationEngine
    
    engine = PowerAutomateAutomationEngine(
        profile_dir=args.profile_dir,
        expressions_file=args.expressions_file,
        headless=args.headless,
        timeout_seconds=args.timeout
    )
    
    print(f"Starting automation engine for flow: {flow_url}")
    print(f"Mode: {args.mode}")
    print(f"Expressions source: {args.expressions_file}")
    
    try:
        success = engine.run(
            flow_url=flow_url,
            list_name=list_name,
            mode=args.mode
        )
        if success:
            print("\n=== SUCCESS: Flow saved successfully ===")
            sys.exit(0)
        else:
            print("\n=== FAILURE: Flow saving failed or was aborted ===", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"\n=== FAILURE: Automation encountered an error ===\nError: {e}", file=sys.stderr)
        sys.exit(1)
