'''Support for colored text output.'''
import sys
import contextlib

# Text styles and colors.
NORMAL     = 0
BOLD       = 1
LIGHT      = 2
ITALICIZED = 3
UNDERLINED = 4
BLINKING   = 5

FG_BLACK  = 30
FG_RED    = 31
FG_GREEN  = 32
FG_YELLOW = 33
FG_BLUE   = 34
FG_PURPLE = 35
FG_CYAN   = 36
FG_WHITE  = 37

BG_BLACK  = 40
BG_RED    = 41
BG_GREEN  = 42
BG_YELLOW = 43
BG_BLUE   = 44
BG_PURPLE = 45
BG_CYAN   = 46
BG_WHITE  = 47

@contextlib.contextmanager
def colored(style=NORMAL, fg=FG_BLACK, bg=None, stream=sys.stdout):
  if not stream.isatty():
    yield
  else:
    if bg is None:
      stream.write('\033[%s;%sm' % (style, fg))
    else:
      stream.write('\033[%s;%s;%sm' % (style, fg, bg))
    try:
      yield
    finally:
      sys.stdout.write('\033[0;0m')

def color(string, style=NORMAL, fg=FG_BLACK, bg=None, stream=sys.stdout):
  if not stream.isatty():
    return string
  else:
    if bg is None:
      intro = '\033[%s;%sm' % (style, fg)
    else:
      intro = '\033[%s;%s;%sm' % (style, fg, bg)
    reset = '\033[0;0m'
    return '%s%s%s' % (intro, string, reset)
