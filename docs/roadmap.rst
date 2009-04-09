MetaPython Roadmap
==================

This page is a placeholder for ideas (not necessarily promises) of what
MetaPython may become in future releases.

Import Time Control Structures
------------------------------

The following structures should be supported for easier conditional compilation,
loop unrolling, etc.

`?if <expr>:...  [ ?else: ]`
    Evaluate `expr` and, if true, expand the "then" block.  Otherwise expand the
    "else" block.  
`?for...:, ?while...:`
    Just like runtime loops in Python, except that the block is expanded at
    import-time (possibly multiple times).  Note that the obscure `?else` in
    loops will also be supported at import time.

Syntax Changes
--------------

It may be better, in macro expansions, to be able to specify some arguments for
evaluation prior to expanding the macro.  In MetaPython 0.2, the following code:

    ?foo(a, ${pass})

may specify that the first argument is to be evaluated, while the second one is
not (the `${...}` construct is already the code-quoting construct as of
MetaPython 0.1).  In 0.2, the `?` at the beginning of the macro call instructs
the system to replace the call with its result, while the `${...}` construct will
instruct the system **not** to evaluate a particular argument.  Maybe.  Or maybe
you can just prefix an argument with `?` to turn off evaluation.
