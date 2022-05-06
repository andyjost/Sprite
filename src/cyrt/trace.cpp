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

  void Trace::indent(Queue * Q)
  {
    if(!Q)
      Q = this->rts->Q();
    assert(Q);
    this->indent_value = this->indents[Q]++;
  }

  void Trace::dedent(Queue * Q)
  {
    if(!Q)
      Q = this->rts->Q();
    assert(Q);
    this->indent_value = --this->indents[Q];
  }

  void Trace::enter_rewrite(Cursor cursor)
  {
    this->indent();
    auto * Q = this->rts->Q();
    if(this->prevexprs[Q] != cursor.fwd_chain_target().id())
    {
      tout << "S <<< ";
      this->show_indent();
      tout << cursor.str() << "\n";
    }
  }

  void Trace::exit_rewrite(Cursor cursor)
  {
    this->dedent();
    tout << "S >>> ";
    this->show_indent();
    tout << cursor.str() << "\n";
    auto * Q = this->rts->Q();
    this->prevexprs[Q] = cursor.fwd_chain_target().id();
  }

  void Trace::failed(Queue * Q)
  {
    tout << "Q ::: failed config dropped from ";
    this->show_queue(Q);
    tout << "\n";
  }

  void Trace::yield(Expr value)
  {
    tout << "Y ::: " << Cursor(value.arg, value.kind).str() << "\n";
  }

  void Trace::activate_queue(Queue * Q)
  {
    tout << "Q ::: switching to ";
    this->show_queue(Q);
    tout << "\n";
  }

  TraceFork Trace::guard_fork(Queue * Q)
  {
    return TraceFork(this, Q);
  }

  void Trace::show_queue(Queue * Q)
  {
    if(!Q)
      Q = this->rts->Q();
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

  void Trace::show_indent()
  {
    for(size_t i=0; i<this->indent_value; ++i)
      tout << "  ";
  }

  size_t Trace::qid(Queue * Q)
  {
    for(size_t i=0; i<this->rts->qstack.size(); ++i)
    {
      if(Q == this->rts->qstack[i])
        return i;
    }
    assert(false);
    return -1;
  }

  TraceFork::TraceFork(Trace * trace, Queue * Q)
    : trace(trace), Q(Q ? Q : trace->rts->Q())
  {
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

  PositionKey Trace::enter_position(Scan const & scan)
  {
    Queue * Q = this->rts->Q();
    auto n = scan.size();
    auto && frame = scan.frames()[n-2];
    this->indent(Q);
    PositionKey key(frame.cur.fwd_chain_target().id(), frame.index);
    if(this->prevpaths[Q] != key)
    {
      tout << "I ::: ";
      this->show_indent();
      tout << "at path=[" << frame.index << "] of " << frame.cur.str() << "\n";
    }
    return key;
  }

  void Trace::exit_position(PositionKey const & key)
  {
    Queue * Q = this->rts->Q();
    this->prevpaths[Q] = key;
    this->dedent(Q);
  }
}
