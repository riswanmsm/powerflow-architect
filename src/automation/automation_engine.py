import csv
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

def normalize_expression(expr: str) -> str:
    """
    Strips leading '@' or wrapping '@{...}' for pasting into Power Automate formula editor.
    """
    if not expr:
        return ""
    expr = expr.strip()
    # Un-wrap inline expressions like @{triggerBody()?['Title']}
    if expr.startswith("@{") and expr.endswith("}"):
        return expr[2:-1]
    # Remove leading @ sign since formula bar adds it implicitly
    if expr.startswith("@"):
        return expr[1:]
    return expr

class PowerAutomateAutomationEngine:
    """
    Independent Playwright-based browser automation engine that:
    1. Rebuilds copied template flows by updating 'Get items', 'List rows',
       'Delete a row', and 'Add a row' inputs to target the specific list/table.
    2. Populates generated expressions into the 'Add a row into a table' columns.
    """

    def __init__(
        self,
        profile_dir: str = "playwright-profile",
        expressions_file: str = "output/expressions.csv",
        headless: bool = False,
        timeout_seconds: int = 30
    ):
        self.profile_dir = Path(profile_dir)
        self.expressions_file = Path(expressions_file)
        self.headless = headless
        self.timeout_seconds = timeout_seconds

    def load_expressions(self) -> Dict[str, Dict[str, Dict[str, str]]]:
        """
        Parses expressions CSV mapping file.
        Returns a nested dictionary structure: { list_name: { display_name: { direct_trigger: str, foreach: str } } }
        """
        if not self.expressions_file.exists():
            raise FileNotFoundError(f"Expressions file not found at {self.expressions_file}. Please run 'python main.py expressions' first.")

        db: Dict[str, Dict[str, Dict[str, str]]] = {}
        with open(self.expressions_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                list_name = row.get("List Name") or row.get("list_name")
                display_name = row.get("Display Name") or row.get("display_name")
                direct_expr = row.get("Direct Trigger Expression") or row.get("direct_trigger_expression") or ""
                foreach_expr = row.get("Foreach Expression") or row.get("foreach_expression") or ""

                if not list_name or not display_name:
                    continue

                if list_name not in db:
                    db[list_name] = {}
                db[list_name][display_name] = {
                    "direct_trigger": direct_expr,
                    "foreach": foreach_expr
                }

        return db

    def take_screenshot(self, page: Page, filename: str) -> None:
        """Saves a diagnostic screenshot on failure."""
        try:
            screenshot_dir = Path("output") / "screenshots"
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            path = screenshot_dir / filename
            page.screenshot(path=str(path))
            print(f"Diagnostic screenshot saved to: {path}")
        except Exception as e:
            print(f"Failed to capture screenshot: {e}")

    def wait_for_any_visible(self, page: Page, selectors: list, timeout_ms: int) -> bool:
        """
        Waits for at least one of the selectors to become visible on the page.
        """
        start_time = time.monotonic()
        deadline = start_time + (timeout_ms / 1000.0)
        while time.monotonic() < deadline:
            for sel in selectors:
                try:
                    loc = page.locator(sel).first
                    if loc.is_visible():
                        return True
                except Exception:
                    pass
            page.wait_for_timeout(500)
        return False

    def find_action_card(self, page: Page, card_title: str):
        """
        Locates an action card on the canvas by its title text, polling to allow lazy rendering.
        """
        card_selectors = [
            f'div[role="button"]:has-text("{card_title}")',
            f'.fl-ActivityCard:has-text("{card_title}")',
            f'.node-title:has-text("{card_title}")',
            f'[aria-label*="{card_title}"]',
            f'text="{card_title}"'
        ]
        
        start_time = time.monotonic()
        while time.monotonic() - start_time < 10.0:
            for selector in card_selectors:
                try:
                    locs = page.locator(selector)
                    count = locs.count()
                    if count > 0:
                        for i in range(count):
                            loc = locs.nth(i)
                            if loc.is_visible():
                                return loc
                except Exception:
                    pass
            page.wait_for_timeout(500)
            
        return None

    def set_property_value(self, page: Page, field_label: str, value: str) -> bool:
        """
        Finds a field by its label in the open properties panel, clicks it,
        and sets its value (handling dropdowns, comboboxes, and text fields).
        """
        print(f"  Setting property '{field_label}' to '{value}'...")
        try:
            # 1. Locate the field label
            label_locators = [
                page.locator(f"xpath=//label[text()='{field_label}']"),
                page.locator(f"xpath=//*[contains(@class, 'label')][text()='{field_label}']"),
                page.get_by_text(field_label, exact=True)
            ]
            
            label_locator = None
            for loc in label_locators:
                if loc.first.is_visible():
                    label_locator = loc.first
                    break
                    
            if not label_locator:
                print(f"    Warning: Label '{field_label}' not found.")
                return False
                
            # 2. Find the input or combobox within the same control group or following sibling
            control_locator = label_locator.locator(
                "xpath=../following-sibling::div//div[@role='combobox'] | "
                "../following-sibling::div//input | "
                "../following-sibling::div//div[@contenteditable='true']"
            ).first
            
            if not control_locator.is_visible():
                control_locator = page.locator(
                    f"xpath=//*[text()='{field_label}']/following::div[@role='combobox'][1] | "
                    f"//*[text()='{field_label}']/following::input[1] | "
                    f"//*[text()='{field_label}']/following::div[@contenteditable='true'][1]"
                ).first
                
            if not control_locator.is_visible():
                print(f"    Warning: Control for '{field_label}' not found.")
                return False
                
            control_locator.scroll_into_view_if_needed()
            control_locator.click()
            page.wait_for_timeout(1000)

            # 3. Try to select option directly if a dropdown popup opened
            options_locator = page.locator('[role="option"], [class*="option"], [class*="listitem"]')
            if options_locator.count() > 0:
                option_selectors = [
                    f'[role="option"]:has-text("{value}")',
                    f'[class*="option"]:has-text("{value}")',
                    f'text="{value}"'
                ]
                for sel in option_selectors:
                    try:
                        target_option = page.locator(sel).first
                        if target_option.is_visible():
                            target_option.click()
                            print(f"    Selected option '{value}' from dropdown options.")
                            page.wait_for_timeout(1000)
                            return True
                    except Exception:
                        pass

            # 4. If option not selected directly, type and search
            try:
                page.keyboard.type(value)
                page.wait_for_timeout(1200)
                
                option_selectors = [
                    f'[role="option"]:has-text("{value}")',
                    f'[class*="option"]:has-text("{value}")',
                    f'text="{value}"'
                ]
                for sel in option_selectors:
                    try:
                        target_option = page.locator(sel).first
                        if target_option.is_visible():
                            target_option.click()
                            print(f"    Selected option '{value}' after typing filter.")
                            page.wait_for_timeout(1000)
                            return True
                    except Exception:
                        pass
            except Exception as e:
                print(f"    Error typing filter: {e}")

            # 5. Try "Enter custom value" if option still not selected
            custom_val_btn = page.locator('button:has-text("Enter custom value"), [role="option"]:has-text("Enter custom value")').first
            if custom_val_btn.is_visible():
                print("    Clicking 'Enter custom value' button...")
                custom_val_btn.click()
                page.wait_for_timeout(800)
                
                text_input = label_locator.locator("xpath=../following-sibling::div//input").first
                if not text_input.is_visible():
                    text_input = page.locator(f"xpath=//*[text()='{field_label}']/following::input[1]").first
                if text_input.is_visible():
                    text_input.click()
                    text_input.fill(value)
                    text_input.press("Enter")
                    print(f"    Filled custom value '{value}' directly.")
                    page.wait_for_timeout(1000)
                    return True

            # Final direct fill fallback
            try:
                control_locator.fill(value)
                control_locator.press("Enter")
                print(f"    Directly filled control with '{value}'.")
                page.wait_for_timeout(1000)
                return True
            except Exception:
                pass

        except Exception as e:
            print(f"    Failed setting property '{field_label}': {e}")
            
        return False

    def set_file_property(self, page: Page, filename: str) -> bool:
        """
        Specifies the File path by entering it as a custom value in the File combobox.
        Maps to /SystemExports/{filename}
        """
        file_path = f"/SystemExports/{filename}"
        print(f"  Setting File path to '{file_path}'...")
        try:
            # 1. Locate the 'File' label
            file_label = page.locator("xpath=//label[text()='File'] | //*[contains(@class, 'label')][text()='File']").first
            if not file_label.is_visible():
                file_label = page.get_by_text("File").first
                
            if not file_label.is_visible():
                print("    Warning: File label not found.")
                return False
                
            # 2. Find the input/combobox next to it
            file_control = file_label.locator("xpath=../following-sibling::div//div[@role='combobox'] | ../following-sibling::div//input").first
            if not file_control.is_visible():
                file_control = page.locator("xpath=//*[text()='File']/following::div[@role='combobox'][1] | //*[text()='File']/following::input[1]").first
                
            if not file_control.is_visible():
                print("    Warning: File input control not found.")
                return False
                
            file_control.click()
            page.wait_for_timeout(1000)
            
            # Click "Enter custom value" if options popover shows it
            custom_val_btn = page.locator('button:has-text("Enter custom value"), [role="option"]:has-text("Enter custom value")').first
            if custom_val_btn.is_visible():
                custom_val_btn.click()
                page.wait_for_timeout(800)
                
            # Focus on the text field and fill the path
            text_input = file_label.locator("xpath=../following-sibling::div//input").first
            if not text_input.is_visible():
                text_input = page.locator("xpath=//*[text()='File']/following::input[1]").first
                
            if text_input.is_visible():
                text_input.click()
                text_input.fill(file_path)
                text_input.press("Enter")
                page.wait_for_timeout(1500)
                print(f"    Set File custom value '{file_path}' successfully.")
                return True
        except Exception as e:
            print(f"    Failed setting custom File path: {e}")
            
        return False

    def expand_canvas_containers(self, page: Page) -> None:
        """
        Finds and clicks collapsed container buttons on the canvas to ensure all sections are expanded.
        Only clicks if they are currently collapsed (checking Expand labels or aria-expanded attributes)
        to prevent toggling expanded containers closed.
        Restricted to the designer canvas area to avoid header menu buttons.
        """
        print("Checking for collapsed containers on canvas to expand...")
        
        # Scopes the search strictly inside the designer canvas
        canvas_selectors = [
            '.flow-designer-canvas',
            '.fl-Studio',
            '.fl-Canvas',
            '#canvas'
        ]
        canvas = None
        for sel in canvas_selectors:
            loc = page.locator(sel).first
            if loc.is_visible():
                canvas = loc
                break
        if not canvas:
            canvas = page
            
        expand_selectors = [
            'button[aria-label*="Expand"]',
            'button[title*="Expand"]',
            'button[aria-label*="expand"]',
            'button[title*="expand"]',
            'div[role="button"][aria-expanded="false"]',
            'button[aria-expanded="false"]'
        ]
        
        for pass_idx in range(3):
            expanded_any = False
            for sel in expand_selectors:
                try:
                    locs = canvas.locator(sel)
                    count = locs.count()
                    for i in range(count):
                        loc = locs.nth(i)
                        if loc.is_visible():
                            label = loc.get_attribute("aria-label") or loc.get_attribute("title") or loc.text_content() or "Container"
                            print(f"    Expanding collapsed container: '{label.strip()}'")
                            loc.click()
                            page.wait_for_timeout(2000) # Wait for children to render
                            expanded_any = True
                except Exception:
                    pass
            if not expanded_any:
                break

    def click_show_all_parameters(self, page: Page) -> None:
        """
        Locates and clicks the 'Show all' button under Advanced parameters in the open panel
        to reveal hidden input fields.
        """
        print("Checking for 'Show all' advanced parameters button...")
        show_all_selectors = [
            'button:has-text("Show all")',
            'button:has-text("Show All")',
            'button[aria-label*="Show all"]',
            'button[aria-label*="Show All"]',
            'text="Show all"',
            'text="Show All"'
        ]
        for sel in show_all_selectors:
            try:
                btn = page.locator(sel).first
                if btn.is_visible():
                    btn.click()
                    print("  Clicked 'Show all' advanced parameters button.")
                    page.wait_for_timeout(2000)
                    return
            except Exception:
                pass
        print("  'Show all' button not found or already expanded.")

    def detect_flow_name(self, page: Page) -> Optional[str]:
        """Detects the flow name from the designer UI header aria-label."""
        try:
            elem = page.locator('[aria-label^="The flow name is"]').first
            if elem.is_visible():
                aria_label = elem.get_attribute("aria-label") or ""
                prefix = "The flow name is "
                suffix = ". Press enter to edit."
                name = aria_label
                if name.startswith(prefix):
                    name = name[len(prefix):]
                if name.endswith(suffix):
                    name = name[:-len(suffix)]
                return name.strip()
        except Exception:
            pass
        return None

    def select_excel_file_from_picker(self, page: Page, list_name: str) -> bool:
        """
        Clicks the File picker button, navigates to SystemExports folder,
        and selects the {list_name}.xlsx file.
        """
        print(f"  Selecting Excel file '{list_name}.xlsx' via folder picker...")
        try:
            file_label = page.locator("xpath=//label[text()='File'] | //*[contains(@class, 'label')][text()='File']").first
            if not file_label.is_visible():
                file_label = page.get_by_text("File").first
                
            if not file_label.is_visible():
                print("    Warning: 'File' label not found.")
                return False
                
            folder_btn = file_label.locator("xpath=../following-sibling::div//button").first
            if not folder_btn.is_visible():
                folder_btn = page.locator("xpath=//*[text()='File']/following::button[1]").first
                
            if not folder_btn.is_visible():
                print("    Warning: Folder browser button not found.")
                return False
                
            folder_btn.click()
            page.wait_for_timeout(2500)
            
            folder_selectors = [
                'div[role="listitem"]:has-text("SystemExports")',
                'div[role="button"]:has-text("SystemExports")',
                'text="SystemExports"'
            ]
            
            folder_clicked = False
            for sel in folder_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    loc.click()
                    folder_clicked = True
                    print("    Clicked 'SystemExports' folder in picker.")
                    page.wait_for_timeout(2500)
                    break
                    
            if not folder_clicked:
                print("    Warning: 'SystemExports' folder not found in folder picker.")
                return False
                
            excel_filename = f"{list_name}.xlsx"
            file_selectors = [
                f'div[role="listitem"]:has-text("{excel_filename}")',
                f'div[role="button"]:has-text("{excel_filename}")',
                f'text="{excel_filename}"'
            ]
            
            for file_sel in file_selectors:
                loc = page.locator(file_sel).first
                if loc.is_visible():
                    loc.click()
                    print(f"    Selected Excel file '{excel_filename}' from picker.")
                    page.wait_for_timeout(2000)
                    return True
                    
            print(f"    Warning: Excel file '{excel_filename}' not found in folder picker.")
        except Exception as e:
            print(f"    Exception in folder picker navigation: {e}")
            
        return False

    def run(self, flow_url: str, list_name: str, mode: str = "foreach") -> bool:
        """
        Executes the Playwright flow automation.
        """
        db = self.load_expressions()
        if not db:
            raise ValueError("No expressions found in expressions mapping file.")

        print(f"Loaded expressions database successfully. Found {len(db)} lists/tables.")

        self.profile_dir.mkdir(parents=True, exist_ok=True)
        
        with sync_playwright() as playwright:
            print(f"Launching persistent browser context using profile: {self.profile_dir}")
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=self.headless,
                viewport={"width": 1440, "height": 900},
                args=["--start-maximized"],
            )

            # Set a high base timeout for stability in heavy designer UI
            context.set_default_timeout(self.timeout_seconds * 1000)
            page = context.pages[0] if context.pages else context.new_page()

            try:
                # 3. Open Flow Designer Edit Page
                print(f"Navigating to flow URL: {flow_url}")
                page.goto(flow_url, wait_until="domcontentloaded", timeout=120_000)

                # Check if redirected to login
                current_url = page.url
                if "login.microsoftonline.com" in current_url or "login.live.com" in current_url:
                    print("\n" + "=" * 80)
                    print("AUTHENTICATION REQUIRED: Redirected to Microsoft Login page.")
                    print("Please complete the sign-in / MFA steps in the browser window.")
                    print("Waiting up to 300 seconds for flow designer canvas to load...")
                    print("=" * 80 + "\n")
                    
                    selectors = [
                        'button:has-text("Save draft")',
                        'button:has-text("Save")',
                        'button[aria-label*="Save"]',
                        'button:has-text("Back")',
                        '.flow-designer-canvas',
                        'text="Get items"'
                    ]
                    success = self.wait_for_any_visible(page, selectors, 300000)
                    if not success:
                        raise PlaywrightTimeoutError("MFA login or page loading timed out.")
                else:
                    # Multi-option selector waiting for designer loading to complete
                    selectors = [
                        'button:has-text("Save draft")',
                        'button:has-text("Save")',
                        'button[aria-label*="Save"]',
                        'button:has-text("Back")',
                        '.flow-designer-canvas',
                        'text="Get items"'
                    ]
                    success = self.wait_for_any_visible(page, selectors, 90000)
                    if not success:
                        raise PlaywrightTimeoutError("Timeout waiting for flow designer canvas to load.")

                page.wait_for_timeout(3000)

                # 4. Validate list name
                if not list_name:
                    raise ValueError("list_name parameter is required.")

                if list_name not in db:
                    raise KeyError(
                        f"Target list '{list_name}' not found in expressions file. "
                        f"Available lists: {list(db.keys())}"
                    )

                # =========================================================================
                # 5. Full Rebuild / Setup Inputs First (Commented out as requested)
                # =========================================================================
                # print(f"\n--- Phase 1: Rebuilding flow action parameters to target '{list_name}' ---")
                # 
                # # Proactively expand collapsed containers so nested cards render and become visible
                # self.expand_canvas_containers(page)
                # 
                # actions_to_rebuild = [
                #     {
                #         "title": "Get items",
                #         "updates": {"List Name": list_name}
                #     },
                #     {
                #         "title": "List rows present in a table",
                #         "updates": {"File": f"{list_name}.xlsx", "Table": list_name}
                #     },
                #     {
                #         "title": "Delete a row",
                #         "updates": {"File": f"{list_name}.xlsx", "Table": list_name}
                #     },
                #     {
                #         "title": "Add a row into a table",
                #         "updates": {"File": f"{list_name}.xlsx", "Table": list_name}
                #     }
                # ]
                # 
                # for act in actions_to_rebuild:
                #     title = act["title"]
                #     updates = act["updates"]
                #     
                #     print(f"\nLocating action card: '{title}'...")
                #     card = self.find_action_card(page, title)
                #     if not card:
                #         print(f"Warning: Action card '{title}' not found on canvas. Skipping.")
                #         continue
                #         
                #     card.scroll_into_view_if_needed()
                #     card.click()
                #     page.wait_for_timeout(3500)
                #     
                #     for field_label, value in updates.items():
                #         if field_label == "File":
                #             self.select_excel_file_from_picker(page, list_name)
                #         else:
                #             self.set_property_value(page, field_label, value)
                #         page.wait_for_timeout(2000)
                #             
                #     page.wait_for_timeout(2500)

                # =========================================================================
                # 6. Populate input fields for "Add a row into a table"
                # =========================================================================
                print(f"\n--- Phase 2: Populating field expressions for 'Add a row into a table' ---")
                
                # # Expand collapsed containers first to expose target cards (Bypassed)
                # # self.expand_canvas_containers(page)
                # # 
                # # # Make sure the "Add a row into a table" card is active and open
                # # add_row_card = self.find_action_card(page, "Add a row into a table")
                # # if not add_row_card:
                # #     raise ValueError("Target action 'Add a row into a table' not found on canvas.")
                # # 
                # # add_row_card.scroll_into_view_if_needed()
                # # add_row_card.click()
                # # page.wait_for_timeout(3500) # Let columns load
                # # 
                # # # Click 'Show all' to reveal all dynamic fields
                # # self.click_show_all_parameters(page)

                columns_to_map = dict(db[list_name])
                
                # Dynamic mode override check based on flow name header
                flow_name = self.detect_flow_name(page)
                if flow_name:
                    print(f"Detected Flow Name: '{flow_name}'")
                    flow_name_lower = flow_name.lower()
                    if "sync" in flow_name_lower and ("add" in flow_name_lower or "update" in flow_name_lower or "upd" in flow_name_lower):
                        print("  [AUTO-DETECT] Flow detected as a 'sync add/update' flow. Switching mode to 'direct_trigger'.")
                        mode = "direct_trigger"
                    elif "add and update" in flow_name_lower or "add update" in flow_name_lower:
                        print("  [AUTO-DETECT] Flow detected as an 'add/update' flow. Switching mode to 'direct_trigger'.")
                        mode = "direct_trigger"

                # Append the 4 extra fields requested by the user
                columns_to_map["SourceList"] = {"direct_trigger": list_name, "foreach": list_name}
                columns_to_map["SourceDomain"] = {"direct_trigger": "Governance", "foreach": "Governance"}
                columns_to_map["LastSynced"] = {
                    "direct_trigger": "@formatDateTime(convertTimeZone(utcNow(),'UTC','GMT Standard Time'),'yyyy-MM-dd HH:mm')",
                    "foreach": "@formatDateTime(convertTimeZone(utcNow(),'UTC','GMT Standard Time'),'yyyy-MM-dd HH:mm')"
                }
                columns_to_map["SharePointItemID"] = {
                    "direct_trigger": "@triggerBody()?['ID']",
                    "foreach": "@items('Apply_to_each_1')?['ID']"
                }
                
                # Interactive blocker to let the user manually open the card and click Show all
                print("\n" + "=" * 80)
                print("USER ACTION REQUIRED:")
                print("1. Locate and click on the 'Add a row into a table' action card inside the designer canvas.")
                print("2. Click the 'Show all' button under Advanced parameters inside the right properties panel.")
                print("3. Once the dynamic fields are fully visible, come back here and press ENTER.")
                print("=" * 80 + "\n")
                input("Press ENTER to continue and start mapping field expressions...")
                
                # Diagnostics DOM dump
                try:
                    panel_html = page.content()
                    diag_path = Path("output") / "panel_dom.html"
                    diag_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(diag_path, "w", encoding="utf-8") as f:
                        f.write(panel_html)
                    print(f"  [DIAGNOSTIC] Current page DOM dumped to: {diag_path}")
                    self.take_screenshot(page, "panel_state.png")
                except Exception as e:
                    print(f"  [DIAGNOSTIC] Failed to dump page DOM: {e}")

                print(f"Beginning mapping of {len(columns_to_map)} fields for list: {list_name}")

                fields_populated = 0
                fields_skipped = 0

                for display_name, exprs in columns_to_map.items():
                    expr_val = exprs.get(mode)
                    if not expr_val:
                        continue

                    print(f"Mapping field '{display_name}' -> Expression: '{expr_val}'")

                    # Cascading locators to find input box in properties panel
                    input_box = None
                    
                    # Method 0: Primary Direct Match using automation-id and aria-labelledby starts-with (most precise)
                    try:
                        primary_sel = f'div[data-automation-id="flow-editor-input"][aria-labelledby^="{display_name}"]'
                        loc = page.locator(primary_sel).first
                        if loc.is_visible():
                            input_box = loc
                    except Exception:
                        pass
                        
                    # Method 1: Sibling lookup from matching label
                    if not input_box:
                        label_selectors = [
                            page.locator(f"xpath=//label[text()='{display_name}']"),
                            page.locator(f"xpath=//label[text()='{display_name} *']"),
                            page.locator(f"xpath=//*[contains(@class, 'label')][text()='{display_name}']"),
                            page.locator(f"xpath=//*[contains(@class, 'label')][text()='{display_name} *']"),
                            page.get_by_text(display_name, exact=True),
                            page.get_by_text(f"{display_name} *", exact=True)
                        ]
                        for label_loc in label_selectors:
                            try:
                                if label_loc.first.is_visible():
                                    control = label_loc.first.locator(
                                        "xpath=../following-sibling::div//div[@contenteditable='true'] | "
                                        "../following-sibling::div//input | "
                                        "../following-sibling::div//textarea"
                                    ).first
                                    if control.is_visible():
                                        input_box = control
                                        break
                            except Exception:
                                pass

                    # Method 2: Sibling lookup fallback using partial label text
                    if not input_box:
                        try:
                            partial_label = page.get_by_text(display_name, exact=False).first
                            if partial_label.is_visible():
                                control = partial_label.locator(
                                    "xpath=../following-sibling::div//div[@contenteditable='true'] | "
                                    "../following-sibling::div//input | "
                                    "../following-sibling::div//textarea"
                                ).first
                                if control.is_visible():
                                    input_box = control
                        except Exception:
                            pass

                    # Method 3: Direct inputs / placeholders fallback
                    if not input_box:
                        input_locators = [
                            page.get_by_label(display_name, exact=True),
                            page.get_by_label(display_name, exact=False),
                            page.get_by_label(f"{display_name} *", exact=True),
                            page.locator(f"xpath=//*[text()='{display_name}']/following::div[@contenteditable='true'][1]"),
                            page.locator(f"xpath=//*[text()='{display_name} *']/following::div[@contenteditable='true'][1]"),
                            page.locator(f"xpath=//*[contains(text(), '{display_name}')]/following::div[@contenteditable='true'][1]"),
                            page.locator(f"xpath=//*[text()='{display_name}']/following::input[1]"),
                            page.locator(f"xpath=//*[text()='{display_name} *']/following::input[1]"),
                            page.get_by_placeholder(display_name, exact=False),
                            page.locator(f"xpath=//div[contains(@class, 'field') or contains(@class, 'parameter')][contains(., '{display_name}')]//div[@contenteditable='true']").first,
                            page.locator(f"xpath=//div[contains(@class, 'field') or contains(@class, 'parameter')][contains(., '{display_name}')]//input").first
                        ]

                        for loc in input_locators:
                            try:
                                if loc.first.is_visible():
                                    input_box = loc.first
                                    break
                            except Exception:
                                pass

                    if not input_box:
                        print(f"  [SKIPPED] Field input not visible or could not be located.")
                        fields_skipped += 1
                        continue

                    # Focus input box, clear existing text, and fill raw expression directly
                    try:
                        input_box.scroll_into_view_if_needed()
                        page.wait_for_timeout(50)
                        
                        # Option 2: Select all and delete via instant browser command
                        try:
                            input_box.evaluate("el => { el.focus(); document.execCommand('selectAll', false, null); document.execCommand('delete', false, null); }")
                        except Exception:
                            # Fallback clearing
                            try:
                                input_box.focus()
                                input_box.press("Meta+A")
                                input_box.press("Backspace")
                            except Exception:
                                pass
                                
                            try:
                                input_box.press("Control+A")
                                input_box.press("Backspace")
                            except Exception:
                                pass
                                
                            try:
                                input_box.fill("")
                            except Exception:
                                pass
                        
                        page.wait_for_timeout(50)
                        
                        # Option 3: Paste expression instantly via insertText browser command
                        print(f"  Filling raw expression directly: {expr_val}")
                        try:
                            input_box.evaluate("(el, val) => { el.focus(); document.execCommand('insertText', false, val); }", expr_val)
                        except Exception:
                            # Fallback to direct fill/type
                            try:
                                input_box.fill(expr_val)
                            except Exception:
                                input_box.type(expr_val)
                                
                        page.wait_for_timeout(50)
                        print(f"  [OK] Successfully filled field '{display_name}'.")
                        fields_populated += 1
                    except Exception as e:
                        print(f"  [SKIPPED] Failed to write expression directly: {e}")
                        fields_skipped += 1

                print(f"\nCompleted field mapping. Fields filled: {fields_populated}, Skipped: {fields_skipped}")

                # 7. Save Flow
                print("\nSaving flow...")
                save_selectors = [
                    'button:has-text("Save draft")',
                    'button:has-text("Save")',
                    'button[aria-label="Save"]',
                    'button[aria-label*="Save"]',
                    '#save-flow-button'
                ]

                save_button = None
                for save_sel in save_selectors:
                    btn = page.locator(save_sel).first
                    if btn.is_visible():
                        save_button = btn
                        break

                if not save_button:
                    raise ValueError("Save button not found in designer menu.")

                save_button.click()
                print("Clicked Save. Flow save initiated.")
                
                # Interactive blocker to let the user review the save result and decide when to exit
                print("\n" + "=" * 80)
                print("FLOW MAPPING COMPLETED:")
                print("1. All field expressions have been populated.")
                print("2. The 'Save' button has been clicked.")
                print("3. Please review the save progress/status in your browser.")
                print("4. When you are ready to close the browser and exit, return here and press ENTER.")
                print("=" * 80 + "\n")
                input("Press ENTER to close the browser and exit...")
                return True

            except Exception as e:
                print(f"Automation execution exception: {e}", file=sys.stderr)
                self.take_screenshot(page, "execution_error.png")
                raise e
            finally:
                context.close()
