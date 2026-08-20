# Creative Scanner Pro — Technical Documentation

This folder is the **technical source of truth** for the Creative Scanner Pro
project. It was produced by reading the actual source code (not the pre-existing
summary docs in the repo). Every file, function, column, and business rule below
was verified against the code in `Backend_Screenshot/` and `Frontend_Screenshot/`.

## How to use this documentation

If you (or an AI assistant) need to modify the project, start with:

1. `01_PROJECT_OVERVIEW.md` — what the system is and its major modules.
2. `02_ARCHITECTURE.md` — how the pieces fit together (frontend, backend, two databases, scanner).
3. `03_DATA_FLOW.md` — end-to-end request flows for each module.
4. The relevant file in `MODULES/` for the module you are changing.
5. `FUTURE_DEVELOPMENT/MODIFICATION_GUIDE.md` — "If I need to change X, look here."

## Folder map

```
PROJECT_DOCUMENTATION/
├── 00_README.md                         ← you are here
├── 01_PROJECT_OVERVIEW.md
├── 02_ARCHITECTURE.md
├── 03_DATA_FLOW.md
├── MODULES/
│   ├── CRM_EXCEL_GENERATOR.md
│   ├── REACH_REPORT_GENERATOR.md
│   ├── FINAL_REPORT_GENERATOR.md
│   └── OTHER_MODULES.md                 ← Scanner, PPT store, Auth, Utilities
├── FILE_DOCUMENTATION/
│   └── FILE_REFERENCE.md
├── DATA/
│   ├── DATA_DICTIONARY.md
│   └── EXCEL_STRUCTURE.md
├── BUSINESS_LOGIC/
│   └── BUSINESS_RULES.md
├── CONFIGURATION/
│   └── CONFIGURATION.md
├── ERROR_HANDLING/
│   └── ERROR_HANDLING.md
├── DEPENDENCIES/
│   └── DEPENDENCY_MAP.md
├── KNOWN_ISSUES/
│   └── TECHNICAL_DEBT.md
└── FUTURE_DEVELOPMENT/
    └── MODIFICATION_GUIDE.md
```

## Confidence markers used throughout

- **[CONFIRMED]** — behavior read directly from source code.
- **[INFERRED]** — deduced from code structure/naming but not 100% explicit.
- **[ASSUMPTION]** — a reasonable guess stated as such.
- **[UNKNOWN]** — "Not determinable from the available source code."

## Repository root paths referenced

- Backend root: `Backend_Screenshot/`
- Frontend root: `Frontend_Screenshot/`
- Standalone maintenance scripts and DB migration tools: repository root (`./`)
