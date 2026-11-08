"""Point d'entrée `odoo-gen`.

    odoo-gen new library_demo                      # questions interactives
    odoo-gen new library_demo --no-input \\
        --title "Library" --author "Me" --model library.book \\
        --field pages:integer --field price:float --odoo-version 17.0
"""
import argparse
import sys

from . import __version__
from .generator import (
    FIELD_TYPES,
    ODOO_VERSIONS,
    GeneratorError,
    ModuleSpec,
    generate,
    parse_field,
)


def _ask(prompt, default):
    answer = input(f"{prompt} [{default}]: ").strip()
    return answer or default


def _ask_fields():
    fields = []
    print(f"Fields as name:type ({', '.join(FIELD_TYPES)}); empty line to finish.")
    print("  e.g. partner_id:many2one:res.partner, tag_ids:many2many:res.partner.category, state:selection:draft,done")
    print("  one2many needs its inverse many2one on the same model: parent_id:many2one:library.book,")
    print("  then child_ids:one2many:library.book:parent_id")
    while True:
        answer = input("Field: ").strip()
        if not answer:
            return fields
        try:
            fields.append(parse_field(answer))
        except GeneratorError as exc:
            print(f"  {exc}")


def build_spec(args, interactive):
    name = args.name
    defaults = {
        "title": args.title or name.replace("_", " ").title(),
        "author": args.author or "Your Name",
        "model": args.model or name.replace("_", "."),
        "odoo_version": args.odoo_version or ODOO_VERSIONS[-1],
    }
    fields = [parse_field(f) for f in args.field]
    if interactive:
        # On ne pose que les questions dont la réponse n'a pas été passée en argument.
        if not args.title:
            defaults["title"] = _ask("Module title", defaults["title"])
        if not args.author:
            defaults["author"] = _ask("Author", defaults["author"])
        if not args.model:
            defaults["model"] = _ask("Model name", defaults["model"])
        if not args.odoo_version:
            defaults["odoo_version"] = _ask("Odoo version", defaults["odoo_version"])
        if not args.field:
            fields = _ask_fields()
    if "." not in defaults["model"]:
        defaults["model"] = f"{name}.{defaults['model']}"
    return ModuleSpec(name, defaults["title"], defaults["author"], defaults["model"], fields,
                      defaults["odoo_version"])


def make_parser():
    parser = argparse.ArgumentParser(prog="odoo-gen", description="Odoo module skeleton generator.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    new = sub.add_parser("new", help="create a new module")
    new.add_argument("name", help="technical module name, e.g. library_demo")
    new.add_argument("--title", help="human readable name")
    new.add_argument("--author", help="manifest author")
    new.add_argument("--model", help="model name, e.g. library.book")
    # --version est déjà pris par la version de l'outil, d'où --odoo-version.
    new.add_argument("--odoo-version", choices=ODOO_VERSIONS,
                     help=f"target Odoo version (default: {ODOO_VERSIONS[-1]})")
    new.add_argument("--field", action="append", default=[], metavar="NAME:TYPE",
                     help=f"extra field (repeatable); types: {', '.join(FIELD_TYPES)}")
    new.add_argument("-o", "--output", default=".", help="parent directory (default: current)")
    new.add_argument("--no-input", action="store_true", help="never ask questions, use defaults")
    return parser


def main(argv=None):
    args = make_parser().parse_args(argv)
    interactive = not args.no_input and sys.stdin.isatty()
    try:
        spec = build_spec(args, interactive)
        path = generate(spec, args.output)
    except GeneratorError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Module created in {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
