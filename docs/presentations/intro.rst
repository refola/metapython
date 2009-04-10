============
 MetaPython
============

.. image:: ../_images/Ouroboros.png
   :height: 200
   :alt: Ouroboros
   :align: center

...another project with a dire need for a better logo

:Author: Rick Copeland
:Date: April 9, 2009

MetaPython: What is It?
=======================

.. class:: incremental

* Code quoting::

     defcode foo:
         print "hello, world"

* Macros ("import-time code")::

     $from foo import bar
     $for x in ...:
     $:
         ...
     $macro_call(a,?<b>,c)

Why Macros?
===========

Inadequate Syntax in Your Language
----------------------------------

.. class:: incremental

.. container::

   Common example for Lisp/Scheme: `while`::

      (defmacro while (expression &body body)
        ...)

.. container::
   :class: incremental

   .. figure:: ../_images/already_got_one.jpg
       :height: 150
       :alt: Already got one
       :align: center
       :class: incremental
       
       I told him we already got one!

Why Macros?
===========

Class Factories
---------------

.. class:: incremental

* Example: collections.namedtuple in Python 2.6

  .. class:: incremental

  * Giant string template that is then `exec` ed

  * Already ugly and could use a better syntax

* `unittest.TestCase` factories

  .. class:: incremental

  * One `TestCase` per browser

    .. class:: incremental

    * Avoid using `type(...)` constructor

    * Use something more obscure instead!

Why Macros? 
============

Avoid Expensive Evaluations
---------------------------

.. class:: incremental

* Example::

       log.debug('Some value: %s', 
                 expensive_computation(...))

  * No matter what the log_level is, `expensive_computation()` will still be
    called

* Possible (ugly) fix::

      if loglevel >= logging.DEBUG: 
          log.debug(...)

Why Macros?
===========

Performance
-----------

.. class:: incremental

* Possible to inline function calls

* Probably least compelling

* Used to do this in Lisp, but Lisp grew inline functions

MetaPython Mechanics
====================

How do you actually use this stuff?
-----------------------------------

Import-Time Code
================

.. class:: incremental

* Defines code to be run that is used to *generate* the code that will be
  imported

* Always denoted with a `$` token::

      $import namedtuple
      $namedtuple(...)
      $:
          # entire
          # block 
          # to be run
          # at import time

Code Quoting
============

.. class:: incremental

* Rather than executing code, create an object that represents some code

* Example::

      defcode foo:
          print "hello"

  Becomes::

      foo = _mpy.Block()
      foo.add('print "hello"', locals())

* Can also use inline quoting `?<expr>`

Actual Usage
============

.. class:: incremental

* Enable MetaPython import hook::

      import metapython
      metapython.install_import_hook()

* Now create files with the `.mpy` extension

* These can be imported just like `.py` files

Example: Named Tuples
=====================

Original Code

.. sourcecode:: python

    def namedtuple(typename, field_names):
        # ... lots of setup
        template = '''class %(typename)s(tuple):
            ... lots of text ...''' % locals()
        for i, name in enumerate(field_names):
            template += '...'
        # ... snip ...
        try:
            exec template in namespace
        except SyntaxError, e:
            raise SyntaxError(e.message...)
        return result = namespace[typename]

Example: Named Tuples
=====================

.. container::
   :class: incremental

   Original Usage::

       Point = namedtuple('Point', 'x y')

.. container::
   :class: incremental

   Easy to get wrong::

       MyPoint = namedtuple('Point', 'x y')

Example: Named Tuples
=====================

New Code

.. sourcecode:: python

   def namedtuple(typename, *field _names):
       ...
       defcode result:
           class $<typename>(tuple):
               ...
       return result

New Usage

.. sourcecode:: python

    $namedtuple(?Point, ?x, ?y)

Status, Docs, Development
==========================

.. class:: incremental

* Version 0.1 uses Jinja2 Templates for Code

  .. class:: incremental

  * but that's a little crazy

  * but it works, kind of

* Version 0.2 uses more consistent syntax

  .. class:: incremental

  * that's what's documented here

  * no Jinja2 required

  * still under development

* Documentation, Code, etc

  * http://code.google.com/p/metapython/
  * http://metapython.org

Questions?
==========



