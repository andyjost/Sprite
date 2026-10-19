"""The Curry prompt: answer lines, types and session commands."""
from . import repl
from ..utility import program_warnings
import sys

HELP = """usage: python -m curry.tools.icy [COMMAND ...]

python -m curry or sprite-exec without a program starts this REPL too.
Evaluate Curry expressions and print curry.show(answer) per answer.
Commands: :load FILE, :reload, :eval EXPR, :type EXPR,
          :set FLAG VALUE, :set [+|-]FLAG, :quit.
:set accepts the session flags of curry.reset; :set alone lists them.
No value: *** No value found! (status 2).
Error: ERROR: msg (status 1). Suspension: *** Evaluation suspended! (status 1).
IO () prints no result. At the prompt errors keep the session;
:quit or EOF returns the last evaluation status (initially 0).
"""


def main(args):
  if args in (['-h'], ['--help']):
    print(HELP, end='')
    return
  with program_warnings():
    repl.REPL(args).enter()


if __name__ == '__main__':
  main(sys.argv[1:])
