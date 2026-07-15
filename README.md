# PowerFlow Architect

PowerFlow Architect is an enterprise governance, static validation, and schema-driven generation tool for Microsoft Power Automate flow configurations. It treats Power Automate flow configurations as structured metadata, introducing automation, reliability, and architectural guardrails to list-to-spreadsheet synchronization workflows.

## Scale & Performance Baselines

The following metrics demonstrate the real-world scale and capabilities of the platform during testing and verification runs:

| Metric            |            Value |
| ----------------- | ---------------: |
| Lists Discovered  |              123 |
| Fields Discovered |            6,742 |
| Export Formats    | CSV, JSON, Excel |
| Authentication    |       Playwright |

---

## Features

- **Metadata Extractor**: Discovers sites, lists, and field classifications (such as Lookup, Person, Choice, Managed Metadata, Calculated, etc.) from SharePoint.
- **Offline Static Validation**: Checks connection limits, syntax structures, and schema compatibility before flow compilation to prevent runtime failures.
- **Standardized Session Authentication**: Utilizes browser profile redirection via Playwright to securely cache and reuse authenticated standard user sessions, bypassing MFA blockages.
- **Multi-Format Exporter**: Automatically generates structured data outputs in CSV, JSON, and fully formatted/styled Excel (Overview and Details tabs).

---

## Getting Started

### Prerequisites

- **Python**: `3.10+`
- **Dependency Manager**: `pipenv`

### Installation

1. Install project dependencies:
   ```bash
   pipenv install --dev
   ```

2. Install Playwright browser binaries:
   ```bash
   pipenv run playwright install
   ```

### Running the CLI

Configure target SharePoint site URLs in [config.yaml](file:///Users/runedigital/Development/testing/powerflow-architect/config.yaml) or provide them directly via the CLI command:

```bash
pipenv run python main.py inventory --site <SHAREPOINT_SITE_URL>
```

Outputs will be saved in the `Inventory/` directory.

### Running Tests

Execute the unit test suite using `pytest`:

```bash
pipenv run python -m pytest
```

---

## Repository Structure

- [src/](file:///Users/runedigital/Development/testing/powerflow-architect/src): Core implementation modules
  - [auth/](file:///Users/runedigital/Development/testing/powerflow-architect/src/auth): Playwright-based secure authentication
  - [sharepoint/](file:///Users/runedigital/Development/testing/powerflow-architect/src/sharepoint): SharePoint site, list, and field discovery and classification
  - [excel/](file:///Users/runedigital/Development/testing/powerflow-architect/src/excel): Excel spreadsheet generation engines
  - [validators/](file:///Users/runedigital/Development/testing/powerflow-architect/src/validators): Static schema verification logic
- [examples/](file:///Users/runedigital/Development/testing/powerflow-architect/examples): Mock offline mock datasets for local development
  - [sample_inventory.json](file:///Users/runedigital/Development/testing/powerflow-architect/examples/sample_inventory.json): Full mock SharePoint site definition
  - [sample_inventory.csv](file:///Users/runedigital/Development/testing/powerflow-architect/examples/sample_inventory.csv): Flat columns reference
- [tests/](file:///Users/runedigital/Development/testing/powerflow-architect/tests): Automated unit tests verifying auth, classifiers, lists, fields, and sample data validity
