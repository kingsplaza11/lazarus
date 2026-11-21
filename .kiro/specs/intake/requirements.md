# Requirements Document: Intake

## Introduction

Intake is how a legacy app ("corpse") enters Lazarus. A user uploads a zip file, gives a public GitHub URL, or loads the built-in demo corpse (TaskFreak! 0.6.4). Lazarus stores the files safely without ever running them, builds a file tree, counts files per language, and shows the result. Later features (autopsy, spec generator) read the stored files. The Graveyard home page lists every corpse as a tombstone.

## Requirements

### Requirement 1: Upload a zip

**User Story:** As a developer with a legacy app, I want to upload it as a zip file, so that Lazarus can analyze it.

#### Acceptance Criteria
1. WHEN a user submits the upload form with a name and a `.zip` file THEN THE system SHALL create a `Corpse` record and store the extracted files under `MEDIA_ROOT/corpses/<corpse id>/`.
2. IF the uploaded file is not a valid zip archive THEN THE system SHALL show the message "That file isn't a valid zip archive."
3. IF the uploaded file is larger than 20 MB THEN THE system SHALL reject it with the message "Corpses must be 20 MB or smaller."
4. WHEN an upload succeeds THEN THE system SHALL redirect the user to that corpse's detail page.

### Requirement 2: Import from a GitHub URL

**User Story:** As a developer, I want to paste a public GitHub repository URL, so that I don't have to download and re-upload code.

#### Acceptance Criteria
1. WHEN a user submits a URL of the form `https://github.com/<owner>/<repo>` THEN THE system SHALL download the default branch as a zip archive and process it like an uploaded zip.
2. WHEN a user submits a URL that includes `/tree/<branch>` THEN THE system SHALL download that branch.
3. IF the URL is not a `github.com` repository URL THEN THE system SHALL show the message "Only public github.com repository URLs are supported."
4. IF the download fails or takes longer than 30 seconds THEN THE system SHALL show the message "Couldn't fetch that repository. Is it public?"
5. THE system SHALL store the submitted URL in the corpse's `source_url` field.

### Requirement 3: Load the demo corpse

**User Story:** As a judge or first-time visitor, I want to load a ready-made demo app in one click, so that I can try Lazarus without finding legacy code myself.

#### Acceptance Criteria
1. WHEN a user clicks "Summon the demo corpse" THEN THE system SHALL create a `Corpse` named "TaskFreak! 0.6.4" from a copy of `samples/corpse/`.
2. THE system SHALL NOT modify, move or delete any file in `samples/corpse/`.
3. WHEN the demo corpse already exists THEN THE system SHALL redirect to the existing demo corpse instead of creating a duplicate.

### Requirement 4: Safe extraction

**User Story:** As the operator of a hosted service, I want uploads handled safely, so that a malicious archive cannot harm the server.

#### Acceptance Criteria
1. THE system SHALL NOT execute, import or include any uploaded file.
2. IF an archive entry's path would resolve outside the corpse's folder THEN THE system SHALL reject the whole archive with the message "This archive contains unsafe paths."
3. IF an archive contains more than 500 files THEN THE system SHALL reject it with the message "Corpses can contain at most 500 files."
4. IF the total uncompressed size of an archive exceeds 100 MB THEN THE system SHALL reject it with the message "This archive expands to more than 100 MB."
5. THE system SHALL skip symbolic links and the folders `.git`, `node_modules`, `vendor` and `__MACOSX` during extraction.
6. WHEN an archive is rejected THEN THE system SHALL delete any files already extracted for it and set the corpse status to `failed`.
7. WHEN an archive has a single top-level folder THEN THE system SHALL treat that folder's contents as the corpse root.

### Requirement 5: File tree and language summary

**User Story:** As a developer, I want to see what's inside the corpse, so that I know Lazarus received the right code.

#### Acceptance Criteria
1. WHEN extraction succeeds THEN THE system SHALL save a nested file tree, the total file count and a count of files per language on the corpse.
2. THE system SHALL detect languages by file extension, recognising at least PHP, SQL, HTML, CSS, JavaScript, and "Other".
3. WHEN extraction succeeds THEN THE system SHALL set the corpse status to `done`.
4. IF a corpse contains no `.php` files THEN THE system SHALL show the warning "No PHP files found. Lazarus currently resurrects PHP apps only."

### Requirement 6: Corpse detail page

**User Story:** As a developer, I want a page for each corpse, so that I can review it before the autopsy.

#### Acceptance Criteria
1. WHEN a user opens a corpse's detail page THEN THE system SHALL show its name, source, status, file count, language summary and an expandable file tree.
2. WHEN a user clicks a folder in the file tree THEN THE system SHALL expand or collapse it without reloading the page.
3. THE system SHALL show a disabled "Begin autopsy" button on the detail page.

### Requirement 7: The Graveyard

**User Story:** As a returning user, I want to see all my corpses on the home page, so that I can get back to any of them.

#### Acceptance Criteria
1. WHEN a user opens `/` THEN THE system SHALL list every corpse as a tombstone showing its name, file count, status and date, newest first.
2. WHEN no corpses exist THEN THE system SHALL show the message "The graveyard is empty. Summon the demo corpse or upload your own."
3. THE system SHALL show an enabled "Upload a corpse" button and a "Summon the demo corpse" button on the home page.
4. WHEN a user clicks a tombstone THEN THE system SHALL open that corpse's detail page.
