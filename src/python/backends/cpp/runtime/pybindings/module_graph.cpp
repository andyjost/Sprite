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
  InfoTable Int = {
      "Int"
    , 1
    , 0
    , nullptr
    , nullptr
    , nullptr
    , 0
    , "i"
    , sizeof(void*) * 2
    };

  InfoTable Pair = {
      "Pair"
    , 2
    , 0
    , nullptr
    , nullptr
    , nullptr
    , 0
    , "pp"
    , sizeof(void*) * 3
    };

  Node * _i42()
  {
    Arg args[1];
    args[0] = Arg(42);
    return Node::create(&Int, args);
  }

  Node * _i7()
  {
    Arg args[1];
    args[0] = Arg(7);
    return Node::create(&Int, args);
  }

  Node * pair(Node * lhs, Node * rhs)
  {
    Arg args[2] = {lhs, rhs};
    return Node::create(&Pair, args);
  }

  int hello()
  {
    Node * node = _i42();
    NodeU u{node};
    return u.int_->value;
  }

  void walk()
  {
    Node * node = _i42();
    for(auto && state = walk(node); state; ++state)
      std::cout << state.cursor().kind << "\n";
  }

  void equality()
  {
    Node * i42 = _i42();
    Node * i7 = _i7();
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
    Node * i42 = _i42();
    Node * i7 = _i7();
    Node * i42_7a = pair(i42, i7);

    Arg copy42 = copynode(i42);
    std::cout << "i42 == i42': " << logically_equal(i42, copy42.node) << "\n";

    Arg copyP = copygraph(i42_7a);
    std::cout << "(42,7) == (42,7)': " << logically_equal(i42_7a, copyP.node) << "\n";
  }

  void show()
  {
    Node * i42 = _i42();
    std::cout << i42->str() << std::endl;

    Node * cycle = pair(i42, nullptr);
    *cycle->successor(1) = cycle;
    std::cout << cycle->str() << std::endl;
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
