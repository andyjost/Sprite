#include "pybind11/pybind11.h"
#include "sprite/graph/node.hpp"
#include "sprite/graph/raw.hpp"

using namespace sprite;
namespace py = pybind11;

namespace sprite { namespace python
{
  InfoTable Hello = {
      "hello"
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
    Node * node = Node::create(&Hello, args);
    NodeU u{node};
    return u.int_->value;
  }

  void register_graph(py::module_ mod)
  {
    mod.def("hello", &hello);
  }
}}
