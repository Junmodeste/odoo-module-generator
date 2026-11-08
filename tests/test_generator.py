import ast
import csv
import xml.etree.ElementTree as ET

import pytest

from odoo_gen import cli
from odoo_gen.generator import GeneratorError, ModuleSpec, generate, parse_field

EXPECTED_FILES = {
    "__init__.py",
    "__manifest__.py",
    "README.md",
    "models/__init__.py",
    "models/library_book.py",
    "views/library_book_views.xml",
    "security/ir.model.access.csv",
    "tests/__init__.py",
    "tests/test_library_book.py",
}


@pytest.fixture
def spec():
    return ModuleSpec(
        "library_demo", "Library Demo", "Koffi's Lab", "library.book",
        [parse_field("pages:integer"), parse_field("price:float"), parse_field("summary:text")],
    )


def test_generates_all_files(tmp_path, spec):
    path = generate(spec, tmp_path)
    files = {p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file()}
    assert files == EXPECTED_FILES


def test_python_files_compile_and_manifest_is_valid(tmp_path, spec):
    path = generate(spec, tmp_path)
    for py in path.rglob("*.py"):
        compile(py.read_text(encoding="utf-8"), str(py), "exec")
    manifest = ast.literal_eval((path / "__manifest__.py").read_text(encoding="utf-8"))
    assert manifest["version"] == "19.0.1.0.0"
    assert manifest["license"] == "LGPL-3"
    assert manifest["author"] == "Koffi's Lab"  # apostrophe correctement échappée
    for data_file in manifest["data"]:
        assert (path / data_file).exists()


def test_model_fields(tmp_path, spec):
    model = (generate(spec, tmp_path) / "models/library_book.py").read_text(encoding="utf-8")
    assert "class LibraryBook(models.Model):" in model
    assert '_name = "library.book"' in model
    assert "pages = fields.Integer(" in model
    assert "price = fields.Float(" in model


def test_views_are_valid_odoo_19_xml(tmp_path, spec):
    root = ET.parse(generate(spec, tmp_path) / "views/library_book_views.xml").getroot()
    archs = {rec.get("id"): rec for rec in root.iter("record")}
    assert set(archs) == {
        "library_book_view_list", "library_book_view_form", "library_book_view_search", "library_book_action",
    }
    assert root.find(".//list") is not None and root.find(".//tree") is None
    list_fields = [f.get("name") for f in root.find(".//list").iter("field")]
    assert list_fields == ["name", "pages", "price"]  # pas de champ text en liste
    assert root.find("menuitem").get("action") == "library_book_action"


def test_access_csv(tmp_path, spec):
    with open(generate(spec, tmp_path) / "security/ir.model.access.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows == [{
        "id": "access_library_book_user", "name": "library.book user", "model_id:id": "model_library_book",
        "group_id:id": "base.group_user", "perm_read": "1", "perm_write": "1", "perm_create": "1", "perm_unlink": "1",
    }]


@pytest.mark.parametrize("version, tag", [("17.0", "tree"), ("18.0", "list"), ("19.0", "list")])
def test_views_and_manifest_follow_odoo_version(tmp_path, spec, version, tag):
    spec.odoo_version = version
    path = generate(spec, tmp_path)
    manifest = ast.literal_eval((path / "__manifest__.py").read_text(encoding="utf-8"))
    assert manifest["version"] == f"{version}.1.0.0"
    root = ET.parse(path / "views/library_book_views.xml").getroot()
    other = "list" if tag == "tree" else "tree"
    assert root.find(f".//{tag}") is not None and root.find(f".//{other}") is None
    assert root.find(".//field[@name='view_mode']").text == f"{tag},form"
    assert f"Odoo {version[:2]} module" in (path / "README.md").read_text(encoding="utf-8")


def test_cli_odoo_version(tmp_path):
    assert cli.main(["new", "library_demo", "--no-input", "-o", str(tmp_path), "--odoo-version", "17.0"]) == 0
    manifest = ast.literal_eval((tmp_path / "library_demo/__manifest__.py").read_text(encoding="utf-8"))
    assert manifest["version"] == "17.0.1.0.0"


def test_cli_rejects_unknown_odoo_version(tmp_path):
    with pytest.raises(SystemExit):
        cli.main(["new", "library_demo", "--no-input", "-o", str(tmp_path), "--odoo-version", "16.0"])


def test_relational_and_selection_fields(tmp_path, spec):
    spec.fields = [
        parse_field("partner_id:many2one:res.partner"),
        parse_field("state:selection:draft, in_progress,done"),
    ]
    path = generate(spec, tmp_path)
    model_src = (path / "models/library_book.py").read_text(encoding="utf-8")
    compile(model_src, "model.py", "exec")
    assert 'partner_id = fields.Many2one("res.partner", string="Partner")' in model_src
    assert '[("draft", "Draft"), ("in_progress", "In progress"), ("done", "Done")]' in model_src
    search = ET.parse(path / "views/library_book_views.xml").getroot().find(".//search")
    assert [f.get("name") for f in search.iter("field")] == ["name", "partner_id", "state"]


def test_many2many_field(tmp_path, spec):
    spec.fields = [parse_field("tag_ids:many2many:res.partner.category")]
    path = generate(spec, tmp_path)
    model_src = (path / "models/library_book.py").read_text(encoding="utf-8")
    compile(model_src, "model.py", "exec")
    assert 'tag_ids = fields.Many2many("res.partner.category", string="Tags")' in model_src
    root = ET.parse(path / "views/library_book_views.xml").getroot()
    for view in ("list", "form"):
        field_node = root.find(f".//{view}//field[@name='tag_ids']")
        assert field_node.get("widget") == "many2many_tags"
    assert root.find(".//search/field[@name='tag_ids']") is not None


def test_two_many2many_to_same_comodel_rejected(tmp_path, spec):
    spec.fields = [parse_field("tag_ids:many2many:res.partner"), parse_field("reader_ids:many2many:res.partner")]
    with pytest.raises(GeneratorError, match="share the relation table library_book_res_partner_rel"):
        generate(spec, tmp_path)


def test_many2many_explicit_relation(tmp_path, spec):
    spec.fields = [
        parse_field("tag_ids:many2many:res.partner.category"),
        parse_field("genre_ids:many2many:res.partner.category:library_book_genre_rel"),
    ]
    model_src = (generate(spec, tmp_path) / "models/library_book.py").read_text(encoding="utf-8")
    compile(model_src, "model.py", "exec")
    assert 'tag_ids = fields.Many2many("res.partner.category", string="Tags")' in model_src
    assert (
        'genre_ids = fields.Many2many("res.partner.category", relation="library_book_genre_rel", string="Genres")'
        in model_src
    )


def test_many2many_to_model_itself(tmp_path, spec):
    spec.fields = [
        parse_field("related_ids:many2many:library.book"),
        parse_field("sequel_ids:many2many:library.book:library_book_sequel_link"),
    ]
    model_src = (generate(spec, tmp_path) / "models/library_book.py").read_text(encoding="utf-8")
    compile(model_src, "model.py", "exec")
    tree = ast.parse(model_src)
    calls = {
        node.targets[0].id: {kw.arg: kw.value.value for kw in node.value.keywords}
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and node.value.func.attr == "Many2many"
    }
    assert calls["related_ids"] == {
        "relation": "library_book_related_rel", "column1": "library_book_id", "column2": "related_id", "string": "Related",
    }
    assert calls["sequel_ids"]["relation"] == "library_book_sequel_link"
    assert calls["sequel_ids"]["column2"] == "sequel_id"


@pytest.mark.parametrize("fields_text, message", [
    # Table explicite identique au nom par défaut de l'autre champ.
    (["tag_ids:many2many:res.partner", "reader_ids:many2many:res.partner:library_book_res_partner_rel"], "share"),
    (["tag_ids:many2many:res.partner:book_rel", "reader_ids:many2many:res.users:book_rel"], "share"),
    (["tag_ids:many2many:res.partner:library_book"], "own table"),
    # Many2many vers le modèle lui-même.
    (["library_book_ids:many2many:library.book"], "both columns"),
    (["related_ids:many2many:library.book", "other_ids:many2many:library.book:library_book_related_rel"], "share"),
    (["r" * 52 + "_ids:many2many:library.book"], "63 characters"),
])
def test_invalid_many2many_relations(tmp_path, spec, fields_text, message):
    spec.fields = [parse_field(text) for text in fields_text]
    with pytest.raises(GeneratorError, match=message):
        generate(spec, tmp_path)


def test_one2many_field(tmp_path, spec):
    spec.fields = [
        parse_field("parent_id:many2one:library.book"),
        parse_field("child_ids:one2many:library.book:parent_id"),
    ]
    path = generate(spec, tmp_path)
    model_src = (path / "models/library_book.py").read_text(encoding="utf-8")
    compile(model_src, "model.py", "exec")
    assert 'child_ids = fields.One2many("library.book", "parent_id", string="Children")' in model_src
    root = ET.parse(path / "views/library_book_views.xml").getroot()
    assert root.find(".//form//field[@name='child_ids']") is not None
    assert root.find(".//list//field[@name='child_ids']") is None
    assert root.find(".//search/field[@name='child_ids']") is None


@pytest.mark.parametrize("fields_text, message", [
    (["child_ids:one2many:res.partner:parent_id"], "only supports the generated model"),
    (["child_ids:one2many:library.book:parent_id"], "inverse 'parent_id'"),
    (["parent_id:many2one:res.partner", "child_ids:one2many:library.book:parent_id"], "inverse 'parent_id'"),
    (["pages:integer", "child_ids:one2many:library.book:pages"], "inverse 'pages'"),
])
def test_invalid_one2many(tmp_path, spec, fields_text, message):
    spec.fields = [parse_field(text) for text in fields_text]
    with pytest.raises(GeneratorError, match=message):
        generate(spec, tmp_path)


@pytest.mark.parametrize("text", [
    "pages", "pages:", "Pages:integer", "name:char", "x:money", "2x:char",
    "partner_id:many2one", "partner_id:many2one:partner", "tag_ids:many2many", "state:selection", "state:selection:a,,b",
    "state:selection:Draft", "state:selection:a,a", "pages:integer:10",
    "tag_ids:many2many:res.partner:", "tag_ids:many2many:res.partner:Book-Rel", "tag_ids:many2many:res.partner:" + "x" * 64,
    "partner_id:many2one:res.partner:rel",
    "child_ids:one2many", "child_ids:one2many:library.book", "child_ids:one2many:library.book:",
    "child_ids:one2many:book:parent_id",
])
def test_invalid_fields(text):
    with pytest.raises(GeneratorError):
        parse_field(text)


@pytest.mark.parametrize("kwargs", [
    {"technical_name": "Library"},
    {"model": "book"},
    {"title": " "},
    {"odoo_version": "16.0"},
    {"fields": [parse_field("pages:integer"), parse_field("pages:float")]},
])
def test_invalid_spec(tmp_path, spec, kwargs):
    for key, value in kwargs.items():
        setattr(spec, key, value)
    with pytest.raises(GeneratorError):
        generate(spec, tmp_path)


def test_refuses_existing_directory(tmp_path, spec):
    generate(spec, tmp_path)
    with pytest.raises(GeneratorError):
        generate(spec, tmp_path)


def test_cli_non_interactive(tmp_path, capsys):
    code = cli.main([
        "new", "library_demo", "--no-input", "-o", str(tmp_path),
        "--title", "Library", "--author", "Me", "--model", "library.book", "--field", "pages:integer",
    ])
    assert code == 0
    assert (tmp_path / "library_demo/models/library_book.py").exists()
    assert "Module created" in capsys.readouterr().out


def test_cli_defaults(tmp_path):
    assert cli.main(["new", "library_demo", "--no-input", "-o", str(tmp_path)]) == 0
    assert (tmp_path / "library_demo/models/library_demo.py").exists()


def test_cli_error_exit_code(tmp_path, capsys):
    assert cli.main(["new", "library_demo", "--no-input", "-o", str(tmp_path), "--field", "bad"]) == 1
    assert "error:" in capsys.readouterr().err


def test_cli_interactive(tmp_path, monkeypatch):
    answers = iter(["Ma Bibliothèque", "Koffi", "library.book", "17.0", "pages:integer", "oops", "price:float", ""])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    assert cli.main(["new", "library_demo", "-o", str(tmp_path)]) == 0
    manifest = ast.literal_eval((tmp_path / "library_demo/__manifest__.py").read_text(encoding="utf-8"))
    assert manifest["name"] == "Ma Bibliothèque"
    assert manifest["version"] == "17.0.1.0.0"
    model = (tmp_path / "library_demo/models/library_book.py").read_text(encoding="utf-8")
    assert "pages = fields.Integer(" in model and "price = fields.Float(" in model


@pytest.mark.parametrize("text, label", [
    ("tag_ids:many2many:res.partner.category", "Tags"),
    ("child_ids:one2many:library.book:parent_id", "Children"),
    ("related_ids:many2many:library.book", "Related"),
    ("category_ids:many2many:product.category", "Categories"),
    ("day_ids:many2many:res.partner", "Days"),
    ("box_ids:many2many:res.partner", "Boxes"),
    ("sale_branch_ids:many2many:res.partner", "Sale branches"),
    ("partner_id:many2one:res.partner", "Partner"),
])
def test_relational_labels(text, label):
    assert parse_field(text).label == label
