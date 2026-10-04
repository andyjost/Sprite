#pragma once
#include "cyrt/fwd.hpp"
#include "cyrt/graph/cursor.hpp"
#include "cyrt/state/scan.hpp"
#include <string>
#include <tuple>
#include <unordered_map>
#include <vector>

namespace cyrt
{
  using PositionKey = std::tuple<void *, index_type>;

  struct TraceFork
  {
    TraceFork(Trace *, Queue const *);
    TraceFork(TraceFork const &) = delete;
    TraceFork(TraceFork &&);
    TraceFork & operator=(TraceFork const &) = delete;
    TraceFork & operator=(TraceFork &&) = delete;
    ~TraceFork();
  private:
    Trace *       trace;
    Queue const * Q;
    std::string msg;
  };

  struct Trace
  {
    Trace(RuntimeState & rts) : rts(&rts) {}

    void indent(Queue const *);
    void dedent(Queue const *);
    void enter_rewrite(Queue const *, Cursor);
    void exit_rewrite(Queue const *, Cursor);
    void failed(Queue const *);
    void yield(Expr);
    void activate_queue(Queue const *);
    friend TraceFork;
    TraceFork guard_fork(Queue const *);
    PositionKey enter_position(Queue const *, Scan const &);
    void exit_position(Queue const *, PositionKey const &);
    void show_queue(Queue const *, size_t skip=0);
    void show_indent(Queue const *, size_t extra=0);
    size_t qid(Queue const *);
  private:
    RuntimeState * rts;
    size_t indent_value = 0;
    // Keyed by the serial number of the queue: a queue is freed when its
    // set function is done, and another may take its address.
    std::unordered_map<size_t, int>         indents;
    std::unordered_map<size_t, void *>      prevexprs;
    std::unordered_map<size_t, PositionKey> prevpaths;
  };
}
