"""
The public Python surface of Sprite.

This installed stub records the names and signatures that have landed.
Session operations retain their current signatures until lane 5 lands;
wait is omitted with that lane. Stream and stream await lane 7. Constructor
classes await lane 6; constructors currently produce Term and Data.
Module metadata lives under the dotted slot returned by info(module).
Internal builders and interpreter methods are outside this surface.
"""

from __future__ import annotations

import types
from collections.abc import Collection, Iterable, Iterator, Mapping, Sequence
from os import PathLike
from typing import Any, ClassVar, Final, NamedTuple, NoReturn, TypeAlias, TypeVar, final

__all__ = [
    'import_'
  , 'compile'
  , 'reload'
  , 'reset'
  , 'save'
  , 'load'
  , 'modules'
  , 'path'
  , 'flags'
  , 'stats'
  , 'term'
  , 'parse'
  , 'free'
  , 'anonymous'
  , 'choice'
  , 'let'
  , 'ref'
  , 'symbol'
  , 'type'
  , 'eval'
  , 'solve'
  , 'typeof'
  , 'show'
  , 'Module'
  , 'Symbol'
  , 'DataType'
  , 'Term'
  , 'Data'
  , 'Function'
  , 'Var'
  , 'Values'
  , 'Char'
  , 'Anonymous'
  , 'Results'
  , 'Answer'
  , 'Bindings'
  , 'CurryError'
  , 'CurryWarning'
  , 'CurryTypeError'
  , 'ConversionError'
  , 'MismatchError'
  , 'ArityError'
  , 'NoInstanceError'
  , 'DefaultingError'
  , 'TypeSyntaxError'
  , 'InterfaceError'
  , 'IntOverflowError'
  , 'CompileError'
  , 'EvaluationError'
  , 'SuspensionError'
  , 'DivisionByZeroError'
  , 'CurryIOError'
  , 'CurryFileNotFoundError'
  , 'NondetError'
  , 'StackLimitError'
  , 'EvaluationTimeout'
  , 'InstantiationError'
  , 'NoValueError'
  , 'ManyValuesError'
  , 'ModuleLookupError'
  , 'ModuleExistsError'
  , 'SymbolLookupError'
  , 'TypeLookupError'
  , 'StaleError'
  , 'LoadError'
  , 'PrerequisiteError'
  , 'FlagError'
  , 'NotConstructorError'
  , 'CurryIndexError'
  , 'info'
  , 'Reference'
  ]

T = TypeVar('T')

# ---------------------------------------------------------------------------
# The two tables of the boundary, as type aliases.
# ---------------------------------------------------------------------------

#: What ``eval`` yields and what a binding holds: a Curry value as Python
#: data, by the type of the goal after defaulting, carried into every
#: position.
#:
#: ====================  ==================================================
#: Curry                 Python
#: ====================  ==================================================
#: ``Bool``              ``bool``
#: ``Int``               ``int``
#: ``Float``             ``float``
#: ``Char``              ``Char`` (a ``str`` of length one)
#: ``String``            ``str`` (the empty one is ``''``); by the type when
#:                       the goal's type fixes it, by the value when it
#:                       does not
#: ``[t]``               ``list``
#: ``(t1, .., tn)``      ``tuple``; ``()`` is ``()``
#: ``Values t``          ``Values``
#: ``IO t``              the action runs; the value of ``t`` converts
#: another data type     ``Data``: an instance of the constructor's class
#:                       (``Nothing``, ``Just 5``, ``Point 0 0``)
#: a function type       ``Function`` (callable)
#: an unbound variable   the ``Var`` itself, inside any of the above
#: ====================  ==================================================
PyValue: TypeAlias = (
    'bool | int | float | Char | str | list[PyValue] | tuple[PyValue, ...]'
    ' | Data | Function | Var | Values[PyValue]'
)

#: What a term position accepts, converted by the table of ``term``.
#:
#: ===================  ===================================================
#: Python               Curry
#: ===================  ===================================================
#: ``bool``             ``Bool`` (never an ``Int``)
#: ``int``              the numeric literal, ``Num a => a``: ``Int`` by the
#:                      REPL's defaulting, a ``Float`` in a ``Float`` slot,
#:                      ``fromInt n`` at another ``Num`` instance; outside
#:                      the signed 64-bit range ``IntOverflowError``
#: ``float``            ``Float`` (never an ``Int``)
#: ``str``              ``String``, whatever its length
#: ``Char``             ``Char``
#: ``tuple``            a Curry tuple of 2 to 15 components; ``()`` is the
#:                      unit; a 1-tuple is a ``ConversionError``
#: ``list``, ``range`` and any other ``collections.abc.Sequence`` that is
#:                      not a ``str``, ``bytes`` or ``tuple``: a Curry list,
#:                      every element at the element type 
#: iterator             a lazy Curry list, drawn once, on demand, shared by
#:                      the term that holds it; an item that does not fit
#:                      the element type is ``ConversionError`` when drawn
#: ``Term``             itself: one object, one node
#: ``types.ChoiceType`` ``a ? b`` (the fork's ``1 ? 2`` of two values)
#: ``anonymous``        a fresh free variable per occurrence
#: anything else        ``ConversionError`` naming the type and the
#:                      spelling that works: ``None`` (``P.Nothing``,
#:                      ``P.Just(x)``), ``bytes`` (``decode``), ``dict``
#:                      (``list(d.items())``), ``set``, a function, a
#:                      ``Results`` (``list(results)``, or a set function)
#: ===================  ===================================================
Convertible: TypeAlias = (
    'Term | bool | int | float | str | Char | Sequence[Any] | tuple[Any, ...]'
    ' | Iterator[Any] | types.ChoiceType | Anonymous'
)

# ---------------------------------------------------------------------------
# Modules and the session
# ---------------------------------------------------------------------------

def import_(arg: str | PathLike[str], currypath: Sequence[str] | None = None, is_sourcefile: bool = False) -> Module:
  """Import a module or source file, optionally using a search path."""

def compile(string: str, imports: Iterable[Module | str] | None = None, modulename: str | None = None) -> Module:
  """Compile source into a module, with optional imports and module name."""

def reload(flags: dict[str, object] = {}) -> None:
  """Replace the interpreter, applying the supplied flags."""

def reset() -> None:
  """Clear the current session and restore the path from the environment."""

def save(cymodule: Module, filename: str | PathLike[str] | None = None, goal: str | None = None, **kwds: Any) -> None:
  """Save generated code; goal selects the program entry point."""

def load(filename: str | PathLike[str], **kwds: Any) -> Module:
  """Load a compiled object into the current session."""


#: The loaded modules by qualified name (``'Prelude'``, ``'Data.List'``);
#: Packages are included until the session lane changes the registry.
modules: Mapping[str, Module]

#: The directories ``import_`` searches, in order (``CURRYPATH``, then the
#: library of the installation); mutate the list in place.
path: list[str]

#: Mutable interpreter flags, initialized from SPRITE_INTERPRETER_FLAGS.
flags: dict[str, object]

def stats() -> dict[str, int | float]:
  """The counters of the session: rewrite steps, forks, collections, seconds."""

# ---------------------------------------------------------------------------
# Terms
# ---------------------------------------------------------------------------

def term(value: Convertible, *, type: str | None = None) -> Term:
  """
  The Curry term of a Python value, by the type of the value alone (the
  table of ``Convertible``).  ``type`` states the type in Curry syntax and
  is unified with the inferred one; it is the typed escape for a bare
  ``[]``.  A ``Term`` is returned as it is.

  >>> str(curry.term('a')), str(curry.term(curry.Char('a'))), str(curry.term([], type='[Int]'))
  ('"a"', "'a'", '[]')
  """

def parse(text: str, *, imports: Iterable[Module | str] = ()) -> Term:
  """Parse Curry expression text; imports makes additional modules available."""

def free(name: str | None = None, *, type: str | None = None) -> Var:
  """Create a free variable, optionally named and annotated with a Curry type."""

@final
class Anonymous:
  """A placeholder that creates a fresh anonymous variable at each occurrence."""
  def __repr__(self) -> str: ...

anonymous: Final[Anonymous]

def choice(first: Convertible, second: Convertible, *more: Convertible) -> Term:
  """
  The term ``first ? second ? ..``, nested to the right, a fresh choice
  each time it is built; the function spelling of the fork's ``?``, which
  ``Term.__choice__`` serves.

  >>> list(curry.eval(curry.choice(1, 2, 3)))
  [1, 2, 3]
  """

def let(body: Convertible, /, **bindings: Convertible) -> Term:
  """
  The term ``let a = .. in body``; ``ref(name)`` inside the body or a
  binding names a binding, so a cyclic term has a Python spelling (A5).
  A Python name is already a ``let`` for a shared term; ``let`` is the
  spelling for a cycle.

  >>> ones = curry.let(curry.ref('a'), a=P[':'](1, curry.ref('a')))
  >>> str(ones), curry.eval(P.take(3, ones)).one()
  ('let a = 1 : a in a', [1, 1, 1])
  """

def ref(name: str) -> Reference:
  """A reference to a binding of the enclosing ``let``; anywhere else a ``CurryTypeError`` that names the bindings."""

def symbol(name: str) -> Term:
  """
  The term of a qualified name, its module imported on demand by the
  longest prefix that is a module (A13).

  >>> str(curry.symbol('Data.List.nub'))
  'nub'
  """

def type(name: str) -> DataType:
  """``curry.type('Peano.Nat')``: the data type of a qualified name, its module imported on demand (A13)."""

class Term:
  """A typed Curry expression held by Python. Reusing one object shares its computation."""

  __match_args__: ClassVar[tuple[str, ...]] = ('symbol', 'args')

  #: The symbol at the root; None for a literal, a variable or a lazy list.
  symbol: Symbol | None
  #: The arguments at the root, each a term; a list term is a cons cell
  #: ``(head, tail)``.
  args: tuple[Term, ...]
  #: The free variables of the term by name, in order of first occurrence;
  #: the ones ``solve`` reports.
  free_vars: Mapping[str, Var]

  def __call__(self, *args: Convertible) -> Term:
    """
    Applies the term to ``args``, left to right: ``inc 1`` for
    ``Coin.inc(1)``; more arguments than the arity apply the result
    (``P.id(Coin.inc, 1)`` is ``apply (id inc) 1``) when the result is a
    function type or a type variable, else ``ArityError``; a call with no
    argument raises ``TypeError`` naming the rule (``Coin.coin`` alone is
    the term ``coin``).

    >>> str(Coin.inc(1)), str(P.id(Coin.inc, 1))
    ('inc 1', 'apply (id inc) 1')
    """
  def __choice__(self, other: Convertible) -> Term:
    """``self ? other`` of the fork: the same as ``curry.choice(self, other)``."""
  def __rchoice__(self, other: Convertible) -> Term:
    """``other ? self`` of the fork."""
  def __eq__(self, other: object) -> bool:
    """Structural equality of two terms, a ``bool``; ``False`` for any other object, never an error.  Curry's equations are ``P['=='](a, b)`` and ``P['=:='](a, b)``."""
  def __hash__(self) -> int: ...
  def __bool__(self) -> NoReturn:
    """Raises ``TypeError``: a Curry term has no truth value; evaluate it (``curry.eval(t).one()``)."""
  def __str__(self) -> str:
    """
    The term as Curry text, as ``show`` prints it: ``inc 1``, ``[1,2]``,
    ``inc (1 ? 2)``, ``1 : a``.  A reducible subterm that is shared prints
    through a ``let``, so the text says what the graph says: for
    ``c = Coin.coin``, ``str(P['+'](c, c))`` is ``let x1 = coin in x1 + x1``
    and ``str(P['+'](Coin.coin, Coin.coin))`` is ``coin + coin``.
    """
  def __repr__(self) -> str:
    """``<Term TEXT :: TYPE>``, for example ``<Term inc 1 :: Int>``."""

  # The stock dunders that stand in for the deferred operators of DL-4.
  # Each builds a term through the Prelude's operator and returns
  # ``NotImplemented`` for a foreign operand.  No comparison dunder is
  # defined on a term: the comparisons are ``P['<'](a, b)`` until DL-4
  # lands. Data ordering through Curry compare awaits lane 6.
  def __add__(self, other: Convertible) -> Term:
    """``self + other`` is the term ``self + other``; ``1 + Coin.coin`` is ``1 + coin``."""
  def __radd__(self, other: Convertible) -> Term: ...
  def __sub__(self, other: Convertible) -> Term: ...
  def __rsub__(self, other: Convertible) -> Term: ...
  def __mul__(self, other: Convertible) -> Term: ...
  def __rmul__(self, other: Convertible) -> Term: ...
  def __truediv__(self, other: Convertible) -> Term:
    """Curry's ``/`` (``Fractional``)."""
  def __rtruediv__(self, other: Convertible) -> Term: ...
  def __floordiv__(self, other: Convertible) -> Term:
    """Curry's ``div``."""
  def __rfloordiv__(self, other: Convertible) -> Term: ...
  def __mod__(self, other: Convertible) -> Term:
    """Curry's ``mod``."""
  def __rmod__(self, other: Convertible) -> Term: ...
  def __neg__(self) -> Term:
    """Curry's ``negate``."""
  def __and__(self, other: Convertible) -> Term:
    """``self & other``, Curry's concurrent conjunction of two ``Bool`` terms: ``P['=:='](x, 1) & P['=:='](y, 2)``."""
  def __rand__(self, other: Convertible) -> Term: ...
  def __infix__(self, op: str, other: Convertible) -> Term:
    """
    DL-4's hook: ``self OP other`` for an operator named ``op`` in the
    Prelude or in a module of the operands' symbols, with the fixity of
    its ``Symbol``; ``NotImplemented`` when no module defines it.

    >>> str(curry.term([1, 2]).__infix__('++', [3]))
    '[1,2] ++ [3]'
    """
  def __rinfix__(self, op: str, other: Convertible) -> Term: ...

class Data(Term):
  """
  A value of a user type, with its constructor symbol and converted args.

  Equality is structural. Pass the value back into Curry as an argument.
  Constructor classes and ordering through Curry compare await lane 6.
  """
  __match_args__: ClassVar[tuple[str, ...]] = ('symbol', 'args')
  symbol: Symbol
  args: tuple[PyValue, ...]  # type: ignore[assignment]
  def __lt__(self, other: Data) -> bool: ...
  def __le__(self, other: Data) -> bool: ...
  def __gt__(self, other: Data) -> bool: ...
  def __ge__(self, other: Data) -> bool: ...
  def __bool__(self) -> bool: ...

class Function(Term):
  """A callable function value; its application builds a typed Term."""
  symbol: Symbol
  args: tuple[PyValue, ...]  # type: ignore[assignment]
  def __bool__(self) -> bool: ...

@final
class Var(Term):
  """A free variable, shared by Python identity; solve reports named bindings."""
  name: str | None
  symbol: None  # type: ignore[assignment]
  args: tuple[()]  # type: ignore[assignment]

class Values(Term, Collection[T]):
  """A finite multiset of converted values returned by a set function."""
  def __len__(self) -> int: ...
  def __iter__(self) -> Iterator[T]: ...
  def __contains__(self, value: object) -> bool: ...
  def __bool__(self) -> bool: ...

@final
class Char(str):
  """
  A Curry ``Char`` as a Python ``str`` of exactly one character: equal to
  and hashed as that ``str``; ``Char('ab')`` raises ``ValueError``; it is
  what a ``Char`` value comes back as and the only way a ``str`` enters a
  ``Char`` slot.

  >>> c = curry.eval(P.chr(65)).one(); type(c).__name__, c == 'A', curry.show(c)
  ('Char', True, "'A'")
  """
  def __new__(cls, value: str) -> Char: ...

@final
class Symbol:
  """Metadata of a function or constructor, separate from its term."""
  name: str
  fullname: str
  module: Module
  #: ``'function'`` or ``'constructor'``.
  kind: str
  arity: int
  #: The type scheme in Curry syntax, constraints kept, as ``:type`` prints it.
  signature: str
  public: bool
  #: For an operator: ``'infixl 6'`` and the like; None otherwise.
  fixity: str | None
  #: For a record constructor: the field names, in order; None otherwise.
  #: [A26; the interface carries them; not run]
  fields: tuple[str, ...] | None

@final
class DataType:
  """Metadata of a data type: its name, module, and constructor symbols."""
  name: str
  fullname: str
  module: Module
  constructors: tuple[Symbol, ...]

@final
class Module(types.ModuleType):
  """
  A loaded Curry module; attributes and item lookup return typed terms.

  Metadata is read through info(module); the namespace holds Curry names.
  Each symbol access creates a fresh term. Private symbols use item lookup.
  """
  def __getattr__(self, name: str) -> Term: ...
  def __getitem__(self, name: str) -> Term: ...
  def __dir__(self, /) -> list[str]: ...

# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def eval(goal: Convertible) -> Results[PyValue]:
  """
  The values of ``goal``, lazily: nothing runs at the call; each ``next``
  runs the Fair Scheme to the next value and yields it as Python data by
  the table of ``PyValue``, the class constraints of the goal defaulted as
  the REPL defaults them (the rest is ``DefaultingError``).  A failure is
  no value; an error raises from ``next`` when the run reaches it and ends
  the run; the values of the alternatives scheduled before the error come
  first, and the order of the values is the schedule's.  ``goal`` is a
  term or anything ``term`` converts, except a bare ``str``, which raises
  ``ConversionError`` naming ``parse`` (text) and ``term`` (a String).

  >>> list(curry.eval(Coin.coin)), list(curry.eval(P.failed)), list(curry.eval((Coin.coin, 'ab')))
  ([0, 1], [], [(0, 'ab'), (1, 'ab')])
  """

def solve(goal: Convertible) -> Results[Answer]:
  """
  The answers of ``goal``: for each value, an ``Answer`` of the value and
  the bindings of the named free variables of the goal (``curry.free('x')``
  or ``where x free``), in the order of their first occurrence; an unbound
  one is bound to itself, a variable bound to another unbound variable to
  that variable (PAKCS: ``{x=x, y=x} True`` for ``x =:= y``).
  ``print(answer)`` is the REPL's line.  Two different variables with one
  name raise ``CurryTypeError`` at the call.

  >>> for a in curry.solve(curry.parse('not b where b free')): print(a)
  {b=False} True
  {b=True} False
  """

@final
class Results(Iterator[T]):
  """
  The lazy iterator ``eval`` and ``solve`` return.  ``next(r)`` is the next
  value, ``next(r, None)`` the first or ``None`` (``None`` is never a
  value), ``list(r)`` every value (it ends when the search ends), a
  ``break`` keeps the search where it is, ``close()`` or the end of a
  ``with`` block ends it; no ``len``; several may be open at once.  The
  order of the values is the schedule's and no promise.

  >>> with curry.eval(Stream.three) as r: first = next(r)
  >>> first, list(r)
  (1, [])
  """
  def __iter__(self) -> Results[T]: ...
  def __next__(self) -> T:
    """The next value; ``StopIteration`` at the end; the error of an alternative when the run reaches it."""
  def one(self) -> T:
    """
    Exactly one value: runs the search to its end, raises
    ``NoValueError`` when there is none and ``ManyValuesError`` when
    there is a second; ``next(r)`` is the spelling for the first value
    when the second alternative is costly.

    >>> curry.eval(Coin.inc(41)).one()
    42
    """
  def close(self) -> None:
    """Ends the search; nothing more comes."""
  def __enter__(self) -> Results[T]: ...
  def __exit__(self, *exc: object) -> None: ...

@final
class Bindings(Mapping[str, PyValue]):
  """
  The bindings of an answer, name to value, in the order of the first
  occurrence of the variables in the goal; indexed by name or by the
  ``Var`` itself; hashable; prints as ``{xs=[1,2], x=3}`` and as ``{}``
  when empty.

  >>> x = curry.free('x'); a = next(curry.solve(P['=:='](x, 1)))
  >>> a.bindings['x'], a.bindings[x], str(a.bindings)
  (1, 1, '{x=1}')
  """
  def __getitem__(self, key: str | Var) -> PyValue: ...  # type: ignore[override]
  def __iter__(self) -> Iterator[str]: ...
  def __len__(self) -> int: ...
  def __hash__(self) -> int: ...
  def __str__(self) -> str: ...

class Answer(NamedTuple):
  """
  One answer of ``solve``: the value and the bindings, a 2-tuple
  (``value, bindings = answer``).  ``str`` is the REPL's line,
  ``{xs=[1,2]} True``, or the value alone when there are no bindings.

  >>> a = next(curry.solve(curry.parse('xs ++ [3] =:= [1,2,3] where xs free')))
  >>> a.value, a.bindings['xs'], str(a)
  (True, [1, 2], '{xs=[1,2]} True')
  """
  value: PyValue
  bindings: Bindings
  def __str__(self) -> str: ...



# ---------------------------------------------------------------------------
# Types and printing
# ---------------------------------------------------------------------------

def typeof(value: Convertible | Answer, *, defaulted: bool = False) -> str:
  """Return the Curry type scheme; defaulted applies the REPL defaulting table."""

def show(value: Convertible | Answer) -> str:
  """
  The text of a value, a term or an answer as the PAKCS REPL prints it:
  ``[1,2]``, ``(1,"ab")``, ``'a'``, ``Just (-1)``, ``Point 1 2``,
  ``{xs=[1,2]} True``, ``Values [0,1]``; operators infix with their
  fixity, ``inc (1 ? 2)``, ``1 : a``; an unbound anonymous variable is
  ``_a``, ``_b`` by order of appearance in this text, a named one its
  name; a shared reducible subterm of a term prints through a ``let``.
  ``str`` of a Curry object is the same text; Python data prints as Python
  prints it.  Two departures, stated: the empty ``String`` prints ``""``
  when its type is known to be ``String`` (PAKCS ``[]``; the owner's
  veto), and a partial application of an operator prints ``(+) 1`` (PAKCS
  prints the instance method's internal name).  The REPL and
  ``sprite-exec`` print with this function.

  >>> curry.show([1, 2]), curry.show('ab'), curry.show((curry.Char('a'), 1)), curry.show('')
  ('[1,2]', '"ab"', "('a',1)", '""')
  """

# ---------------------------------------------------------------------------
# Errors: one tree under CurryError(Exception); a leaf mixes in the standard
# class a Python programmer would catch.  Nothing derives from BaseException.
# Every message names the rule, the operand, its position and the spelling
# that follows; no message holds a machine path or a class of a backend; the
# same class on both backends and both routes.  Warnings go through
# ``warnings.warn(CurryWarning)``; the package logs to the logger ``curry``
# with a ``NullHandler`` and never configures the root logger.
# ---------------------------------------------------------------------------

class CurryError(Exception):
  """The base of every error of the package: ``except curry.CurryError`` catches them all."""

class CurryTypeError(CurryError, TypeError):
  """
  The typed boundary refused a term at construction: a conversion, an
  arity, a type mismatch, a missing instance, a type the table cannot
  default, a type annotation that does not parse, an interface the front
  end wrote badly.

  >>> P.ord('a')
  ConversionError: cannot convert 'a' to Char at argument 1 of Prelude.ord :: Char -> Int: a str is a String; write curry.Char('a')
  """

class ConversionError(CurryTypeError):
  """A Python value has no Curry value at its position (``None``, ``dict``, a 1-tuple, a bare ``str`` goal, a ``Results``), or an item of an iterator does not fit the element type when it is drawn."""

class MismatchError(CurryTypeError):
  """The type of an argument does not unify with the parameter's type; the message shows both and what fixed them."""

class ArityError(CurryTypeError):
  """More arguments than a symbol takes, when the result is not a function: ``Items.A :: Item takes 0 arguments, 1 given``."""

class NoInstanceError(CurryTypeError):
  """A class constraint has no instance at the type: ``no instance for Num Bool in argument 1 of Prelude.+``."""

class DefaultingError(CurryTypeError):
  """
  A class constraint of the goal that the REPL's table does not default,
  on either route: the message is the REPL's sentence and names
  ``curry.term(..., type=)`` or ``:: T`` in the text.

  >>> curry.eval(P.read('5'))
  DefaultingError: cannot handle the overloaded goal read "5" of type Read a => a
  Cannot handle arbitrary overloaded top-level expressions
  state the type: curry.term(P.read('5'), type='Int')
  """

class TypeSyntaxError(CurryTypeError):
  """A ``type=`` annotation that does not parse, names an unknown type constructor or has the wrong kind."""

class InterfaceError(CurryTypeError):
  """The interface of a module cannot be read; the message names the module, not the file (A20)."""

class IntOverflowError(CurryError, OverflowError):
  """
  An ``Int`` left the signed 64-bit range, at the boundary (raised when the
  term is built) or in a step (raised from ``next``): one class for both.

  >>> curry.term(2 ** 63)
  IntOverflowError: 9223372036854775808 is outside the range of Int (-9223372036854775808 to 9223372036854775807)
  """

class CompileError(CurryError):
  """
  The front end rejected Curry text (``compile``, ``parse``): ``report`` is
  its text as written, ``line`` and ``column`` locate the error in the
  user's text; ``str`` is the first error line without any machine path.
  """
  report: str
  line: int | None
  column: int | None

class EvaluationError(CurryError):
  """
  A Curry computation raised: ``error "boom"`` is ``EvaluationError: boom``;
  ``ioError (userError "x")`` is ``user error: x``.  Raised from ``next``
  when the run reaches the alternative.
  """

class SuspensionError(EvaluationError):
  """
  The run has only suspended alternatives left (a rigid operation on an
  unbound variable): ``Evaluation suspended: <the goal's text>``; raised
  after the values of the other alternatives.
  """

class DivisionByZeroError(EvaluationError, ZeroDivisionError):
  """``div 1 0``, ``mod 1 0`` and kin: ``division by zero: div 1 0``.  A ``Float`` division keeps the IEEE result and raises nothing."""

class CurryIOError(EvaluationError, OSError):
  """An uncaught I/O error of the action, the same class on both backends (A20)."""

class CurryFileNotFoundError(CurryIOError, FileNotFoundError):
  """``readFile "/nosuch"``: ``except FileNotFoundError`` catches it and ``.filename`` is set (A20)."""

class NondetError(EvaluationError):
  """A choice inside an I/O action, as ``print (1 ? 2)`` (A20)."""

class StackLimitError(EvaluationError, RecursionError):
  """The stack limit of the backend (the flag ``stack_limit``) was reached (A20)."""

class EvaluationTimeout(EvaluationError):
  """An evaluation exceeded its time limit (A20)."""

class InstantiationError(EvaluationError):
  """A free variable of a function type could not be instantiated (A20)."""

class NoValueError(CurryError, LookupError):
  """``Results.one()`` found no value: ``No value found: nothing``."""

class ManyValuesError(CurryError, ValueError):
  """``Results.one()`` found a second value: ``more than one value: coin has 0 and 1``."""

class ModuleLookupError(CurryError, ModuleNotFoundError):
  """No module of that name on ``curry.path``, or no such file; ``from curry.lib import X`` raises it as an ``ImportError``."""

class ModuleExistsError(CurryError, ValueError):
  """``compile`` was given the name of a loaded module: ``module 'Same' is loaded; curry.reload(curry.modules['Same'], text=...) replaces its code``."""

class SymbolLookupError(CurryError, AttributeError):
  """The module has no symbol of that name: ``module 'Tools' has no symbol 'nosuch'``; for a type, ``'Item' is a type: Items.types['Item']``."""

class TypeLookupError(CurryError, AttributeError):
  """``curry.type`` or ``info(module).types`` has no type of that name (A20)."""

class StaleError(CurryError, RuntimeError):
  """
  A term, variable or module of an earlier session (before ``reset``) or
  of an earlier version of its module (before ``reload``) was used; the
  message names the module, the event and the spelling that follows
  (``build it again from Coin``).
  """

class LoadError(CurryError, OSError):
  """``save``, ``load`` or ``reload`` could not write, read or replace the object; the message names the file, the backend and the way out."""

class PrerequisiteError(CurryError, OSError):
  """A tool or a file the operation needs is missing (the C++ compiler, the object of the other backend) (A20)."""

class FlagError(CurryError, ValueError):
  """A flag that does not exist or a value it does not take: ``'bogus' is not a flag; the flags are backend, interpret, rotation, stack_limit, ...`` (A17)."""

class NotConstructorError(CurryError, ValueError):
  """The raw route met a function where a constructor was required (A20, A23)."""

class CurryIndexError(CurryError, IndexError):
  """An index past the successors of a raw node (A20, A23)."""

class CurryWarning(UserWarning):
  """The category of a warning of the front end (overlapping rules) or of the loader (an edited source not read again); ``warnings.filterwarnings`` filters it (A18)."""

# Submodules are outside this file's surface. The curry.lib import hook stays.
class Reference(Term):
  """A named reference used by let; resolved within its bindings."""

def info(module: Module) -> _ModuleInfo:
  """Return the metadata record stored in a module's dotted slot."""

class _ModuleInfo:
  name: str
  file: str | None
  symbols: Mapping[str, Symbol]
  types: Mapping[str, DataType]
