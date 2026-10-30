'''
The JIT of the C++ backend: LLVM code from the bytecode of an interpreted
function, compiled in process on llvmlite (the spike of issue #65).

The JIT plugs in where the interpreter plugs in.  The materializer builds
the info tables of a module and attaches the bytecode of each function
(materialize.py, bytecode.py); under the flag ``jit`` it then hands the
function to :func:`compile`, which reads the bytecode back from the
runtime (``icurry_bytecode``, the constants as addresses), writes one LLVM
function with the signature of a step, links the bitcode of the helpers
(src/curryrt/jit/helpers.cpp, ``lib/curryrt-helpers.bc``), optimizes,
compiles with the ORC JIT of LLVM, and swaps the step of the table to the
code (``icurry_set_step``).  Every helper is inlined, so the step holds the
inline code of the runtime headers as compiled code does: the allocation
fast path, the reads of the successors, the rewrite of the redex.  What the
headers declare out of line is a call into the runtime library, resolved
against the library loaded in this process.

The emitter follows the interpreter opcode by opcode (curryrt/icurry.hpp):
a register is an SSA value, a variable is storage of the stack of the step
that the helpers manage, the operand stack of the bytecode is tracked at
emission time, and a case is a head-normalization and a switch over the
branch table; every block of the bytecode ends in a return, an exempt or
a case, so no block has a join.

The JIT is unavailable without llvmlite or without the bitcode, which CMake
builds when it finds clang (WITH_CLANG); the materializer then leaves the
function interpreted and logs the reason once.
'''
from ... import config
from . import bytecode
from . import curryrtbindings as curryrt
import logging, threading, time

__all__ = ['Unavailable', 'available', 'compile', 'statistics']

logger = logging.getLogger(__name__)

class Unavailable(Exception):
  '''The JIT cannot run in this installation or this process.'''

# A tag below T_CTOR is a status, not a constructor.
T_CTOR = curryrt.T_CTOR

_lock = threading.Lock()
_jit = None       # the JIT of the process, made at the first compile
_reason = None    # why the JIT is unavailable, once known

def available():
  '''Whether the JIT can compile in this process.'''
  try:
    _get()
  except Unavailable:
    return False
  return True

def compile(info, name):
  '''
  Compiles the interpreted function of ``info`` and swaps its step to the
  code.  ``name`` is the full name of the function.  Raises Unavailable when
  the JIT cannot run; any other error is a bug of the emitter.
  '''
  jit = _get()
  with _lock:
    jit.compile(info, name)

def statistics():
  '''The counts and the seconds of the JIT of this process.'''
  jit = _jit
  if jit is None:
    return {'functions': 0, 'seconds': 0.0}
  return {'functions': jit.functions, 'seconds': jit.seconds}

def _get():
  global _jit, _reason
  with _lock:
    if _jit is not None:
      return _jit
    if _reason is not None:
      raise Unavailable(_reason)
    try:
      _jit = _JIT()
    except Unavailable as exc:
      _reason = str(exc)
      raise
    return _jit


class _JIT(object):
  '''The LLVM state of the process: the target, the helpers, the ORC JIT.'''
  def __init__(self):
    try:
      import llvmlite.binding as llvm
      from llvmlite import ir
    except ImportError as exc:
      raise Unavailable('llvmlite is not installed (%s)' % exc)
    bitcode = config.jit_bitcode()
    if bitcode is None:
      raise Unavailable(
          'the installation has no bitcode of the JIT helpers '
          '(lib/curryrt-helpers.bc; CMake builds it when it finds clang)'
        )
    self.llvm, self.ir = llvm, ir
    # The headers carry inline assembly (a compiler barrier), so the code
    # generator needs the assembly parser of the target as well.
    for init in ('initialize_native_target', 'initialize_native_asmprinter'
        , 'initialize_native_asmparser'):
      getattr(llvm, init)()
    with open(bitcode, 'rb') as stream:
      self.helpers = llvm.parse_bitcode(stream.read())
    self.helpers.verify()
    # The symbols of the runtime library, for the ORC JIT (the extension
    # loaded the library for itself; the JIT needs it in the process table).
    llvm.load_library_permanently(
        config.installed_path('lib', config.curryrt_lib_name())
      )
    self.target = llvm.Target.from_default_triple()
    self.machine = self.target.create_target_machine(
        cpu=llvm.get_host_cpu_name(), opt=2
      )
    self.lljit = llvm.create_lljit_compiler(self.machine)
    self.sizes = curryrt.jit_sizes()
    self.trackers = []   # the code lives as long as the process
    self.functions = 0
    self.seconds = 0.0

  def compile(self, info, name):
    start = time.perf_counter()
    bc = curryrt.icurry_bytecode(info)
    if bc is None:
      raise ValueError('%s is not an interpreted function' % name)
    symbol = 'jit%d_%s' % (self.functions, _identifier(name))
    module = _Emitter(self, symbol, bc).emit()
    llmod = self.llvm.parse_assembly(str(module))
    t_ir = time.perf_counter()
    llmod.link_in(self.helpers, preserve=True)
    # The helpers are internal to the module once linked: the inliner folds
    # the ones the step calls into it, and the dead-code pass drops the
    # rest, so the optimizer and the code generator see the step alone.
    for fn in llmod.functions:
      if fn.name.startswith('jit_') and not fn.is_declaration and fn.name != symbol:
        fn.linkage = 'internal'
    llmod.verify()
    t_link = time.perf_counter()
    options = self.llvm.create_pipeline_tuning_options(speed_level=2)
    builder = self.llvm.create_pass_builder(self.machine, options)
    builder.getModulePassManager().run(llmod, builder)
    t_opt = time.perf_counter()
    library = self.llvm.JITLibraryBuilder().add_ir(llmod) \
        .add_current_process().export_symbol(symbol)
    tracker = library.link(self.lljit, symbol)
    address = tracker[symbol]
    self.trackers.append(tracker)
    curryrt.icurry_set_step(info, address)
    self.functions += 1
    end = time.perf_counter()
    self.seconds += end - start
    logger.debug(
        'JIT %s: %d units, %.1f ms (IR %.1f, link %.1f, optimize %.1f, code %.1f)'
      , name, len(bc['code']), 1000 * (end - start), 1000 * (t_ir - start)
      , 1000 * (t_link - t_ir), 1000 * (t_opt - t_link), 1000 * (end - t_opt)
      )


def _identifier(name):
  return ''.join(c if c.isalnum() else '_' for c in name)


# The helpers of src/curryrt/jit/helpers.cpp: name, result, arguments.
# p: a pointer; i: a 32-bit count or index; t: a tag; q: a 64-bit integer;
# d: a double; v: void.
_HELPERS = {
    'jit_cursor': ('v', 'pp'), 'jit_redex': ('p', 'p')
  , 'jit_root_succ': ('p', 'pi'), 'jit_var_succ': ('p', 'pi')
  , 'jit_var_init': ('v', 'p'), 'jit_var_destroy': ('v', 'p')
  , 'jit_var_copy': ('v', 'pp')
  , 'jit_bind_root': ('v', 'ppi'), 'jit_bind_var': ('v', 'ppi')
  , 'jit_freshvar': ('p', 'p'), 'jit_rvalue': ('p', 'p')
  , 'jit_make': ('p', 'ppi'), 'jit_make_partial': ('p', 'ppi')
  , 'jit_cstring': ('p', 'p')
  , 'jit_store_var': ('v', 'ppp'), 'jit_set_succ': ('v', 'pip')
  , 'jit_exempt': ('t', 'p'), 'jit_ret_ref': ('t', 'pp')
  , 'jit_ret_node': ('t', 'pppi'), 'jit_ret_string': ('t', 'pp')
  , 'jit_hnf': ('t', 'pppp'), 'jit_var_target': ('p', 'p')
  , 'jit_is_bigint': ('i', 'p'), 'jit_int_value': ('q', 'p')
  , 'jit_char_value': ('i', 'p'), 'jit_float_value': ('d', 'p')
  , 'jit_integer_compare': ('i', 'pp')
  }

OP = bytecode.OP
ROOT_VAR = bytecode.ROOT_VAR
NO_BRANCH = bytecode.NO_BRANCH


class _Emitter(object):
  '''Writes the LLVM function of one bytecode.'''
  def __init__(self, jit, symbol, bc):
    ir = jit.ir
    self.jit, self.ir = jit, ir
    self.symbol = symbol
    self.code = list(bc['code'])
    self.consts = list(bc['consts'])
    self.nregs, self.nvars, self.nstack = bc['nregs'], bc['nvars'], bc['nstack']
    self.ptr = ir.PointerType()
    self.i8, self.i16 = ir.IntType(8), ir.IntType(16)
    self.i32, self.i64 = ir.IntType(32), ir.IntType(64)
    self.f64 = ir.DoubleType()
    self.types = {
        'p': self.ptr, 'i': self.i32, 't': self.i16, 'q': self.i64
      , 'd': self.f64, 'v': ir.VoidType()
      }
    self.module = ir.Module(name=symbol)
    self.module.triple = jit.llvm.get_default_triple()
    self.helpers = {}
    for name, (result, args) in _HELPERS.items():
      fnty = ir.FunctionType(self.types[result], [self.types[a] for a in args])
      self.helpers[name] = ir.Function(self.module, fnty, name=name)
    self.fn = ir.Function(
        self.module, ir.FunctionType(self.i16, [self.ptr, self.ptr]), name=symbol
      )
    self.rts, self.C = self.fn.args
    self.rts.name, self.C.name = 'rts', 'C'
    self.blocks = {}   # pc -> block

  def call(self, name, *args):
    return self.builder.call(self.helpers[name], list(args))

  def const(self, k):
    '''The constant ``k`` of the bytecode, a pointer of the process.'''
    return self.ir.Constant(self.i64, self.consts[k]).inttoptr(self.ptr)

  def i32c(self, value):
    return self.ir.Constant(self.i32, value)

  def emit(self):
    ir = self.ir
    entry = self.fn.append_basic_block('entry')
    self.builder = ir.IRBuilder(entry)
    b = self.builder
    sizes = self.jit.sizes
    self.cursor = b.alloca(ir.ArrayType(self.i8, sizes['cursor']), name='cursor')
    self.cursor.align = 8
    vartype = ir.ArrayType(self.i8, sizes['variable'])
    self.vars = []
    for v in range(self.nvars + 1):     # one more: the temporary of a path
      var = b.alloca(vartype, name='var%d' % v)
      var.align = 8
      self.vars.append(var)
    self.tmpvar = self.vars[self.nvars]
    self.cells = [b.alloca(self.ptr, name='cell%d' % v) for v in range(self.nvars)]
    self.regs = [b.alloca(self.ptr, name='reg%d' % r) for r in range(self.nregs)]
    for reg in self.regs:
      b.store(ir.Constant(self.ptr, None), reg)
    self.args = b.alloca(ir.ArrayType(self.ptr, max(self.nstack, 1)), name='args')
    self.call('jit_cursor', self.C, self.cursor)
    for var in self.vars:
      self.call('jit_var_init', var)
    # The blocks: the entry of the code and every target of a case.
    starts = self.block_starts()
    for pc in starts:
      self.blocks[pc] = self.fn.append_basic_block('L%d' % pc)
    b.branch(self.blocks[0])
    for pc in starts:
      self.emit_block(pc)
    return self.module

  def decode(self, pc):
    '''The opcode at ``pc``, its operands, and the length of the unit.'''
    code = self.code
    op = code[pc]
    name = bytecode.OPCODES[op]
    if name == 'CASE_CONS':
      ntab = code[pc + 3]
      return name, code[pc + 1:pc + 4 + ntab], 4 + ntab
    if name == 'CASE_LIT':
      n = code[pc + 4]
      return name, code[pc + 1:pc + 5 + 3 * n], 5 + 3 * n
    fixed, count_at = bytecode._LENGTHS[name]
    length = 1 + fixed
    if count_at is not None:
      length += code[pc + 1 + count_at]
    return name, code[pc + 1:pc + length], length

  def block_starts(self):
    starts = {0}
    pc = 0
    while pc < len(self.code):
      name, ops, length = self.decode(pc)
      if name == 'CASE_CONS':
        starts.update(t for t in ops[3:] if t != NO_BRANCH)
      elif name == 'CASE_LIT':
        n = ops[3]
        starts.update(ops[4 + 3 * i + 2] for i in range(n))
      pc += length
    return sorted(starts)

  def emit_block(self, start):
    b = self.builder
    b.position_at_end(self.blocks[start])
    stack = []
    pc = start
    while True:
      name, ops, length = self.decode(pc)
      pc += length
      if self.emit_op(name, ops, stack):
        return      # the block ended in a return, an exempt or a case
      assert pc < len(self.code), 'the bytecode runs off its end'
      assert pc not in self.blocks, 'a block falls into another'

  def path(self, base, path, into):
    '''Binds the variable ``into`` to the end of ``path`` from ``base``.'''
    if base == ROOT_VAR:
      self.call('jit_bind_root', self.cursor, into, self.i32c(path[0]))
    else:
      self.call('jit_bind_var', into, self.vars[base], self.i32c(path[0]))
    for p in path[1:]:
      self.call('jit_bind_var', into, into, self.i32c(p))

  def store_args(self, values):
    '''Writes ``values`` into the argument buffer; returns its address.'''
    b = self.builder
    for i, value in enumerate(values):
      slot = b.gep(self.args, [self.i32c(0), self.i32c(i)], inbounds=True)
      b.store(value, slot)
    return b.gep(self.args, [self.i32c(0), self.i32c(0)], inbounds=True)

  def ret(self, tag):
    '''Destroys the variables and returns ``tag``.'''
    for var in self.vars:
      self.call('jit_var_destroy', var)
    self.builder.ret(tag)

  def emit_op(self, name, ops, stack):
    '''Emits one opcode; returns True when it ends the block.'''
    b = self.builder
    if name == 'LOAD_ROOT_SUCC':
      b.store(self.call('jit_root_succ', self.cursor, self.i32c(ops[1])), self.regs[ops[0]])
    elif name == 'LOAD_VAR_SUCC':
      b.store(self.call('jit_var_succ', self.vars[ops[1]], self.i32c(ops[2])), self.regs[ops[0]])
    elif name == 'BIND_ROOT':
      self.path(ROOT_VAR, ops[2:2 + ops[1]], self.vars[ops[0]])
    elif name == 'BIND_VAR':
      self.path(ops[1], ops[3:3 + ops[2]], self.vars[ops[0]])
    elif name == 'COPY_REG':
      b.store(b.load(self.regs[ops[1]]), self.regs[ops[0]])
    elif name == 'COPY_VAR':
      self.call('jit_var_copy', self.vars[ops[0]], self.vars[ops[1]])
    elif name == 'FREE_REG':
      b.store(self.call('jit_freshvar', self.rts), self.regs[ops[0]])
    elif name == 'PUSH_REG':
      stack.append(b.load(self.regs[ops[0]]))
    elif name == 'PUSH_VAR':
      stack.append(self.call('jit_rvalue', self.vars[ops[0]]))
    elif name == 'PUSH_ROOT':
      stack.append(self.call('jit_redex', self.cursor))
    elif name == 'PUSH_CONST':
      stack.append(self.const(ops[0]))
    elif name == 'PUSH_SUCC':
      if ops[0] == ROOT_VAR:
        stack.append(self.call('jit_root_succ', self.cursor, self.i32c(ops[1])))
      else:
        stack.append(self.call('jit_var_succ', self.vars[ops[0]], self.i32c(ops[1])))
    elif name == 'PUSH_PATH':
      self.path(ops[0], ops[2:2 + ops[1]], self.tmpvar)
      stack.append(self.call('jit_rvalue', self.tmpvar))
    elif name in ('MAKE', 'MAKE_PARTIAL'):
      n = ops[1]
      values = stack[len(stack) - n:]
      del stack[len(stack) - n:]
      helper = 'jit_make' if name == 'MAKE' else 'jit_make_partial'
      stack.append(self.call(helper, self.const(ops[0]), self.store_args(values), self.i32c(n)))
    elif name == 'MAKE_STRING':
      stack.append(self.call('jit_cstring', self.const(ops[0])))
    elif name == 'STORE_REG':
      b.store(stack.pop(), self.regs[ops[0]])
    elif name == 'STORE_VAR':
      v = ops[0]
      self.call('jit_store_var', self.vars[v], self.cells[v], stack.pop())
    elif name == 'SET_SUCC':
      n = ops[1]
      path = ops[2:2 + n]
      value = stack.pop()
      if n == 1:
        self.call('jit_set_succ', self.vars[ops[0]], self.i32c(path[0]), value)
      else:
        self.path(ops[0], path[:-1], self.tmpvar)
        self.call('jit_set_succ', self.tmpvar, self.i32c(path[-1]), value)
    elif name == 'EXEMPT':
      self.ret(self.call('jit_exempt', self.cursor))
      return True
    elif name == 'RET_REF':
      assert len(stack) == 1
      self.ret(self.call('jit_ret_ref', self.cursor, stack.pop()))
      return True
    elif name == 'RET_NODE':
      n = ops[1]
      assert len(stack) == n
      args = self.store_args(stack)
      del stack[:]
      self.ret(self.call('jit_ret_node', self.cursor, self.const(ops[0]), args, self.i32c(n)))
      return True
    elif name == 'RET_STRING':
      self.ret(self.call('jit_ret_string', self.cursor, self.const(ops[0])))
      return True
    elif name == 'CASE_CONS':
      assert not stack
      v, k, ntab = ops[0], ops[1], ops[2]
      table = ops[3:3 + ntab]
      tag = self.call('jit_hnf', self.rts, self.C, self.vars[v], self.const(k))
      default = self.fn.append_basic_block('ret_tag')
      switch = b.switch(tag, default)
      for t, target in enumerate(table):
        if target != NO_BRANCH:
          switch.add_case(self.ir.Constant(self.i16, t), self.blocks[target])
      b.position_at_end(default)
      self.ret(tag)
      return True
    elif name == 'CASE_LIT':
      assert not stack
      v, k, kind, n = ops[0], ops[1], ops[2], ops[3]
      entries = [tuple(ops[4 + 3 * i:7 + 3 * i]) for i in range(n)]
      tag = self.call('jit_hnf', self.rts, self.C, self.vars[v], self.const(k))
      is_status = b.icmp_signed('<', tag, self.ir.Constant(self.i16, T_CTOR))
      status = self.fn.append_basic_block('ret_status')
      value_block = self.fn.append_basic_block('value')
      b.cbranch(is_status, status, value_block)
      b.position_at_end(status)
      self.ret(tag)
      b.position_at_end(value_block)
      node = self.call('jit_var_target', self.vars[v])
      fail = self.fn.append_basic_block('no_branch')
      kind = chr(kind)
      if kind in 'ic':
        if kind == 'i':
          big = self.call('jit_is_bigint', node)
          is_big = b.icmp_unsigned('!=', big, self.i32c(0))
          small = self.fn.append_basic_block('small')
          b.cbranch(is_big, fail, small)
          b.position_at_end(small)
          value = self.call('jit_int_value', node)
        else:
          value = b.zext(self.call('jit_char_value', node), self.i64)
        switch = b.switch(value, fail)
        for lo, hi, target in entries:
          switch.add_case(self.ir.Constant(self.i64, (lo | (hi << 32))), self.blocks[target])
      elif kind == 'f':
        import struct
        value = self.call('jit_float_value', node)
        for lo, hi, target in entries:
          branch_value = struct.unpack('<d', struct.pack('<Q', lo | (hi << 32)))[0]
          hit = b.fcmp_ordered('==', value, self.ir.Constant(self.f64, branch_value))
          miss = self.fn.append_basic_block('miss')
          b.cbranch(hit, self.blocks[target], miss)
          b.position_at_end(miss)
        b.branch(fail)
      elif kind == 'p':
        for lo, hi, target in entries:
          other = self.const(lo | (hi << 32))
          same = b.icmp_signed('==', self.call('jit_integer_compare', node, other), self.i32c(0))
          miss = self.fn.append_basic_block('miss')
          b.cbranch(same, self.blocks[target], miss)
          b.position_at_end(miss)
        b.branch(fail)
      else:
        raise ValueError('a literal case of kind %r' % kind)
      b.position_at_end(fail)
      self.ret(self.call('jit_exempt', self.cursor))
      return True
    else:
      raise ValueError('an unknown opcode %r' % name)
    return False
