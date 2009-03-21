MetaPython Syntax Reference
===========================

MetaPython provides two main facilities for `.mpy` MetaPython modules:
import-time escapes and code quoting.

Import-Time Escapes
-------------------

All import-time escapes are prefixed by the question mark `?`.  The meaning of
each escape construct is defined here:

`?:`
    Begins an import-time block.  The following suite (which may be inline) is to
    be executed at import-time.  For instance, the following code defines a
    variable to be used at import time::
        
        ?: DEBUG=True

    So does this::

        ?:
            DEBUG=True

    Note that `?:` blocks are *removed* from the module source when they are
    executed at import time.  So the `__expanded__` attribute of the module will
    not include any of the text marked with `?:`.

`?(...)`
    Defines an import-time expression.  The enclosed expression will be executed
    at import-time and the result of its evaluation will be inserted into the
    python module source code where the import-time expression appears.

`?import... , ?from...`
    Shorthand syntax for import-time imports.  The following code::

        ?import foo

    is exactly equivalent to::

        ?: import foo

    and::

        ?: 
            import foo

    `?import` and `?from` statements must be at the top-level of indentation in
    the MetaPython source.

`?<expr>(...)`
    This is the syntax for a macro call.  The `<expr>` is evaluated and the
    resulting macro is called at import time.  It is important to note that the
    arguments in a macro call, unlike the arguments to a function call, **are not
    evaluated**.  The macro will be called with `metapython.Code` objects for
    each of its arguments.  The result of the macro call is inserted into the
    expanded Python source code.

Code Quoting Escapes
--------------------

For a macro system to be useful, it should be simple to represent code to be
generated.  To that end, MetaPython provides two mechanisms to quote Python code.

`defcode <name>:`
    This construct denotes the following suite as a code template.  Code
    templates use 
    `Jinja2 <http://http://jinja.pocoo.org/2/documentation/templates>`_ syntax
    and are evaluated in the context (`globals()` and `locals()`) where they are
    defined.  Prior to evaluation of a template, all code objects present in the
    context are converted to their Python text representation, allowing their use
    in the Jinja2 expansion.

    Standard Jinja2 escapes are used in the templates with one exception: rather
    than using curly braces `{{...}}` for escaping expressions, MetaPython
    surrounds expressions with dollar signs `$...$` in order to keep Jinja2's and
    MetaPython's lexers from interfering with one another.


`?{...}`
    This is the "short form" of code quoting.  The expression within the curly
    braces is treated as a Jinja2 template.  This is often used where only a
    short code block is needed, such as passing a default code argument to a
    macro::

        def macro_if(cond, true_expr, false_expr=?{pass}):
            cond = eval(str(cond))
            if cond: return true_expr
            else: return false_expr



