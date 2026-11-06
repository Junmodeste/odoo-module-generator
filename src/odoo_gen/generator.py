"""Validation des paramètres et rendu des templates Jinja2."""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, PackageLoader, StrictUndefined

# Types simples acceptés pour --field nom:type, et leur classe Odoo.
FIELD_TYPES = {
    "char": "Char",
    "text": "Text",
    "html": "Html",
    "integer": "Integer",
    "float": "Float",
    "boolean": "Boolean",
    "date": "Date",
    "datetime": "Datetime",
    # Types à paramètre : many2one:<modèle>, selection:<clé>,<clé>...
    "many2one": "Many2one",
    "selection": "Selection",
}

# Versions d'Odoo ciblées par --odoo-version ; la dernière est la valeur par défaut.
ODOO_VERSIONS = ("17.0", "18.0", "19.0")

MODULE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
MODEL_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
FIELD_RE = re.compile(r"^[a-z][a-z0-9_]*$")
# Le champ `name` est toujours généré ; les autres noms réservés casseraient l'ORM.
RESERVED_FIELDS = {"name", "id", "create_uid", "create_date", "write_uid", "write_date", "display_name"}

# Template -> chemin de sortie (formaté avec les attributs de ModuleSpec).
FILES = {
    "__init__.py.j2": "__init__.py",
    "__manifest__.py.j2": "__manifest__.py",
    "README.md.j2": "README.md",
    "models/__init__.py.j2": "models/__init__.py",
    "models/model.py.j2": "models/{model_file}.py",
    "views/views.xml.j2": "views/{model_file}_views.xml",
    "security/ir.model.access.csv.j2": "security/ir.model.access.csv",
    "tests/__init__.py.j2": "tests/__init__.py",
    "tests/test_model.py.j2": "tests/test_{model_file}.py",
}


class GeneratorError(ValueError):
    """Paramètre invalide ou dossier de sortie déjà présent."""


@dataclass
class Field:
    name: str
    type: str
    comodel: str = ""
    selection: list = field(default_factory=list)

    @property
    def odoo_class(self):
        return FIELD_TYPES[self.type]

    @property
    def label(self):
        # Convention Odoo : partner_id s'affiche « Partner ».
        base = self.name[:-3] if self.type == "many2one" and self.name.endswith("_id") else self.name
        return base.replace("_", " ").capitalize()

    @property
    def selection_items(self):
        return [(key, key.replace("_", " ").capitalize()) for key in self.selection]


@dataclass
class ModuleSpec:
    technical_name: str
    title: str
    author: str
    model: str
    fields: list = field(default_factory=list)
    odoo_version: str = ODOO_VERSIONS[-1]

    @property
    def odoo_major(self):
        return int(self.odoo_version.split(".")[0])

    @property
    def list_tag(self):
        # La vue liste s'appelle <tree> jusqu'à Odoo 17, <list> à partir de 18.
        return "tree" if self.odoo_major < 18 else "list"

    @property
    def model_file(self):
        return self.model.replace(".", "_")

    @property
    def model_class(self):
        return "".join(part.capitalize() for part in re.split(r"[._]", self.model))

    @property
    def model_description(self):
        return self.model.split(".")[-1].replace("_", " ").capitalize()

    def validate(self):
        if not MODULE_RE.match(self.technical_name):
            raise GeneratorError(
                f"Invalid module name {self.technical_name!r}: use lowercase letters, digits and underscores."
            )
        if not MODEL_RE.match(self.model):
            raise GeneratorError(f"Invalid model name {self.model!r}: expected something like 'library.book'.")
        if self.odoo_version not in ODOO_VERSIONS:
            raise GeneratorError(
                f"Unsupported Odoo version {self.odoo_version!r}: choose among {', '.join(ODOO_VERSIONS)}."
            )
        if not self.title.strip():
            raise GeneratorError("The module title cannot be empty.")
        if not self.author.strip():
            raise GeneratorError("The author cannot be empty.")
        names = [f.name for f in self.fields]
        duplicates = {n for n in names if names.count(n) > 1}
        if duplicates:
            raise GeneratorError(f"Duplicate field(s): {', '.join(sorted(duplicates))}.")


def parse_field(text):
    """Transforme 'pages:integer', 'partner_id:many2one:res.partner' ou
    'state:selection:draft,done' en Field ; lève GeneratorError si invalide."""
    name, sep, rest = text.strip().partition(":")
    ftype, _, param = rest.partition(":")
    name, ftype, param = name.strip(), ftype.strip().lower(), param.strip()
    if not sep or not name or not ftype:
        raise GeneratorError(f"Invalid field {text!r}: expected name:type, e.g. pages:integer.")
    if not FIELD_RE.match(name):
        raise GeneratorError(f"Invalid field name {name!r}: use lowercase letters, digits and underscores.")
    if name in RESERVED_FIELDS:
        raise GeneratorError(f"Field name {name!r} is reserved ('name' is always generated).")
    if ftype not in FIELD_TYPES:
        raise GeneratorError(f"Unknown field type {ftype!r}: choose among {', '.join(FIELD_TYPES)}.")
    if ftype == "many2one":
        if not MODEL_RE.match(param):
            raise GeneratorError(f"Invalid field {text!r}: expected name:many2one:model, e.g. partner_id:many2one:res.partner.")
        return Field(name, ftype, comodel=param)
    if ftype == "selection":
        keys = [key.strip() for key in param.split(",")]
        if not param or not all(FIELD_RE.match(key) for key in keys):
            raise GeneratorError(f"Invalid field {text!r}: expected name:selection:key1,key2, e.g. state:selection:draft,done.")
        if len(set(keys)) != len(keys):
            raise GeneratorError(f"Invalid field {text!r}: duplicate selection key.")
        return Field(name, ftype, selection=keys)
    if param:
        raise GeneratorError(f"Invalid field {text!r}: type {ftype!r} takes no parameter.")
    return Field(name, ftype)


def _environment():
    env = Environment(
        loader=PackageLoader("odoo_gen", "templates/module"),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    # Chaîne Python valide entre guillemets doubles (apostrophes, accents, guillemets échappés).
    env.filters["pyrepr"] = lambda value: json.dumps(value, ensure_ascii=False)
    return env


def generate(spec, output_dir="."):
    """Écrit le module dans output_dir/<technical_name> et renvoie son chemin."""
    spec.validate()
    target = Path(output_dir) / spec.technical_name
    if target.exists():
        raise GeneratorError(f"{target} already exists.")
    env = _environment()
    for template_name, output in FILES.items():
        path = target / output.format(model_file=spec.model_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = env.get_template(template_name).render(spec=spec)
        path.write_text(content, encoding="utf-8", newline="\n")
    return target
