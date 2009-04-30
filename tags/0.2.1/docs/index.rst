MetaPython Documentation
========================

.. image:: images/Ouroboros.png

MetaPython provides a macro and code quoting facility for the Python programming
language.  It accomplishes this via the use of an import hook.  MetaPython files
are denoted with an `.mpy` extension and may contain quoted code blocks, macro
definitions, and macro expansions.

Contents:

.. toctree::
   :maxdepth: 2

   Syntax Reference <syntax_reference>
   MetaPython Roadmap <roadmap>
   Presentations <presentations>

Important Links
===============

`Downloads <http://code.google.com/p/metapython/downloads/list>`_
    For those who'd prefer not to use setuptools/easy_install.

`MetaPython Discussion List <http://groups.google.com/group/metapython>`_
    For discussion of all things MetaPython.  Feel free to post questions,
    comments, or feature requests here.

`MetaPython Tutorial <http://code.google.com/p/metapython/wiki/Tutorial>`_
    Provides a good starting point for learning MetaPython.  Following the
    tutorial you will learn how to use MetaPython to create a macro-ized version
    of `collections.namedtuple` from the standard library.

`Issue Tracker <http://code.google.com/p/metapython/issues/list>`_
    Report any bugs or feature requests here.

`MetaPython Announcement <http://blog.pythonisito.com/2009/03/announcing-metapython-macros-for-python.html>`_
    The initial release announcement of MetaPython is here, along with a simple
    conditional compilation example/tutorial.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Modules
=======

.. toctree::
   :maxdepth: 2

   modules/core
   modules/parse
