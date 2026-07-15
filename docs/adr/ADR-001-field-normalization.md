# ADR-001: SharePoint Field Type Normalization

## Status
Accepted

## Date
2026-07-15

## Context

Microsoft SharePoint Online represents list columns using a variety of disparate raw type representations depending on the access method (Microsoft Graph API v1.0, Graph Beta, or SharePoint REST API v1/v2). For instance, a multiple-choice column is retrieved as `MultiChoice` with choice arrays in REST, but in Graph, it is represented as a `choice` type with a check box presentation display property. Similarly, person columns are retrieved as `SP.FieldUser` or a Graph column definition with a `personOrGroup` object.

Directly exposing these raw, evolving API schemas to downstream modules (such as the Excel Mapping Engine, validation validators, and Power Automate flow JSON generators) creates tight coupling. Any change in the underlying Microsoft API structure or the ingestion protocol requires extensive refactoring across multiple layers of the application.

## Decision

We will introduce a strict type normalization layer within the `sharepoint` module.

1. **Preserve Raw Metadata**: The original, raw dictionary payload from the API will be preserved in `Field.raw_definition`. This ensures that any specialized, non-standard, or future metadata property remains accessible if needed for advanced customization without losing data integrity.
2. **Preserve Original `field_type`**: The computed original API type representation (e.g. `DateTime` or `Managed Metadata`) will be preserved as a string in `Field.field_type` for backward compatibility with CLI status metrics and legacy code.
3. **Introduce a Normalized Enum (`NormalizedFieldType`)**: We will map every field type to a member of the type-safe `NormalizedFieldType` Enum. This Enum defines a small, consistent, and standardized set of 17 core logical types (e.g. `TEXT`, `NUMBER`, `DATE`, `BOOLEAN`, `LOOKUP`, `LOOKUP_MULTI`, `PERSON`, `PERSON_MULTI`, `CHOICE`, `CHOICE_MULTI`, `MANAGED_METADATA`, `MANAGED_METADATA_MULTI`, `CALCULATED`, `HYPERLINK`, `IMAGE`, `FILE`, `UNKNOWN`).
4. **Isolate Mapping Capabilities**: Mapping behavior and capabilities (e.g. whether a type can be mapped to spreadsheet columns, or whether it supports joining multi-value collections into a single cell) are isolated into a frozen dataclass representation `MappingCapability` in a separate `mapping_capabilities.py` file to maintain the Single Responsibility Principle.
5. **Decouple Rules**: Type-specific mapping rules are stored in a dedicated `classification_rules.py` module. As new SharePoint field types or API properties emerge, developer edits are restricted to adding rules in this module, keeping the classifier and domain models clean.
6. **Support `UNKNOWN` Fallback**: If a field type cannot be recognized, it is mapped to `NormalizedFieldType.UNKNOWN`. This allows the static validator to safely flag the column as "Unsupported Field Type" or report it without crashing the CLI inventory discovery.

## Consequences

- **Decoupled Downstream Modules**: Downstream mapping, validation, and generation modules will interact exclusively with the `NormalizedFieldType` enum values (accessed via `normalized_field_type` on the `Field` model). They are shielded from underlying Graph/REST API changes.
- **Rule Extensibility**: Introducing new types (e.g., Microsoft Loop or advanced custom fields) only requires defining a new sequential rule in `classification_rules.py`.
- **Backward Compatibility**: The existing `field_type` is kept as a string, preventing any breaking behavior in existing inventory CLI tracking logic.
- **Test Integrity**: Unit tests can be isolated to test rules, capabilities, and normalization formats independently.
