---
inclusion: always
---

# Product: Lazarus

## What it is
Lazarus resurrects dead legacy code. It takes an abandoned PHP application, performs an "autopsy" to understand what it does, generates a complete Kiro spec (requirements, design, tasks, steering), and enables Kiro to rebuild it as a modern Django app. A parity check then proves the rebuilt app behaves like the original.

## Who it's for
- Small teams and solo developers who inherited legacy PHP apps nobody understands
- Agencies asked to "modernize" old client systems without documentation
- Anyone whose app is stuck on PHP 5 / the removed `mysql_*` extension and cannot run on a modern server

## The problem
Legacy apps keep running businesses long after their technology dies. Nobody wants to touch them because nobody knows exactly what they do. Rewrites fail because requirements are lost. Lazarus recovers the requirements from the code itself.

## Hackathon context
- Event: Kiroween 2026 (Devpost), category: Resurrection
- Deadline: Dec 4, 2026, 2:00 PM Pacific; target submit Dec 3
- Must be built with Kiro; this repo's `.kiro/` folder must stay committed

## Scope (locked)
- Input stack: legacy PHP + MySQL only (procedural PHP, `mysql_*`/`mysqli`, inline SQL, HTML forms)
- Output stack: Django
- Demo corpse: TaskFreak! 0.6.4 (GPL, in `samples/corpse/`): third-party input, never modified
- Zero cost: no paid APIs or services

## Core user flow
1. Upload a legacy app (GitHub URL or zip)
2. View the autopsy: pages, forms, database tables, SQL queries, includes, sessions
3. View and download the generated `.kiro/` spec
4. Rebuild with Kiro (IDE or CLI) from that spec
5. Run `lazarus parity` locally to compare old vs new behavior and get a score

## Product principles
- Works without AI: parsing + templates must always produce a usable spec; AI only polishes wording
- Never execute uploaded code on the hosted server
- Every requirement traces back to a source file and line
- Clear over clever: a judge must understand each screen without explanation
- Spooky theme in copy and visuals, but readability first
