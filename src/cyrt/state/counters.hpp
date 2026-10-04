#pragma once
#include <cstddef>

// The scheduler counters of an instrumented build.  They exist when the
// runtime is compiled with -DSPRITE_SCHEDULER_COUNTERS (make COUNTERS=1).  A
// plain build has none of this, and nothing below is referenced there.
//
// The counters answer three questions about the work queue of an evaluation
// (see the parallel-evaluation notes): how much of the work is serial, how
// long a configuration lives, and how much work is shared between
// configurations.
//
//   steps_serial    Steps taken while the outermost queue held exactly one
//                   configuration.  A thread pool over that queue has nothing
//                   to run in parallel during these steps.
//   steps_nested    Steps taken by a nested scheduler, inside a set function.
//   steps_shared    Steps whose redex another configuration created.  Every
//                   node carries the serial number of the configuration whose
//                   step allocated it (see graph/gc/wdgc.cpp).  A redex made
//                   by an ancestor before a fork, or by a sibling, is work
//                   that more than one configuration reaches; this is an
//                   upper bound of the work a copied-world design would
//                   duplicate.  A node made outside the scheduler (the goal
//                   built by Python) has no creator and never counts.
//   queue_max       The largest size of the outermost queue.
//   ended, end_steps, lifetimes
//                   Per queue kind (the outermost queue, or a nested one) and
//                   per end (value, failure, fork): the configurations that
//                   ended that way and the steps they took.  The lifetime of
//                   a configuration is its own step count (Configuration::
//                   steps), which includes the steps of the set functions it
//                   evaluated.  The histogram keeps exact counts below EXACT
//                   steps and one bucket per power of two above.
//
// A configuration still in the outermost queue when the counters are read
// has not ended; the bindings report those separately (see graph.cpp).

namespace cyrt
{
  struct StepHistogram
  {
    // Exact counts for 0 .. EXACT-1 steps.
    static constexpr size_t EXACT = 1024;
    // coarse[k] counts lifetimes in [2^k, 2^(k+1)) for k >= log2(EXACT).
    static constexpr size_t COARSE = 64;

    size_t count = 0;
    size_t sum = 0;
    size_t max = 0;
    size_t exact[EXACT] = {};
    size_t coarse[COARSE] = {};

    void add(size_t steps)
    {
      ++this->count;
      this->sum += steps;
      if(steps > this->max)
        this->max = steps;
      if(steps < EXACT)
        ++this->exact[steps];
      else
        ++this->coarse[63 - __builtin_clzll(steps)];
    }
  };

  // Why a configuration left its queue.
  enum ConfigurationEnd : unsigned
  {
    END_VALUE = 0, END_FAILURE = 1, END_FORK = 2, N_ENDS = 3
  };

  struct SchedulerCounters
  {
    size_t steps_serial = 0;
    size_t steps_nested = 0;
    size_t steps_shared = 0;
    size_t queue_max = 0;
    // Index 0: the outermost queue.  Index 1: a nested queue.
    size_t ended[2][N_ENDS] = {};
    size_t end_steps[2][N_ENDS] = {};
    StepHistogram lifetimes[2];

    void end_configuration(bool nested, ConfigurationEnd end, size_t steps)
    {
      ++this->ended[nested][end];
      this->end_steps[nested][end] += steps;
      this->lifetimes[nested].add(steps);
    }
  };
}
