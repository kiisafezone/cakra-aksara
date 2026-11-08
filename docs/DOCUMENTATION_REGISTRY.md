# Cakra Aksara (UAIL) — Documentation Registry

**Project:** Cakra Aksara  
**System:** Universal Artificial Intelligence Layer (UAIL)  
**Document type:** Master documentation registry  
**Status:** Initial documentation framework  
**Last updated:** 2026-11-08

## Purpose and authority

This registry is the single source of truth for the status, owner, canonical path, and last update of project documentation. `docs/MASTER.md` remains the project’s consolidated product and technical baseline; use this registry to find and track the supporting documents.

A planned path is a target location and does not mean the document already exists. Update this registry whenever a document is created, moved, approved, or materially revised. Use ISO 8601 dates (`YYYY-MM-DD`) for `Last Updated`; use `—` when a document has not yet been created or updated.

## Status definitions

| Status | Meaning |
|---|---|
| **Baseline** | Exists and is the current working reference; may still need owner approval. |
| **Planned** | Identified and scoped, but not yet created. |
| **In progress** | Being drafted or revised. |
| **In review** | Awaiting review or approval. |
| **Approved** | Formally accepted as the current version. |
| **Archived** | Superseded or no longer maintained; retained for history. |

## Registry

| ID | Acronym / artifact | Full name | Category | Status | Owner | Canonical path | Last Updated |
|---|---|---|---|---|---|---|---|
| DOC-01 | PRD | Product Requirements Document | Product & Business Requirements | Planned | Product Owner (TBD) | `docs/01-product/PRD.md` | — |
| DOC-02 | TRD | Technical Requirements Document | Architecture & Engineering | Planned | Technical Lead (TBD) | `docs/04-engineering/TRD.md` | — |
| DOC-03 | AFD | Architecture Framework Document | Architecture & Engineering | Planned | Architect (TBD) | `docs/03-architecture/AFD.md` | — |
| DOC-04 | DBD | Database Design Document | Architecture & Engineering | Planned | Data/Backend Lead (TBD) | `docs/04-engineering/DBD.md` | — |
| DOC-05 | BSD | Business Specification Document | Product & Business Requirements | Planned | Product Owner (TBD) | `docs/01-product/BSD.md` | — |
| DOC-06 | IPD | Implementation Plan Document | Implementation & Operations | Planned | Project Lead (TBD) | `docs/08-deployment/IPD.md` | — |
| DOC-07 | SRS | Software Requirements Specification | Product & Business Requirements | Planned | Product Owner (TBD) | `docs/02-requirements/SRS.md` | — |
| DOC-08 | SDS | Software Design Specification | Architecture & Engineering | Planned | Architect (TBD) | `docs/04-engineering/SDS.md` | — |
| DOC-09 | API | Application Programming Interface Specification | Integration & Security | Planned | API/Backend Lead (TBD) | `docs/05-integration/API.md` | — |
| DOC-10 | TSD | Test Strategy Document | Testing & Quality Assurance | Planned | QA Lead (TBD) | `docs/07-testing/TSD.md` | — |
| DOC-11 | SEC | Security Specification | Integration & Security | Planned | Security Lead (TBD) | `docs/06-security/SEC.md` | — |
| DOC-12 | ADR | Architecture Decision Records | Architecture & Engineering | Planned | Architect (TBD) | `docs/03-architecture/adr/` | — |
| DOC-13 | ODD | Operations & Deployment Document | Implementation & Operations | Planned | Operations Lead (TBD) | `docs/08-deployment/ODD.md` | — |
| DOC-14 | UAT | User Acceptance Testing — plan, execution, and results artifacts | Testing & Quality Assurance (testing activity and artifacts, not a standalone specification document) | Planned | Product Owner / QA Lead (TBD) | `docs/07-testing/uat/` | — |
| DOC-15 | ICD | Interface Control Document | Integration & Security | Planned | Integration Lead (TBD) | `docs/05-integration/ICD.md` | — |
| DOC-16 | RSK | Risk Assessment Document | Implementation & Operations | Planned | Project Lead / Security Lead (TBD) | `docs/09-governance/RSK.md` | — |
| DOC-17 | MASTER | Master Documentation | Project baseline and documentation governance | Baseline | Product Owner (TBD) | `docs/MASTER.md` | 2026-11-08 |

> **Count:** 16 supporting document/artifact entries, plus the master baseline (`DOC-17`). UAT is tracked as a testing activity and its deliverables, not as a standalone specification document.

## Documentation categories

1. **Product & Business Requirements:** PRD, BSD, SRS
2. **Architecture & Engineering:** AFD, TRD, SDS, DBD, ADR
3. **Integration & Security:** API, ICD, SEC
4. **Testing & Quality Assurance:** TSD, UAT artifacts
5. **Implementation & Operations:** IPD, ODD, RSK

## Maintenance rules

- Keep each document’s status, owner, canonical path, and `Last Updated` current here.
- A document owner is accountable for content and review; use `TBD` until a person or role is assigned.
- Update `Last Updated` when the document’s substantive content changes, not for formatting-only edits.
- Record significant architecture decisions in individual ADRs and link them from this registry or the relevant document.
- Keep `docs/MASTER.md` focused on the consolidated project baseline; use this registry for document inventory and lifecycle status.
- When a document is superseded, mark it **Archived** and link its replacement rather than silently deleting its history.
