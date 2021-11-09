'''A repeating timer.'''

import threading

class RepeatingTimer(object):
  def __init__(self, seconds, target):
    self.is_running = False
    self.enabled = False
    self.seconds = seconds
    self.target = target
    self.timer = None

  def cancel(self):
    if self.timer is not None:
      self.enabled = False
      self.timer.cancel()

  def start(self):
    if not self.enabled and not self.is_running:
      self.enabled = True
      self._set_timer()

  def _set_timer(self):
    if self.enabled:
      self.timer = threading.Timer(self.seconds, self)
      self.timer.start()

  def __call__(self):
    self.is_running = True
    self.target()
    self.is_running = False
    self._set_timer()



