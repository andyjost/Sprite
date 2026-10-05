'''
Scheduling tasks fed from Python data.

Passes a list of tasks and a list of precedences from Python to the Curry
function ``schedule`` together with a horizon.  Curry states the constraints.
The runtime finds a schedule that meets them.  Python tries horizons upward,
takes the first schedule of each, reports the shortest horizon that has one,
and draws a Gantt chart.

Usage: python go.py
'''
import os
import curry

# Find Sched.curry next to this file, whatever the working directory is.
curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import Sched

# The tasks: (name, duration, resource).  Two tasks that share a resource
# cannot overlap.
TASKS = [
    ('mix',   2, 'bowl'),
    ('bake',  3, 'oven'),
    ('frost', 1, 'bowl'),
    ('cool',  2, 'rack'),
    ('pack',  1, 'table'),
  ]

# The precedences: (before, after).  The first task ends before the second
# starts.
PRECEDENCES = [
    ('mix', 'bake'),
    ('bake', 'cool'),
    ('cool', 'frost'),
    ('frost', 'pack'),
  ]

def first_schedule(tasks, precedences, horizon):
  '''The first schedule that fits the horizon, or None when there is none.

  One Curry call is a generator of schedules.  next() takes the first one and
  stops the search.  A horizon with no schedule yields zero values, which is
  not an error.
  '''
  # curry.eval converts the tuples, lists, strs and ints by the parameter
  # types of schedule.
  values = curry.eval(Sched.schedule, tasks, precedences, horizon,
                      converter='topython')
  return next(values, None)

def by_start(tasks, schedule):
  '''The tasks in order of their start slot, each with its start.'''
  start = dict(schedule)
  return sorted(((start[name], name, duration, resource)
                 for name, duration, resource in tasks))

def chart(tasks, schedule, horizon):
  '''Draws the schedule as one row per task over the slots of the horizon.'''
  width = max(len(name) for name, _, _ in tasks)
  lines = ['%-*s  %s' % (width, 'slot', ''.join(str(t % 10) for t in range(horizon)))]
  for start, name, duration, resource in by_start(tasks, schedule):
    row = ''.join('#' if start <= t < start + duration else '.' for t in range(horizon))
    lines.append('%-*s  %s  %s' % (width, name, row, resource))
  return '\n'.join(lines)

def main():
  print('tasks: ' + ', '.join('%s %d %s' % task for task in TASKS))
  print('precedences: ' + ', '.join('%s < %s' % pair for pair in PRECEDENCES))
  # No schedule is shorter than the longest task.  The tasks one after the
  # other always fit the sum of the durations.
  longest = max(duration for _, duration, _ in TASKS)
  total = sum(duration for _, duration, _ in TASKS)
  for horizon in range(longest, total + 1):
    schedule = first_schedule(TASKS, PRECEDENCES, horizon)
    if schedule is None:
      print('horizon %d: none' % horizon)
      continue
    print('horizon %d: %s' % (horizon, ' '.join(
        '%s@%d' % (name, start) for start, name, _, _ in by_start(TASKS, schedule))))
    print(chart(TASKS, schedule, horizon))
    break
  else:
    print('no schedule up to horizon %d' % total)

if __name__ == '__main__':
  main()
