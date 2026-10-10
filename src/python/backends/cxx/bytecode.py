'''
The emitter of the ICurry interpreter of the C++ runtime.

The runtime interprets a function from a compact bytecode (cyrt/icurry.hpp):
a sequence of 32-bit units that spell the statements of the ICurry body on
a small machine of registers, variables, and an operand stack.  This module
compiles an IFunction into that form.  The materializer of the C++ backend
attaches the result to the info table of the function (materialize.py) when
the interpreter flag ``interpret`` asks for interpretation.

The emitter follows the C++ code generator (compiler.py) statement by
statement, so an interpreted function takes the steps of its compiled form:

  * An argument that the step only passes on is a register, a plain Node *
    read through successor_node (the rule of passthrough.py).  A variable
    that a case scrutinizes, or that is the base of a path, is a Variable,
    bound by the indexer of Variable.  A free variable is a register.
  * The arguments of a node are pushed on the operand stack, left to right,
    and MAKE pops them.  A literal is a node of the runtime, made once per
    value (the constant table).  A partial application without arguments
    is a node made once per function.
  * A return writes its result into the redex when it fits the block of
    the redex (RET_NODE), or forwards the redex to the result (RET_REF).
  * A case is one hnf call and a branch table (CASE_CONS) or a value table
    (CASE_LIT).  Every block ends with a return, an exempt, or a case, so
    a branch runs to its own end and needs no join.

The names of the opcodes (OPCODES) and their numbers agree with the enum of
cyrt/icurry.hpp; a unit test compares them with the runtime.
'''
from ...exceptions import CompileError
from ... import icurry
from ...utility import strings, visitation
from . import passthrough
import struct

__all__ = [
    'FunctionCode', 'OP', 'OPCODES', 'NO_BRANCH', 'ROOT_VAR'
  , 'compile_function', 'disassemble'
  ]

# The opcodes, in the order of the enum in cyrt/icurry.hpp.
OPCODES = (
    'LOAD_ROOT_SUCC', 'LOAD_VAR_SUCC', 'BIND_ROOT', 'BIND_VAR', 'COPY_REG'
  , 'COPY_VAR', 'FREE_REG', 'PUSH_REG', 'PUSH_VAR', 'PUSH_ROOT', 'PUSH_CONST'
  , 'PUSH_SUCC', 'PUSH_PATH', 'MAKE', 'MAKE_PARTIAL', 'MAKE_STRING'
  , 'STORE_REG', 'STORE_VAR', 'SET_SUCC', 'EXEMPT', 'RET_REF', 'RET_NODE'
  , 'RET_STRING', 'CASE_CONS', 'CASE_LIT'
  )
OP = {name: number for number, name in enumerate(OPCODES)}

# The redex as the base of a path; a constructor without a branch.
ROOT_VAR = 0xffffffff
NO_BRANCH = 0xffffffff
MASK64 = (1 << 64) - 1

# The number of operand units each opcode takes before any variable part,
# and the index of the operand that counts the variable part (None for a
# fixed length).  CASE_CONS and CASE_LIT are read by the disassembler.
_LENGTHS = {
    'LOAD_ROOT_SUCC': (2, None), 'LOAD_VAR_SUCC': (3, None)
  , 'BIND_ROOT': (2, 1), 'BIND_VAR': (3, 2), 'COPY_REG': (2, None)
  , 'COPY_VAR': (2, None), 'FREE_REG': (1, None), 'PUSH_REG': (1, None)
  , 'PUSH_VAR': (1, None), 'PUSH_ROOT': (0, None), 'PUSH_CONST': (1, None)
  , 'PUSH_SUCC': (2, None), 'PUSH_PATH': (2, 1), 'MAKE': (2, None)
  , 'MAKE_PARTIAL': (2, None), 'MAKE_STRING': (1, None)
  , 'STORE_REG': (1, None), 'STORE_VAR': (1, None), 'SET_SUCC': (2, 1)
  , 'EXEMPT': (0, None), 'RET_REF': (0, None), 'RET_NODE': (2, None)
  , 'RET_STRING': (1, None)
  }


class FunctionCode(object):
  '''
  The bytecode of one function: the code units, the constants, and the
  sizes of the frame.  A constant is what the resolver gave for a symbol or
  a type, or a tuple that names a value the runtime makes when the code is
  attached (see cyrtbindings/icurry.cpp): ('I', value), ('C', codepoint),
  ('F', value), ('S', text), ('P', info, missing), ('V', kind, values).
  '''
  def __init__(self, name):
    self.name = name
    self.code = []
    self.consts = []
    self.nregs = 0
    self.nvars = 0
    self.nstack = 0

  def disassemble(self):
    '''The code as lines of text, one instruction per line.'''
    return list(disassemble(self.code, self.consts))


def disassemble(code, consts=None):
  '''
  Yields one line of text per instruction of ``code``: the position, the
  opcode, and the operands.  With ``consts``, a constant operand is shown
  with its value.
  '''
  pc = 0
  n = len(code)
  while pc < n:
    opcode = code[pc]
    name = OPCODES[opcode]
    if name == 'CASE_CONS':
      ntab = code[pc + 3]
      table = code[pc + 4: pc + 4 + ntab]
      shown = ', '.join('-' if t == NO_BRANCH else str(t) for t in table)
      yield '%4d %s v%d %s [%s]' % (
          pc, name, code[pc + 1], _show_const(consts, code[pc + 2]), shown
        )
      pc += 4 + ntab
    elif name == 'CASE_LIT':
      count = code[pc + 4]
      kind = chr(code[pc + 3])
      entries = []
      for i in range(count):
        lo, hi, target = code[pc + 5 + 3 * i: pc + 8 + 3 * i]
        entries.append('%s:%d' % (_show_value(kind, lo | (hi << 32)), target))
      yield '%4d %s v%d %s %s [%s]' % (
          pc, name, code[pc + 1], _show_const(consts, code[pc + 2]), kind
        , ', '.join(entries)
        )
      pc += 5 + 3 * count
    else:
      fixed, countpos = _LENGTHS[name]
      operands = list(code[pc + 1: pc + 1 + fixed])
      length = 1 + fixed
      if countpos is not None:
        extra = code[pc + 1 + fixed: pc + 1 + fixed + operands[countpos]]
        length += len(extra)
      else:
        extra = []
      yield '%4d %s' % (pc, _show_operands(name, operands, extra, consts))
      pc += length


def _show_value(kind, bits):
  if kind == 'i':
    return str(bits - (1 << 64) if bits >> 63 else bits)
  if kind == 'c':
    return repr(chr(bits))
  return repr(struct.unpack('<d', struct.pack('<Q', bits))[0])


def _show_const(consts, k):
  if consts is None or k >= len(consts):
    return 'k%d' % k
  value = consts[k]
  name = getattr(value, 'name', None)
  if name is not None and not isinstance(value, tuple):
    return 'k%d<%s>' % (k, name)
  return 'k%d<%r>' % (k, value)


def _show_operands(name, operands, extra, consts):
  words = [name]
  if name in ('LOAD_ROOT_SUCC', 'LOAD_VAR_SUCC', 'COPY_REG', 'FREE_REG'
              , 'PUSH_REG', 'STORE_REG'):
    words.append('r%d' % operands[0])
    rest = operands[1:]
    if name == 'LOAD_VAR_SUCC':
      words.append('v%d' % rest[0])
      rest = rest[1:]
    elif name == 'COPY_REG':
      words.append('r%d' % rest[0])
      rest = rest[1:]
    words.extend(str(x) for x in rest)
  elif name in ('BIND_ROOT', 'BIND_VAR', 'COPY_VAR', 'PUSH_VAR', 'STORE_VAR'
                , 'SET_SUCC'):
    words.append('v%d' % operands[0])
    if name in ('BIND_VAR', 'COPY_VAR'):
      words.append('v%d' % operands[1])
    words.append('[%s]' % ', '.join(str(x) for x in extra))
  elif name in ('PUSH_SUCC', 'PUSH_PATH'):
    base = operands[0]
    words.append('root' if base == ROOT_VAR else 'v%d' % base)
    if name == 'PUSH_SUCC':
      words.append(str(operands[1]))
    else:
      words.append('[%s]' % ', '.join(str(x) for x in extra))
  elif name in ('PUSH_CONST', 'MAKE_STRING', 'RET_STRING'):
    words.append(_show_const(consts, operands[0]))
  elif name in ('MAKE', 'MAKE_PARTIAL', 'RET_NODE'):
    words.append(_show_const(consts, operands[0]))
    words.append(str(operands[1]))
  return ' '.join(w for w in words if w != '[]')


def compile_function(ifun, resolver):
  '''
  Compiles ``ifun`` into a FunctionCode.  ``resolver`` answers for the
  symbols the body names: ``symbol(fullname)`` gives the constant that
  stands for the info table of a function or constructor, ``tag(fullname)``
  the tag of a constructor, and ``datatype(fullname)`` the constant that
  stands for the type of a constructor.  The constants are handed to the
  runtime as they are (see cyrtbindings/icurry.cpp); a test may pass names.

  Raises CompileError for a body the interpreter cannot run: a built-in
  without a C++ implementation, or an expression of an unknown kind.
  '''
  emitter = _Emitter(ifun, resolver)
  return emitter.compile()


class _Emitter(object):
  def __init__(self, ifun, resolver):
    self.ifun = ifun
    self.resolver = resolver
    self.out = FunctionCode(ifun.fullname)
    self.regs = {}   # vid -> register
    self.vars = {}   # vid -> variable
    self.const_index = {}
    self.depth = 0

  # The body.
  def compile(self):
    body = self.ifun.body
    if isinstance(body, icurry.IExternal):
      # As the generator does for an external without a definition: a call
      # of error with the message.
      message = 'external function %r is not defined' % body.symbolname
      block = icurry.IBlock(
          [], [], icurry.IReturn(
              icurry.IFCall('Prelude.prim_error', [icurry.IString(message)])
            )
        )
    elif isinstance(body, icurry.IBuiltin):
      raise CompileError(
          'function %r is a built-in without an implementation in the '
          'runtime' % self.ifun.fullname
        )
    else:
      block = getattr(body, 'block', None)
      if block is None:
        raise CompileError(
            'function %r has a body of kind %s, which the interpreter '
            'cannot run' % (self.ifun.fullname, type(body).__name__)
          )
    self.classify(block)
    self.stmt(block)
    self.out.nregs = len(self.regs)
    self.out.nvars = len(self.vars)
    return self.out

  # The variables.
  def classify(self, block):
    '''
    Gives every declared variable a register or a Variable.  The plain
    variables of passthrough.py and the free variables are registers.
    '''
    plain = passthrough.plain_variables(self.ifun)
    for decl in self.declarations(block):
      if decl.vid in self.regs or decl.vid in self.vars:
        # Declared in two branches: one slot serves both.
        continue
      if isinstance(decl, icurry.IFreeDecl) or decl.vid in plain:
        self.regs[decl.vid] = len(self.regs)
      else:
        self.vars[decl.vid] = len(self.vars)

  def declarations(self, stmt):
    if isinstance(stmt, icurry.IBlock):
      for decl in stmt.vardecls:
        yield decl
      for part in stmt.assigns, (stmt.stmt,):
        for item in part:
          yield from self.declarations(item)
    elif isinstance(stmt, icurry.ICase):
      for branch in stmt.branches:
        yield from self.declarations(branch.block)

  def reg(self, vid):
    try:
      return self.regs[vid]
    except KeyError:
      raise CompileError(
          'variable %d of %r is not a plain variable'
          % (vid, self.ifun.fullname)
        )

  def var(self, vid):
    try:
      return self.vars[vid]
    except KeyError:
      if vid == 0:
        raise CompileError(
            'the redex of %r cannot be scrutinized' % self.ifun.fullname
          )
      if vid in self.regs:
        raise CompileError(
            'variable %d of %r is a plain variable, which has no path'
            % (vid, self.ifun.fullname)
          )
      raise CompileError(
          'variable %d of %r is not declared' % (vid, self.ifun.fullname)
        )

  def base(self, vid):
    '''The base of a path: the redex or a Variable.'''
    return ROOT_VAR if vid == 0 else self.var(vid)

  # The constants.
  def const(self, key, value):
    index = self.const_index.get(key)
    if index is None:
      index = len(self.out.consts)
      self.out.consts.append(value)
      self.const_index[key] = index
    return index

  def symbol(self, name):
    return self.const(('sym', name), self.resolver.symbol(name))

  def literal(self, lit):
    if isinstance(lit, icurry.IInt):
      return self.const(('I', lit.value), ('I', lit.value))
    if isinstance(lit, icurry.IChar):
      point = ord(lit.value)
      return self.const(('C', point), ('C', point))
    if isinstance(lit, icurry.IFloat):
      # -0.0 and 0.0 are two literals, so the key is the spelling.
      return self.const(('F', repr(lit.value)), ('F', lit.value))
    raise CompileError(
        'literal %r in %r is not an Int, a Char, or a Float'
        % (lit, self.ifun.fullname)
      )

  def string(self, istring):
    text = strings.ensure_str(istring.value)
    return self.const(('S', text), ('S', text))

  # Code.
  def emit(self, name, *operands):
    self.out.code.append(OP[name])
    self.out.code.extend(int(x) for x in operands)

  def push(self, count=1):
    self.depth += count
    if self.depth > self.out.nstack:
      self.out.nstack = self.depth

  def pop(self, count=1):
    assert self.depth >= count
    self.depth -= count

  # Statements.
  @visitation.dispatch.on('stmt')
  def stmt(self, stmt):
    raise CompileError(
        'statement of kind %s in %r is not known to the interpreter'
        % (type(stmt).__name__, self.ifun.fullname)
      )

  @stmt.when(icurry.IBlock)
  def stmt(self, block):
    for decl in block.vardecls:
      if isinstance(decl, icurry.IFreeDecl):
        self.emit('FREE_REG', self.reg(decl.vid))
    for assign in block.assigns:
      self.stmt(assign)
    self.stmt(block.stmt)

  @stmt.when(icurry.IVarAssign)
  def stmt(self, assign):
    rhs = assign.expr
    vid = assign.vid
    if isinstance(rhs, icurry.IVarAccess):
      path = list(rhs.path)
      if not path:
        raise CompileError('empty path in %r' % self.ifun.fullname)
      base = self.base(rhs.vid)
      if vid in self.regs:
        if len(path) != 1:
          raise CompileError(
              'variable %d of %r is plain but has a path of %d entries'
              % (vid, self.ifun.fullname, len(path))
            )
        if base == ROOT_VAR:
          self.emit('LOAD_ROOT_SUCC', self.reg(vid), path[0])
        else:
          self.emit('LOAD_VAR_SUCC', self.reg(vid), base, path[0])
      elif base == ROOT_VAR:
        self.emit('BIND_ROOT', self.var(vid), len(path), *path)
      else:
        self.emit('BIND_VAR', self.var(vid), base, len(path), *path)
    elif isinstance(rhs, icurry.IVar):
      src = rhs.vid
      if vid in self.regs and src in self.regs:
        self.emit('COPY_REG', self.reg(vid), self.reg(src))
      elif vid in self.vars and src in self.vars:
        self.emit('COPY_VAR', self.var(vid), self.var(src))
      else:
        self.expr(rhs)
        self.store(vid)
    else:
      self.expr(rhs)
      self.store(vid)

  def store(self, vid):
    if vid in self.regs:
      self.emit('STORE_REG', self.reg(vid))
    else:
      self.emit('STORE_VAR', self.var(vid))
    self.pop()

  @stmt.when(icurry.INodeAssign)
  def stmt(self, assign):
    path = list(assign.path)
    if not path:
      raise CompileError('empty path in %r' % self.ifun.fullname)
    self.expr(assign.expr)
    self.emit('SET_SUCC', self.var(assign.vid), len(path), *path)
    self.pop()

  @stmt.when(icurry.IExempt)
  def stmt(self, exempt):
    self.emit('EXEMPT')

  @stmt.when(icurry.IReturn)
  def stmt(self, iret):
    expr = iret.expr
    if isinstance(expr, icurry.ILit):
      expr = expr.lit
    if isinstance(expr, (icurry.IVar, icurry.IVarAccess, icurry.ILiteral)) \
        and not isinstance(expr, icurry.IString):
      # A reference result: the redex is forwarded to the node, or takes a
      # copy of a primitive value (forward_or_copy).
      self.expr(expr)
      self.emit('RET_REF')
      self.pop()
    elif isinstance(expr, icurry.IString):
      self.emit('RET_STRING', self.string(expr))
    elif isinstance(expr, icurry.IPartialCall):
      self.expr(expr)
      self.emit('RET_REF')
      self.pop()
    elif isinstance(expr, icurry.ICall):
      for arg in expr.exprs:
        self.expr(arg)
      self.emit('RET_NODE', self.symbol(expr.symbolname), len(expr.exprs))
      self.pop(len(expr.exprs))
    elif isinstance(expr, icurry.IOr):
      self.expr(expr.lhs)
      self.expr(expr.rhs)
      self.emit('RET_NODE', self.symbol('Prelude.?'), 2)
      self.pop(2)
    else:
      raise CompileError(
          'result of kind %s in %r is not known to the interpreter'
          % (type(expr).__name__, self.ifun.fullname)
        )
    assert self.depth == 0

  @stmt.when(icurry.ICaseCons)
  def stmt(self, icase):
    if not icase.branches:
      raise CompileError('case without branches in %r' % self.ifun.fullname)
    v = self.var(icase.vid)
    first = icase.branches[0].symbolname
    k = self.const(('type', first), self.resolver.datatype(first))
    tags = [self.resolver.tag(branch.symbolname) for branch in icase.branches]
    if any(tag < 0 for tag in tags):
      raise CompileError(
          'case on a symbol that is not a constructor in %r'
          % self.ifun.fullname
        )
    ntab = max(tags) + 1
    start = len(self.out.code)
    self.emit('CASE_CONS', v, k, ntab, *([NO_BRANCH] * ntab))
    for tag, branch in zip(tags, icase.branches):
      self.out.code[start + 4 + tag] = len(self.out.code)
      self.stmt(branch.block)

  @stmt.when(icurry.ICaseLit)
  def stmt(self, icase):
    if not icase.branches:
      raise CompileError('case without branches in %r' % self.ifun.fullname)
    v = self.var(icase.vid)
    lits = [branch.lit for branch in icase.branches]
    if all(isinstance(lit, icurry.IInt) for lit in lits):
      kind = 'i'
      bits = [lit.value & MASK64 for lit in lits]
    elif all(isinstance(lit, icurry.IChar) for lit in lits):
      kind = 'c'
      bits = [ord(lit.value) for lit in lits]
    elif all(isinstance(lit, icurry.IFloat) for lit in lits):
      kind = 'f'
      bits = [
          struct.unpack('<Q', struct.pack('<d', lit.value))[0] for lit in lits
        ]
    else:
      raise CompileError(
          'literal case of mixed kinds in %r' % self.ifun.fullname
        )
    values = tuple(lit.value for lit in lits)
    k = self.const(('V', kind, values), ('V', kind, values))
    start = len(self.out.code)
    entries = []
    for value in bits:
      entries.extend([value & 0xffffffff, value >> 32, NO_BRANCH])
    self.emit('CASE_LIT', v, k, ord(kind), len(lits), *entries)
    for i, branch in enumerate(icase.branches):
      self.out.code[start + 5 + 3 * i + 2] = len(self.out.code)
      self.stmt(branch.block)

  # Expressions.  Each one pushes one node.
  @visitation.dispatch.on('expr')
  def expr(self, expr):
    raise CompileError(
        'expression of kind %s in %r is not known to the interpreter'
        % (type(expr).__name__, self.ifun.fullname)
      )

  @expr.when(icurry.IVar)
  def expr(self, ivar):
    vid = ivar.vid
    if vid == 0:
      self.emit('PUSH_ROOT')
    elif vid in self.regs:
      self.emit('PUSH_REG', self.reg(vid))
    else:
      self.emit('PUSH_VAR', self.var(vid))
    self.push()

  @expr.when(icurry.IVarAccess)
  def expr(self, access):
    path = list(access.path)
    if not path:
      raise CompileError('empty path in %r' % self.ifun.fullname)
    base = self.base(access.vid)
    if len(path) == 1:
      self.emit('PUSH_SUCC', base, path[0])
    else:
      self.emit('PUSH_PATH', base, len(path), *path)
    self.push()

  @expr.when(icurry.ILit)
  def expr(self, ilit):
    self.expr(ilit.lit)

  @expr.when(icurry.IString)
  def expr(self, istring):
    self.emit('MAKE_STRING', self.string(istring))
    self.push()

  @expr.when(icurry.ILiteral)
  def expr(self, lit):
    if isinstance(lit, icurry.IUnboxedLiteral):
      raise CompileError(
          'unboxed literal %r in %r: the interpreter builds nodes only'
          % (lit, self.ifun.fullname)
        )
    self.emit('PUSH_CONST', self.literal(lit))
    self.push()

  @expr.when(icurry.IPartialCall)
  def expr(self, ipcall):
    if not ipcall.exprs:
      info = self.resolver.symbol(ipcall.symbolname)
      k = self.const(
          ('P', ipcall.symbolname), ('P', info, int(ipcall.missing))
        )
      self.emit('PUSH_CONST', k)
      self.push()
      return
    self.compound(ipcall)

  @expr.when(icurry.ICall)
  def expr(self, icall):
    self.compound(icall)

  @expr.when(icurry.IOr)
  def expr(self, ior):
    self.compound(ior)

  def compound(self, root):
    '''
    Emits a call, a partial application with arguments, or a choice: the
    arguments of a node are pushed before the node is made, left to right.
    The walk keeps its own stack, so a nested expression of any depth needs
    no recursion (issue #125).
    '''
    stack = [(root, False)]
    while stack:
      expr, visited = stack.pop()
      if visited:
        self.make(expr)
      elif isinstance(expr, icurry.IOr):
        stack.append((expr, True))
        stack.append((expr.rhs, False))
        stack.append((expr.lhs, False))
      elif isinstance(expr, icurry.ICall) \
          and (expr.exprs or not isinstance(expr, icurry.IPartialCall)):
        stack.append((expr, True))
        for arg in reversed(expr.exprs):
          stack.append((arg, False))
      else:
        self.expr(expr)

  def make(self, expr):
    '''The instruction that makes the node of ``expr`` from its arguments.'''
    if isinstance(expr, icurry.IOr):
      self.emit('MAKE', self.symbol('Prelude.?'), 2)
      self.pop(2)
    elif isinstance(expr, icurry.IPartialCall):
      self.emit('MAKE_PARTIAL', self.symbol(expr.symbolname), len(expr.exprs))
      self.pop(len(expr.exprs))
    else:
      self.emit('MAKE', self.symbol(expr.symbolname), len(expr.exprs))
      self.pop(len(expr.exprs))
    self.push()
