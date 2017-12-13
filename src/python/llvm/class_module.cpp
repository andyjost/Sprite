#include <boost/python.hpp>
#include "python/llvm/_llvm.hpp"
#include "sprite/llvm/module.hpp"
#include "sprite/llvm/scope.hpp"
#include <stack>

using namespace boost::python;

namespace
{
  std::stack<sprite::llvm::scope> module_stack;

  sprite::llvm::module module__enter__(sprite::llvm::module const & m)
  {
    auto && scope = sprite::llvm::scope(m);
    module_stack.emplace(std::move(scope));
    return m;
  }

  void module__exit__(sprite::llvm::module const &, object, object, object)
    { module_stack.pop(); }
}

namespace sprite { namespace python
{
  void register_module()
  {
    using self_ns::str;
    class_<sprite::llvm::module>(
        "module", init<std::string const &>()
      )
      .def(self == other<sprite::llvm::module>())
      .def("__enter__", &module__enter__)
      .def("__exit__", &module__exit__)
      .def(str(self))
      ;

    // The .default module holds an example of the current target.  It is needed
    // for certain type calculations (e.g., sizeof).
    module_stack.push(sprite::llvm::module(".default"));
  }
}}
