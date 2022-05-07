#include <cassert>
#include "cyrt/inspect.hpp"
#include "cyrt/state/rts.hpp"
#include "cyrt/trace.hpp"
#include <iostream>
#include <sstream>

namespace cyrt
{
  // Trace output stream.
  static std::ostream & tout = std::cout;

  void Trace::indent(Queue const * Q)
  {
    assert(Q);
    this->indent_value = this->indents[Q]++;
  }

  void Trace::dedent(Queue const * Q)
  {
    assert(Q);
    this->indent_value = --this->indents[Q];
  }

  void Trace::enter_rewrite(Queue const * Q, Cursor cursor)
  {
    assert(Q);
    this->indent(Q);
    if(this->prevexprs[Q] != cursor.fwd_chain_target().id())
    {
      tout << "S <<< ";
      this->show_indent(Q);
      tout << cursor.str(PLAIN_FREEVARS) << "\n";
    }
  }

  void Trace::exit_rewrite(Queue const * Q, Cursor cursor)
  {
    this->dedent(Q);
    tout << "S >>> ";
    this->show_indent(Q);
    tout << cursor.str(PLAIN_FREEVARS) << "\n";
    this->prevexprs[Q] = cursor.fwd_chain_target().id();
  }

  void Trace::failed(Queue const * Q)
  {
    assert(Q);
    tout << "Q ::: failed config dropped from ";
    this->show_queue(Q);
    tout << "\n";
  }

  void Trace::yield(Expr value)
  {
    tout << "Y ::: " << Cursor(value.arg, value.kind).str() << "\n";
  }

  void Trace::activate_queue(Queue const * Q)
  {
    assert(Q);
    tout << "Q ::: switching to ";
    this->show_queue(Q);
    tout << "\n";
  }

  TraceFork Trace::guard_fork(Queue const * Q)
  {
    return TraceFork(this, Q);
  }

  void Trace::show_queue(Queue const * Q)
  {
    assert(Q);
    tout << "queue " << this->qid(Q) << ": [";
    bool first = true;
    for(auto * C: *Q)
    {
      if(first) first = false; else tout << ", ";
      tout << C->fingerprint;
    }
    tout << "]";
  }

  void Trace::show_indent(Queue const * Q, size_t extra)
  {
    assert(Q);
    size_t n = this->indent_value + extra;
    for(size_t i=0; i<n; ++i)
      tout << "  ";
  }

  size_t Trace::qid(Queue const * Q)
  {
    for(size_t i=0; i<this->rts->qstack.size(); ++i)
    {
      if(Q == this->rts->qstack[i])
        return i;
    }
    assert(false);
    return -1;
  }

  TraceFork::TraceFork(Trace * trace, Queue const * Q)
    : trace(trace), Q(Q)
  {
    assert(Q);
    xid_type cid = this->Q->front()->grp_id();
    std::stringstream ss;
    ss << "Q ::: fork " << Q->front()->fingerprint << " on cid=" << cid << " appending to ";
    this->msg = ss.str();
  }

  TraceFork::TraceFork(TraceFork && old)
    : trace(old.trace), Q(old.Q), msg(std::move(old.msg))
    { old.trace = nullptr; }

  TraceFork::~TraceFork()
  {
    if(this->trace)
    {
      tout << msg;
      trace->show_queue(this->Q);
      tout << "\n";
    }
  }

  PositionKey Trace::enter_position(Queue const * Q, Scan const & scan)
  {
    assert(Q);
    auto n = scan.size();
    auto && frame = scan.frames()[n-2];
    PositionKey key(frame.cur.fwd_chain_target().id(), frame.index);
    if(this->prevpaths[Q] != key)
    {
      tout << "I ::: ";
      this->show_indent(Q, 1);
      tout << "at path=[" << frame.index << "] of " << frame.cur.str(PLAIN_FREEVARS) << "\n";
    }
    return key;
  }

  void Trace::exit_position(Queue const * Q, PositionKey const & key)
  {
    assert(Q);
    this->prevpaths[Q] = key;
  }
}
