# ADR-004: Flow Definition Engine and Placeholder Resolution

## Status
Accepted

## Date
2026-07-15

## Context

To automate list-to-spreadsheet sync operations, we need complete, deploy-ready Power Automate flow definition JSON documents for each discovered SharePoint list. 

Manually configuring logicflow definition JSON files for dozens of lists is highly repetitive and prone to syntax errors. We require a templating approach where target parameters (site URLs, file names, tables, and mapping objects) are injected dynamically. 

To ensure stability:
1. All template replacements and syntax validations must be isolated to prevent ad-hoc regex substitutions across different scripts.
2. The definition compilation must NOT duplicate the system column filtering and type classification rules already established in Sprints 2 & 4.
3. The engine must remain decoupled from the deployment or import of logicflows.

## Decision

We will implement a Flow Definition Engine that resolves reusable JSON templates:

1. **Standardized Placeholder format**: Define a clear `${PLACEHOLDER}` syntax inside flow definition JSON files (`templates/default_flow.json`), targeting:
   - `${LIST_NAME}`: The internal/display name of the list.
   - `${EXCEL_FILE}`: The path of the destination Excel workbook.
   - `${EXCEL_TABLE}`: The Excel table name inside the sheet.
   - `${VALUE_OBJECT}`: The JSON block of field-to-expression mappings.
   - `${TRIGGER_NAME}`: The flow trigger connection identifier.
   - `${SITE_URL}`: The default target SharePoint Site URL.
2. **Isolated Placeholder Resolver**: Enforce a strict restriction that all template parsing, replacement logic, and JSON verification are isolated in `PlaceholderResolver.resolve()` inside `placeholder_resolver.py`. No other module is permitted to parse placeholders directly.
3. **Strict Validation Checks**:
   - If any placeholder matching `${...}` is left unresolved, the resolver raises a `ValueError` with a list of missing placeholders.
   - If the resolved string is not structurally valid JSON, the resolver raises a `ValueError` indicating a malformed output.
4. **Decoupled Column Filtering**: The Flow Definition Engine does not filter fields. It consumes filtered mappings directly from the Template Engine (`TemplateEngine.load_templates()`) to prevent duplication of classification logic.

## Consequences

- **Fail-Safe Compilation**: Invalid JSON templates or unresolved placeholders are blocked at build time before any deployment attempt.
- **Isolated Responsibilities**: Changes to expression formats, filtering rules, and definition compilation reside in distinct packages (`powerautomate`, `template_engine`, and `flow_definition`).
- **Flexible File Output**: Developers can configure naming patterns (e.g. `tbl_{list_name}`) via `FlowContext` without editing the core engine.
