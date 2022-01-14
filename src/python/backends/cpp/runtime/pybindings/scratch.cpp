#include "pybind11/pybind11.h"
#include <iostream>
#include "sprite/builtins.hpp"
#include "sprite/fairscheme.hpp"
#include "sprite/graph/copy.hpp"
#include "sprite/graph/equality.hpp"
#include "sprite/graph/memory.hpp"
#include "sprite/graph/node.hpp"
#include "sprite/graph/walk.hpp"

using namespace sprite;
namespace py = pybind11;

namespace sprite { namespace python
{
  int hello()
  {
    Node * node = int_(42);
    NodeU u{node};
    return u.int_->value;
  }

  void walk()
  {
    Node * node = int_(42);
    for(auto && state = walk(node); state; ++state)
      std::cout << state.cursor().kind << "\n";
  }

  void equality()
  {
    Node * i42 = int_(42);
    Node * i7 = int_(7);
    Node * i42_7a = pair(i42, i7);
    Node * i42_7b = pair(i42, i7);
    Node * i7_7 = pair(i7, i7);

    std::cout << "i42 == i42: " << logically_equal(i42, i42) << "\n";
    std::cout << "u42 == u42: " << logically_equal(i42->successor(0), i42->successor(0)) << "\n";
    std::cout << "i42 == i7: " << logically_equal(i42, i7) << "\n";
    std::cout << "(42,7) == (42,7): " << logically_equal(i42_7a, i42_7a) << "\n";
    std::cout << "(42,7) == (42,7)': " << logically_equal(i42_7a, i42_7b) << "\n";
    std::cout << "(42,7) == (7,7): " << logically_equal(i42_7a, i7_7) << "\n";
  }

  void copy()
  {
    Node * i42 = int_(42);
    Node * i7 = int_(7);
    Node * i42_7a = pair(i42, i7);

    Arg copy42 = copy_node(i42).arg;
    std::cout << "i42 == i42': " << logically_equal(i42, copy42.node) << "\n";

    Arg copyP = copy_graph(i42_7a).arg;
    std::cout << "(42,7) == (42,7)': " << logically_equal(i42_7a, copyP.node) << "\n";
  }

  void show()
  {
    Node * i42 = int_(42);
    std::cout << i42->str() << std::endl;

    Node * cycle = pair(i42, nullptr);
    *cycle->successor(1) = cycle;
    std::cout << cycle->repr() << std::endl;

    Node * p = pair(i42, i42);
    std::cout << p->str() << std::endl;

    Node * a = cons(i42, cons(int_(-7), cons(i42, nil())));
    std::cout << a->repr() << std::endl;
    std::cout << a->str() << std::endl;

    Node * b = cons(char_('h'), cons(char_('i'), cons(char_('!'), nil())));
    std::cout << b->repr() << std::endl;
    std::cout << b->str() << std::endl;

    Node * c = cons(int_(42), free(0));
    std::cout << c->repr() << std::endl;
    std::cout << c->str() << std::endl;
  }

  void do_eval(Node * goal)
  {
    InterpreterState is;
    auto rts = RuntimeState(is, goal);
    auto algo = FairSchemeAlgo(&rts);
    size_t n=0;
    std::cout << "*** EVAL: ";
    while(true)
    {
      Expr result = algo.eval();
      if(result)
      {
        ++n;
        std::cout << result.arg.node->str() << ' ';
      }
      else
        break;
    }
    if(!n) std::cout << "No result!";
    std::cout << std::endl;
  }

  void eval()
  {
    do_eval(int_(42));
    do_eval(pair(int_(42), int_(7)));
    do_eval(fwd(int_(5)));
    do_eval(fwd(fwd(int_(6))));
    do_eval(fwd(fwd(fwd(int_(7)))));
    do_eval(fwd(pair(fwd(int_(42)), int_(7))));
    do_eval(fail());
    do_eval(fwd(fail()));
    do_eval(pair(int_(3), fail()));
    do_eval(pair(int_(3), fwd(fail())));
    do_eval(choice(0, int_(1), int_(2)));
    // do_eval(pair(int_(4), choice(0, int_(1), int_(2))));
  }

  void register_scratch(py::module_ mod)
  {
    mod.def("hello", &hello);
    mod.def("walk", &walk);
    mod.def("equality", &equality);
    mod.def("copy", &copy);
    mod.def("show", &show);
    mod.def("eval", &eval);
  }
}}
