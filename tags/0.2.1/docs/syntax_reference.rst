MetaPython Syntax Reference
===========================

MetaPython provides two main facilities for `.mpy` MetaPython modules:
import-time escapes and code quoting.

Import-Time Escapes
-------------------

All import-time escapes are prefixed by the question mark `?`.  The meaning of
each escape construct is defined here:

`$:`
    Begins an import-time block.  The following suite (which may be inline) is to
    be executed at import-time.  For instance, the following code defines a
    variable to be used at import time::
        
        $: DEBUG=True

    So does this::

        $:
            DEBUG=True

    Note that `$:` blocks are *removed* from the module source when they are
    executed at import time.  So the `__expanded__` attribute of the module will
    not include any of the text marked with `?:`.

`$<...>` and `$...`
    Defines an import-time expression.  The enclosed expression will be executed
    at import-time and the result of its evaluation will be inserted into the
    python module source code where the import-time expression appears.

`$import... , $from...import...`
    Shorthand syntax for import-time imports.  The following code::

        ?import foo

    is exactly equivalent to::

        ?: import foo

    and::

        ?: 
            import foo

`$for...:, $while...: $if...:...$else:...:`
    Various Python control structures which allow the user to specify code blocks
    to be repeated (as in the case of `$for` and `$while`) or conditionally
    included (as in the case of `$if...$else`

Code Quoting Escapes
--------------------

For a macro system to be useful, it should be simple to represent code to be
generated.  To that end, MetaPython provides two mechanisms to quote Python code.

`defcode <name>(<name>,...):`
    This construct denotes the following suite as a code template.  Code
    templates can use the same import-time constructs mentioned above to control
    their expansion.  For instance, the following code::

        defcode foo():
            $for i in range(3):
                print $i

    is equivalent to the following code::

        defcode foo():
            print 0
            print 1
            print 2

    and actually expands to the following code::

        _mpy.push()
        for i in range(10):
            _mpy.append('print $i ', globals(), locals())
        foo = _mpy.pop()
        foo = _mpy.sanitize(globals(), locals())

    (The `_mpy.append(...)` performs macro expansion in the context of 
    `globals()` and `locals()` dictionaries.)

    One pitfall of macro expansion is that the `defcode` block you expand may use
    variables that have the same names as the variables in the context into which
    the macro is (eventually) expanded.  To sidestep this problem, code blocks are
    /sanitized/, replacing some or all names used in the code block with names
    that are guaranteed not to conflict with the context into which they are
    expanded.  

    If you *want* to capture some names in the context of the macro expansion,
    you can still pass the names to be omitted to the `sanitize()`
    method.  To pass a literal name, you can prefix the name with a `?` to
    automatically quote it.  For instance, if you wished to write a macro that
    will create a new (dynamically determined) name, you could do the following::

        def set_(var, value):
            defcode result(var):
                $var = $value
            return result

    This expands to the following::

        def set_ (var ,value ):
            _mpy .push ()
            _mpy .append ('$var =$value \n',globals (),locals ())
            result =_mpy .pop ()
            result =result .sanitize (globals (),locals (),'var')
            return result 

    Alternatively, if you wished to write a macro that will set the value of `i`
    to a particular value, you would quote the `i` with a `?`::

        def seti(value):
            defcode result(?i):
                i = $value
            return result

    This block then expands to::

        def seti (value ):
            _mpy .push ()
            _mpy .append ('i =$value \n',globals (),locals ())
            result =_mpy .pop ()
            result =result .sanitize (globals (),locals (),"_mpy .q ('i ')")
            return result 

    (These examples are, of course, contrived, but they serve to illustrate the
    hygenic macro features of MetaPython.)

`?<...>` and `?...`
    This is the "short form" of code quoting.  The expression within the angle
    brackets is treated as an inline code block.  This is often used where only a
    short code block is needed, such as passing a default code argument to a
    macro::

        def macro_if(cond, true_expr, false_expr=?pass):
            cond = eval(str(cond))
            if cond: return true_expr
            else: return false_expr

    The `?` operator can also be thought of as delaying the evaluation of
    arguments to a macro.  For instance, the named tuple macro defined in the
    tutorial uses the `?` operator to quote its arguments::

        $namedtuple(?Point, ?x, ?y)

    this code actually expands to the following MetaPython API calls::

        $namedtuple(_mpy.q('Point'), _mpy.q('x'), _mpy.q('y'))

    which, in turn, expands to the full class definition of `Point`.

