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
    TraceFork(Trace *, Queue *);
    TraceFork(TraceFork const &) = delete;
    TraceFork(TraceFork &&);
    TraceFork & operator=(TraceFork const &) = delete;
    TraceFork & operator=(TraceFork &&) = delete;
    ~TraceFork();
  private:
    Trace * trace;
    Queue * Q;
    std::string msg;
  };

  struct Trace
  {
    Trace(RuntimeState & rts) : rts(&rts) {}

    void indent(Queue * = nullptr);
    void dedent(Queue * = nullptr);
    void enter_rewrite(Cursor);
    void exit_rewrite(Cursor);
    void failed(Queue * = nullptr);
    void yield(Expr);
    void activate_queue(Queue * = nullptr);
    friend TraceFork;
    TraceFork guard_fork(Queue * = nullptr);
    PositionKey enter_position(Scan const &);
    void exit_position(PositionKey const &);
    void show_queue(Queue *);
    void show_indent();
    size_t qid(Queue *);
  private:
    RuntimeState * rts;
    size_t indent_value = 0;
    std::unordered_map<Queue *, size_t>      indents;
    std::unordered_map<Queue *, void *>      prevexprs;
    std::unordered_map<Queue *, PositionKey> prevpaths;
  };
}
