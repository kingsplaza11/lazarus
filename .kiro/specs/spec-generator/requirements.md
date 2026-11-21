# Requirements Document: Spec Generator

## Introduction

The spec generator turns a completed autopsy report into a ready-to-use Kiro `.kiro/` folder for the resurrected app: a requirements document in EARS format with every criterion traced to its legacy source, a design document with Django models and a URL map, an implementation plan, and steering files. Generation works without AI; optional AI polish only rewrites the introduction and can never change facts.

## Requirements

### Requirement 1: Generate the spec

**User Story:** As a developer, I want to turn an autopsy into a Kiro spec with one click, so that Kiro can rebuild the dead app.

#### Acceptance Criteria
1. WHEN a user clicks "Write the spec" on a completed autopsy THEN THE system SHALL generate the spec files and redirect to the spec page.
2. IF the corpse has no completed autopsy THEN THE system SHALL show the message "Run the autopsy before writing the spec."
3. WHEN generation succeeds THEN THE system SHALL produce `requirements.md`, `design.md` and `tasks.md` under `specs/<app>-resurrection/` and `product.md`, `tech.md` and `structure.md` under `steering/`.
4. IF generation raises an error THEN THE system SHALL record the traceback in a failed job and show "Writing the spec failed" with the reason.

### Requirement 2: Requirements document

**User Story:** As a developer, I want requirements Kiro understands and I can verify, so that nothing in the rebuild is guesswork.

#### Acceptance Criteria
1. THE system SHALL write one requirement per legacy page with a user story and EARS acceptance criteria.
2. THE system SHALL end every acceptance criterion with its source as "(source: file:line)" or "(source: file)".
3. THE system SHALL derive criteria from the page's forms, input keys, tables with their SQL verbs, redirects and session use.
4. THE system SHALL ignore queries from include files shared by more than one page when describing a single page.
5. THE system SHALL add a data model requirement with one criterion per table, a modernisation requirement covering removed functions, parameterised queries, CSRF, password hashing and bundled libraries, and a translations requirement when the autopsy found translations.
6. WHEN a legacy name contains line breaks, backticks or PHP placeholders THEN THE system SHALL clean it so the criterion stays a single valid EARS line.

### Requirement 3: Design and plan

**User Story:** As a developer, I want concrete models and tasks, so that Kiro can start building immediately.

#### Acceptance Criteria
1. THE system SHALL map each table to a Django model that keeps the legacy table and column names through `db_table` and `db_column`.
2. WHEN a column ends in "id" and matches another table's single-column primary key THEN THE system SHALL model it as an app-qualified foreign key.
3. WHEN a table has a composite primary key THEN THE system SHALL add a unique constraint over those fields.
4. THE system SHALL include a URL map from each legacy page to its new URL, app and view.
5. THE system SHALL write an implementation plan whose every requirement reference exists in the requirements document.

### Requirement 4: Optional AI polish

**User Story:** As the operator, I want better-written prose without risking wrong facts, so that the spec reads well and stays accurate.

#### Acceptance Criteria
1. WHERE `LAZARUS_AI_POLISH` is set to true THE system SHALL ask Groq, then Gemini, to rewrite only the introduction.
2. IF a rewritten introduction changes, drops or adds any number THEN THE system SHALL discard it and keep the original.
3. IF both providers fail, time out or are rate limited THEN THE system SHALL keep the original introduction.
4. THE system SHALL NOT send acceptance criteria to any AI provider.

### Requirement 5: Review and export

**User Story:** As a developer, I want to read and download the spec, so that I can open it in Kiro.

#### Acceptance Criteria
1. WHEN a user opens the spec page THEN THE system SHALL show each generated file in its own tab and state how many criteria are valid EARS.
2. WHEN a user clicks "Download .kiro/ folder" THEN THE system SHALL return a zip whose top-level folder is `.kiro/`.
3. WHEN a user downloads a single file THEN THE system SHALL return only a file that belongs to the generated spec.
4. IF a requested file path is not part of the spec THEN THE system SHALL respond with 404.
