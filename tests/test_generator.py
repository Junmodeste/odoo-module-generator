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


@pytest.mark.parametrize("text", ["pages", "pages:", "Pages:integer", "name:char", "x:money", "2x:char"])
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
