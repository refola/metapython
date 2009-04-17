MetaPython Roadmap
==================

Version 0.2
-----------

* Extensive syntax redesign, allowing block macros `$if...`, `$for...`, etc.
* Removal of Jinja2 requirements: `defcode` blocks now simply use import-time
  constructs to control their expansion.
* Macro arguments are now evaluated by default and must be quoted using the `?`
  operator to pass them as code blocks.
* Major rework of internal architecture

Version 0.1
-----------

* Original attempt at macros for Python
* Uses Jinja2 for `defcode` blocks

