'''
Code for reporting the status of Sprite over time.
'''
import collections, contextlib, logging, re
from ....utility import timer

logger = logging.getLogger(__name__)

class TelemetryData(object):
  def __init__(self, rts):
    self.rts = rts

  @property
  def stepcount(self):
    'The number of steps taken.'
    return self.rts.stepcounter.count

  P_GET_COUNT = re.compile('count\((\d+)\)')

  @property
  def next_cid(self):
    'The next available choice or variable ID'
    m = re.match(self.P_GET_COUNT, str(self.rts.idfactory))
    return str(m.group(1))

  @property
  def next_sid(self):
    'The next available set ID'
    m = re.match(self.P_GET_COUNT, str(self.rts.setfactory))
    return str(m.group(1))

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

  ATTRS = sorted([
      attr for attr in locals().keys() if isinstance(locals()[attr], property)
    ])

  def report(self):
    logger.info('------ Telemetry Report ------')
    for line in str(self).split('\n'):
      logger.info(line)

  def __str__(self):
    fmt = '%-20s %-8s \'%s'
    def lines():
      for attr in self.ATTRS:
        attr_value = getattr(self, attr)
        attr_doc = getattr(type(self), attr).__doc__
        yield fmt % (attr, attr_value, attr_doc)
    return '\n'.join(lines())


def report_telemetry(rts, interval, generator):
  assert interval > 0
  tel = TelemetryData(rts)
  t = timer.RepeatingTimer(interval, tel.report)
  try:
    t.start()
    for value in generator:
      yield value
  finally:
    t.cancel()
