# Odoo Module Generator

[![Odoo 19](https://img.shields.io/badge/Odoo-19.0-714B67)](https://www.odoo.com)
[![License: LGPL-3](https://img.shields.io/badge/License-LGPL--3-blue.svg)](LICENSE)

🇫🇷 [Français](#français) · 🇬🇧 [English](#english)

## Français

`odoo-gen` est un outil en ligne de commande qui génère le squelette d'un module Odoo 19 : manifeste, modèle, vues (liste, formulaire, recherche, action, menu), droits d'accès, test de base et README.
Il pose quelques questions (nom lisible, auteur, modèle, champs `nom:type`) ou fonctionne sans interaction via des arguments.

```console
$ odoo-gen new library_demo
Module title [Library Demo]: Bibliothèque
Author [Your Name]: Koffi Modeste Junior
Model name [library.demo]: library.book
Fields as name:type (char, text, html, integer, float, boolean, date, datetime); empty line to finish.
Field: pages:integer
Field: price:float
Field:
Module created in library_demo
```

Module généré :

```
library_demo/
├── __init__.py
├── __manifest__.py            # 19.0.1.0.0, LGPL-3
├── README.md
├── models/library_book.py     # champ name + vos champs
├── views/library_book_views.xml   # <list>, form, search, action, menu
├── security/ir.model.access.csv
└── tests/test_library_book.py
```

### Prérequis

- Python 3.10 ou plus récent (Jinja2 est installé automatiquement)
- Odoo 19 pour installer les modules générés

### Installation

1. `git clone https://github.com/Junmodeste/odoo-module-generator.git && cd odoo-module-generator`
2. `pip install .`
3. `odoo-gen new mon_module` (ou `odoo-gen new mon_module --no-input --model x.y --field note:text`)

Options : `--title`, `--author`, `--model`, `--field nom:type` (répétable), `-o/--output`, `--no-input`. Types : `char`, `text`, `html`, `integer`, `float`, `boolean`, `date`, `datetime`. Le champ `name` est toujours créé.

Tests de l'outil : `pip install .[test]` puis `pytest`.

### Version supportée

Génère des modules pour Odoo **19.0**. Un module généré a été installé et testé sur Odoo 19 Enterprise (image `odoo:19` 19.0-20261015).

### Licence

[LGPL-3](LICENSE)

### Auteur

Koffi Modeste Junior — [@Junmodeste](https://github.com/Junmodeste)

## English

`odoo-gen` is a command line tool that generates an Odoo 19 module skeleton: manifest, model, views (list, form, search, action, menu), access rights, a basic test and a README.
It asks a few questions (title, author, model, `name:type` fields) or runs non-interactively from arguments.

### Requirements

- Python 3.10 or newer (Jinja2 is installed automatically)
- Odoo 19 to install the generated modules

### Installation

1. `git clone https://github.com/Junmodeste/odoo-module-generator.git && cd odoo-module-generator`
2. `pip install .`
3. `odoo-gen new my_module` (or `odoo-gen new my_module --no-input --model x.y --field note:text`)

Options: `--title`, `--author`, `--model`, `--field name:type` (repeatable), `-o/--output`, `--no-input`. Types: `char`, `text`, `html`, `integer`, `float`, `boolean`, `date`, `datetime`. A `name` field is always created.

Tool tests: `pip install .[test]` then `pytest`.

### Supported version

Generates modules for Odoo **19.0**. A generated module was installed and tested on Odoo 19 Enterprise (`odoo:19` image 19.0-20261015).

### License

[LGPL-3](LICENSE)

### Author

Koffi Modeste Junior — [@Junmodeste](https://github.com/Junmodeste)
