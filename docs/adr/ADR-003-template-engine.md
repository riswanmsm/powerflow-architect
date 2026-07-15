# ADR-003: Template Engine for Excel Online Actions

## Status
Accepted

## Date
2026-07-15

## Context

Power Automate Excel Online actions, such as "Add a row into a table" and "Update a row", require a complete mapping JSON payload where the key-value pairs link spreadsheet column headers to their corresponding values. 

In Excel Tables sync setups:
1. Column headers are generated using the SharePoint field **Display Names** (e.g. `"Description"`) rather than their **Internal Names** (e.g. `"Description1"`).
2. Many SharePoint fields are read-only metadata columns (e.g. `ID`, `Created`, `Modified`, `Author`) managed automatically by SharePoint, or unsupported complex types (e.g. Geolocation). Attempting to map or write to these system columns during sync operations triggers flow validation crashes.
3. The structural assembly of complete list row mapping templates should remain independent of raw expression string formatting strategies to ensure clean separation of concerns.

## Decision

We will implement a Template Engine module that structures and filters the compiled field mappings:

1. **Map Display Names as Keys**: In `templates.json` and the output schemas, keys correspond to the field's `display_name` instead of its internal `name`.
2. **Exclude Non-Writable Fields**: 
   - Filter out fields where `is_system` is `True`, with the explicit exception of `Title` (which is a default system column but must be mapped).
   - Filter out fields classified as `NormalizedFieldType.UNKNOWN` (unsupported types).
3. **Decouple Templating from Generation**: The Template Engine is structural and is not responsible for creating new expressions. It invokes the Sprint 3 `ExpressionEngine` to obtain expressions and focuses solely on assembly, validation, and filtering.
4. **Optimized Excel Copy-Paste Layout**: Output `templates.xlsx` with columns `"Excel Column Header"` and `"Power Automate Expression"` rather than full metadata headers, ensuring developers can locate columns easily and copy-paste expressions in one click.

## Consequences

- **Header Alignment**: Templates align perfectly with Excel table headers out of the box.
- **Fail-Safe Synced Columns**: Excluding read-only system columns and unsupported types prevents flow run exceptions during row additions/updates.
- **Maintainability**: The parsing of expressions remains isolated inside the `powerautomate` module, while the structural mappings are contained in `template_engine`.
