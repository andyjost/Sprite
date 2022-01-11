#include "pybind11/pybind11.h"
#include "sprite/builtins.hpp"
#include "sprite/graph/equality.hpp"
#include "sprite/graph/node.hpp"
#include "sprite/graph/copy.hpp"
#include "sprite/graph/memory.hpp"
#include "sprite/graph/walk.hpp"
#include <iostream>

using namespace sprite;
namespace py = pybind11;

namespace sprite { namespace python
{
  Node * int_(int value)
  {
    Arg args[1];
    args[0] = Arg(value);
    return Node::create(&Int_Info, args);
  }

  Node * char_(char c)
  {
    Arg args[1];
    args[0] = Arg(c);
    return Node::create(&Char_Info, args);
  }

  Node * pair(Node * lhs, Node * rhs)
  {
    Arg args[2] = {lhs, rhs};
    return Node::create(&Pair_Info, args);
  }

  Node * cons(Node * head, Node * tail)
  {
    Arg args[2] = {head, tail};
    return Node::create(&Cons_Info, args);
  }

  Node * nil()
  {
    return Node::create(&Nil_Info, nullptr);
  }

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

    Arg copy42 = copynode(i42);
    std::cout << "i42 == i42': " << logically_equal(i42, copy42.node) << "\n";

    Arg copyP = copygraph(i42_7a);
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
  }

  void register_graph(py::module_ mod)
  {
    mod.def("hello", &hello);
    mod.def("walk", &walk);
    mod.def("equality", &equality);
    mod.def("copy", &copy);
    mod.def("show", &show);
  }
}}
