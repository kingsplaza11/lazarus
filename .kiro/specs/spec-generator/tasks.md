# Implementation Plan: Spec Generator

- [x] 1. Naming helpers (`specgen/naming.py`)
  - _Requirements: 3.1, 3.4_

- [x] 2. Generator (`specgen/generator.py`)
  - [x] 2.1 Data models with foreign keys and composite constraints
    - _Requirements: 3.1, 3.2, 3.3_
  - [x] 2.2 Page, data, modernisation and translation requirements with source citations
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_
  - [x] 2.3 Design, tasks and steering documents; EARS validation
    - _Requirements: 1.3, 3.4, 3.5_
  - [x] 2.4 Tests including the hostile-names property test
    - _Requirements: 2.6, 3.5_

- [x] 3. Optional AI polish (`specgen/llm.py`) with tests
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 4. Service, views, URLs, spec page, autopsy page button
  - _Requirements: 1.1, 1.2, 1.4, 5.1, 5.2, 5.3, 5.4_

- [x] 5. Verify on TaskFreak: generate, download, open the `.kiro/` folder in Kiro
  - _Requirements: 1.1, 5.2_
