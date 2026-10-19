"""Console entry points shared by packaged installations."""
import sys


def execute():
  from curry.__main__ import main
  main('sprite-exec', sys.argv[1:])


def make():
  from curry.tools.make import main
  main('sprite-make', sys.argv[1:])
