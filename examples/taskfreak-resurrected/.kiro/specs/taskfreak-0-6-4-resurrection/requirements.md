# Requirements Document: TaskFreak! 0.6.4 (resurrected)

## Introduction

TaskFreak! 0.6.4 is a legacy PHP application recovered by Lazarus. Cause of death: 67 calls to 17 functions removed in PHP 7.0 and 8.0, in 13 files. This specification describes its 16 pages, 9 database tables and 9 forms, so it can be rebuilt as a modern Django application that behaves the same way. Every acceptance criterion cites the legacy source it was recovered from.

## Requirements

### Requirement 1: Login page

**User Story:** As a visitor, I want to sign in, so that the resurrected app does everything the original Login page did.

#### Acceptance Criteria
1. WHEN a user opens the Login page THEN THE system SHALL display the Login screen at /login/. (source: login.php:1)
2. WHEN a user submits the Login form with the fields password and login THEN THE system SHALL process the submission as a POST request to login.php. (source: login.php:69)
3. WHEN a user submits the Login form with the fields sProject, id, mode, sort, dir and show THEN THE system SHALL process the submission as a POST request to index.php. (source: include/html/header.php:134)
4. WHEN the Login page is requested with query parameters THEN THE system SHALL handle them as the original did. (source: login.php)
5. WHEN the Login page is requested with the 'xajax' parameter THEN THE system SHALL apply that value as the original did. (source: login.php)
6. WHEN the Login page is requested with the 'xajaxargs' parameter THEN THE system SHALL apply that value as the original did. (source: login.php)
7. WHEN the Login page receives a submitted 'remember' value THEN THE system SHALL process it as the original did. (source: login.php)
8. WHEN the Login page receives a submitted 'username' value THEN THE system SHALL process it as the original did. (source: login.php)
9. WHEN the Login page receives a submitted 'xajax' value THEN THE system SHALL process it as the original did. (source: login.php)
10. WHEN the Login page receives a submitted 'xajaxargs' value THEN THE system SHALL process it as the original did. (source: login.php)
11. IF the original conditions for leaving the Login page are met THEN THE system SHALL redirect the user to error.php?tznMessage=?. (source: _include.php:16)
12. IF the original conditions for leaving the Login page are met THEN THE system SHALL redirect the user to ?. (source: include/classes/tzn_generic.php:1723)
13. WHEN a user signs in successfully THEN THE system SHALL start an authenticated session. (source: login.php)

### Requirement 2: Logout page

**User Story:** As a signed-in user, I want to sign out, so that the resurrected app does everything the original Logout page did.

#### Acceptance Criteria
1. WHEN a user opens the Logout page THEN THE system SHALL display the Logout screen at /logout/. (source: logout.php:1)
2. WHEN a user submits the Logout form with the fields sProject, id, mode, sort, dir and show THEN THE system SHALL process the submission as a POST request to index.php. (source: include/html/header.php:134)
3. WHEN the Logout page is requested with query parameters THEN THE system SHALL handle them as the original did. (source: logout.php)
4. WHEN the Logout page is requested with the 'xajax' parameter THEN THE system SHALL apply that value as the original did. (source: logout.php)
5. WHEN the Logout page is requested with the 'xajaxargs' parameter THEN THE system SHALL apply that value as the original did. (source: logout.php)
6. WHEN the Logout page receives a submitted 'xajax' value THEN THE system SHALL process it as the original did. (source: logout.php)
7. WHEN the Logout page receives a submitted 'xajaxargs' value THEN THE system SHALL process it as the original did. (source: logout.php)
8. IF the original conditions for leaving the Logout page are met THEN THE system SHALL redirect the user to error.php?tznMessage=?. (source: _include.php:16)
9. IF the original conditions for leaving the Logout page are met THEN THE system SHALL redirect the user to ?. (source: include/classes/tzn_generic.php:1723)
10. WHEN a user opens the Logout page THEN THE system SHALL end the user's session. (source: logout.php)

### Requirement 3: User Password page

**User Story:** As a visitor, I want to change my password, so that the resurrected app does everything the original User Password page did.

#### Acceptance Criteria
1. WHEN a user opens the User Password page THEN THE system SHALL display the User Password screen at /user/password/. (source: user_password.php:1)
2. WHEN a user submits the User Password form with the fields reminder THEN THE system SHALL process the submission as a POST request to user_password.php. (source: user_password.php:100)
3. WHEN a user submits the User Password form with the fields sProject, id, mode, sort, dir and show THEN THE system SHALL process the submission as a POST request to index.php. (source: include/html/header.php:134)
4. WHEN the User Password page is requested with query parameters THEN THE system SHALL handle them as the original did. (source: user_password.php)
5. WHEN the User Password page is requested with the 'xajax' parameter THEN THE system SHALL apply that value as the original did. (source: user_password.php)
6. WHEN the User Password page is requested with the 'xajaxargs' parameter THEN THE system SHALL apply that value as the original did. (source: user_password.php)
7. WHEN the User Password page receives a submitted 'email' value THEN THE system SHALL process it as the original did. (source: user_password.php)
8. WHEN the User Password page receives a submitted 'xajax' value THEN THE system SHALL process it as the original did. (source: user_password.php)
9. WHEN the User Password page receives a submitted 'xajaxargs' value THEN THE system SHALL process it as the original did. (source: user_password.php)
10. IF the original conditions for leaving the User Password page are met THEN THE system SHALL redirect the user to error.php?tznMessage=?. (source: _include.php:16)
11. IF the original conditions for leaving the User Password page are met THEN THE system SHALL redirect the user to ?. (source: include/classes/tzn_generic.php:1723)

### Requirement 4: User Register page

**User Story:** As a visitor, I want to create an account, so that the resurrected app does everything the original User Register page did.

#### Acceptance Criteria
1. WHEN a user opens the User Register page THEN THE system SHALL display the User Register screen at /user/register/. (source: user_register.php:1)
2. WHEN a user submits the User Register form with the fields submit THEN THE system SHALL process the submission as a POST request to user_register.php. (source: user_register.php:112)
3. WHEN a user submits the User Register form with the fields sProject, id, mode, sort, dir and show THEN THE system SHALL process the submission as a POST request to index.php. (source: include/html/header.php:134)
4. WHEN the User Register page is requested with query parameters THEN THE system SHALL handle them as the original did. (source: user_register.php)
5. WHEN the User Register page is requested with the 'xajax' parameter THEN THE system SHALL apply that value as the original did. (source: user_register.php)
6. WHEN the User Register page is requested with the 'xajaxargs' parameter THEN THE system SHALL apply that value as the original did. (source: user_register.php)
7. WHEN the User Register page receives a submitted 'password1' value THEN THE system SHALL process it as the original did. (source: user_register.php)
8. WHEN the User Register page receives a submitted 'password2' value THEN THE system SHALL process it as the original did. (source: user_register.php)
9. WHEN the User Register page receives a submitted 'xajax' value THEN THE system SHALL process it as the original did. (source: user_register.php)
10. WHEN the User Register page receives a submitted 'xajaxargs' value THEN THE system SHALL process it as the original did. (source: user_register.php)
11. IF the original conditions for leaving the User Register page are met THEN THE system SHALL redirect the user to error.php?tznMessage=?. (source: _include.php:16)
12. IF the original conditions for leaving the User Register page are met THEN THE system SHALL redirect the user to ?. (source: include/classes/tzn_generic.php:1723)

### Requirement 5: Error page

**User Story:** As a visitor, I want to understand what went wrong, so that the resurrected app does everything the original Error page did.

#### Acceptance Criteria
1. WHEN a user opens the Error page THEN THE system SHALL display the Error screen at /error/. (source: error.php:1)

### Requirement 6: Home page

**User Story:** As a signed-in user, I want to use the Home screen, so that the resurrected app does everything the original Home page did.

#### Acceptance Criteria
1. WHEN a user opens the Home page THEN THE system SHALL display the Home screen at /. (source: index.php:1)
2. WHEN a user submits the Home form with the fields sProject, id, mode, sort, dir and show THEN THE system SHALL process the submission as a POST request to index.php. (source: include/html/header.php:134)
3. WHEN the Home page is requested with query parameters THEN THE system SHALL handle them as the original did. (source: index.php)
4. WHEN the Home page is requested with the 'xajax' parameter THEN THE system SHALL apply that value as the original did. (source: index.php)
5. WHEN the Home page is requested with the 'xajaxargs' parameter THEN THE system SHALL apply that value as the original did. (source: index.php)
6. WHEN the Home page receives a submitted 'xajax' value THEN THE system SHALL process it as the original did. (source: index.php)
7. WHEN the Home page receives a submitted 'xajaxargs' value THEN THE system SHALL process it as the original did. (source: index.php)
8. IF the original conditions for leaving the Home page are met THEN THE system SHALL redirect the user to error.php?tznMessage=?. (source: _include.php:16)
9. IF the original conditions for leaving the Home page are met THEN THE system SHALL redirect the user to ?. (source: include/classes/tzn_generic.php:1723)

### Requirement 7: Install page

**User Story:** As a visitor, I want to install the application, so that the resurrected app does everything the original Install page did.

#### Acceptance Criteria
1. WHEN a user opens the Install page THEN THE system SHALL display the Install screen at /install/. (source: install/index.php:1)
2. WHEN a user submits the Install form with the fields action, src_host, src_user, src_pass, src_base, src_table and 7 more THEN THE system SHALL process the submission as a POST request to the same page. (source: install/mysql.copy.php:84)
3. WHEN the Install page is requested with query parameters THEN THE system SHALL handle them as the original did. (source: install/index.php)
4. IF the original conditions for leaving the Install page are met THEN THE system SHALL redirect the user to ?. (source: include/classes/tzn_generic.php:1723)

### Requirement 8: Print List page

**User Story:** As a signed-in user, I want to see the list of prints, so that the resurrected app does everything the original Print List page did.

#### Acceptance Criteria
1. WHEN a user opens the Print List page THEN THE system SHALL display the Print List screen at /print/list/. (source: print_list.php:1)
2. WHEN a user submits the Print List form with the fields sProject, id, mode, sort, dir and show THEN THE system SHALL process the submission as a POST request to index.php. (source: include/html/header.php:134)
3. WHEN the Print List page is requested with query parameters THEN THE system SHALL handle them as the original did. (source: print_list.php)
4. WHEN the Print List page is requested with the 'xajax' parameter THEN THE system SHALL apply that value as the original did. (source: print_list.php)
5. WHEN the Print List page is requested with the 'xajaxargs' parameter THEN THE system SHALL apply that value as the original did. (source: print_list.php)
6. WHEN the Print List page receives a submitted 'xajax' value THEN THE system SHALL process it as the original did. (source: print_list.php)
7. WHEN the Print List page receives a submitted 'xajaxargs' value THEN THE system SHALL process it as the original did. (source: print_list.php)
8. IF the original conditions for leaving the Print List page are met THEN THE system SHALL redirect the user to error.php?tznMessage=?. (source: _include.php:16)
9. IF the original conditions for leaving the Print List page are met THEN THE system SHALL redirect the user to ?. (source: include/classes/tzn_generic.php:1723)

### Requirement 9: Project Edit page

**User Story:** As a signed-in user, I want to create and edit projects, so that the resurrected app does everything the original Project Edit page did.

#### Acceptance Criteria
1. WHEN a user opens the Project Edit page THEN THE system SHALL display the Project Edit screen at /project/edit/. (source: project_edit.php:1)
2. WHEN a user submits the Project Edit form with the fields submit THEN THE system SHALL process the submission as a POST request to project_edit.php. (source: project_edit.php:223)
3. WHEN a user submits the Project Edit form with the fields invite THEN THE system SHALL process the submission as a POST request to project_edit.php. (source: project_edit.php:317)
4. WHEN a user submits the Project Edit form with the fields sProject, id, mode, sort, dir and show THEN THE system SHALL process the submission as a POST request to index.php. (source: include/html/header.php:134)
5. WHEN the Project Edit page is requested with query parameters THEN THE system SHALL handle them as the original did. (source: project_edit.php)
6. WHEN the Project Edit page is requested with the 'xajax' parameter THEN THE system SHALL apply that value as the original did. (source: project_edit.php)
7. WHEN the Project Edit page is requested with the 'xajaxargs' parameter THEN THE system SHALL apply that value as the original did. (source: project_edit.php)
8. WHEN the Project Edit page receives a submitted 'status' value THEN THE system SHALL process it as the original did. (source: project_edit.php)
9. WHEN the Project Edit page receives a submitted 'xajax' value THEN THE system SHALL process it as the original did. (source: project_edit.php)
10. WHEN the Project Edit page receives a submitted 'xajaxargs' value THEN THE system SHALL process it as the original did. (source: project_edit.php)
11. IF the original conditions for leaving the Project Edit page are met THEN THE system SHALL redirect the user to error.php?tznMessage=?. (source: _include.php:16)
12. IF the original conditions for leaving the Project Edit page are met THEN THE system SHALL redirect the user to ?. (source: include/classes/tzn_generic.php:1723)

### Requirement 10: Project List page

**User Story:** As a signed-in user, I want to see the list of projects, so that the resurrected app does everything the original Project List page did.

#### Acceptance Criteria
1. WHEN a user opens the Project List page THEN THE system SHALL display the Project List screen at /project/list/. (source: project_list.php:1)
2. WHEN a user submits the Project List form with the fields sProject, id, mode, sort, dir and show THEN THE system SHALL process the submission as a POST request to index.php. (source: include/html/header.php:134)
3. WHEN the Project List page is requested with query parameters THEN THE system SHALL handle them as the original did. (source: project_list.php)
4. WHEN the Project List page is requested with the 'xajax' parameter THEN THE system SHALL apply that value as the original did. (source: project_list.php)
5. WHEN the Project List page is requested with the 'xajaxargs' parameter THEN THE system SHALL apply that value as the original did. (source: project_list.php)
6. WHEN the Project List page receives a submitted 'xajax' value THEN THE system SHALL process it as the original did. (source: project_list.php)
7. WHEN the Project List page receives a submitted 'xajaxargs' value THEN THE system SHALL process it as the original did. (source: project_list.php)
8. IF the original conditions for leaving the Project List page are met THEN THE system SHALL redirect the user to error.php?tznMessage=?. (source: _include.php:16)
9. IF the original conditions for leaving the Project List page are met THEN THE system SHALL redirect the user to ?. (source: include/classes/tzn_generic.php:1723)

### Requirement 11: Public page

**User Story:** As a visitor, I want to see public information, so that the resurrected app does everything the original Public page did.

#### Acceptance Criteria
1. WHEN a user opens the Public page THEN THE system SHALL display the Public screen at /public/. (source: public.php:1)
2. WHEN the Public page is requested with query parameters THEN THE system SHALL handle them as the original did. (source: public.php)
3. IF the original conditions for leaving the Public page are met THEN THE system SHALL redirect the user to error.php?tznMessage=?. (source: _include.php:16)
4. IF the original conditions for leaving the Public page are met THEN THE system SHALL redirect the user to ?. (source: include/classes/tzn_generic.php:1723)

### Requirement 12: RSS page

**User Story:** As a visitor, I want to follow updates in a feed reader, so that the resurrected app does everything the original RSS page did.

#### Acceptance Criteria
1. WHEN a user opens the RSS page THEN THE system SHALL display the RSS screen at /rss/. (source: rss.php:1)
2. WHEN the RSS page is requested with query parameters THEN THE system SHALL handle them as the original did. (source: rss.php)
3. IF the original conditions for leaving the RSS page are met THEN THE system SHALL redirect the user to error.php?tznMessage=?. (source: _include.php:16)
4. IF the original conditions for leaving the RSS page are met THEN THE system SHALL redirect the user to ?. (source: include/classes/tzn_generic.php:1723)

### Requirement 13: Task page

**User Story:** As a signed-in user, I want to use the Task screen, so that the resurrected app does everything the original Task page did.

#### Acceptance Criteria
1. WHEN a user opens the Task page THEN THE system SHALL display the Task screen at /task/. (source: xajax.task.php:1)
2. WHEN the Task page is requested with query parameters THEN THE system SHALL handle them as the original did. (source: xajax.task.php)
3. WHEN the Task page is requested with the 'xajax' parameter THEN THE system SHALL apply that value as the original did. (source: xajax.task.php)
4. WHEN the Task page is requested with the 'xajaxargs' parameter THEN THE system SHALL apply that value as the original did. (source: xajax.task.php)
5. WHEN the Task page receives a submitted 'xajax' value THEN THE system SHALL process it as the original did. (source: xajax.task.php)
6. WHEN the Task page receives a submitted 'xajaxargs' value THEN THE system SHALL process it as the original did. (source: xajax.task.php)
7. IF the original conditions for leaving the Task page are met THEN THE system SHALL redirect the user to error.php?tznMessage=?. (source: _include.php:16)
8. IF the original conditions for leaving the Task page are met THEN THE system SHALL redirect the user to ?. (source: include/classes/tzn_generic.php:1723)

### Requirement 14: User Details page

**User Story:** As a signed-in user, I want to view user details, so that the resurrected app does everything the original User Details page did.

#### Acceptance Criteria
1. WHEN a user opens the User Details page THEN THE system SHALL display the User Details screen at /user/details/. (source: user_details.php:1)
2. WHEN a user submits the User Details form with its fields THEN THE system SHALL process the submission as a GET request to user_details.php. (source: user_details.php:166)
3. WHEN a user submits the User Details form with the fields sProject, id, mode, sort, dir and show THEN THE system SHALL process the submission as a POST request to index.php. (source: include/html/header.php:134)
4. WHEN the User Details page is requested with query parameters THEN THE system SHALL handle them as the original did. (source: user_details.php)
5. WHEN the User Details page is requested with the 'xajax' parameter THEN THE system SHALL apply that value as the original did. (source: user_details.php)
6. WHEN the User Details page is requested with the 'xajaxargs' parameter THEN THE system SHALL apply that value as the original did. (source: user_details.php)
7. WHEN the User Details page receives a submitted 'xajax' value THEN THE system SHALL process it as the original did. (source: user_details.php)
8. WHEN the User Details page receives a submitted 'xajaxargs' value THEN THE system SHALL process it as the original did. (source: user_details.php)
9. IF the original conditions for leaving the User Details page are met THEN THE system SHALL redirect the user to error.php?tznMessage=?. (source: _include.php:16)
10. IF the original conditions for leaving the User Details page are met THEN THE system SHALL redirect the user to ?. (source: include/classes/tzn_generic.php:1723)

### Requirement 15: User Edit page

**User Story:** As a signed-in user, I want to create and edit users, so that the resurrected app does everything the original User Edit page did.

#### Acceptance Criteria
1. WHEN a user opens the User Edit page THEN THE system SHALL display the User Edit screen at /user/edit/. (source: user_edit.php:1)
2. WHEN a user submits the User Edit form with the fields submit THEN THE system SHALL process the submission as a POST request to user_edit.php. (source: user_edit.php:113)
3. WHEN a user submits the User Edit form with the fields sProject, id, mode, sort, dir and show THEN THE system SHALL process the submission as a POST request to index.php. (source: include/html/header.php:134)
4. WHEN the User Edit page is requested with query parameters THEN THE system SHALL handle them as the original did. (source: user_edit.php)
5. WHEN the User Edit page is requested with the 'xajax' parameter THEN THE system SHALL apply that value as the original did. (source: user_edit.php)
6. WHEN the User Edit page is requested with the 'xajaxargs' parameter THEN THE system SHALL apply that value as the original did. (source: user_edit.php)
7. WHEN the User Edit page receives a submitted 'enabled' value THEN THE system SHALL process it as the original did. (source: user_edit.php)
8. WHEN the User Edit page receives a submitted 'level' value THEN THE system SHALL process it as the original did. (source: user_edit.php)
9. WHEN the User Edit page receives a submitted 'password1' value THEN THE system SHALL process it as the original did. (source: user_edit.php)
10. WHEN the User Edit page receives a submitted 'password2' value THEN THE system SHALL process it as the original did. (source: user_edit.php)
11. WHEN the User Edit page receives a submitted 'xajax' value THEN THE system SHALL process it as the original did. (source: user_edit.php)
12. WHEN the User Edit page receives a submitted 'xajaxargs' value THEN THE system SHALL process it as the original did. (source: user_edit.php)
13. IF the original conditions for leaving the User Edit page are met THEN THE system SHALL redirect the user to error.php?tznMessage=?. (source: _include.php:16)
14. IF the original conditions for leaving the User Edit page are met THEN THE system SHALL redirect the user to ?. (source: include/classes/tzn_generic.php:1723)

### Requirement 16: User List page

**User Story:** As a signed-in user, I want to see the list of users, so that the resurrected app does everything the original User List page did.

#### Acceptance Criteria
1. WHEN a user opens the User List page THEN THE system SHALL display the User List screen at /user/list/. (source: user_list.php:1)
2. WHEN a user submits the User List form with the fields sProject, id, mode, sort, dir and show THEN THE system SHALL process the submission as a POST request to index.php. (source: include/html/header.php:134)
3. WHEN the User List page is requested with query parameters THEN THE system SHALL handle them as the original did. (source: user_list.php)
4. WHEN the User List page is requested with the 'xajax' parameter THEN THE system SHALL apply that value as the original did. (source: user_list.php)
5. WHEN the User List page is requested with the 'xajaxargs' parameter THEN THE system SHALL apply that value as the original did. (source: user_list.php)
6. WHEN the User List page receives a submitted 'xajax' value THEN THE system SHALL process it as the original did. (source: user_list.php)
7. WHEN the User List page receives a submitted 'xajaxargs' value THEN THE system SHALL process it as the original did. (source: user_list.php)
8. IF the original conditions for leaving the User List page are met THEN THE system SHALL redirect the user to error.php?tznMessage=?. (source: _include.php:16)
9. IF the original conditions for leaving the User List page are met THEN THE system SHALL redirect the user to ?. (source: include/classes/tzn_generic.php:1723)

### Requirement 17: Data model

**User Story:** As the operator, I want every record type of the original database preserved, so that existing data can be migrated without loss.

#### Acceptance Criteria
1. THE system SHALL store country records with the fields countryid and name. (source: schema: frk_country)
2. THE system SHALL store item records with the fields itemid, projectid, itemparentid, priority, context, title, description, deadlinedate and 5 more. (source: schema: frk_item)
3. THE system SHALL store item comment records with the fields itemcommentid, itemid, memberid, postdate, body and lastchangedate. (source: schema: frk_itemcomment)
4. THE system SHALL store item file records with the fields itemfileid, itemid, memberid, filetitle, filename, filetype, filesize, postdate and 2 more. (source: schema: frk_itemfile)
5. THE system SHALL store item status records with the fields itemstatusid, itemid, statusdate, statuskey and memberid. (source: schema: frk_itemstatus)
6. THE system SHALL store member records with the fields memberid, email, title, firstname, middlename, lastname, zipcode, city and 21 more. (source: schema: frk_member)
7. THE system SHALL store member project records with the fields memberid, projectid and position. (source: schema: frk_memberproject)
8. THE system SHALL store project records with the fields projectid, name and description. (source: schema: frk_project)
9. THE system SHALL store project status records with the fields projectstatusid, projectid, statusdate, statuskey and memberid. (source: schema: frk_projectstatus)

### Requirement 18: Modernisation

**User Story:** As the operator, I want the resurrected app to run safely on a supported platform, so that it can stay online for years.

#### Acceptance Criteria
1. THE system SHALL NOT depend on any of the 17 removed PHP functions found by the autopsy, such as ereg, mysql_error, get_magic_quotes_gpc and 14 more. (source: cause of death)
2. THE system SHALL perform all database access through parameterised queries. (source: autopsy: 103 SQL statements)
3. THE system SHALL protect every form against cross-site request forgery. (source: autopsy: 9 forms)
4. WHERE a record stores a password THE system SHALL keep only a salted one-way hash of it. (source: schema: frk_member)
5. THE system SHALL replace the bundled jscalendar library with native HTML date inputs. (source: jscalendar)
6. THE system SHALL replace the bundled xajax library with HTMX partial requests. (source: xajax)

### Requirement 19: Look and feel

**User Story:** As a returning user, I want the resurrected app to look finished and familiar, so that I can use it without relearning it.

#### Acceptance Criteria
1. THE system SHALL style every page through one shared stylesheet linked from the base template. (source: skins/redfreak/css/freak.css)
2. THE system SHALL keep the layout, colours, images and typography of the original stylesheet skins/redfreak/css/freak.css, provided in legacy-assets/. (source: skins/redfreak/css/freak.css)
3. WHERE more than one skin is offered THE system SHALL let the user choose between the original skins bluefreak and redfreak. (source: skins)
4. THE system SHALL show the signed-in user and the main navigation on every page after sign-in. (source: autopsy: 16 pages)
5. THE system SHALL lay out every page so it remains usable on a phone-sized screen. (source: modernisation)

### Requirement 20: Translations

**User Story:** As a user who doesn't read English, I want the interface in my language, so that I can use the app as before.

#### Acceptance Criteria
1. WHERE translations are enabled THE system SHALL offer the interface in the 24 languages of the original: ca, cn, cs, da, de, en, es, fr and 16 more. (source: include/language)
2. THE system SHALL use en as the default language. (source: include/language/en)
