'''Tests running the Kiel code examples.'''
import cytest # from ./lib; must be first

class TestKiel(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/kiel/'
  PRINT_SKIPPED_GOALS = True
  # To determine the curent set of failures, clear this list and run.
  SKIP = [
      'Imports'
    , 'account'
    , 'accountport'
    , 'addnamedserver'
    , 'addserver'
    , 'addtimeoutserver'
    , 'allsols'
    , 'arithseq'
    , 'assembler'
    , 'best'
    , 'calc'
    , 'checkbutton'
    , 'chords'
    , 'circuit'
    , 'colormap'
    , 'colormap_nd'
    , 'config'
    , 'counter'
    , 'counter_controlled'
    , 'daVinciTest'
    , 'diamond'
    , 'digit'
    , 'england'
    , 'escher_cond'
    , 'events'
    , 'expr_parser'
    , 'family_con'
    , 'family_nd'
    , 'family_rel'
    , 'fractal'
    , 'hello'
    , 'higher'
    , 'hilbert'
    , 'horseman'
    , 'httpget'
    , 'infresiduate'
    , 'inputmask'
    , 'iodemo'
    , 'last'
    , 'magicseries'
    , 'mail'
    , 'mailsearch'
    , 'member'
    , 'menu'
    , 'mergesort'
    , 'mortgage'
    , 'nameserver'
    , 'nats'
    , 'palindrome'
    , 'philo'
    , 'prolog'
    , 'psort'
    , 'putModuleHead'
    , 'queens'
    , 'radiotraffic'
    , 'relational'
    , 'rigidadd'
    , 'scrollbar'
    , 'search'
    , 'sema'
    , 'sierpinski'
    , 'smm'
    , 'sportsdb'
    , 'sudoku'
    , 'talk'
    , 'temperature'
    , 'textappend'
    , 'textstyledappend'
    ]

