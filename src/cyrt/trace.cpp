#include <cassert>
#include "cyrt/trace.hpp"
#include "cyrt/state/rts.hpp"
#include <iostream>
#include <sstream>

namespace cyrt
{
  static std::ostream & trace_out = std::cout;

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
    if(this->prevexprs[Q] != cursor.id())
    {
      trace_out << "S <<< ";
      this->show_indent();
      trace_out << cursor.str() << std::endl;
    }
  }

  void Trace::exit_rewrite(Cursor cursor)
  {
    this->dedent();
    trace_out << "S >>> ";
    this->show_indent();
    trace_out << cursor.str() << std::endl;
    auto * Q = this->rts->Q();
    this->prevexprs[Q] = cursor.id();
  }

  void Trace::failed(Queue * Q)
  {
    trace_out << "Q ::: failed config dropped from ";
    this->show_queue(Q);
    trace_out << std::endl;
  }

  void Trace::yield(Expr value)
  {
    trace_out << "Y ::: " << Cursor(value.arg, value.kind).str() << std::endl;
  }

  void Trace::activate_queue(Queue * Q)
  {
    trace_out << "Q ::: switching to ";
    this->show_queue(Q);
    trace_out << std::endl;
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
    trace_out << "queue " << this->qid(Q) << ": [";
    bool first = true;
    for(auto * C: *Q)
    {
      if(first) first = false; else trace_out << ", ";
      trace_out << C->fingerprint;
    }
    trace_out << "]";
  }

  void Trace::show_indent()
  {
    for(size_t i=0; i<this->indent_value; ++i)
      trace_out << "  ";
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
      trace_out << msg;
      trace->show_queue(this->Q);
      trace_out << std::endl;
    }
  }

  PositionKey Trace::enter_position(Scan const & scan)
  {
    Queue * Q = this->rts->Q();
    auto n = scan.size();
    auto && frame = scan.frames()[n-2];
    this->indent(Q);
    PositionKey key(frame.cur.id(), frame.index);
    if(this->prevpaths[Q] != key)
    {
      trace_out << "I ::: ";
      this->show_indent();
      trace_out << "at path=[" << frame.index << "] of " << frame.cur.str() << std::endl;
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
