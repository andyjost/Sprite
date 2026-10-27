=============
Using the API
=============

Sprite lets Python build typed Curry computations and consume their
answers.  This guide follows the boundary from a first call to streams.
Run the transcripts from ``examples/`` with ``install/bin`` on ``PATH``;
``curry.path`` searches the lesson directories added below and the
installed library.  :doc:`../Examples` lists every runnable lesson.

Curry ``Int`` is unbounded and converts to and from Python ``int`` without
loss. The runtime keeps signed 64-bit values inline, promotes overflowing
arithmetic to libtommath integers, and demotes results that fit inline.
``Char`` retains its Unicode code point range.

.. _building-expressions:

Import and evaluate one call
============================

:ref:`01: Hello, both ways <example-01>` is the first complete script.
Import a module, call a symbol to build a term, then evaluate it:

    >>> import curry
    >>> curry.path.insert(0, '01-run-with-python')
    >>> from curry.lib import Hello as H, Prelude as P
    >>> goal = H.greet('Python')
    >>> curry.eval(goal).one()
    'Hello, Python!'

The call builds a typed computation; evaluation returns converted Python
values.  A held term stays unchanged by evaluation.  A list describes a
list value, including a list of symbols.  Operators and Python keywords
use item lookup, such as ``P['+']`` and ``P['not']``.

:ref:`02: Compile and parse <example-02>` builds a module with
``curry.compile(source, name='M')`` and a text goal with
``curry.parse(text, imports=[M])``.  Use ``curry.term('hello')`` for a
String value; a bare string passed to ``eval`` is refused because it could
be mistaken for source text.  Symbol calls need no text compilation.

.. _results-lifecycle:

Consume results
===============

``eval`` and ``solve`` return lazy ``Results`` iterators.  ``next`` asks
for the next answer; ``one()`` checks that exactly one answer exists by
running to the end or finding a second.  ``list`` collects every answer of
a finite search.  :ref:`Lesson 01 <example-01>` shows all three.

    >>> with curry.eval(H.number) as results:
    ...   for value in results:
    ...     first = value
    ...     break
    ...   remaining = list(results)
    >>> first, remaining
    (1, [2, 3])
    >>> list(results)
    []
    >>> list(curry.eval(H.number))
    [1, 2, 3]
    >>> list(curry.eval(H.nothing))
    []

A break preserves the search's position.  ``close()`` or leaving ``with``
ends it; several searches may be open at once.  ``next(results, None)``
gives the first value or None, since None is never a Curry value.
Failure yields no value; ``one()`` raises ``NoValueError`` for none or
``ManyValuesError`` for more than one.  Work and runtime errors occur as
the iterator advances.  Answer order belongs to the scheduler; sort when
order is immaterial.  The step-mode transcripts here use the test runner's
repeatable schedule.

.. _typed-expressions:
.. _values-and-types:

Values and types
================

Calling a symbol checks its arguments against its Curry type.
``curry.typeof`` returns type text; ``defaulted=True`` asks for the type
chosen for evaluation (:ref:`goal-defaulting`).  The three recoverable
mistakes in :ref:`01 <example-01>` introduce these rules.

    >>> curry.typeof([1, 2.5])
    '[Float]'
    >>> curry.eval([1, 2.5]).one()
    [1.0, 2.5]
    >>> curry.typeof(P['+'](1, 2))
    'Num a => a'
    >>> curry.typeof(P['+'](1, 2), defaulted=True)
    'Int'
    >>> curry.eval(curry.term(1, type='Float')).one()
    1.0
    >>> curry.eval(P.ord(curry.Char('A'))).one()
    65

Python bool, int and float become Bool, a numeric literal and Float.
A str is always String; ``curry.Char`` spells a Char.  Lists are
homogeneous; tuples have zero or two through fifteen components; ranges
become lists.  Iterators enter lazily, and ``type=`` can state their element
type without consuming them.  Bytes, dictionaries, sets and None are
refused.  Use constructors such as ``P.Nothing`` and ``P.Just(x)`` for an
optional value.  Built-in results become Python scalars, lists and tuples;
a returned Char is a ``Char`` equal to the same one-character string.
``curry.show`` prints Curry syntax, including nested values.

.. _values-and-match:

User data on either side
------------------------

:ref:`05: Trees <example-05>` develops construction and pattern matching
on both sides of the boundary, then bounded generation.  Constructors with
arguments are classes; nullary constructors are values.  Applying a
constructor to values builds its instance, while an application to a term
stays a computation.  An evaluated user value is a ``Data`` with ``symbol``
and ``args``, and it can go back into Curry.

    >>> curry.path.insert(0, '05-trees')
    >>> from curry.lib import Tree as T
    >>> tree = T.Node(T.Leaf, 7, T.Leaf)
    >>> curry.eval(T.size(tree)).one()
    1
    >>> tree = curry.eval(T.fromList([7])).one()
    >>> isinstance(tree, T.Node)
    True
    >>> match tree:
    ...   case T.Node(left, x, right): print(x)
    ...   case T.Leaf: print('empty')
    7
    >>> curry.show(tree)
    'Node Leaf 7 Leaf'
    >>> isinstance(tree, curry.info(T).types['Tree'].cls)
    True

Record patterns use field names; positional constructors expose ``_0``,
``_1`` and so on.  Equality and hashing are structural; ordering uses
Curry's compare when the type has an Ord instance.  Classes and values
held across reload or reset become stale.  The public type's class lives
in metadata, leaving a same-named constructor on the module.

.. _logic-choices:

Logic: choices and variables
============================

:ref:`07: Choices, sharing, functions <example-07>` is the Python
companion to :ref:`00 <example-00>`.  One held term used twice shares a
computation; two separate reads of a function create independent ones.
Arithmetic builds terms, and ``__choice__`` is the explicit choice hook.

    >>> curry.path.insert(0, '07-choices')
    >>> from curry.lib import Choice as C
    >>> t = C.coin
    >>> str(t + t)
    'let x1 = coin in x1 + x1'
    >>> sorted(curry.eval(t + t))
    [0, 2]
    >>> sorted(set(curry.eval(C.coin + C.coin)))
    [0, 1, 2]
    >>> sorted(curry.eval((curry.term(1) + C.coin).__choice__(9)))
    [1, 2, 9]

The independent sum has four answers, with 1 twice; the transcript compares
distinct values.  ``curry.choice(1, 2)`` constructs a choice directly.
``let`` and ``ref`` also express sharing and tie cycles:

    >>> ones = curry.let(curry.ref('a'), a=P[':'](1, curry.ref('a')))
    >>> curry.eval(P.take(5, ones)).one()
    [1, 1, 1, 1, 1]

Curry observes a finite prefix lazily.  Converting a whole infinite list
would not finish: Python receives eager values.  This differs from a
stream of separate answers.  Functions can be passed as arguments and
returned as callable ``Function`` values:

    >>> curry.eval(P.map(C.inc, [1, 2, 3])).one()
    [2, 3, 4]
    >>> function = curry.eval(C.adder(10)).one()
    >>> isinstance(function, curry.Function)
    True
    >>> curry.eval(function(5)).one()
    15

.. _logic-answers:

Named variables and answers
---------------------------

:ref:`06: Variables <example-06>` shows narrowing and reading bindings.
``free(name)`` creates a named variable; reuse the Python object to share
it.  ``anonymous`` creates a new unnamed variable at each occurrence.
``solve`` returns an ``Answer`` of the converted value and a ``Bindings``
mapping, indexed by name or the original variable.  Bindings belong to
one evaluation; the variable's static type persists.

    >>> x = curry.free('x', type='Int')
    >>> answer = curry.solve(P['=:='](x, 3)).one()
    >>> answer.value, answer.bindings['x'], answer.bindings[x]
    (True, 3, 3)
    >>> curry.show(answer)
    '{x=3} True'
    >>> curry.solve(P['=:='](x, 4)).one().bindings[x]
    4
    >>> split = curry.parse('xs ++ [3] =:= [1,2,3] where xs free')
    >>> curry.show(curry.solve(split).one())
    '{xs=[1,2]} True'

Rigid arithmetic on an unknown variable can suspend.  Lesson 06 catches
``SuspensionError`` and then binds the variable with concurrent conjunction
``&`` so arithmetic can resume.  See :doc:`../CurryPrimer/Semantics` for
residuation and :ref:`13 <example-13>` and :ref:`17 <example-17>` for
applications of unification.

.. _set-functions:

Encapsulated search
===================

:ref:`08: Permutation sort <example-08>` collects permutations with a set
function and reads the returned ``Values`` multiset.  Multiplicity is
preserved; ``len``, iteration and membership work on the finite collection.

    >>> SF = curry.import_('Control.SetFunctions')
    >>> values = curry.eval(SF.set0(curry.choice(1, 2))).one()
    >>> isinstance(values, curry.Values), sorted(values)
    (True, [1, 2])
    >>> len(values), 2 in values
    (2, True)

A choice inside the capsule contributes to its collection.  An argument
choice outside gives a collection per alternative.  A Python-held term
shared inside and outside ``set0`` follows weak encapsulation: whichever
evaluation owns it first determines the result.  ``SF.set1(P.id, term)``
puts the choice outside deliberately; a free argument narrows outside too,
giving a set per binding.  See :doc:`../CurryPrimer/Semantics` for the full
rules, :ref:`10: N queens <example-10>` for an application, and
:ref:`25: Perfect hash <example-25>` for program search.

.. _typed-errors:

Errors
======

:ref:`01 <example-01>` catches errors at construction and at a pull;
:ref:`06 <example-06>` adds suspension.  All public errors descend from
``CurryError(Exception)``.  ``CurryTypeError`` also derives from TypeError;
its children distinguish conversion, mismatch, arity, missing instance,
defaulting, type syntax and interface errors.  For example:

    >>> try:
    ...   P.ord('A')
    ... except curry.ConversionError:
    ...   print("use curry.Char('A')")
    use curry.Char('A')
    >>> results = curry.eval(H.bad)
    >>> try:
    ...   next(results)
    ... except curry.DivisionByZeroError as error:
    ...   print(error)
    division by zero: div 1 0

``EvaluationError`` covers errors reached while running, including
``SuspensionError``, ``DivisionByZeroError``, I/O errors and nondeterminism
inside I/O.  ``NoValueError`` and ``ManyValuesError`` describe ``one()``
cardinality. ``IntOverflowError`` marks bounded conversions, such as a
conversion to Char, and conversions of a non-finite Float to Int. It can
arise during construction or a runtime step.  ``CompileError`` carries
the front end's report and source location.  Lookup, session, load and
prerequisite errors name the operation to correct.  The complete public
error tree is in :doc:`../Reference/curry`; callers can catch either a
specific leaf or ``CurryError``.  A failed search remains an empty result.

A shared free variable keeps the type inferred by its first use.  Reusing
it at an incompatible type raises ``CurryTypeError`` during construction.
An iterator represents one homogeneous Curry list: its context fixes the
element type, or its first item fixes it when the context leaves it open.
A later incompatible item raises ``ConversionError`` when it is drawn;
``typeof`` does not draw items.

.. _goal-defaulting:

Defaulting an ambiguous goal
----------------------------

Class constraints default as in the PAKCS REPL: Num and Integral to Int,
Fractional and Floating to Float, Monad to IO, and a lone Data to Bool.
Other ambiguous constraints raise ``DefaultingError`` and require a type.
A held partial application has already been typed; a later application
unifies with that type.

    >>> try:
    ...   curry.eval(P.read('5'))
    ... except curry.DefaultingError:
    ...   print('state the result type')
    state the result type
    >>> curry.eval(curry.term(P.read('5'), type='Int')).one()
    5

.. _session-control:

Metadata and session control
============================

:ref:`03: Metadata <example-03>` reads ``info(M).name``, ``file``,
``symbols`` and ``types``.  Types live in metadata; qualified lookup can
import the owning module as needed.

    >>> curry.path.insert(0, '.')
    >>> Peano = curry.import_('Peano')
    >>> curry.info(Peano).name
    'Peano'
    >>> [c.name for c in curry.type('Peano.Nat').constructors]
    ['O', 'S']
    >>> curry.symbol('Data.List.nub').fullname
    'Data.List.nub'
    >>> P['=:='].symbol.fullname
    'Prelude.=:='

``import_`` returns a registered module unchanged; an edited source emits
``CurryWarning`` once.  A PathLike or a string with a source suffix or path
separator names a file; other strings name modules on ``curry.path``.
``curry.modules`` and ``curry.flags`` are read-only mappings.  Edit or
replace ``curry.path`` to change the search path.

:ref:`04: Session <example-04>` demonstrates the complete workflow.
``compile`` registers source under ``name=``, its module header or a fresh
``Interactive_N``.  ``reload`` updates the module in place and stales
held terms:

    >>> M = curry.compile('answer :: Int\nanswer = 41', name='Session')
    >>> old = M.answer
    >>> _ = curry.reload(M, text='answer :: Int\nanswer = 42')
    >>> curry.eval(M.answer).one()
    42
    >>> try:
    ...   curry.eval(old).one()
    ... except curry.StaleError:
    ...   print('build the term again from M')
    build the term again from M

Text modules require ``text=`` on reload.  File modules reread their source
when text is omitted; C++ with ``interpret='tiered'`` or ``'off'`` requires
a new process, or ``reset(interpret='new')`` before import, for reload.
``wait(M)`` waits for that module's background compilation; ``wait()`` joins
all background compilations.  ``reset(**flags)`` starts a new session,
retains the search path, leaves Prelude registered and stales earlier
terms, variables and modules.

``save(M, path)`` writes an object for the current backend.
``load(path)`` registers it; loading the same file again returns the same
module.  A different backend or format, or an already registered name
from another file, raises ``LoadError``.  ``save(M, path, main=M.answer)``
writes an executable program that loads its embedded object and prints
that goal's answers.  Lesson 04 runs both forms in a temporary directory.

.. _io-streams:

I/O and streams
===============

An ``IO t`` goal runs its effects when evaluation advances and returns its
action result.  :ref:`09: Streams <example-09>` adds the output channel:
``Sprite.Stream.yield`` hands whole deterministic values to Python, one at
a time.  Start with a finite action before an infinite producer:

    >>> curry.path.insert(0, '09-streams')
    >>> from curry.lib import Streams as S
    >>> s = curry.stream(S.threeOut)
    >>> s.result is None
    True
    >>> list(s)
    [1, 2, 3]
    >>> curry.show(s.result)
    '()'
    >>> totals = curry.stream(S.totalsOut)
    >>> list(totals), totals.result
    ([1, 3, 6], 6)
    >>> from itertools import islice
    >>> primes = curry.stream(S.primesOut)
    >>> try:
    ...   print(list(islice(primes, 10)))
    ... finally:
    ...   primes.close()
    [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]

``curry.stream`` requires C++ and an ``IO t`` goal.  Nothing runs at the
call; each pull runs to the next yield and converts that whole value.
After exhaustion, ``Stream.result`` holds the action's return value.
Exhaust a stream or close it to release its paused run.  A choice in the
action or its yielded value raises ``NondetError`` at that pull and ends
the stream.  Yields inside capsules or nested evaluations are refused;
set functions inside streamed actions are allowed.

``sprite-exec Streams.curry -g threeOut`` writes one yielded value per
line, with no result line for IO ().  :doc:`../REPL` covers interactive I/O,
commands and exit statuses; the tools use ``curry.show`` to print values
and named answers.

.. _important-notes:

Two notes
=========

[1] Type signatures are optional for goals.
    Sprite reads the type of every function and constructor from the
    interface that the Curry front end writes beside a module.  A goal
    without a type signature keeps its class constraints, and Sprite
    defaults them as the REPL of PAKCS does: ``Num`` to ``Int``,
    ``Fractional`` to ``Float``, ``Monad`` to ``IO``, a lone ``Data`` to
    ``Bool``.  A constraint outside that table, such as ``Enum a`` for
    ``toEnum 65``, is an error that asks for a type annotation.
    Expressions built in Python with ``curry.term`` and symbol calls are typed before
    they are built; see :ref:`typed-expressions`.


[2] The front end runs once per change.
    Sprite relies on an external program, the Curry front end of PAKCS, to
    convert Curry source code into FlatCurry, from which it writes an
    intermediate representation called ICurry.  The front end is the
    slowest step of the compilation: a fraction of a second for a small
    module (0.6 s for ``Peano``), seconds for a large one, and nothing when
    the files are current.  It does not affect the performance of programs
    compiled by Sprite.  On the C++ backend a module runs interpreted at
    once, and its compilation to native code happens in the background.
