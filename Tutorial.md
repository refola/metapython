# Introduction #

MetaPython provides a macro and code quoting facility for Python.  It
accomplishes this via the use of an import hook.

This tutorial will describe the basic features of MetaPython and take you through
the creation of a macro-based implementation of the `collections.namedtuple`
class factory.

# Installing MetaPython #

`easy_install MetaPython`

That's it.

# MetaPython Basics #

The main features of MetaPython are divided into import-time programming and code quoting.

## Import Time Programming ##

MetaPython introduces a concept called _import time_ to Python.  _import time_ is
the time between which a module has been located and when the text of the module
is handed over to Python to be interpreted.  In regular Python, nothing happens
at import time.

MetaPython, however, provides import-time hooks to allow you to
write code that changes the text of the module being imported before the regular
Python interpreter ever sees it.  It accomplishes this via a small set of syntax
extensions which currently (as of Python 2.6) generate syntax errors in regular
Python.  (Each import-time construct begins with the question mark `?` which is
not even recognized by Python as a valid Python token.)

MetaPython accomplishes its import-time magic via the use of a PEP 302 import
hook.  To use MetaPython, you don't really need to understand the details of
import hooks.  Suffice it to say that before anything works, you need to execute

` import metapython; metapython.install_import_hook() `

Once this is done, you will be able to import MetaPython files with the .mpy
extension just as other Python files.

## Code Quoting ##

Being able to affect the text of a module is somewhat useful, but becomes much
more useful when it's easy to _generate_ Python code to be inserted into the
module.  This is provided by the code quoting facility of MetaPython.  MetaPython
uses a new keyword `defcode` along with import-time syntax to expand blocks of
templated Python code into MetaPython code objects which can be inserted into the
text of a module at import-time.

# Your First MetaPython Module #

To begin, we will create a MetaPython module which provides the a macro-based
implementation of the `collections.namedtuple` class factory.  Create a file
"namedtuple.mpy" with the following text:

```
'''Simple metapython file'''
def namedtuple(typename, *field_name_toks):
    # Create and fill-in the class template
    field_names = tuple(str(f) for f in field_name_toks)
    numfields = len(field_names)
    # tuple repr without parens or quotes
    argtxt = repr(field_names).replace("'", "")[1:-1]   
    reprtxt = ', '.join('%s=%%r' % name for name in field_names)
    dicttxt = ', '.join('%r: t[%d]' % (name, pos)
                        for pos, name in enumerate(field_names))
    defcode result(typename):
        from operator import itemgetter
        class $<typename>(tuple):
            $("'%s(%s)'" % (typename, argtxt))
            __slots__ = ()
            _fields = $field_names

            def __new__(cls, $argtxt):
                return tuple.__new__(cls, $field_name_toks)

            @classmethod
            def _make(cls, iterable, new=tuple.__new__, len=len):
                $("'Make a new %s object from a sequence or iterable'" %
                  typename)
                result = new(cls, iterable)
                if len(result) != $numfields:
                    raise TypeError(
                        $("'Expected %s arguments, got %%d'" % numfields)
                         % len(result))
                return result

            def __repr__(self):
                return $('"%s(%s)"' % (typename, reprtxt)) % self

            def _asdict(t):
                'Return a new dict which maps field names to their values'
                return { $dicttxt }

            def _replace(self, **kwds):
                $("""'''Return a new %s object replacing specified
                  fields with new values'''""" % typename)
                result = self._make(map(kwds.pop, $field_names, self))
                if kwds:
                    raise ValueError('Got unexpected field names: %r'
                                     % kwds.keys())
                return result

            def __getnewargs__(self):
                return tuple(self)

            $for i,name in enumerate(field_names):
                $name = property(itemgetter($i))
    return result
```

At this point, a bit of explanation is in order.  Namely, what is the meaning of
all the `$` stuff and `defcode`?

`$` introduces an import-time construct.  If `$` begins a statement such as
`$import ...`, `$for ...`, `$if...`, etc., then that statement will be executed
at import time.  If, on the other hand, `$` simply begins an expression, then the
value of the expression will be computed at import time and inserted into the
module text.  For instance, the following MetaPython code:

```
$for i in range(3):
    print $i
```

will expand to the following Python code:

```
print 0
print 1
print 2
```

MetaPython also allows you to explicitly delimit an import-time construct with
angle brackets `<>` such as in the code above: `$<typename>`.  This can be useful
when you are trying to construct part of an expression.

`defcode` introduces a quoted code template.  Code templates are converted at
import-time into calls to the MetaPython API which builds a data structure
representing the code contained in the block.  Inside a `defcode` block, the
import-time escape `$` allows you to "break out" of the quoting in order to
modify the code returned.

MetaPython's quoted code blocks are, by default, "hygienic".  This means that any
variables used within a `defcode` block will not override variables in the
context into which the code block is eventually expanded.  MetaPython
accomplishes this by replacing any names created in a `defcode` block with new
names with the `_mpy_` prefix Sometimes, however, you /want/ a new name
introduced (as above, when you are defining a new class).  To prevent a name from
being replaced by MetaPython's "sanitization", you specify the name as an
argument to the defcode block.  In the case of `namedtuple`, we did this by
passing `typename` as an argument.

Although the exact details of the MetaPython API are
beyond the scope of this tutorial, an example of the code that MetaPython
constructs for a defcode block is instructive.  For instance, the following
MetaPython code:

```
defcode x():
    $for i in range(10):
        print "hi", $i
```

expands to the following Python code:

```
_mpy.push()
for i in range(10):
    _mpy.append('print "hi",$i ', globals(), locals())
x = _mpy.pop()
x = _mpy.sanitize(globals(), locals())
```

(_mpy is a MetaPython object used to construct code objects)._

So what we have in `namedtuple.mpy` is a MetaPython file which, at import time,
defines a function/macro called `namedtuple` which will itself create a code
block.  That's great and all, but how do we use it?

# Calling Macros #

MetaPython provides a facility for calling a function/macro at import time and
inserting the result into the module's text at import time.  This is illustrated
by the code below.  Save it in a file "test1.mpy":

```
$:
    from namedtuple import namedtuple
$namedtuple(?Point, ?x, ?y)
```

OK, that was pretty short.  We have introduced two new constructs, however.  The
first is the import-time block `$:...` .  There's nothing special there
- it's just an block that's executed at import time.  This is necessary so we can
use the `namedtuple` function at import time.  The syntax above is
exactly equivalent to the following:

```
$from namedtuple import namedtuple
```

The next construct is the references to `?Point`, `?x`, and `?y`.  The `?`
operator is a shorthand way of doing a small `defcode` block.  In this case,
these operators allow us to pass the **names** Point, x, and y rather than the
**values** of Point, x, and y (which are undefined and would lead to an error).
You can also think of `?` as the opposite of `$`: where `$` makes something be
evaluated **earlier** (at import time), `?` makes something be evaluated **later**
(or not at all).

We also see in this example the import-time function call ("macro call") `$namedtuple(...)`.
This will be replaced by the result of the macro call at import time.  In this
case, we can see what the expansion is by importing the
module and inspecting its expanded attribute.  One thing to note is that
before we do _anything_ with MetaPython, we must import it and enable its import hook:

```
>>> import metapython; metapython.install_import_hook()
>>> import test1
>>> print dir(test1)
['Point', '__builtins__', '__doc__', '__expanded__', '__name__', '_mpy', 'itemgetter', 'namedtuple']
>>> print test1.__expanded__
from operator import itemgetter 
class Point (tuple ):
    'Point (x , y )'
    __slots__ =()
    _fields =('x ','y ')

    def __new__ (cls ,x ,y ):
        return tuple .__new__ (cls ,(x ,y ))


    @classmethod 
    def _make (cls ,iterable ,new =tuple .__new__ ,len =len ):
        'Make a new Point  object from a sequence or iterable'
        result =new (cls ,iterable )
        if len (result )!=2 :
            raise TypeError (
            'Expected 2 arguments, got %d'
            %len (result ))

        return result 


    def __repr__ (self ):
        return "Point (x =%r, y =%r)"%self 


    def _asdict (t ):
        'Return a new dict which maps field names to their values'
        return {'x ':t [0 ],'y ':t [1 ]}


    def _replace (self ,**kwds ):
        '''Return a new Point  object replacing specified
                  fields with new values'''
        result =self ._make (map (kwds .pop ,('x ','y '),self ))
        if kwds :
            raise ValueError ('Got unexpected field names: %r'
            %kwds .keys ())

        return result 


    def __getnewargs__ (self ):
        return tuple (self )


    x =property (itemgetter (0 ))
    y =property (itemgetter (1 ))
```

# Advanced Features #

You can do even more with MetaPython, including nested and recursive macro
calls.  For instance, say you wanted to have a macro that defined a point in N
dimensions (not necessarily 2).  Create the following file and save it as test2.mpy:

```
$:
    from namedtuple import namedtuple
    def point(typename, ndim):
        ndim = eval(str(ndim))
        dimnames = [ 'x%d' % i for i in xrange(int(str(ndim))) ]
        defcode result:
            ?namedtuple($str(typename)$, $','.join(dimnames)$)
        return result

    def point_types(prefix, *ndims):
        import metapython
        result = metapython.Code()
        for ndim in ndims:
            ndim = int(ndim.eval()) # remember, ndim is a Code object
            typename = '%s%dd' % (prefix, ndim)
            result.extend(point(typename, ndim))
        return result

$point_types(Point, 2, 3, 4, 5)
```

Now, you can examine the 4 new classes created:

```
>>> import metapython; metapython.install_import_hook()
>>> import test2
>>> print dir(test2)
['Cartesian', 'Point2', 'Point3', 'Point4', 'Point5', '__builtins__', '__doc__', '__expanded__', '__name__', '_mpy', 'itemgetter', 'namedtuple', 'point', 'point_types']
>>> print test2.__expanded__
from operator import itemgetter 
class Cartesian (tuple ):
    'Cartesian (x0, x1)'
    __slots__ =()
    _fields =('x0','x1')

    def __new__ (cls ,x0 ,x1 ):
        return tuple .__new__ (cls ,(x0 ,x1 ))


    @classmethod 
    def _make (cls ,iterable ,new =tuple .__new__ ,len =len ):
        'Make a new Cartesian  object from a sequence or iterable'
        result =new (cls ,iterable )
        if len (result )!=2 :
            raise TypeError (
            'Expected 2 arguments, got %d'
            %len (result ))

        return result 


    def __repr__ (self ):
        return "Cartesian (x0=%r, x1=%r)"%self 


    def _asdict (t ):
        'Return a new dict which maps field names to their values'
        return {'x0':t [0 ],'x1':t [1 ]}


    def _replace (self ,**kwds ):
        '''Return a new Cartesian  object replacing specified
                  fields with new values'''
        result =self ._make (map (kwds .pop ,('x0','x1'),self ))
        if kwds :
            raise ValueError ('Got unexpected field names: %r'
            %kwds .keys ())

        return result 


    def __getnewargs__ (self ):
        return tuple (self )


    x0 =property (itemgetter (0 ))
    x1 =property (itemgetter (1 ))


from operator import itemgetter 
class Point2 (tuple ):
    'Point2 (x0, x1)'
    __slots__ =()
    _fields =('x0','x1')

    def __new__ (cls ,x0 ,x1 ):
        return tuple .__new__ (cls ,(x0 ,x1 ))


    @classmethod 
    def _make (cls ,iterable ,new =tuple .__new__ ,len =len ):
        'Make a new Point2  object from a sequence or iterable'
        result =new (cls ,iterable )
        if len (result )!=2 :
            raise TypeError (
            'Expected 2 arguments, got %d'
            %len (result ))

        return result 


    def __repr__ (self ):
        return "Point2 (x0=%r, x1=%r)"%self 


    def _asdict (t ):
        'Return a new dict which maps field names to their values'
        return {'x0':t [0 ],'x1':t [1 ]}


    def _replace (self ,**kwds ):
        '''Return a new Point2  object replacing specified
                  fields with new values'''
        result =self ._make (map (kwds .pop ,('x0','x1'),self ))
        if kwds :
            raise ValueError ('Got unexpected field names: %r'
            %kwds .keys ())

        return result 


    def __getnewargs__ (self ):
        return tuple (self )


    x0 =property (itemgetter (0 ))
    x1 =property (itemgetter (1 ))



from operator import itemgetter 
class Point3 (tuple ):
    'Point3 (x0, x1, x2)'
    __slots__ =()
    _fields =('x0','x1','x2')

    def __new__ (cls ,x0 ,x1 ,x2 ):
        return tuple .__new__ (cls ,(x0 ,x1 ,x2 ))


    @classmethod 
    def _make (cls ,iterable ,new =tuple .__new__ ,len =len ):
        'Make a new Point3  object from a sequence or iterable'
        result =new (cls ,iterable )
        if len (result )!=3 :
            raise TypeError (
            'Expected 3 arguments, got %d'
            %len (result ))

        return result 


    def __repr__ (self ):
        return "Point3 (x0=%r, x1=%r, x2=%r)"%self 


    def _asdict (t ):
        'Return a new dict which maps field names to their values'
        return {'x0':t [0 ],'x1':t [1 ],'x2':t [2 ]}


    def _replace (self ,**kwds ):
        '''Return a new Point3  object replacing specified
                  fields with new values'''
        result =self ._make (map (kwds .pop ,('x0','x1','x2'),self ))
        if kwds :
            raise ValueError ('Got unexpected field names: %r'
            %kwds .keys ())

        return result 


    def __getnewargs__ (self ):
        return tuple (self )


    x0 =property (itemgetter (0 ))
    x1 =property (itemgetter (1 ))
    x2 =property (itemgetter (2 ))



from operator import itemgetter 
class Point4 (tuple ):
    'Point4 (x0, x1, x2, x3)'
    __slots__ =()
    _fields =('x0','x1','x2','x3')

    def __new__ (cls ,x0 ,x1 ,x2 ,x3 ):
        return tuple .__new__ (cls ,(x0 ,x1 ,x2 ,x3 ))


    @classmethod 
    def _make (cls ,iterable ,new =tuple .__new__ ,len =len ):
        'Make a new Point4  object from a sequence or iterable'
        result =new (cls ,iterable )
        if len (result )!=4 :
            raise TypeError (
            'Expected 4 arguments, got %d'
            %len (result ))

        return result 


    def __repr__ (self ):
        return "Point4 (x0=%r, x1=%r, x2=%r, x3=%r)"%self 


    def _asdict (t ):
        'Return a new dict which maps field names to their values'
        return {'x0':t [0 ],'x1':t [1 ],'x2':t [2 ],'x3':t [3 ]}


    def _replace (self ,**kwds ):
        '''Return a new Point4  object replacing specified
                  fields with new values'''
        result =self ._make (map (kwds .pop ,('x0','x1','x2','x3'),self ))
        if kwds :
            raise ValueError ('Got unexpected field names: %r'
            %kwds .keys ())

        return result 


    def __getnewargs__ (self ):
        return tuple (self )


    x0 =property (itemgetter (0 ))
    x1 =property (itemgetter (1 ))
    x2 =property (itemgetter (2 ))
    x3 =property (itemgetter (3 ))



from operator import itemgetter 
class Point5 (tuple ):
    'Point5 (x0, x1, x2, x3, x4)'
    __slots__ =()
    _fields =('x0','x1','x2','x3','x4')

    def __new__ (cls ,x0 ,x1 ,x2 ,x3 ,x4 ):
        return tuple .__new__ (cls ,(x0 ,x1 ,x2 ,x3 ,x4 ))


    @classmethod 
    def _make (cls ,iterable ,new =tuple .__new__ ,len =len ):
        'Make a new Point5  object from a sequence or iterable'
        result =new (cls ,iterable )
        if len (result )!=5 :
            raise TypeError (
            'Expected 5 arguments, got %d'
            %len (result ))

        return result 


    def __repr__ (self ):
        return "Point5 (x0=%r, x1=%r, x2=%r, x3=%r, x4=%r)"%self 


    def _asdict (t ):
        'Return a new dict which maps field names to their values'
        return {'x0':t [0 ],'x1':t [1 ],'x2':t [2 ],'x3':t [3 ],'x4':t [4 ]}


    def _replace (self ,**kwds ):
        '''Return a new Point5  object replacing specified
                  fields with new values'''
        result =self ._make (map (kwds .pop ,('x0','x1','x2','x3','x4'),self ))
        if kwds :
            raise ValueError ('Got unexpected field names: %r'
            %kwds .keys ())

        return result 


    def __getnewargs__ (self ):
        return tuple (self )


    x0 =property (itemgetter (0 ))
    x1 =property (itemgetter (1 ))
    x2 =property (itemgetter (2 ))
    x3 =property (itemgetter (3 ))
    x4 =property (itemgetter (4 ))


```