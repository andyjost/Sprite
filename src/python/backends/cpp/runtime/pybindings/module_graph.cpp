#include "pybind11/pybind11.h"
#include "sprite/graph/equality.hpp"
#include "sprite/graph/node.hpp"
#include "sprite/graph/raw.hpp"
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
    , nullptr
    , 0
    , "i"
    , sizeof(void*) * 2
    };

  int hello()
  {
    Arg args[1];
    args[0] = Arg(42);
    Node * node = Node::create(&Int, args);
    NodeU u{node};
    return u.int_->value;
  }

  void walk()
  {
    Arg args[1];
    args[0] = Arg(42);
    Node * node = Node::create(&Int, args);
    for(auto && state = walk(node); state; ++state)
      std::cout << state.cursor().kind << "\n";
  }

  InfoTable Pair = {
      "Pair"
    , 2
    , 0
    , nullptr
    , nullptr
    , nullptr
    , nullptr
    , 0
    , "pp"
    , sizeof(void*) * 3
    };

  void equality()
  {
    Arg args[2];
    args[0] = Arg(42);
    Node * i42 = Node::create(&Int, args);
    args[0] = Arg(7);
    Node * i7 = Node::create(&Int, args);
    args[0] = i42;
    args[1] = i7;
    Node * i42_7a = Node::create(&Pair, args);
    Node * i42_7b = Node::create(&Pair, args);
    assert(i42_7a != i42_7b);
    args[0] = i7;
    Node * i7_7 = Node::create(&Pair, args);

    std::cout << "i42 == i42: " << logically_equal(i42, i42) << "\n";
    std::cout << "i42 == i7: " << logically_equal(i42, i7) << "\n";
    std::cout << "(42,7) == (42,7): " << logically_equal(i42_7a, i42_7a) << "\n";
    std::cout << "(42,7) == (42,7)': " << logically_equal(i42_7a, i42_7b) << "\n";
    std::cout << "(42,7) == (7,7): " << logically_equal(i42_7a, i7_7) << "\n";
  }

  void register_graph(py::module_ mod)
  {
    mod.def("hello", &hello);
    mod.def("walk", &walk);
    mod.def("equality", &equality);
  }
}}
