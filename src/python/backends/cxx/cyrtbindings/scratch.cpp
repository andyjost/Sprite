#include "pybind11/pybind11.h"
#include <iostream>
#include "cyrt/builtins.hpp"
#include "cyrt/graph/copy.hpp"
#include "cyrt/graph/equality.hpp"
#include "cyrt/graph/memory.hpp"
#include "cyrt/graph/node.hpp"
#include "cyrt/graph/walk.hpp"
#include "cyrt/misc/unionfind.hpp"
#include "cyrt/state/rts.hpp"

using namespace cyrt;
namespace py = pybind11;

namespace cyrt { namespace python
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

    Arg copy42 = copy_node(i42);
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

    Node * hello = cstring("Hello, World!");
    std::cout << hello->repr() << std::endl;
    std::cout << hello->str() << std::endl;
  }

  void unionfind()
  {
    UnionFind uf;
    std::cout << uf << std::endl;
    uf.unite(2,3);
    std::cout << uf << std::endl;
    uf.unite(4,3);
    std::cout << uf << std::endl;
    uf.unite(7,2);
    std::cout << uf << std::endl;
    uf.unite(8,1);
    std::cout << uf << std::endl;
  }

  void do_eval(Node * goal)
  {
    InterpreterState is;
    auto rts = RuntimeState(is, goal);
    size_t n=0;
    std::cout << "*** EVAL: ";
    while(true)
    {
      Expr result = rts.procD();
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

  tag_type main42_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    auto i42 = int_(42);
    _0->forward_to(i42);
    return T_FWD;
  }

  InfoTable const Main42_Info{
      /*tag*/        T_FUNC
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "main"
    , /*format*/     ""
    , /*step*/       &main42_step
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  struct Main42Node : Node1
  {
    static constexpr InfoTable const * static_info = &Main42_Info;
  };

  Node * make_zip_goal();
  Node * make_narrow_goal1();
  Node * make_narrow_goal2();
  Node * make_narrow_goal3();
  Node * make_narrow_goal4();
  Node * make_narrow_goal5();
  Node * make_narrow_goal6();
  Node * make_narrow_goal7();
  Node * make_partial_goal1();
  Node * make_partial_goal2();
  Node * make_partial_goal3();
  Node * make_partial_goal4();
  Node * make_partial_goal5();

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
    do_eval(pair(int_(4), choice(0, int_(1), int_(2))));
    Node * ch = choice(0, int_(1), int_(2));
    do_eval(pair(ch, ch));
    do_eval(free(0));
    do_eval(make_node<Main42Node>());
    do_eval(make_zip_goal());
    do_eval(make_narrow_goal1());
    do_eval(make_narrow_goal2());
    do_eval(make_narrow_goal3());
    do_eval(make_narrow_goal4());
    do_eval(make_narrow_goal5());
    do_eval(make_narrow_goal6());
    do_eval(make_narrow_goal7());
    do_eval(make_partial_goal1());
    do_eval(make_partial_goal2());
    do_eval(make_partial_goal3());
    do_eval(make_partial_goal4());
    do_eval(make_partial_goal5());
  }
  void register_scratch(py::module_ mod)
  {
    mod.def("copy", &copy);
    mod.def("equality", &equality);
    mod.def("eval", &eval);
    mod.def("hello", &hello);
    mod.def("show", &show);
    mod.def("unionfind", &unionfind);
    mod.def("walk", &walk);
  }
}}
