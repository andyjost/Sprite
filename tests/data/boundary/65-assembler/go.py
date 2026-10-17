'''
A one-pass assembler whose forward references are logic variables, driven
from Python (the public API).

assembler of PAKCS crosses the boundary by import.  Its main assembles a
program of two labels and two jumps: a jump to a label defined later gets a
free variable for its address, and the variable is bound when the label is
reached.  The driver then builds the same program in Python: a list of user
constructors, each instruction the term M.Jump(M.L1).  A second program
jumps forward twice.
'''
import os
import curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
M = curry.import_('assembler')

# main = assembler [Label L0, Jump L1, Jump L0, Label L1] [] 0.  Jump is
# the opcode 9 and its address: L1 is at 4 (after two jumps of two words),
# L0 at 0.
print('main ->', list(curry.eval(M.main)))

# The same program built in Python.  The symbol table is the empty list
# and the start address 0.
program = [M.Label(M.L0), M.Jump(M.L1), M.Jump(M.L0), M.Label(M.L1)]
print('assembler (built in Python) ->', list(curry.eval(M.assembler(program, [], 0))))

# A second program: two forward jumps to L2, then a backward jump to L1.
# L1 is at 0, L2 at 4; the jump to L1 is the last instruction.
program = [M.Label(M.L1), M.Jump(M.L2), M.Jump(M.L2), M.Label(M.L2), M.Jump(M.L1)]
print('assembler (two forward jumps) ->', list(curry.eval(M.assembler(program, [], 0))))

# A jump to a label that is never defined: the address stays a free
# variable, which the value shows as an unbound variable.
program = [M.Jump(M.L3)]
print('assembler (undefined label) ->',
  [curry.show(v) for v in curry.eval(M.assembler(program, [], 0))])
