"""The Curry prompt: answer lines, types and session commands."""
from . import repl
from ..utility import program_warnings
import sys

HELP = """usage: sprite [OPTION ...] [COMMAND ...] [-- ARG ...]

python -m curry or sprite-exec without a program starts this REPL too.
Evaluate Curry expressions and print curry.show(answer) per answer.
Commands: :load FILE, :add MODULE, :reload, :eval EXPR, :type EXPR,
          :set FLAG VALUE, :set [+|-]FLAG, :save [EXPR], :quit.
:set accepts the session flags of curry.reset; :set alone lists them.
PAKCS options: --nocypm, --noreadline, -q; :set v0 through v4,
:set +/-time, :set parser -Wnone, :set rts -T, :set path PATH, :set args ARGS.
Version probes: --compiler-name --numeric-version --base-version.
No value: *** No value found! (status 2).
Error: ERROR: msg (status 1). Suspension: *** Evaluation suspended! (status 1).
IO () prints no result. At the prompt errors keep the session;
:quit or EOF returns the last evaluation status (initially 0).
"""


def main(args):
  args = list(args)
  probes = ('--compiler-name', '--numeric-version', '--base-version')
  requested = []
  while args:
    if args[0] in probes:
      requested.append(args.pop(0))
    elif args[0] in ('--nocypm', '--noreadline', '-q'):
      # CPM supplies CURRYPATH; there is no startup banner to disable.
      args.pop(0)
    else:
      break
  if requested:
    import curry
    distribution = curry.import_('Curry.Compiler.Distribution')
    version = '.'.join(str(curry.eval(distribution[name]).one()) for name in
        ('curryCompilerMajorVersion', 'curryCompilerMinorVersion',
         'curryCompilerRevisionVersion'))
    values = dict(zip(probes, ('sprite', version, curry.config.currylib_version())))
    for arg in requested:
      print(values[arg])
    return
  if args in (['-h'], ['--help']):
    print(HELP, end='')
    return
  with program_warnings():
    session = repl.REPL(args)
    if not session.batch:
      session.enter()
    elif session.status:
      sys.exit(session.status)


if __name__ == '__main__':
  main(sys.argv[1:])
