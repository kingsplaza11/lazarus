---
inclusion: always
---

# Structure

```
manage.py
config/        settings, urls
accounts/      auth, users
core/          everything else
templates/     base.html, per-app templates
tests/
```

## Legacy page → new view
- `error.php` → `core/views.py::error` at `/error/`
- `index.php` → `core/views.py::home` at `/`
- `install/index.php` → `core/views.py::install` at `/install/`
- `login.php` → `accounts/views.py::login` at `/login/`
- `logout.php` → `accounts/views.py::logout` at `/logout/`
- `print_list.php` → `core/views.py::print_list` at `/print/list/`
- `project_edit.php` → `core/views.py::project_edit` at `/project/edit/`
- `project_list.php` → `core/views.py::project_list` at `/project/list/`
- `public.php` → `core/views.py::public` at `/public/`
- `rss.php` → `core/views.py::rss` at `/rss/`
- `user_details.php` → `accounts/views.py::user_details` at `/user/details/`
- `user_edit.php` → `accounts/views.py::user_edit` at `/user/edit/`
- `user_list.php` → `accounts/views.py::user_list` at `/user/list/`
- `user_password.php` → `accounts/views.py::user_password` at `/user/password/`
- `user_register.php` → `accounts/views.py::user_register` at `/user/register/`
- `xajax.task.php` → `core/views.py::task` at `/task/`

## Legacy table → model
- `frk_country` → `core.Country`
- `frk_item` → `core.Item`
- `frk_itemcomment` → `core.ItemComment`
- `frk_itemfile` → `core.ItemFile`
- `frk_itemstatus` → `core.ItemStatus`
- `frk_member` → `accounts.Member`
- `frk_memberproject` → `core.MemberProject`
- `frk_project` → `core.Project`
- `frk_projectstatus` → `core.ProjectStatus`
