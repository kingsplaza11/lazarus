import re

from hypothesis import given, settings
from hypothesis import strategies as st

from specgen.generator import (
    EARS, build_models, clean, criteria_of, django_field, generate_spec, model_code, validate_ears,
)
from specgen.naming import common_prefix, model_name, page_group, page_title, page_url, table_base

from specgen_fixtures import taskfreak_like_report


def files_for(report=None, name="TaskFreak! 0.6.4"):
    return generate_spec(report or taskfreak_like_report(), name)


def pick(files, suffix):
    return next(v for k, v in files.items() if k.endswith(suffix))


def test_generates_kiro_layout():
    files = files_for()
    assert set(files) == {
        "specs/taskfreak-0-6-4-resurrection/requirements.md",
        "specs/taskfreak-0-6-4-resurrection/design.md",
        "specs/taskfreak-0-6-4-resurrection/tasks.md",
        "steering/product.md", "steering/tech.md", "steering/structure.md",
    }
    for name in ("product.md", "tech.md", "structure.md"):
        assert files[f"steering/{name}"].startswith("---\ninclusion: always\n---")


def test_every_criterion_is_ears_and_cites_a_source():
    requirements = pick(files_for(), "requirements.md")
    total, invalid = validate_ears(requirements)
    assert total > 20
    assert invalid == []
    for criterion in criteria_of(requirements):
        assert re.search(r"\(source: [^)]+\)$", criterion), criterion


def test_task_requirement_refs_all_exist():
    files = files_for()
    requirements, tasks = pick(files, "requirements.md"), pick(files, "tasks.md")
    existing = set()
    for match in re.finditer(r"^### Requirement (\d+):.*?(?=^### |\Z)", requirements, re.M | re.S):
        count = len(re.findall(r"^\d+\. ", match.group(0), re.M))
        existing |= {f"{match.group(1)}.{i}" for i in range(1, count + 1)}
    refs = {ref.strip() for line in re.findall(r"_Requirements: ([^_]+)_", tasks) for ref in line.split(",")}
    assert refs and refs <= existing, refs - existing


def test_login_requirement_traces_form_redirect_and_table():
    requirements = pick(files_for(), "requirements.md")
    login = requirements.split("### Requirement 1: Login page")[1].split("### Requirement 2")[0]
    assert "the fields username and password" in login and "(source: login.php:30)" in login
    assert "redirect the user to index.php. (source: login.php:18)" in login
    assert "member records on the Login page" in login
    assert "{php}" not in requirements


def test_shared_includes_do_not_leak_into_every_page():
    requirements = pick(files_for(), "requirements.md")
    home = requirements.split("Home page\n")[1].split("### Requirement")[0]
    assert "_common.php" not in home


def test_modernisation_lists_removed_functions_libraries_and_passwords():
    requirements = pick(files_for(), "requirements.md")
    assert "mysql_query" in requirements
    assert "replace the bundled jscalendar library with native HTML date inputs" in requirements
    assert "replace the bundled xajax library with HTMX partial requests" in requirements
    assert "salted one-way hash" in requirements


def test_design_has_url_map_and_app_qualified_foreign_keys():
    design = pick(files_for(), "design.md")
    assert "| `login.php` | `/login/` | accounts | `login` |" in design
    assert 'models.ForeignKey("accounts.Member", on_delete=models.CASCADE, db_column="memberid")' in design
    assert 'models.UniqueConstraint(fields=["member", "project"], name="frk_memberproject_pk")' in design
    assert 'db_table = "frk_item"' in design


def test_models_compile_as_python():
    for model in build_models(taskfreak_like_report()["tables"]):
        compile("from django.db import models\n" + model_code(model), model.name, "exec")


def test_django_field_mapping():
    assert django_field("int(10)", True) == "models.AutoField(primary_key=True)"
    assert django_field("varchar(30)", False) == "models.CharField(max_length=30, blank=True)"
    assert django_field("tinyint(1)", False) == "models.BooleanField(default=False)"
    assert django_field("decimal(8,2)", False) == "models.DecimalField(max_digits=8, decimal_places=2, default=0)"
    assert django_field("datetime", False) == "models.DateTimeField(null=True, blank=True)"
    assert django_field("mystery", False) == "models.TextField(blank=True)"


def test_naming():
    names = ["frk_item", "frk_itemcomment", "frk_memberproject", "frk_project", "frk_member"]
    prefix = common_prefix(names)
    bases = {table_base(n, prefix) for n in names}
    assert prefix == "frk_"
    assert model_name("frk_itemcomment", prefix, bases) == "ItemComment"
    assert model_name("frk_memberproject", prefix, bases) == "MemberProject"
    assert page_title("index.php") == "Home"
    assert page_title("install/index.php") == "Install"
    assert page_group("user_register.php") == "Authentication"
    assert page_url("xajax.task.php") == "/task/"
    assert page_url("project_edit.php") == "/project/edit/"


def test_report_without_tables_or_i18n():
    report = taskfreak_like_report()
    report["tables"], report["i18n"], report["libraries"] = [], None, []
    files = files_for(report)
    requirements = pick(files, "requirements.md")
    assert "Data model" not in requirements and "Translations" not in requirements
    assert validate_ears(requirements)[1] == []


def test_clean_flattens_and_limits():
    assert clean("a\nb   `c`", 80) == "a b 'c'"
    assert len(clean("x" * 200, 40)) == 40


# Names built from tokens (st.text only accepts single characters, and "{php}" is five).
awkward = st.lists(st.sampled_from(list("ab_ \n\t`'\"<>{}?*.:/\\()") + ["{php}"]), min_size=1, max_size=12).map("".join)


@settings(max_examples=60, deadline=None)
@given(get_keys=st.lists(awkward, max_size=4), post_keys=st.lists(awkward, max_size=4),
       field_names=st.lists(awkward, max_size=4), target=awkward, action=awkward)
def test_prop_any_legacy_names_still_give_valid_ears(get_keys, post_keys, field_names, target, action):
    """Whatever strange names the legacy code used, every generated criterion stays valid EARS."""
    report = taskfreak_like_report()
    page = report["pages"][0]
    page["reads"] = {"GET": get_keys, "POST": post_keys}
    page["forms"] = [{"action": action, "method": "POST", "line": 3, "file": page["path"],
                      "fields": [{"name": n, "type": "text"} for n in field_names]}]
    page["redirects"] = [{"target": target, "line": 4, "file": page["path"]}]
    requirements = pick(files_for(report), "requirements.md")
    total, invalid = validate_ears(requirements)
    assert invalid == []
    for criterion in criteria_of(requirements):
        assert "\n" not in criterion and EARS.match(criterion)
