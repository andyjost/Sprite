'''
Code for reporting the status of Sprite over time.
'''
import collections, contextlib, logging, re
from ....utility import timer

logger = logging.getLogger(__name__)

class TelemetryData(object):
  def __init__(self, rts, full_report_interval=20):
    self.full_report_interval = full_report_interval
    self.report_count = 0
    self.rts = rts
    self.prev = None
    self._forks = 0
    self._eqconstr = 0
    self._values = 0
    self._constrlift = 0
    self._copyspine = 0
    self._pulltabs = 0
    self._enterD = 0
    self._enterN = 0
    self._enterS = 0
    self._enterhnf = 0
    self._iterD = 0
    self._iterhnf = 0

  @property
  def iterations_in_D(self):
    'The number of iterations in D.'
    return self._iterD

  @property
  def rewrite_steps(self):
    'The number of rewrite steps taken.'
    return self.rts.stepcounter.count

  @property
  def forks(self):
    'The number of times a configuration forked.'
    return self._forks

  @property
  def top_eqconstr(self):
    'The number of times an equational constraint was handled by D.'
    return self._eqconstr

  @property
  def num_values(self):
    'The number of values produced.'
    return self._values

  @property
  def num_values(self):
    'The number of constrint-lifting steps.'
    return self._constrlift

  @property
  def copy_spine(self):
    'The number of times a spine was copied.'
    return self._copyspine

  @property
  def pull_tab_steps(self):
    'The number of pull-tab steps.'
    return self._pulltabs

  @property
  def entries_to_D(self):
    'The number of entries to D.'
    return self._enterD

  @property
  def entries_to_N(self):
    'The number of entries to N.'
    return self._enterN

  @property
  def entries_to_S(self):
    'The number of entries to S.'
    return self._enterS

  @property
  def entries_to_hnf(self):
    'The number of entries to hnf.'
    return self._enterhnf

  @property
  def iterations_in_hnf(self):
    'The number of iterations in hnf.'
    return self._iterhnf

  P_GET_COUNT = re.compile('count\((\d+)\)')

  @property
  def next_cid(self):
    'The next available choice or variable ID'
    m = re.match(self.P_GET_COUNT, str(self.rts.idfactory))
    return int(str(m.group(1)))

  @property
  def next_sid(self):
    'The next available set ID'
    m = re.match(self.P_GET_COUNT, str(self.rts.setfactory))
    return int(str(m.group(1)))

  @property
  def number_of_queues(self):
    'The number of work queues in existence'
    return len(self.rts.qtable)

  @property
  def queue_stack_depth(self):
    'The set function nesting depth'
    return len(self.rts.qstack)

  @property
  def vtable_size(self):
    'The number of free variables in existence'
    return len(self.rts.vtable)

  @property
  def sftable_size(self):
    'The number of set functions currently being evaluated'
    return len(self.rts.sftable)

  ATTRS = sorted([k for k,v in locals().items() if isinstance(v, property)])

  def capture(self):
    '''Capture the telemetry information.'''
    return {attr: getattr(self, attr) for attr in self.ATTRS}

  def report(self, prev=None):
    '''Output a report to the log.'''
    is_full = self.report_count % self.full_report_interval == 0
    self.report_count += 1
    logger.info('------ Telemetry Report ------')
    data = self.capture()
    for line in self.show(data, full=is_full).split('\n'):
      logger.info(line)
    self.prev = data

  @staticmethod
  def _formatdiff(a, b):
    if a is None or not (b - a):
      return ''
    else:
      return '(%+8d)' % (b - a)

  def show(self, data, full=False):
    '''Show the telemetry information.'''
    fmt = '%-20s %-8s %-10s \'%s'
    def lines():
      for attr in self.ATTRS:
        attr_value = data[attr]
        attr_doc = getattr(type(self), attr).__doc__
        prev_value = None if self.prev is None else self.prev[attr]
        diff = self._formatdiff(prev_value, attr_value)
        if full or diff:
          yield fmt % (attr, attr_value, diff, attr_doc)
    return '\n'.join(lines())

def report_telemetry(rts, interval, generator):
  '''
  Sets a repeating timer to log telemetry every ``interval`` seconds while
  evaluating the generator.
  '''
  assert interval > 0
  t = timer.RepeatingTimer(interval, rts.telemetry.report)
  try:
    t.start()
    for value in generator:
      yield value
  finally:
    t.cancel()
