---
inclusion: always
---

# Requirement format: EARS

Every requirement Lazarus generates, and every requirement in this repo's own specs, uses EARS (Easy Approach to Requirements Syntax), matching Kiro's spec format.

## Structure of a requirements.md
Each requirement is a user story followed by numbered acceptance criteria:

```
### Requirement 1: <short name>

**User Story:** As a <role>, I want <capability>, so that <benefit>.

#### Acceptance Criteria
1. WHEN <trigger> THEN THE <system> SHALL <response>
2. IF <unwanted condition> THEN THE <system> SHALL <response>
```

## The patterns
| Pattern | Template |
|---|---|
| Event-driven | WHEN <trigger> THEN THE <system> SHALL <response> |
| State-driven | WHILE <state> THE <system> SHALL <response> |
| Unwanted behavior | IF <condition> THEN THE <system> SHALL <response> |
| Optional feature | WHERE <feature is included> THE <system> SHALL <response> |
| Ubiquitous | THE <system> SHALL <response> |

## Rules
- Keywords in capitals: WHEN, WHILE, IF, THEN, WHERE, SHALL
- One behavior per criterion; split "and" into separate criteria
- Testable: a response must be observable (page shown, record saved, redirect, message)
- No implementation details (no "use Django forms", no class names)
- For generated specs, end each criterion with its source: `(source: login.php:42)`

## Good examples
1. WHEN a user submits the login form with a valid username and password THEN THE system SHALL redirect the user to the task list. (source: login.php:31)
2. IF a user submits a task without a title THEN THE system SHALL show the message "Title is required". (source: xajax.task.php:118)

## Bad examples (and why)
1. "The system should handle logins properly."
   - No trigger, uses "should", and "properly" isn't testable.
2. "WHEN the user saves a task THEN THE system SHALL validate it using a Django ModelForm and save it to the tasks table and send an email."
   - Three behaviors in one criterion, and it names implementation details (ModelForm).

## Validation regex (used by tests and hooks)
A criterion is valid if it matches:
`^(WHEN .+ THEN |WHILE .+ |IF .+ THEN |WHERE .+ )?THE .+ SHALL .+$`
