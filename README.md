# Odoo Module Generator

[![tests](https://github.com/Junmodeste/odoo-module-generator/actions/workflows/tests.yml/badge.svg)](https://github.com/Junmodeste/odoo-module-generator/actions/workflows/tests.yml)
[![Odoo 17 | 18 | 19](https://img.shields.io/badge/Odoo-17.0%20|%2018.0%20|%2019.0-714B67)](https://www.odoo.com)
[![License: LGPL-3](https://img.shields.io/badge/License-LGPL--3-blue.svg)](LICENSE)

🇫🇷 [Français](#français) · 🇬🇧 [English](#english)

## Français

`odoo-gen` est un outil en ligne de commande qui génère le squelette d'un module Odoo 17, 18 ou 19 : manifeste, modèle, vues (liste, formulaire, recherche, action, menu), droits d'accès, test de base et README.
Il pose quelques questions (nom lisible, auteur, modèle, champs `nom:type`) ou fonctionne sans interaction via des arguments.

```console
$ odoo-gen new library_demo
Module title [Library Demo]: Bibliothèque
Author [Your Name]: Koffi Modeste Junior
Model name [library.demo]: library.book
Odoo version [19.0]: 19.0
Fields as name:type (char, text, html, integer, float, boolean, date, datetime, many2one, selection); empty line to finish.
  e.g. partner_id:many2one:res.partner, state:selection:draft,done
Field: pages:integer
Field: author_id:many2one:res.partner
Field: state:selection:draft,available,borrowed
Field:
Module created in library_demo
```

Module généré (Odoo 19) :

```
library_demo/
├── __init__.py
├── __manifest__.py            # 19.0.1.0.0 (17.0.1.0.0 avec --odoo-version 17.0), LGPL-3
├── README.md
├── models/library_book.py     # champ name + vos champs
├── views/library_book_views.xml   # <list> (<tree> en 17), form, search, action, menu
├── security/ir.model.access.csv
└── tests/test_library_book.py
```

### Prérequis

- Python 3.10 ou plus récent (Jinja2 est installé automatiquement)
- Odoo 17, 18 ou 19 pour installer les modules générés

### Installation

1. `git clone https://github.com/Junmodeste/odoo-module-generator.git && cd odoo-module-generator`
2. `pip install .`
3. `odoo-gen new mon_module` (ou `odoo-gen new mon_module --no-input --model x.y --field note:text`)

Options : `--title`, `--author`, `--model`, `--odoo-version 17.0|18.0|19.0` (défaut 19.0), `--field nom:type` (répétable), `-o/--output`, `--no-input`. Types : `char`, `text`, `html`, `integer`, `float`, `boolean`, `date`, `datetime`, `many2one:<modèle>` (ex. `partner_id:many2one:res.partner`), `selection:<clé>,<clé>` (ex. `state:selection:draft,done`, libellés déduits des clés). Le champ `name` est toujours créé. Le manifeste dépend de `base` seul : pour un `many2one` vers un modèle d'un autre module (ex. `product.product`), ajoutez ce module (`product`) dans `depends`.

Tests de l'outil : `pip install .[test]` puis `pytest`.

### Versions supportées

Génère des modules pour Odoo **17.0**, **18.0** et **19.0** (`--odoo-version`). Selon la version : numéro du manifeste, vue liste `<tree>` en 17 et `<list>` en 18+, `view_mode` de l'action. La CI installe et teste un module généré sur les images Community `odoo:17`, `odoo:18` et `odoo:19`.

### Licence

[LGPL-3](LICENSE)

### Auteur

Koffi Modeste Junior — [@Junmodeste](https://github.com/Junmodeste)

## English

`odoo-gen` is a command line tool that generates an Odoo 17, 18 or 19 module skeleton: manifest, model, views (list, form, search, action, menu), access rights, a basic test and a README.
It asks a few questions (title, author, model, `name:type` fields) or runs non-interactively from arguments.

### Requirements

- Python 3.10 or newer (Jinja2 is installed automatically)
- Odoo 17, 18 or 19 to install the generated modules

### Installation

1. `git clone https://github.com/Junmodeste/odoo-module-generator.git && cd odoo-module-generator`
2. `pip install .`
3. `odoo-gen new my_module` (or `odoo-gen new my_module --no-input --model x.y --field note:text`)

Options: `--title`, `--author`, `--model`, `--odoo-version 17.0|18.0|19.0` (default 19.0), `--field name:type` (repeatable), `-o/--output`, `--no-input`. Types: `char`, `text`, `html`, `integer`, `float`, `boolean`, `date`, `datetime`, `many2one:<model>` (e.g. `partner_id:many2one:res.partner`), `selection:<key>,<key>` (e.g. `state:selection:draft,done`, labels derived from keys). A `name` field is always created. The manifest only depends on `base`: for a `many2one` to a model from another module (e.g. `product.product`), add that module (`product`) to `depends`.

Tool tests: `pip install .[test]` then `pytest`.

### Supported versions

Generates modules for Odoo **17.0**, **18.0** and **19.0** (`--odoo-version`). Per version: manifest number, `<tree>` list view in 17 and `<list>` in 18+, action `view_mode`. CI installs and tests a generated module on the Community images `odoo:17`, `odoo:18` and `odoo:19`.

### License

[LGPL-3](LICENSE)

### Author

Koffi Modeste Junior — [@Junmodeste](https://github.com/Junmodeste)
