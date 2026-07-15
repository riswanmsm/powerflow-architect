# ADR-002: Production Expression Engine and Offline Generator

## Status
Accepted

## Date
2026-07-15

## Context

Power Automate (formerly Microsoft Flow) expressions used in loop blocks require specific formatting (e.g. starting with `@`) to be accepted directly by the flow designer's expression editor. Manual compilation of these expressions is error-prone, particularly for complex lookups, people properties, or multi-value fields.

Multi-value fields (e.g., `ChoiceMulti`, `LookupMulti`, `PersonMulti`, `ManagedMetadataMulti`) store data as JSON arrays of objects. To map these into a single string cell (e.g. in a CSV/Excel sync file), a single-line expression must be constructed to format and join the array contents. A standard Power Automate flow lacks a simple `join(map(...))` operator, necessitating a verbose but highly reliable combination of `json()`, `xml()`, and `xpath()` to filter and extract values.

Furthermore, flow development environments can vary (custom loop names, alternative delimiters, custom lookup value fields), so all generated expressions must be configurable without hardcoding environment details. Lastly, this generation should be fast, offline, and consume list inventories previously created.

## Decision

We will implement a modular Production Expression Engine and an offline Generator module:

1. **Include Leading `@`**: Every generated expression starts with `@` so it is copy-paste-ready in the Power Automate expression editor without manual tweaks.
2. **Immutable `ExpressionContext`**: Introduce a frozen `ExpressionContext` dataclass containing configurable defaults:
   - `loop_name` (default: `"Apply_to_each_1"`)
   - `delimiter` (default: `" | "`)
   - `lookup_property` (default: `"Value"`)
   - `person_property` (default: `"Email"`)
3. **Dedicated Strategy Pattern**: Map each `NormalizedFieldType` to a subclass of `ExpressionStrategy`.
   - Single-value lookups, choices, people, and metadata utilize direct sub-property paths (e.g. `?['Project/Value']`, `?['AssignedTo/Email']`, `?['Category/Label']`).
   - Standard single-value fields access the property directly (`?['Title']`).
4. **XPath Multi-Value Engine**: Implement the production-validated XML/XPath single-line array mapping template for multi-value types:
   ```text
   @join(xpath(xml(json(concat('{"items":{"item":',string(items('<loop_name>')?['<InternalFieldName>']),'}}'))),'//<property>/text()'),'<delimiter>')
   ```
   This has been verified in production and serves as the canonical implementation.
5. **ExpressionEngine Wrapper**: Implement a parser method `ExpressionEngine.generate(field: dict, context)` that maps inventory JSON fields to their corresponding strategy. It includes a fallback translation registry mapping raw `"field_type"` strings (e.g., `DateTime`, `TaxonomyFieldType`) to their normalized types if `"NormalizedFieldType"` is missing from the input JSON.
6. **System Column Filtering**: Automatically exclude read-only, SharePoint-managed system columns (e.g., `ID`, `Created`, `Modified`, `Author`, `Editor`) from the generated expressions, while preserving user-writable columns like `Title` to keep spreadsheet maps clean and actionable.
7. **Offline Generator**: Implement `ExpressionGenerator` to parse list definitions offline from the input JSON and export the results to JSON, CSV, and formatted Excel sheets (with a `"Copy Value"` column).

## Consequences

- **Copy-Paste Flow Design**: Flow developers can copy generated expressions directly from the spreadsheet into the Power Automate editor, eliminating syntax errors.
- **Offline Reliability**: Generation runs entirely offline from the inventory JSON file, removing the need for SharePoint authentication or API queries during generation.
- **Flexible Environment Context**: The generated code dynamically adjusts to loop names or delimiters by changing the `ExpressionContext` options, removing hardcoded logic.
- **Clean Sync Spreadsheets**: Automatically filtering system columns ensures that only the columns that can actually be mapped and modified are visible to the user.
