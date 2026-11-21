# Requirements Document: Autopsy

## Introduction

The autopsy reads every PHP file in a stored corpse and works out what the application does: its pages, the input each page reads, its forms, the database tables and SQL it uses, its include graph, and why it no longer runs on modern PHP ("cause of death"). It never executes the code. The resulting report is the input to the spec generator.

## Requirements

### Requirement 1: Start an autopsy

**User Story:** As a developer, I want to start an autopsy from a corpse's page, so that Lazarus analyses the code I uploaded.

#### Acceptance Criteria
1. WHEN a user clicks "Begin autopsy" on a corpse whose status is `done` THEN THE system SHALL analyse the corpse and redirect to its autopsy report.
2. IF the corpse's status is not `done` THEN THE system SHALL show the message "This corpse isn't ready for an autopsy."
3. WHEN an autopsy already exists for a corpse THEN THE system SHALL replace its report when the user re-runs it.
4. IF the analysis raises an error THEN THE system SHALL mark the autopsy `failed` and show the message "The autopsy failed" with the reason.
5. THE system SHALL NOT execute, include or evaluate any file from the corpse.

### Requirement 2: Per-file analysis

**User Story:** As a developer, I want each PHP file read structurally, so that the findings are accurate rather than guessed.

#### Acceptance Criteria
1. THE system SHALL parse PHP with tree-sitter and record each file's functions, classes (with parent class and methods), includes, superglobal keys read, SQL statements, redirects and session use.
2. WHEN a string or string concatenation starts with an SQL keyword THEN THE system SHALL record it as an SQL statement with its verb, tables and line number.
3. WHEN part of a concatenated string is not a literal THEN THE system SHALL replace that part with "?" before detecting SQL.
4. THE system SHALL record the HTML forms in each file with their action, method, named fields and line number.
5. WHEN a file contains a syntax error THEN THE system SHALL still analyse the readable parts and flag the file as having errors.

### Requirement 3: Cause of death

**User Story:** As a developer, I want to know why the app is dead, so that I understand what blocks it from running today.

#### Acceptance Criteria
1. WHEN a file calls a function removed in PHP 7 or PHP 8 THEN THE system SHALL record the function name, line and the PHP version that removed it.
2. THE system SHALL summarise the cause of death as the total number of calls, the number of distinct removed functions and the number of affected files.
3. WHEN no removed functions are called THEN THE system SHALL state that the code may still run on modern PHP.

### Requirement 4: Pages, includes and database

**User Story:** As a developer, I want the app's pages and data model identified, so that the spec can describe the app as a user sees it.

#### Acceptance Criteria
1. THE system SHALL resolve include targets to files in the corpse, treating dynamic path parts as unknown prefixes.
2. THE system SHALL treat a PHP file as a page WHEN no other file includes it AND it sits at the corpse root or reads input, shows a form or redirects.
3. THE system SHALL list for each page the input keys, forms, tables, redirects and session use found in the page and every file it includes.
4. THE system SHALL read table names, columns, column types and primary keys from CREATE TABLE statements in the corpse's `.sql` files.
5. WHEN an SQL statement names a table without its dynamic prefix THEN THE system SHALL match it to the schema table that ends with that name.

### Requirement 5: Translations

**User Story:** As a developer, I want translation files handled sensibly, so that 20 copies of the same text don't swamp the report.

#### Acceptance Criteria
1. WHEN a folder named `language`, `lang` or `locale` contains two or more language subfolders THEN THE system SHALL analyse only the English subfolder, or the first one if English is absent.
2. THE system SHALL report the translation folder, the list of languages and the number of skipped files.

### Requirement 6: Autopsy report page

**User Story:** As a developer or judge, I want a readable report, so that I can see what Lazarus found at a glance.

#### Acceptance Criteria
1. WHEN a user opens a corpse's autopsy page THEN THE system SHALL show vital signs (PHP files, lines, pages, forms, tables, SQL statements), the cause of death, a pages table, the database tables and the forms.
2. IF no completed autopsy exists for the corpse THEN THE system SHALL redirect to the corpse's detail page.
3. WHEN an autopsy is complete THEN THE system SHALL show a "View autopsy report" link on the corpse's detail page.

### Requirement 7: Command line

**User Story:** As the developer, I want to run and debug the autopsy from the terminal, so that I can iterate on the parser quickly.

#### Acceptance Criteria
1. WHEN the developer runs `python manage.py autopsy <corpse id>` THEN THE system SHALL run the autopsy and print its summary, cause of death, pages and tables.
2. WHEN the developer runs the command with `--file` THEN THE system SHALL print one file's analysis as JSON.
3. WHEN the developer runs the command with `--tree` THEN THE system SHALL print one file's raw syntax tree.
