import cytest # from ./lib; must be first
from curry.toolchain import flat2icurry as f2i
from curry.toolchain.flat2icurry import (
    casecompletion, caselifting, compiler, elimnewtype, flatcurry as fc
  , icurrytypes as ic, interfaces, terms
  )
from curry.toolchain.flat2icurry import __main__ as cli
from curry.utility import readcurry
from curry.utility.readcurry import lex
from curry import config
import flat2icurry_oracle as oracle
import contextlib, glob, io, os, shutil, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(HERE, 'data', 'curry')

# Where the FlatCurry interfaces of the library modules may be found.  The
# front end wrote them when icurry compiled the library.
LIBRARY_DIRS = [
    os.path.join(ROOT, 'curry', 'lib'), os.path.join(ROOT, 'curry', 'pakcs-3.4.1')
  ]

def corpus_fcy(name, directory=DATA):
  '''The FlatCurry file of a test module, written by the front end.'''
  pattern = os.path.join(directory, '.curry', '*', name + '.fcy')
  found = [
      f for f in sorted(glob.glob(pattern))
        if os.path.basename(os.path.dirname(f)) != config.intermediate_subdir()
    ]
  return found[0] if found else None

def M(name):
  return ('M', name)

def P(name):
  return fc.prelude(name)

def fcall(name, *args):
  return fc.Comb(fc.FuncCall, name, list(args))

def ccall(name, *args):
  return fc.Comb(fc.ConsCall, name, list(args))

def func(name, args, body, vis=fc.Public, arity=None):
  arity = len(args) if arity is None else arity
  return fc.Func(M(name), arity, vis, fc.TVar(0), fc.Rule(args, body))

def prog(functions, types=(), imports=('Prelude',), name='M'):
  return fc.Prog(name, list(imports), list(types), list(functions), [])

# A stand-in for the Prelude interface with the few entities the tests use.
BOOL = fc.Type(P('Bool'), fc.Public, [], [
    fc.Cons(P('False'), 0, fc.Public, []), fc.Cons(P('True'), 0, fc.Public, [])
  ])
LIST = fc.Type(P('[]'), fc.Public, [(0, fc.KStar)], [
    fc.Cons(P('[]'), 0, fc.Public, [])
  , fc.Cons(P(':'), 2, fc.Public, [fc.TVar(0), fc.TCons(P('[]'), [fc.TVar(0)])])
  ])
def pfunc(name, arity):
  return fc.Func(P(name), arity, fc.Public, fc.TVar(0), fc.Rule([], fc.Var(0)))
PRELUDE = fc.Prog(
    'Prelude', [], [BOOL, LIST]
  , [pfunc('failed', 0), pfunc('?', 2), pfunc('id', 1), pfunc('not', 1)], []
  )

class TestReader(cytest.TestCase):
  '''Tests the FlatCurry reader.'''

  def test_peano(self):
    fcyfile = corpus_fcy('Peano')
    if fcyfile is None:
      self.skipTest('Peano.fcy is not in the test corpus')
    p = f2i.load_flatcurry(fcyfile)
    self.assertIsInstance(p, fc.Prog)
    self.assertEqual(p.name, 'Peano')
    self.assertEqual(p.imports, ['Prelude'])
    self.assertEqual(p.operators, [])
    nat, = p.types
    self.assertEqual(nat.name, ('Peano', 'Nat'))
    self.assertEqual(nat.visibility, fc.Public)
    self.assertEqual(
        [(c.name, c.arity) for c in nat.constructors]
      , [(('Peano', 'O'), 0), (('Peano', 'S'), 1)]
      )
    self.assertEqual(
        [f.name[1] for f in p.functions]
      , [ '_inst#Prelude.Data#Peano.Nat', '_impl#===#Prelude.Data#Peano.Nat'
        , '_impl#aValue#Prelude.Data#Peano.Nat', 'add', 'main']
      )
    add = p.functions[3]
    self.assertEqual(add.arity, 2)
    self.assertEqual(add.rule.args, [1, 2])
    body = add.rule.body
    self.assertIsInstance(body, fc.Case)
    self.assertEqual(body.casetype, fc.Flex)
    self.assertEqual(body.scrutinee, fc.Var(1))
    o, s = body.branches
    self.assertEqual(o.pattern, fc.Pattern(('Peano', 'O'), []))
    self.assertEqual(o.body, fc.Var(2))
    self.assertEqual(s.pattern, fc.Pattern(('Peano', 'S'), [3]))
    self.assertEqual(
        s.body
      , ccall(('Peano', 'S'), fcall(('Peano', 'add'), fc.Var(3), fc.Var(2)))
      )

  def test_every_constructor(self):
    '''A text that uses every FlatCurry constructor.'''
    text = '''Prog "M" ["Prelude"]
      [ Type ("M","T") Public [(0,KStar),(1,KArrow KStar KStar)]
          [Cons ("M","C") 1 Private
            [ForallType [(2,KStar)] (FuncType (TVar 2) (TCons ("M","T") [TVar 0,TVar 1]))]]
      , TypeSyn ("M","S") Public [] (TCons ("Prelude","Int") [])
      , TypeNew ("M","N") Public [] (NewCons ("M","N") Public (TCons ("Prelude","Int") []))
      ]
      [ Func ("M","f") 1 Public (TVar 0)
          (Rule [1] (Case Rigid (Var 1)
            [ Branch (LPattern (Intc (-1))) (Lit (Floatc 1.0e-5))
            , Branch (LPattern (Charc '\\NUL')) (Typed (Var 1) (TVar 0))
            , Branch (LPattern (Charc '\\''))
                (Let [(2,Lit (Intc 3))] (Free [4] (Or (Var 2) (Var 4))))
            ]))
      , Func ("M","g") 0 Public (TVar 0) (External "M.g")
      , Func ("M","h") 0 Private (TVar 0)
          (Rule [] (Comb (FuncPartCall 2) ("M","f")
            [ Comb (ConsPartCall 1) ("M","C") []
            , Comb ConsCall ("M","C") [Comb FuncCall ("M","g") []]]))
      ]
      [Op ("M","+++") InfixlOp 5, Op ("M","***") InfixrOp 6, Op ("M","///") InfixOp 7]'''
    p = f2i.read_flatcurry(text)
    t, s, n = p.types
    self.assertEqual(t.typevars, [(0, fc.KStar), (1, fc.KArrow(fc.KStar, fc.KStar))])
    c, = t.constructors
    self.assertEqual(c.visibility, fc.Private)
    self.assertEqual(
        c.argtypes
      , [fc.ForallType(
            [(2, fc.KStar)]
          , fc.FuncType(fc.TVar(2), fc.TCons(M('T'), [fc.TVar(0), fc.TVar(1)]))
          )]
      )
    self.assertEqual(s, fc.TypeSyn(M('S'), fc.Public, [], fc.TCons(P('Int'), [])))
    self.assertEqual(n.constructor, fc.NewCons(M('N'), fc.Public, fc.TCons(P('Int'), [])))
    f, g, h = p.functions
    case = f.rule.body
    self.assertEqual(case.casetype, fc.Rigid)
    b1, b2, b3 = case.branches
    self.assertEqual(b1.pattern, fc.LPattern(fc.Intc(-1)))
    self.assertEqual(b1.body, fc.Lit(fc.Floatc(1.0e-5)))
    self.assertIsInstance(b1.body.literal.value, float)
    self.assertEqual(b2.pattern, fc.LPattern(fc.Charc(terms.Char('\0'))))
    self.assertEqual(b2.body, fc.Typed(fc.Var(1), fc.TVar(0)))
    self.assertEqual(b3.pattern.literal.value, "'")
    self.assertIsInstance(b3.pattern.literal.value, terms.Char)
    self.assertEqual(
        b3.body
      , fc.Let([(2, fc.Lit(fc.Intc(3)))], fc.Free([4], fc.Or(fc.Var(2), fc.Var(4))))
      )
    self.assertEqual(g.rule, fc.External('M.g'))
    self.assertEqual(h.visibility, fc.Private)
    self.assertEqual(
        h.rule.body
      , fc.Comb(fc.FuncPartCall(2), M('f'), [
            fc.Comb(fc.ConsPartCall(1), M('C'), []), ccall(M('C'), fcall(M('g')))
          ])
      )
    self.assertEqual(
        p.operators
      , [ fc.Op(M('+++'), fc.InfixlOp, 5), fc.Op(M('***'), fc.InfixrOp, 6)
        , fc.Op(M('///'), fc.InfixOp, 7)
        ]
      )
    # Strings are plain str; a Char is not a str of the string kind.
    self.assertIs(type(p.name), str)
    self.assertIs(type(p.imports[0]), str)

  def test_bad_input(self):
    self.assertRaisesRegex(
        f2i.Flat2ICurryError, 'unknown FlatCurry constructor', f2i.read_flatcurry, 'Bogus 1'
      )
    self.assertRaisesRegex(
        f2i.Flat2ICurryError, 'Public takes no arguments', f2i.read_flatcurry, 'Lit (Public 1)'
      )
    self.assertRaisesRegex(
        f2i.Flat2ICurryError, 'Var takes 1 arguments, got 0', f2i.read_flatcurry, 'Var'
      )
    self.assertRaisesRegex(
        f2i.Flat2ICurryError, 'Var takes 1 arguments, got 2', f2i.read_flatcurry, 'Var 1 2'
      )
    # A bare identifier reaches the decoder only from a hand-built term.
    ident = readcurry.types.make_identifier(lex.ConstructorToken('Flex'))
    self.assertIs(fc.decode(ident), fc.Flex)
    ident = readcurry.types.make_identifier(lex.ConstructorToken('Var'))
    self.assertRaisesRegex(f2i.Flat2ICurryError, 'Var needs 1 arguments', fc.decode, ident)

  def test_all_vars(self):
    e = fc.Let(
        [(5, fcall(M('f'), fc.Var(6)))]
      , fc.Case(fc.Flex, fc.Var(1), [
            fc.Branch(
                fc.Pattern(M('C'), [2, 3])
              , fc.Free([7], fc.Or(fc.Var(3), fc.Typed(fc.Var(8), fc.TVar(0))))
              )
          , fc.Branch(fc.LPattern(fc.Intc(0)), fc.Lit(fc.Intc(1)))
          ])
      )
    # The body comes first, then each let variable and its expression.
    self.assertEqual(fc.all_vars(e), [1, 2, 3, 7, 3, 8, 5, 6])

  def test_data_decls_of(self):
    p = prog([], types=[
        fc.TypeSyn(M('S'), fc.Public, [], fc.TVar(0))
      , fc.TypeNew(M('N'), fc.Public, [], fc.NewCons(M('N'), fc.Public, fc.TVar(0)))
      , fc.Type(M('T'), fc.Public, [], [
            fc.Cons(M('A'), 0, fc.Public, []), fc.Cons(M('B'), 2, fc.Public, [])
          ])
      ])
    self.assertEqual(
        fc.data_decls_of(p)
      , [(M('N'), [(M('N'), 1)]), (M('T'), [(M('A'), 0), (M('B'), 2)])]
      )

  def test_terms(self):
    v = fc.Var(1)
    self.assertEqual(repr(v), 'Var(1)')
    self.assertEqual(repr(fc.Flex), 'Flex')
    self.assertEqual(v, fc.Var(1))
    self.assertNotEqual(v, fc.Lit(1))
    self.assertNotEqual(fc.Public, ic.Public) # the two Public constructors differ
    self.assertEqual(hash(v), hash(fc.Var(1)))
    self.assertEqual(v.replace(index=2), fc.Var(2))
    self.assertRaises(ValueError, v.replace, bogus=1)
    self.assertRaises(ValueError, terms.Char, 'ab')
    match fc.Comb(fc.FuncCall, M('f'), [v]):
      case fc.Comb(ct, name, [arg]):
        self.assertEqual((ct, name, arg), (fc.FuncCall, M('f'), v))
      case _:
        self.fail('no match')

class TestLexer(cytest.TestCase):
  '''Tests the extensions of the readcurry lexer for FlatCurry.'''

  def test_negative_numbers(self):
    self.assertEqual(readcurry.parse('(-1)'), -1)
    self.assertEqual(readcurry.parse('[1,-2]'), [1, -2])
    self.assertEqual(readcurry.parse('-5'), -5)
    self.assertEqual(readcurry.parse('(-2.5)'), -2.5)
    e = readcurry.parse('Lit (Intc (-1))')
    self.assertEqual(e.args[0].args[0], -1)
    # Between two terms, '-' stays an operator.
    toks = list(lex.tokenize('1 - 2'))
    self.assertEqual(
        [type(t).__name__ for t in toks], ['NumberToken', 'OperatorToken', 'NumberToken']
      )
    toks = list(lex.tokenize('f -1'))
    self.assertEqual(
        [type(t).__name__ for t in toks], ['FunctionToken', 'OperatorToken', 'NumberToken']
      )

  def test_exponents(self):
    self.assertEqual(readcurry.parse('1.0e-5'), 1.0e-5)
    self.assertEqual(readcurry.parse('2.5e3'), 2500.0)
    self.assertEqual(readcurry.parse('1.0E+2'), 100.0)
    self.assertIsInstance(readcurry.parse('1.0e-5'), readcurry.Float)
    self.assertEqual(readcurry.parse('Floatc 1.0e-5').args[0], 1.0e-5)

  def test_ascii_names(self):
    cases = [
        (r"'\NUL'", '\0'), (r"'\SOH'", '\x01'), (r"'\SO'", '\x0e'), (r"'\SP'", ' ')
      , (r"'\DEL'", '\x7f'), (r"'\ESC'", '\x1b'), (r"'\US'", '\x1f')
      ]
    for text, expected in cases:
      tok, = lex.tokenize(text)
      self.assertIsInstance(tok, lex.CharToken)
      self.assertEqual(tok, expected, text)
    tok, = lex.tokenize(r'"\SO\&H\SOH"')
    self.assertEqual(tok, '\x0eH\x01')

class TestWriter(cytest.TestCase):
  '''Tests the showTerm writer: escapes, numbers, and parenthesization.'''

  def test_chars(self):
    cases = [
        (0, r"'\00'"), (1, r"'\01'"), (7, r"'\a'"), (8, r"'\b'"), (9, r"'\t'")
      , (10, r"'\n'"), (11, r"'\v'"), (12, r"'\f'"), (13, r"'\r'"), (27, r"'\27'")
      , (31, r"'\31'"), (32, "' '"), (34, "'\"'"), (39, r"'\''"), (92, r"'\\'")
      , (65, "'A'"), (126, "'~'"), (127, r"'\127'"), (160, r"'\160'")
      , (228, r"'\228'"), (0x1f600, r"'\128512'")
      ]
    for code, expected in cases:
      self.assertEqual(terms.show_char(terms.Char(chr(code))), expected, code)
      self.assertEqual(terms.showterm(terms.Char(chr(code))), expected, code)

  def test_strings(self):
    self.assertEqual(terms.show_string(''), '[]')
    self.assertEqual(terms.showterm(''), '[]')
    self.assertEqual(terms.showterm('abc'), '"abc"')
    self.assertEqual(terms.showterm('a"b'), r'"a\"b"')
    self.assertEqual(terms.showterm("it's"), '"it\'s"')
    self.assertEqual(terms.showterm('a\\b'), r'"a\\b"')
    self.assertEqual(terms.showterm('\0\x1b\n\t'), r'"\00\27\n\t"')
    self.assertEqual(terms.showterm('\xe4\x7f'), r'"\228\127"')

  def test_ints(self):
    self.assertEqual(terms.showterm(0), '0')
    self.assertEqual(terms.showterm(42), '42')
    self.assertEqual(terms.showterm(-42), '(-42)')
    self.assertEqual(terms.showterm(2**70), str(2**70))

  def test_floats(self):
    # The expected texts were printed by SWI-Prolog, as PAKCS does.
    cases = [
        (1.0e-5, '1.0e-5'), (1.0e22, '1.0e+22'), (123456789012345678.0, '1.2345678901234568e+17')
      , (0.1, '0.1'), (1.0e21, '1.0e+21'), (1.0e15, '1.0e+15'), (1.0e16, '1.0e+16')
      , (100.0, '100.0'), (1.5e300, '1.5e+300'), (5.0e-324, '5.0e-324')
      , (0.000123, '0.000123'), (1.0e-4, '0.0001'), (0.001, '0.001'), (1.0e7, '10000000.0')
      , (12345678.9, '12345678.9'), (1.0e100, '1.0e+100'), (-2.5, '(-2.5)'), (0.0, '0.0')
      , (-0.0, '-0.0'), (1.0e-7, '1.0e-7'), (3.0e-10, '3.0e-10'), (1.1, '1.1')
      , (3.14, '3.14'), (0.25, '0.25'), (123456789012345.67, '123456789012345.67')
      , (1.0, '1.0'), (-1.0e-5, '(-1.0e-5)')
      ]
    for value, expected in cases:
      self.assertEqual(terms.showterm(value), expected, value)
    self.assertRaises(ValueError, terms.showterm, float('inf'))
    self.assertRaises(ValueError, terms.showterm, float('nan'))

  def test_terms(self):
    self.assertEqual(terms.showterm(ic.Public), 'Public')
    self.assertEqual(terms.showterm(ic.IExempt), 'IExempt')
    self.assertEqual(terms.showterm(ic.IVarDecl(1)), '(IVarDecl 1)')
    self.assertEqual(
        terms.showterm(ic.IVarAssign(1, ic.IVarAccess(0, [0, 1])))
      , '(IVarAssign 1 (IVarAccess 0 [0,1]))'
      )
    self.assertEqual(terms.showterm(('M', 'f', 0)), '("M","f",0)')
    self.assertEqual(terms.showterm([]), '[]')
    self.assertEqual(terms.showterm(()), '()')
    self.assertEqual(
        terms.showterm(ic.IFPCall(('M', 'f', 0), 2, [ic.ILit(ic.IChar(terms.Char('x')))]))
      , '''(IFPCall ("M","f",0) 2 [(ILit (IChar 'x'))])'''
      )
    self.assertEqual(
        terms.showterm(ic.IProg('M', [], [], []))
      , '(IProg "M" [] [] [])'
      )
    self.assertRaises(TypeError, terms.showterm, True)
    self.assertRaises(TypeError, terms.showterm, object())

  def test_deep_term(self):
    '''A deep term, such as a long string literal, needs a raised recursion limit.'''
    deep = ic.ILit(ic.IInt(0))
    for i in range(3000):
      deep = ic.ICCall(('Prelude', ':', 1), [ic.ILit(ic.IInt(i)), deep])
    text = terms.showterm(deep)
    self.assertTrue(text.startswith('(ICCall ("Prelude",":",1) [(ILit (IInt 2999)),'))
    self.assertTrue(text.endswith('(ILit (IInt 0))' + '])' * 3000))

class TestElimNewtype(cytest.TestCase):
  '''Tests newtype elimination.'''

  NT = fc.TypeNew(M('N'), fc.Public, [(0, fc.KStar)], fc.NewCons(M('N'), fc.Public, fc.TVar(0)))

  def test_no_newtype(self):
    p = prog([func('f', [1], fc.Var(1))])
    self.assertIs(elimnewtype.elim_newtype([PRELUDE], p), p)

  def test_declaration(self):
    p = prog([], types=[self.NT])
    q = elimnewtype.elim_newtype([], p)
    self.assertEqual(
        q.types
      , [fc.Type(M('N'), fc.Public, [(0, fc.KStar)], [fc.Cons(M('N'), 1, fc.Public, [fc.TVar(0)])])]
      )

  def test_expressions(self):
    body = fcall(
        M('g')
      , ccall(M('N'), fc.Var(1))                                     # N e  ->  e
      , fc.Comb(fc.ConsPartCall(1), M('N'), [])                      # N    ->  Prelude.id
      , fc.Case(fc.Flex, fc.Var(1), [
            fc.Branch(fc.Pattern(M('N'), [2]), fcall(M('h'), fc.Var(2), fc.Var(3)))
          ])
      , fc.Case(fc.Rigid, fcall(M('k')), [fc.Branch(fc.Pattern(M('N'), [4]), fc.Var(4))])
      , fc.Case(fc.Flex, fc.Var(1), [
            fc.Branch(fc.Pattern(M('N'), [5]), fc.Var(5))
          , fc.Branch(fc.Pattern(M('N'), [6]), fc.Var(6))
          ])
      , fc.Let([(7, ccall(M('N'), fc.Var(1)))], fc.Free([8], fc.Or(
            fc.Typed(ccall(M('N'), fc.Var(8)), fc.TVar(0)), fc.Lit(fc.Intc(1))
          )))
      )
    p = prog([func('f', [1, 3], body)], types=[self.NT])
    q = elimnewtype.elim_newtype([], p)
    f, = q.functions
    self.assertEqual(
        f.rule.body
      , fcall(
            M('g')
          , fc.Var(1)
          , fc.Comb(fc.FuncPartCall(1), P('id'), [])
          , fcall(M('h'), fc.Var(1), fc.Var(3))
          , fc.Let([(4, fcall(M('k')))], fc.Var(4))
          , fc.Case(fc.Flex, fc.Var(1), [
                fc.Branch(fc.Pattern(M('N'), [5]), fc.Var(5))
              , fc.Branch(fc.Pattern(M('N'), [6]), fc.Var(6))
              ])
          , fc.Let([(7, fc.Var(1))], fc.Free([8], fc.Or(
                fc.Typed(fc.Var(8), fc.TVar(0)), fc.Lit(fc.Intc(1))
              )))
          )
      )

  def test_skipped_functions(self):
    inst = func('_inst#Prelude.Eq#M.N', [1], ccall(M('N'), fc.Var(1)))
    ext = fc.Func(M('e'), 0, fc.Public, fc.TVar(0), fc.External('e'))
    p = prog([inst, ext], types=[self.NT])
    q = elimnewtype.elim_newtype([], p)
    self.assertEqual(q.functions, [inst, ext])

  def test_imported_newtype(self):
    '''A newtype of an import is eliminated from the uses in this module.'''
    wrapper = fc.TypeNew(
        ('I', 'W'), fc.Public, [], fc.NewCons(('I', 'W'), fc.Public, fc.TCons(P('Int'), []))
      )
    imp = fc.Prog('I', [], [wrapper], [], [])
    p = fc.Prog('M', ['I'], [], [
        fc.Func(
            M('f'), 1, fc.Public
          , fc.FuncType(fc.TCons(('I', 'W'), []), fc.TCons(('I', 'W'), []))
          , fc.Rule([1], ccall(('I', 'W'), fc.Var(1)))
          )
      ], [])
    q = elimnewtype.elim_newtype([imp], p)
    f, = q.functions
    self.assertEqual(f.rule.body, fc.Var(1))
    self.assertEqual(f.typeexpr, fc.FuncType(fc.TCons(P('Int'), []), fc.TCons(P('Int'), [])))

  def test_types(self):
    nti = elimnewtype.newtypes_of([self.NT])
    te = fc.ForallType([(1, fc.KStar)], fc.FuncType(
        fc.TCons(M('N'), [fc.TVar(1)])
      , fc.TCons(M('T'), [fc.TCons(M('N'), [fc.TCons(P('Int'), [])])])
      ))
    self.assertEqual(
        elimnewtype.elim_type(nti, te)
      , fc.ForallType([(1, fc.KStar)], fc.FuncType(
            fc.TVar(1), fc.TCons(M('T'), [fc.TCons(P('Int'), [])])
          ))
      )

class TestCaseCompletion(cytest.TestCase):
  '''Tests case completion.'''

  DECLS = [(M('T'), [(M('A'), 0), (M('B'), 2), (M('C'), 1)])]

  def test_complete_and_order(self):
    case = fc.Case(fc.Flex, fc.Var(1), [
        fc.Branch(fc.Pattern(M('B'), [2, 3]), fc.Var(2))
      , fc.Branch(fc.Pattern(M('A'), []), fc.Var(1))
      ])
    completed = casecompletion.complete_exp(self.DECLS, case)
    self.assertEqual(
        completed
      , fc.Case(fc.Flex, fc.Var(1), [
            fc.Branch(fc.Pattern(M('A'), []), fc.Var(1))
          , fc.Branch(fc.Pattern(M('B'), [2, 3]), fc.Var(2))
          , fc.Branch(fc.Pattern(M('C'), [101]), fcall(P('failed')))
          ])
      )

  def test_failed_branch(self):
    self.assertEqual(
        casecompletion.failed_branch(M('B'), 2)
      , fc.Branch(fc.Pattern(M('B'), [101, 102]), fcall(P('failed')))
      )
    self.assertEqual(casecompletion.failed_branch(M('A'), 0).pattern.vars, [])

  def test_literals_and_empty(self):
    lit = fc.Case(fc.Rigid, fc.Var(1), [fc.Branch(fc.LPattern(fc.Intc(1)), fc.Var(1))])
    self.assertEqual(casecompletion.complete_exp(self.DECLS, lit), lit)
    empty = fc.Case(fc.Rigid, fc.Var(1), [])
    self.assertEqual(casecompletion.complete_exp(self.DECLS, empty), empty)

  def test_nested(self):
    inner = fc.Case(fc.Flex, fc.Var(2), [fc.Branch(fc.Pattern(M('A'), []), fc.Var(2))])
    done = fc.Case(fc.Flex, fc.Var(2), [
        fc.Branch(fc.Pattern(M('A'), []), fc.Var(2))
      , fc.Branch(fc.Pattern(M('B'), [101, 102]), fcall(P('failed')))
      , fc.Branch(fc.Pattern(M('C'), [101]), fcall(P('failed')))
      ])
    e = fc.Let([(3, fcall(M('f'), inner))], fc.Free([4], fc.Or(
        fc.Typed(inner, fc.TVar(0))
      , fc.Case(fc.Rigid, inner, [fc.Branch(fc.Pattern(M('C'), [5]), inner)])
      )))
    expected = fc.Let([(3, fcall(M('f'), done))], fc.Free([4], fc.Or(
        fc.Typed(done, fc.TVar(0))
      , fc.Case(fc.Rigid, done, [
        fc.Branch(fc.Pattern(M('A'), []), fcall(P('failed')))
      , fc.Branch(fc.Pattern(M('B'), [101, 102]), fcall(P('failed')))
      , fc.Branch(fc.Pattern(M('C'), [5]), done)
      ]))))
    self.assertEqual(casecompletion.complete_exp(self.DECLS, e), expected)

  def test_program(self):
    ext = fc.Func(M('e'), 0, fc.Public, fc.TVar(0), fc.External('e'))
    case = fc.Case(fc.Flex, fc.Var(1), [fc.Branch(fc.Pattern(M('C'), [2]), fc.Var(2))])
    p = prog([ext, func('f', [1], case)])
    q = casecompletion.complete_prog(self.DECLS, p)
    self.assertEqual(q.functions[0], ext)
    self.assertEqual(len(q.functions[1].rule.body.branches), 3)

  def test_unknown_constructor(self):
    case = fc.Case(fc.Flex, fc.Var(1), [fc.Branch(fc.Pattern(M('Z'), []), fc.Var(1))])
    self.assertRaisesRegex(
        f2i.Flat2ICurryError, "Type of constructor 'Z' not found!"
      , casecompletion.complete_exp, self.DECLS, case
      )

class TestCaseLifting(cytest.TestCase):
  '''Tests the lifting of nested cases, lets, and free declarations.'''

  @staticmethod
  def case(var, body_a, body_b, casetype=fc.Flex):
    return fc.Case(casetype, fc.Var(var), [
        fc.Branch(fc.Pattern(M('A'), []), body_a), fc.Branch(fc.Pattern(M('B'), [9]), body_b)
      ])

  def lift(self, *functions):
    return caselifting.lift_prog(prog(functions)).functions

  def test_union(self):
    self.assertEqual(caselifting.union([1, 2], [2, 3]), [1, 2, 3])
    self.assertEqual(caselifting.union([3, 1], [1, 2]), [3, 1, 2])
    self.assertEqual(caselifting.unionmap(lambda x: x, [[3], [1], [3]]), [1, 3])
    self.assertEqual(caselifting.unionmap(lambda x: x, [[1, 2], [2, 3]]), [1, 2, 3])

  def test_unbound_vars(self):
    case = fc.Case(fc.Flex, fc.Var(5), [
        fc.Branch(fc.Pattern(M('B'), [6]), fc.Or(fc.Var(6), fc.Typed(fc.Var(7), fc.TVar(0))))
      , fc.Branch(fc.LPattern(fc.Intc(0)), fc.Var(4))
      ])
    e = fc.Let([(2, fcall(M('f'), fc.Var(3), fc.Var(2)))], fc.Free([4], case))
    self.assertEqual(caselifting.unbound_vars(e), [5, 7, 3])
    self.assertEqual(caselifting.unbound_vars(fc.Lit(fc.Intc(1))), [])

  def test_nested_case(self):
    body = fcall(M('g'), fc.Var(2), self.case(1, fc.Var(2), fc.Var(9)))
    f, f_case0 = self.lift(func('f', [1, 2], body))
    # The arguments are the unbound variables: the scrutinee first, then the
    # branches in order.  The pattern variable 9 is bound.
    self.assertEqual(
        f.rule.body, fcall(M('g'), fc.Var(2), fcall(M('f_CASE0'), fc.Var(1), fc.Var(2)))
      )
    self.assertEqual(f_case0.name, M('f_CASE0'))
    self.assertEqual(f_case0.arity, 2)
    self.assertEqual(f_case0.visibility, fc.Private)
    self.assertEqual(f_case0.typeexpr, fc.TCons(P('None'), []))
    self.assertEqual(f_case0.rule, fc.Rule([1, 2], self.case(1, fc.Var(2), fc.Var(9))))

  def test_sibling_order(self):
    '''Two nested cases: the second one comes first in the output.'''
    body = fcall(M('g'), self.case(1, fc.Var(1), fc.Var(1)), self.case(2, fc.Var(2), fc.Var(2)))
    names = [fd.name[1] for fd in self.lift(func('f', [1, 2], body))]
    self.assertEqual(names, ['f', 'f_CASE1', 'f_CASE0'])

  def test_inner_case_order(self):
    '''A case nested in a nested case: the outer one comes first.'''
    inner = self.case(2, fc.Var(2), fc.Var(2))
    body = fcall(M('g'), self.case(1, fcall(M('h'), inner), fc.Var(1)))
    lifted = self.lift(func('f', [1, 2], body))
    self.assertEqual([fd.name[1] for fd in lifted], ['f', 'f_CASE0', 'f_CASE1'])
    f, case0, case1 = lifted
    self.assertEqual(
        case0.rule.body.branches[0].body, fcall(M('h'), fcall(M('f_CASE1'), fc.Var(2)))
      )

  def test_root_case_and_branches(self):
    '''A root case stays.  A case in a branch is lifted.'''
    body = self.case(1, self.case(2, fc.Var(2), fc.Var(9)), fc.Var(9))
    f, case0 = self.lift(func('f', [1, 2], body))
    self.assertEqual(f.rule.body, self.case(1, fcall(M('f_CASE0'), fc.Var(2)), fc.Var(9)))
    self.assertEqual(case0.rule.args, [2])

  def test_complex_case(self):
    body = fc.Case(fc.Rigid, fcall(M('g'), fc.Var(1)), [
        fc.Branch(fc.Pattern(M('A'), []), fc.Var(2))
      , fc.Branch(fc.Pattern(M('B'), [5]), fcall(M('h'), fc.Var(5), fc.Var(3)))
      ])
    f, cc0 = self.lift(func('f', [1, 2, 3], body))
    self.assertEqual(
        f.rule.body
      , fcall(M('f_COMPLEXCASE0'), fc.Var(2), fc.Var(3), fcall(M('g'), fc.Var(1)))
      )
    self.assertEqual(cc0.name, M('f_COMPLEXCASE0'))
    self.assertEqual(cc0.arity, 3)
    self.assertEqual(cc0.rule.args, [2, 3, 6])
    self.assertEqual(cc0.rule.body, fc.Case(fc.Rigid, fc.Var(6), body.branches))

  def test_complex_case_counter(self):
    '''The scrutinee is lifted before the new name is drawn.'''
    scrutinee = fcall(M('g'), self.case(1, fc.Var(1), fc.Var(1)))
    body = fc.Case(fc.Rigid, scrutinee, [fc.Branch(fc.Pattern(M('A'), []), fc.Var(1))])
    names = [fd.name[1] for fd in self.lift(func('f', [1], body))]
    self.assertEqual(names, ['f', 'f_COMPLEXCASE1', 'f_CASE0'])

  def test_let_and_free(self):
    let = fc.Let([(3, fc.Var(1))], fc.Var(3))
    free = fc.Free([4], fcall(M('g'), fc.Var(4), fc.Var(2)))
    body = fcall(M('h'), let, free)
    f, free1, let0 = self.lift(func('f', [1, 2], body))
    self.assertEqual(
        f.rule.body
      , fcall(M('h'), fcall(M('f_LET0'), fc.Var(1)), fcall(M('f_FREE1'), fc.Var(2)))
      )
    none = fc.TCons(P('None'), [])
    self.assertEqual(let0, fc.Func(M('f_LET0'), 1, fc.Private, none, fc.Rule([1], let)))
    self.assertEqual(free1, fc.Func(M('f_FREE1'), 1, fc.Private, none, fc.Rule([2], free)))

  def test_root_let(self):
    '''
    A root let stays.  Its bindings and its body are nested, so the case in
    the binding and the free declaration in the body are lifted, and so is
    the case inside the new free function.
    '''
    inner = self.case(3, fc.Var(3), fc.Var(9))
    body = fc.Let([(3, self.case(1, fc.Var(1), fc.Var(9)))], fc.Free([4], fc.Or(fc.Var(4), inner)))
    lifted = self.lift(func('f', [1], body))
    self.assertEqual([fd.name[1] for fd in lifted], ['f', 'f_FREE1', 'f_CASE2', 'f_CASE0'])
    f, free1, case2, case0 = lifted
    self.assertEqual(
        f.rule.body
      , fc.Let([(3, fcall(M('f_CASE0'), fc.Var(1)))], fcall(M('f_FREE1'), fc.Var(3)))
      )
    self.assertEqual(
        free1.rule, fc.Rule([3], fc.Free([4], fc.Or(fc.Var(4), fcall(M('f_CASE2'), fc.Var(3)))))
      )
    self.assertEqual(case2.rule, fc.Rule([3], inner))
    self.assertEqual(case0.rule.args, [1])

  def test_root_free(self):
    '''A root free declaration stays; the case in its body is lifted.'''
    body = fc.Free([4], fcall(M('g'), fc.Var(4), self.case(1, fc.Var(4), fc.Var(9))))
    f, case0 = self.lift(func('f', [1], body))
    self.assertEqual(
        f.rule.body
      , fc.Free([4], fcall(M('g'), fc.Var(4), fcall(M('f_CASE0'), fc.Var(1), fc.Var(4))))
      )
    self.assertEqual(case0.rule.args, [1, 4])

  def test_name_collision(self):
    '''A generated name that names a top-level function is skipped.'''
    body = fcall(M('g'), self.case(1, fc.Var(1), fc.Var(1)))
    clash = func('f_CASE0', [], fc.Lit(fc.Intc(0)))
    names = [fd.name[1] for fd in self.lift(func('f', [1], body), clash)]
    self.assertEqual(names, ['f', 'f_CASE1', 'f_CASE0'])

  def test_typed_and_external(self):
    body = fc.Typed(self.case(1, fc.Var(1), fc.Var(1)), fc.TVar(0))
    ext = fc.Func(M('e'), 0, fc.Public, fc.TVar(0), fc.External('e'))
    f, e = self.lift(func('f', [1], body), ext)
    self.assertEqual(f.rule.body, body) # a root case under Typed is not nested
    self.assertEqual(e, ext)

class TestCompiler(cytest.TestCase):
  '''Tests the index maps and the ICurry generation.'''

  T = fc.Type(M('T'), fc.Public, [], [
      fc.Cons(M('A'), 0, fc.Public, []), fc.Cons(M('B'), 2, fc.Public, [])
    ])
  SYN = fc.TypeSyn(M('S'), fc.Public, [], fc.TVar(0))

  def translate(self, *functions, types=None, icurry_compat=True):
    types = [self.T] if types is None else types
    return f2i.translate(prog(functions, types=types), [PRELUDE], icurry_compat)

  def function(self, iprog, name):
    for ifun in iprog.functions:
      if ifun.name[1] == name:
        return ifun
    self.fail('no function %r' % name)

  def test_demand_of(self):
    self.assertEqual(compiler.demand_of(fc.Rule([1, 2], fc.Case(fc.Flex, fc.Var(2), []))), [1])
    self.assertEqual(compiler.demand_of(fc.Rule([1, 2], fc.Case(fc.Flex, fc.Var(3), []))), [])
    self.assertEqual(compiler.demand_of(fc.Rule([1], fcall(M('f')))), [])
    self.assertEqual(compiler.demand_of(fc.External('f')), [])

  def test_maps(self):
    p = prog([
        func('pub1', [], fc.Lit(fc.Intc(0))), func('priv1', [], fc.Lit(fc.Intc(0)), fc.Private)
      , func('pub2', [], fc.Lit(fc.Intc(0)))
      ], types=[self.SYN, self.T])
    case0 = func('pub1_CASE0', [], fc.Var(1), fc.Private)
    lifted = prog(p.functions[:2] + [case0] + p.functions[2:], types=p.types)
    maps = compiler.NameMaps.build(p, [PRELUDE], lifted)
    self.assertEqual(maps.funs[M('pub1')], 0)
    self.assertEqual(maps.funs[M('pub2')], 1)
    self.assertEqual(maps.funs[M('priv1')], 2)
    self.assertEqual(maps.funs[M('pub1_CASE0')], 3)
    self.assertEqual(maps.funs[P('failed')], 0)
    self.assertEqual(maps.funs[P('id')], 2)
    self.assertEqual(maps.cons[M('A')], (0, 0))
    self.assertEqual(maps.cons[M('B')], (2, 1))
    self.assertEqual(maps.cons[P('True')], (0, 1))
    self.assertEqual(maps.cons[P(':')], (2, 1))
    self.assertRaisesRegex(
        f2i.Flat2ICurryError, 'arity of constructor M.Z is unknown'
      , maps.arity_pos_of_cons, M('Z')
      )
    self.assertRaisesRegex(
        f2i.Flat2ICurryError, 'arity of operation M.z is unknown', maps.pos_of_fun, M('z')
      )
    # A type synonym takes a type index.
    iprog = compiler.flat2icurry(maps, lifted)
    self.assertEqual(
        iprog.types, [ic.IDataType(('M', 'T', 1), [(('M', 'A', 0), 0), (('M', 'B', 1), 2)])]
      )
    self.assertEqual(
        [f.name for f in iprog.functions]
      , [('M', 'pub1', 0), ('M', 'priv1', 2), ('M', 'pub1_CASE0', 3), ('M', 'pub2', 1)]
      )

  def test_constructor_case(self):
    body = fc.Case(fc.Flex, fc.Var(1), [fc.Branch(fc.Pattern(M('B'), [3, 4]), fc.Var(4))])
    iprog = self.translate(func('f', [1, 2], body))
    f = self.function(iprog, 'f')
    self.assertEqual(f.demanded, [0])
    self.assertEqual(f.visibility, ic.Public)
    self.assertEqual(
        f.body
      , ic.IFuncBody(ic.IBlock(
            [ic.IVarDecl(1)], [ic.IVarAssign(1, ic.IVarAccess(0, [0]))]
          , ic.ICaseCons(1, [
                ic.IConsBranch(('M', 'A', 0), 0, ic.IBlock([], [], ic.IExempt))
              , ic.IConsBranch(('M', 'B', 1), 2, ic.IBlock(
                    [ic.IVarDecl(4)], [ic.IVarAssign(4, ic.IVarAccess(1, [1]))]
                  , ic.IReturn(ic.IVar(4))
                  ))
              ])
          ))
      )

  def test_literal_case(self):
    body = fc.Case(fc.Rigid, fc.Var(1), [
        fc.Branch(fc.LPattern(fc.Intc(1)), fc.Lit(fc.Charc(terms.Char('a'))))
      , fc.Branch(fc.LPattern(fc.Floatc(2.5)), fc.Lit(fc.Floatc(0.5)))
      ])
    f = self.function(self.translate(func('f', [1], body)), 'f')
    self.assertEqual(
        f.body.block.statement
      , ic.ICaseLit(1, [
            ic.ILitBranch(
                ic.IInt(1), ic.IBlock([], [], ic.IReturn(ic.ILit(ic.IChar(terms.Char('a')))))
              )
          , ic.ILitBranch(ic.IFloat(2.5), ic.IBlock([], [], ic.IReturn(ic.ILit(ic.IFloat(0.5)))))
          ])
      )

  def test_complex_case(self):
    body = fc.Case(
        fc.Flex, fcall(M('g'), fc.Var(1)), [fc.Branch(fc.Pattern(M('A'), []), fc.Var(1))]
      )
    iprog = self.translate(func('f', [1], body), func('g', [1], fc.Var(1)))
    f = self.function(iprog, 'f')
    self.assertEqual(f.demanded, [])
    # The call passes the unbound variables of the branches, then the scrutinee.
    self.assertEqual(
        f.body.block.statement
      , ic.IReturn(ic.IFCall(
            ('M', 'f_COMPLEXCASE0', 2), [ic.IVar(1), ic.IFCall(('M', 'g', 1), [ic.IVar(1)])]
          ))
      )
    # Case completion ran first and added the branch B 101 102, so the fresh
    # variable for the scrutinee is 103.
    cc = self.function(iprog, 'f_COMPLEXCASE0')
    self.assertEqual(cc.arity, 2)
    self.assertEqual(cc.visibility, ic.Private)
    self.assertEqual(cc.demanded, [1])
    self.assertEqual(cc.body.block.decls, [ic.IVarDecl(1), ic.IVarDecl(103)])
    self.assertEqual(
        cc.body.block.assigns
      , [ic.IVarAssign(1, ic.IVarAccess(0, [0])), ic.IVarAssign(103, ic.IVarAccess(0, [1]))]
      )
    self.assertEqual(cc.body.block.statement.var, 103)
    self.assertEqual(
        [br.name for br in cc.body.block.statement.branches], [('M', 'A', 0), ('M', 'B', 1)]
      )
    self.assertEqual(cc.body.block.statement.branches[1].block, ic.IBlock([], [], ic.IExempt))

  def test_let_free_or_choice(self):
    let = fc.Let([(2, ccall(P(':'), fc.Lit(fc.Intc(1)), fc.Var(2)))], fc.Var(2))
    f = self.function(self.translate(func('f', [1], let)), 'f')
    self.assertEqual(
        f.body.block
      , ic.IBlock(
            [ic.IVarDecl(2)]
          , [ ic.IVarAssign(2, ic.ICCall(('Prelude', ':', 1), [ic.ILit(ic.IInt(1)), ic.IVar(2)]))
            , ic.INodeAssign(2, [1], ic.IVar(2))]
          , ic.IReturn(ic.IVar(2))
          )
      )
    mutual = fc.Let(
        [(2, ccall(M('B'), fc.Var(3), fc.Var(1))), (3, ccall(M('B'), fc.Var(2), fc.Var(3)))]
      , fc.Var(2)
      )
    f = self.function(self.translate(func('f', [1], mutual)), 'f')
    self.assertEqual(
        f.body.block.assigns[1:]
      , [ ic.IVarAssign(2, ic.ICCall(('M', 'B', 1), [ic.IVar(3), ic.IVar(1)]))
        , ic.IVarAssign(3, ic.ICCall(('M', 'B', 1), [ic.IVar(2), ic.IVar(3)]))
        , ic.INodeAssign(2, [0], ic.IVar(3))
        , ic.INodeAssign(3, [1], ic.IVar(3))
        ]
      )
    free = fc.Free([2, 3], fcall(P('?'), fc.Var(2), fc.Typed(fc.Var(3), fc.TVar(0))))
    f = self.function(self.translate(func('f', [1], free)), 'f')
    self.assertEqual(
        f.body.block
      , ic.IBlock(
            [ic.IFreeDecl(2), ic.IFreeDecl(3)], [], ic.IReturn(ic.IOr(ic.IVar(2), ic.IVar(3)))
          )
      )
    partial = fcall(
        P('?'), fc.Comb(fc.FuncPartCall(1), P('not'), [])
      , fc.Comb(fc.ConsPartCall(1), M('B'), [fc.Var(1)]), fc.Or(fc.Var(1), fc.Var(1))
      )
    f = self.function(self.translate(func('f', [1], partial)), 'f')
    self.assertEqual(
        f.body.block.statement
      , ic.IReturn(ic.IFCall(('Prelude', '?', 1), [
            ic.IFPCall(('Prelude', 'not', 3), 1, []), ic.ICPCall(('M', 'B', 1), 1, [ic.IVar(1)])
          , ic.IOr(ic.IVar(1), ic.IVar(1))
          ]))
      )

  def test_external_and_failed(self):
    ext = fc.Func(M('e'), 1, fc.Public, fc.TVar(0), fc.External('M.e'))
    iprog = self.translate(ext, func('f', [], fcall(P('failed'))))
    self.assertEqual(
        self.function(iprog, 'e')
      , ic.IFunction(('M', 'e', 0), 1, ic.Public, [], ic.IExternal('M.e'))
      )
    self.assertEqual(self.function(iprog, 'f').body, ic.IFuncBody(ic.IBlock([], [], ic.IExempt)))

  def test_errors(self):
    self.assertRaisesRegex(
        f2i.Flat2ICurryError, "Function 'f': toIExpr: Case occurred"
      , self.translate, func('f', [1], fc.Case(fc.Flex, fc.Var(1), []))
      )
    self.assertRaisesRegex(
        f2i.Flat2ICurryError, 'ICurry.Compiler: newtype occurred!'
      , compiler.flat2icurry, compiler.NameMaps()
      , prog([], types=[
            fc.TypeNew(M('N'), fc.Public, [], fc.NewCons(M('N'), fc.Public, fc.TVar(0)))
          ])
      )
    self.assertRaisesRegex(
        f2i.Flat2ICurryError, 'arity of operation M.zz is unknown'
      , self.translate, func('f', [], fcall(M('zz')))
      )

  def test_var_pos(self):
    e = ic.IFCall(('M', 'f', 0), [
        ic.IVar(1)
      , ic.IOr(ic.ILit(ic.IInt(0)), ic.ICPCall(('M', 'B', 1), 1, [ic.IVar(2)]))
      , ic.IVarAccess(0, [0])
      ])
    self.assertEqual(compiler.var_pos([], e), [(1, [0]), (2, [1, 1, 0])])

  def test_typed_root(self):
    '''
    icurry 3.1.0 does not look through a type annotation at the root of a
    rule.  By default the port copies its output: the bindings of a let or a
    free declaration are lost, and a case is an error.  Without the
    compatibility flag the annotation is removed first.
    '''
    INT = fc.TCons(P('Int'), [])
    let = func('tlet', [1], fc.Typed(fc.Let([(2, fcall(P('not'), fc.Var(1)))], fc.Var(2)), INT))
    free = func('tfree', [1], fc.Typed(fc.Free([2], fcall(P('?'), fc.Var(1), fc.Var(2))), INT))
    case = func('tcase', [1], fc.Typed(fc.Typed(fc.Case(fc.Rigid, fc.Var(1), [
        fc.Branch(fc.Pattern(P('True'), []), fc.Var(1))
      , fc.Branch(fc.Pattern(P('False'), []), fc.Var(1))
      ]), INT), INT))
    # The output of icurry: variable 2 is used but not declared.
    iprog = self.translate(let, free)
    self.assertEqual(
        self.function(iprog, 'tlet').body.block
      , ic.IBlock(
            [ic.IVarDecl(1)], [ic.IVarAssign(1, ic.IVarAccess(0, [0]))], ic.IReturn(ic.IVar(2))
          )
      )
    self.assertEqual(
        self.function(iprog, 'tfree').body.block
      , ic.IBlock(
            [ic.IVarDecl(1)], [ic.IVarAssign(1, ic.IVarAccess(0, [0]))]
          , ic.IReturn(ic.IOr(ic.IVar(1), ic.IVar(2)))
          )
      )
    self.assertRaisesRegex(
        f2i.Flat2ICurryError, "Function 'tcase': toIExpr: Case occurred", self.translate, case
      )
    self.assertEqual(compiler.demand_of(case.rule), [])
    # Without the flag, the block is built from the expression under the
    # annotation.
    iprog = self.translate(let, free, case, icurry_compat=False)
    self.assertEqual(
        self.function(iprog, 'tlet').body.block
      , ic.IBlock(
            [ic.IVarDecl(1), ic.IVarDecl(2)]
          , [ ic.IVarAssign(1, ic.IVarAccess(0, [0]))
            , ic.IVarAssign(2, ic.IFCall(('Prelude', 'not', 3), [ic.IVar(1)]))]
          , ic.IReturn(ic.IVar(2))
          )
      )
    self.assertEqual(
        self.function(iprog, 'tfree').body.block.decls, [ic.IVarDecl(1), ic.IFreeDecl(2)]
      )
    tcase = self.function(iprog, 'tcase')
    self.assertEqual(tcase.demanded, [0])
    self.assertEqual(compiler.demand_of(case.rule, icurry_compat=False), [0])
    self.assertIsInstance(tcase.body.block.statement, ic.ICaseCons)
    self.assertEqual(tcase.body.block.statement.var, 1)
    self.assertEqual(compiler.strip_typed(fc.Typed(fc.Typed(fc.Var(1), INT), INT)), fc.Var(1))
    # Annotations in nested positions are lifted away, so the flag has no
    # effect on them.
    nested = func('n', [1], fcall(P('not'), fc.Typed(fc.Let([(2, fc.Var(1))], fc.Var(2)), INT)))
    for flag in (True, False):
      iprog = self.translate(nested, icurry_compat=flag)
      self.assertEqual(
          self.function(iprog, 'n').body.block.statement
        , ic.IReturn(ic.IFCall(
              ('Prelude', 'not', 3), [ic.IFCall(('M', 'n_LET0', 1), [ic.IVar(1)])]
            ))
        )

class TestInterfaces(cytest.TestCase):
  '''Tests the interface finder and the module root.'''

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))

  def tearDown(self):
    shutil.rmtree(self.tmpdir)
    super().tearDown()

  def write(self, relpath, text):
    filename = os.path.join(self.tmpdir, relpath)
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as ostream:
      ostream.write(text)
    return filename

  def test_candidates(self):
    finder = f2i.InterfaceFinder([self.tmpdir], ['sub'])
    expected = [
        os.path.join(self.tmpdir, '.curry', 'sub', 'A', 'B.fint')
      , os.path.join(self.tmpdir, 'A', '.curry', 'sub', 'B.fint')
      , os.path.join(self.tmpdir, '.curry', 'sub', 'A', 'B.fcy')
      , os.path.join(self.tmpdir, 'A', '.curry', 'sub', 'B.fcy')
      ]
    self.assertEqual(list(finder.candidates('A.B')), expected)
    self.assertEqual(list(finder.candidates('C')), [
        os.path.join(self.tmpdir, '.curry', 'sub', 'C.fint')
      , os.path.join(self.tmpdir, '.curry', 'sub', 'C.fcy')
      ])

  def test_find(self):
    self.write('A/.curry/sub/B.fint', 'Prog "A.B" [] [] [] []')
    self.write('.curry/sub/C.fcy', 'Prog "C" [] [] [] []')
    finder = f2i.InterfaceFinder([self.tmpdir], ['other', 'sub'], progs=[PRELUDE])
    self.assertIs(finder.find('Prelude'), PRELUDE)
    self.assertEqual(finder.find('A.B').name, 'A.B')
    self.assertEqual(finder.find('C').name, 'C')
    self.assertIs(finder.find('C'), finder.find('C'))
    self.assertRaisesRegex(
        f2i.Flat2ICurryError, "no FlatCurry interface for module 'D'; tried:", finder.find, 'D'
      )

  def test_module_root(self):
    root = self.tmpdir
    self.assertEqual(f2i.module_root(os.path.join(root, '.curry', 'sub', 'M.fcy'), 'M'), root)
    hierarchical = os.path.join(root, '.curry', 'sub', 'A', 'B', 'M.fcy')
    self.assertEqual(f2i.module_root(hierarchical, 'A.B.M'), root)
    perdirectory = os.path.join(root, 'A', 'B', '.curry', 'sub', 'M.fcy')
    self.assertEqual(f2i.module_root(perdirectory, 'A.B.M'), root)

  def test_product_path(self):
    root = self.tmpdir
    self.assertEqual(
        f2i.product_path(os.path.join(root, '.curry', 'sub', 'M.fcy')), (root, 'sub', '')
      )
    self.assertEqual(
        f2i.product_path(os.path.join(root, '.curry', 'sub', 'A', 'B', 'M.fint'))
      , (root, 'sub', os.path.join('A', 'B'))
      )
    self.assertEqual(
        f2i.product_path(os.path.join(root, 'A', 'B', '.curry', 'sub', 'M.fcy'))
      , (os.path.join(root, 'A', 'B'), 'sub', '')
      )
    self.assertIsNone(f2i.product_path(os.path.join(root, 'A', 'M.fcy')))

class TestEndToEnd(cytest.TestCase):
  '''
  Compares the port with the .icy files that icurry wrote.  The FlatCurry
  inputs come from the test corpus and from the library build directories.
  The tests skip when the inputs are absent.
  '''

  def check(self, fcyfile):
    if fcyfile is None:
      self.skipTest('the FlatCurry file is not available')
    result = oracle.check_file(fcyfile, LIBRARY_DIRS)
    if result.status == oracle.FAILED and 'no FlatCurry interface' in result.detail:
      self.skipTest(result.detail.splitlines()[0])
    self.assertEqual(result.status, oracle.EQUAL, result.detail)
    return result

  def test_peano(self):
    self.check(corpus_fcy('Peano'))

  def test_hello(self):
    self.check(corpus_fcy('hello'))

  def test_chars(self):
    self.check(corpus_fcy('Chars'))

  def test_library_module(self):
    # The front end writes the hierarchical layout (.curry/<subdir>/Data/Maybe.fcy)
    # under the library root; an older run may have left the per-directory one.
    for directory in LIBRARY_DIRS:
      for name, where in [('Data/Maybe', directory), ('Maybe', os.path.join(directory, 'Data'))]:
        fcyfile = corpus_fcy(name, where)
        if fcyfile and oracle.expected_icy(fcyfile):
          self.check(fcyfile)
          return
    self.skipTest('no FlatCurry for Data.Maybe')

  def test_cli(self):
    fcyfile = corpus_fcy('Peano')
    icyfile = oracle.expected_icy(fcyfile) if fcyfile else None
    if icyfile is None:
      self.skipTest('Peano is not in the test corpus')
    tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    try:
      out = os.path.join(tmpdir, 'Peano.icy')
      argv = ['-o', out, fcyfile]
      for directory in LIBRARY_DIRS:
        argv[:0] = ['-i', directory]
      try:
        self.assertEqual(cli.main(argv), 0)
      except f2i.Flat2ICurryError as e:
        if 'no FlatCurry interface' in str(e):
          self.skipTest(str(e).splitlines()[0])
        raise
      with open(out, 'rb') as a, open(icyfile, 'rb') as b:
        self.assertEqual(a.read(), b.read())
    finally:
      shutil.rmtree(tmpdir)

class OverlayTestCase(cytest.TestCase):
  '''
  A test case over the overlay archive, the fixed oracle.  The archive is
  extracted once per class into a scratch directory.
  '''
  overlay = None

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    if oracle.overlay_archive() is None:
      raise unittest.SkipTest('the overlay archive is not in the repository')
    cls.tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    cls.overlay = oracle.Overlay.extract(cls.tmpdir)

  @classmethod
  def tearDownClass(cls):
    shutil.rmtree(cls.tmpdir, ignore_errors=True)
    super().tearDownClass()

  def check_modules(self, modules):
    '''
    Checks the test modules, given as ``(directory, name)`` pairs, against
    their .icy files in the archive.
    '''
    for directory, name in modules:
      with self.subTest(module='%s/%s' % (directory, name)):
        fcy = self.overlay.fcy(directory, name)
        self.assertTrue(os.path.isfile(fcy), 'not in the overlay archive: %s' % fcy)
        result = oracle.check_file(fcy, self.overlay.library_dirs())
        self.assertEqual(result.status, oracle.EQUAL, result.detail)

  def oracle_text(self, directory, name):
    '''The .icy text of a test module in the archive.'''
    icy = oracle.expected_icy(self.overlay.fcy(directory, name))
    with open(icy, 'r', encoding='utf-8', newline='') as istream:
      return istream.read()

class TestSample(OverlayTestCase):
  '''
  Compares the port with the oracle on a fixed sample of 60 test programs.
  The sample spans eight directories of the test corpus and covers nested
  and complex cases, lifted lets and free declarations, literal cases,
  characters, floats, failures, and imports of test and library modules.
  The whole corpus runs in func_flat2icurry.py.
  '''

  SAMPLE = (
      ('eqconstr', 'a0_000'), ('eqconstr', 'a0_126'), ('eqconstr', 'a0b0c0_072')
    , ('eqconstr', 'a0b0c0_198'), ('eqconstr', 'a0b0c0_324'), ('eqconstr', 'a2b1c0_006')
    , ('eqconstr', 'cprog02'), ('eqconstr', 'cprog03'), ('eqconstr', 'cprog06')
    , ('eqconstr', 'fprog02'), ('eqconstr', 'fprog03'), ('eqconstr', 'fprog06')
    , ('math', 'compare00'), ('math', 'compare18'), ('math', 'compare19')
    , ('math', 'compare37'), ('math', 'floatmath010'), ('math', 'floatmath045')
    , ('math', 'intmath003'), ('math', 'intmath038'), ('math', 'sort01')
    , ('math', 'sort02'), ('math', 'sort03'), ('math', 'sort04')
    , ('setfunctions', 'Common'), ('setfunctions', 'applic00'), ('setfunctions', 'applic01')
    , ('setfunctions', 'applic02'), ('setfunctions', 'applyS'), ('setfunctions', 'basic05')
    , ('setfunctions', 'basic14'), ('setfunctions', 'free03')
    , ('kiel', 'account'), ('kiel', 'assembler'), ('kiel', 'escher_cond')
    , ('kiel', 'family_rel'), ('kiel', 'first'), ('kiel', 'infresiduate')
    , ('kiel', 'member'), ('kiel', 'multgen')
    , ('funpat', 'funpat_isin00'), ('funpat', 'funpat_isin01'), ('funpat', 'funpat_isin02')
    , ('funpat', 'funpat_isin03'), ('funpat', 'funpat_last05'), ('funpat', 'funpat_split03')
    , ('io', 'appendFile'), ('io', 'appendFile_catcherror'), ('io', 'appendFile_error')
    , ('io', 'bindIO'), ('io', 'getChar_error'), ('io', 'readFile')
    , ('readshow', 'readchar'), ('readshow', 'readfloat'), ('readshow', 'readstring')
    , ('readshow', 'show')
    , ('benchmarks', 'Diamond'), ('benchmarks', 'Peano'), ('benchmarks', 'Qsortlet')
    , ('benchmarks', 'QueensSet9')
    )

  def test_sample(self):
    self.assertEqual(len(self.SAMPLE), 60)
    self.assertEqual(
        sorted(set(d for d, _ in self.SAMPLE))
      , ['benchmarks', 'eqconstr', 'funpat', 'io', 'kiel', 'math', 'readshow', 'setfunctions']
      )
    self.check_modules(self.SAMPLE)

class TestProbes(OverlayTestCase):
  '''
  Compares the port with the oracle on the probe modules under
  tests/data/curry/flat2icurry.  They hold what the rest of the corpus does
  not: negative numbers, float exponents, characters outside ASCII,
  recursive lets, partial constructor applications, newtypes, external
  declarations, a hierarchical import, and type annotations at the root of
  a rule.
  '''

  PROBES = (
      ('flat2icurry', 'Literals'), ('flat2icurry', 'Lets'), ('flat2icurry', 'Partials')
    , ('flat2icurry', 'Newtypes'), ('flat2icurry', 'Lifting'), ('flat2icurry', 'Classes')
    , ('flat2icurry', 'Externals'), ('flat2icurry', 'TypedRoot'), ('flat2icurry/Sub', 'Deep')
    )

  def test_probes(self):
    self.check_modules(self.PROBES)

  def test_probe_contents(self):
    '''The oracle files of the probes hold the constructs they are for.'''
    literals = self.oracle_text('flat2icurry', 'Literals')
    for text in [
        'IInt (-1)', 'IInt (-7)', 'IInt 12345678901234567890', 'IFloat (-0.5)', 'IFloat 1.0e-5'
      , 'IFloat 1.0e+22', 'IFloat 1.5e+15', 'IFloat 10000000000.0', 'IFloat 0.0001'
      , 'IFloat 1.234567890123457e+17', "IChar '\\128512'", "IChar '\\955'", "IChar '\\00'"
      , "IChar '\\31'", "IChar '\\127'", "IChar '\\''", "IChar '\"'", "IChar '\\\\'"
      , 'ICaseLit'
      ]:
      self.assertIn(text, literals)
    lets = self.oracle_text('flat2icurry', 'Lets')
    self.assertIn('(INodeAssign 1 [1] (IVar 1))', lets)
    self.assertIn('(INodeAssign 1 [1,1] (IVar 1))', lets)
    self.assertIn('_LET0', lets)
    partials = self.oracle_text('flat2icurry', 'Partials')
    self.assertIn('(ICPCall ("Prelude",":",1) 2 [])', partials)
    self.assertIn('(ICPCall ("Partials","Pair",0) 1 [(ILit (IInt 1))])', partials)
    newtypes = self.oracle_text('flat2icurry', 'Newtypes')
    self.assertIn('(IDataType ("Newtypes","Wrap",0) [(("Newtypes","Wrap",0),1)])', newtypes)
    self.assertNotIn('ICCall ("Newtypes","Wrap"', newtypes)
    self.assertNotIn('ICCall ("Data.Functor.Identity","Identity"', newtypes)
    lifting = self.oracle_text('flat2icurry', 'Lifting')
    for name in ['collide_CASE2', 'twice_CASE0', 'twice_CASE2', '_COMPLEXCASE', '_FREE', '_LET']:
      self.assertIn(name, lifting)
    self.assertIn('(IExternal "Externals.prim_ext")', self.oracle_text('flat2icurry', 'Externals'))
    classes = self.oracle_text('flat2icurry', 'Classes')
    self.assertIn('("Sub.Deep","deep",10)', classes)
    self.assertIn('(IProg "Classes" ["Prelude","Sub.Deep"]', classes)

  def test_hierarchical_layout(self):
    '''
    The front end writes the imported module Sub.Deep under the root of the
    importer, at .curry/<subdir>/Sub/Deep.fcy.  The harness takes the
    subdirectory and the expected file from that path.
    '''
    root = os.path.join(self.overlay.directory, 'tests', 'data', 'curry', 'flat2icurry')
    fcy = os.path.join(root, '.curry', self.overlay.subdir, 'Sub', 'Deep.fcy')
    self.assertTrue(os.path.isfile(fcy), 'not in the overlay archive: %s' % fcy)
    icy = os.path.join(root, 'Sub', '.curry', 'sprite-' + self.overlay.subdir, 'Deep.icy')
    self.assertEqual(oracle.expected_icy(fcy), icy)
    finder = oracle.make_finder(fcy, f2i.load_interface(fcy))
    self.assertEqual(finder.subdirs, [self.overlay.subdir])
    self.assertEqual(finder.searchdirs[0], root)
    result = oracle.check_file(fcy, self.overlay.library_dirs())
    self.assertEqual(result.status, oracle.EQUAL, result.detail)
    self.assertIn((fcy, icy), self.overlay.test_pairs())

  def test_typed_root(self):
    '''
    The oracle for a type annotation at the root of a rule is the output of
    icurry 3.1.0, which loses the bindings.  Without the compatibility flag
    the port declares and assigns them.
    '''
    fcy = self.overlay.fcy('flat2icurry', 'TypedRoot')
    text = self.oracle_text('flat2icurry', 'TypedRoot')
    self.assertIn(
        '(IBlock [(IVarDecl 1)] [(IVarAssign 1 (IVarAccess 0 [0]))] (IReturn (IFCall '
        '("Prelude","_impl#*#Prelude.Num#Prelude.Int",343) [(IVar 2),(IVar 2)])))'
      , text
      )
    self.assertNotIn('IFreeDecl', text)
    finder = oracle.make_finder(fcy, f2i.load_interface(fcy), self.overlay.library_dirs())
    iprog = f2i.translate_file(fcy, finder, icurry_compat=False)
    functions = {f.name[1]: f for f in iprog.functions}
    self.assertEqual(functions['typedLetRoot'].body.block.decls, [ic.IVarDecl(1), ic.IVarDecl(2)])
    self.assertEqual(functions['typedFreeRoot'].body.block.decls, [ic.IVarDecl(1), ic.IFreeDecl(2)])
    self.assertEqual(f2i.showterm(f2i.translate_file(fcy, finder)), text)
    # The command line option.
    tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    try:
      out = os.path.join(tmpdir, 'TypedRoot.icy')
      argv = ['--no-icurry-compat', '-o', out, fcy]
      for directory in self.overlay.library_dirs():
        argv[:0] = ['-i', directory]
      self.assertEqual(cli.main(argv), 0)
      with open(out, 'r', encoding='utf-8', newline='') as istream:
        self.assertIn('(IFreeDecl 2)', istream.read())
    finally:
      shutil.rmtree(tmpdir)

class TestOracleHarness(cytest.TestCase):
  '''Tests the harness in tests/lib/flat2icurry_oracle.py.'''

  def test_overlay(self):
    subdir = config.intermediate_subdir()
    self.assertEqual('sprite-' + oracle.frontend_subdir(), subdir)
    archive = oracle.overlay_archive()
    if archive is None:
      self.skipTest('the overlay archive is not in the repository')
    self.assertEqual(os.path.basename(archive), 'overlay-%s.tgz' % oracle.frontend_subdir())
    self.assertIsNone(oracle.overlay_archive(os.path.join(ROOT, 'docs')))
    tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    try:
      overlay = oracle.Overlay.extract(tmpdir)
      self.assertEqual(overlay.directory, tmpdir)
      self.assertEqual(overlay.subdir, oracle.frontend_subdir())
      fcy = overlay.fcy('eqconstr', 'a0_000')
      self.assertTrue(os.path.isfile(fcy))
      self.assertTrue(fcy.startswith(tmpdir))
      pairs = overlay.test_pairs()
      self.assertGreater(len(pairs), 1000)
      self.assertIn((fcy, oracle.expected_icy(fcy)), pairs)
      self.assertEqual(sorted(set(icy for _, icy in pairs)), overlay.test_icys())
      library = overlay.library_pairs()
      self.assertEqual(
          sorted(os.path.basename(icy) for _, icy in library)
        , ['Char.icy', 'Either.icy', 'Function.icy', 'Identity.icy', 'List.icy', 'Maybe.icy'
          , 'Prelude.icy', 'SetFunctions.icy']
        )
      for fcy, icy in library:
        self.assertTrue(icy.startswith(os.path.join(ROOT, 'curry', 'lib')), icy)
      libdir, = overlay.library_dirs()
      self.assertTrue(
          os.path.isfile(os.path.join(libdir, '.curry', overlay.subdir, 'Prelude.fint'))
        )
      results = oracle.check_pairs(pairs[:2], overlay.library_dirs())
      self.assertEqual(oracle.summarize(results), (2, 0, 0))
      self.assertEqual(oracle.report(results), 'equal 2 / different 0 / failed 0')
      wrong = oracle.Result('x.fcy', 'x.icy', oracle.FAILED, 'boom')
      self.assertEqual(
          oracle.report([wrong]), 'equal 0 / different 0 / failed 1\nfailed    x.fcy\nboom'
        )
      self.assertRaises(
          FileNotFoundError, oracle.Overlay.extract, tmpdir, None, os.path.join(ROOT, 'docs')
        )
    finally:
      shutil.rmtree(tmpdir)

  def test_expected_icy(self):
    fcyfile = corpus_fcy('Peano')
    if fcyfile is None:
      self.skipTest('Peano is not in the test corpus')
    icyfile = oracle.expected_icy(fcyfile)
    self.assertEqual(
        icyfile, os.path.join(DATA, '.curry', config.intermediate_subdir(), 'Peano.icy')
      )
    self.assertIsNone(oracle.expected_icy(os.path.join(DATA, '.curry', 'x', 'nothing.fcy')))
    # The hierarchical layout: <root>/.curry/<subdir>/A/M.fcy.  The expected
    # file is the mirror under sprite-<subdir>, the per-directory product of
    # Sprite, or the committed product beside the source, in that order.
    tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    try:
      def touch(*parts):
        path = os.path.join(tmpdir, *parts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'w').close()
        return path
      fcy = touch('.curry', 'fe', 'A', 'M.fcy')
      self.assertIsNone(oracle.expected_icy(fcy))
      committed = touch('A', 'M.icy')
      self.assertEqual(oracle.expected_icy(fcy), committed)
      perdirectory = touch('A', '.curry', 'sprite-fe', 'M.icy')
      self.assertEqual(oracle.expected_icy(fcy), perdirectory)
      mirror = touch('.curry', 'sprite-fe', 'A', 'M.icy')
      self.assertEqual(oracle.expected_icy(fcy), mirror)
      self.assertIsNone(oracle.expected_icy(os.path.join(tmpdir, 'A', 'M.fcy')))
    finally:
      shutil.rmtree(tmpdir)

  def test_first_difference(self):
    expected = '(IProg "M" [] [] [(IFunction ("M","f",0) 0 Public [] ' \
               '(IFuncBody (IBlock [] [] (IReturn (ILit (IInt 1))))))])'
    actual = expected.replace('IInt 1', 'IInt 2')
    text = oracle.first_difference(expected, actual)
    self.assertIn('first difference at byte %d' % expected.index('1))))'), text)
    self.assertIn("IFunction ('M', 'f', 0)", text)
    self.assertIn('IReturn[0].ILit[0].IInt[0]', text)
    self.assertIn('expected: 1', text)
    self.assertIn('actual:   2', text)
    self.assertIn('formatting only', oracle.first_difference('(IVar 1)', '(IVar  1)'))
    self.assertIn(
        'a sequence of 1'
      , oracle.first_difference('(IBlock [] [] IExempt)', '(IBlock [(IVarDecl 1)] [] IExempt)')
      )

  def test_check_and_main(self):
    fcyfile = corpus_fcy('hello')
    icyfile = oracle.expected_icy(fcyfile) if fcyfile else None
    if icyfile is None:
      self.skipTest('hello is not in the test corpus')
    results = oracle.check([fcyfile], LIBRARY_DIRS)
    if results[0].status == oracle.FAILED:
      self.skipTest(results[0].detail.splitlines()[0])
    self.assertEqual(oracle.summarize(results), (1, 0, 0))
    tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    try:
      wrong = os.path.join(tmpdir, 'hello.icy')
      with open(icyfile, 'r', newline='') as istream, open(wrong, 'w', newline='') as ostream:
        ostream.write(istream.read().replace('"hello"', '"other"', 1))
      argv = ['-q', fcyfile, '%s=%s' % (fcyfile, wrong)]
      for directory in LIBRARY_DIRS:
        argv[:0] = ['-i', directory]
      stdout = io.StringIO()
      with contextlib.redirect_stdout(stdout):
        status = oracle.main(argv)
      self.assertEqual(status, 1)
      self.assertIn('equal 1 / different 1 / failed 0', stdout.getvalue())
      self.assertIn('different', stdout.getvalue().splitlines()[0])
      missing = oracle.check_file(os.path.join(tmpdir, 'none.fcy'))
      self.assertEqual(missing.status, oracle.FAILED)
    finally:
      shutil.rmtree(tmpdir)
