from . import repl
import sys

def main(args):
  repl.REPL(args).enter()

if __name__ == '__main__':
  main(sys.argv[1:])
