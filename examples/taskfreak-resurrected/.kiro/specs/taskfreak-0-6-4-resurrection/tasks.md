# Implementation Plan: TaskFreak! 0.6.4 (resurrected)

- [x] 1. Set up the Django project with `accounts` and `core` apps, a styled `base.html` with navigation, and HTMX
  - _Requirements: 18.1, 18.2, 18.3, 19.1_

- [x] 2. Create the data models
  - [x] 2.1 `Country` in `core/models.py` (table `frk_country`)
    - _Requirements: 17.1_
  - [x] 2.2 `Item` in `core/models.py` (table `frk_item`)
    - _Requirements: 17.2_
  - [x] 2.3 `ItemComment` in `core/models.py` (table `frk_itemcomment`)
    - _Requirements: 17.3_
  - [x] 2.4 `ItemFile` in `core/models.py` (table `frk_itemfile`)
    - _Requirements: 17.4_
  - [x] 2.5 `ItemStatus` in `core/models.py` (table `frk_itemstatus`)
    - _Requirements: 17.5_
  - [x] 2.6 `Member` in `accounts/models.py` (table `frk_member`)
    - _Requirements: 17.6_
  - [x] 2.7 `MemberProject` in `core/models.py` (table `frk_memberproject`)
    - _Requirements: 17.7_
  - [x] 2.8 `Project` in `core/models.py` (table `frk_project`)
    - _Requirements: 17.8_
  - [x] 2.9 `ProjectStatus` in `core/models.py` (table `frk_projectstatus`)
    - _Requirements: 17.9_
  - [x] 2.10 Make migrations; write a loader for data from the legacy database
    - _Requirements: 17.1, 17.2, 17.3_

- [x] 3. Authentication: build the pages
  - [x] 3.1 `login` view at `/login/` replacing `login.php`, with template and tests
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 1.11, 1.12, 1.13_
  - [x] 3.2 `logout` view at `/logout/` replacing `logout.php`, with template and tests
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10_
  - [x] 3.3 `user_password` view at `/user/password/` replacing `user_password.php`, with template and tests
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11_
  - [x] 3.4 `user_register` view at `/user/register/` replacing `user_register.php`, with template and tests
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 4.11, 4.12_

- [x] 4. Error: build the pages
  - [x] 4.1 `error` view at `/error/` replacing `error.php`, with template and tests
    - _Requirements: 5.1_

- [x] 5. Home: build the pages
  - [x] 5.1 `home` view at `/` replacing `index.php`, with template and tests
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9_

- [x] 6. Install: build the pages
  - [x] 6.1 `install` view at `/install/` replacing `install/index.php`, with template and tests
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 7. Print: build the pages
  - [x] 7.1 `print_list` view at `/print/list/` replacing `print_list.php`, with template and tests
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9_

- [x] 8. Project: build the pages
  - [x] 8.1 `project_edit` view at `/project/edit/` replacing `project_edit.php`, with template and tests
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10, 9.11, 9.12_
  - [x] 8.2 `project_list` view at `/project/list/` replacing `project_list.php`, with template and tests
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9_

- [x] 9. Public: build the pages
  - [x] 9.1 `public` view at `/public/` replacing `public.php`, with template and tests
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [x] 10. RSS: build the pages
  - [x] 10.1 `rss` view at `/rss/` replacing `rss.php`, with template and tests
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

- [x] 11. Task: build the pages
  - [x] 11.1 `task` view at `/task/` replacing `xajax.task.php`, with template and tests
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 13.8_

- [x] 12. User: build the pages
  - [x] 12.1 `user_details` view at `/user/details/` replacing `user_details.php`, with template and tests
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8, 14.9, 14.10_
  - [x] 12.2 `user_edit` view at `/user/edit/` replacing `user_edit.php`, with template and tests
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7, 15.8, 15.9, 15.10, 15.11, 15.12, 15.13, 15.14_
  - [x] 12.3 `user_list` view at `/user/list/` replacing `user_list.php`, with template and tests
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.7, 16.8, 16.9_

- [x] 13. Modernise: remove legacy dependencies, harden forms and passwords, replace bundled libraries
  - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6_

- [x] 14. Look and feel: port the original styling from `legacy-assets/skins/redfreak/css/freak.css` (included in the download, with its images) into `static/` and apply it to every template
  - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5_

- [-] 15. Translations with Django i18n, porting the original language files
  - _Requirements: 20.1, 20.2_

- [~] 16. Verify parity with the original
  - Run the test suite, then `lazarus parity` against the legacy app; fix differences until the score is acceptable
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1_
