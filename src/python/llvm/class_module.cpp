#include "boost/python.hpp"
#include "boost/python/iterator.hpp"
#include "boost/iterator/transform_iterator.hpp"
#include "llvm/IR/ValueSymbolTable.h"
#include "python/llvm/_llvm.hpp"
#include "sprite/llvm/module.hpp"
#include "sprite/llvm/scope.hpp"
#include "sprite/llvm/value.hpp"
#include <stack>

using namespace boost::python;
using namespace sprite::llvm;
using module_ = ::sprite::llvm::module;
using SymbolTable = ::llvm::ValueSymbolTable;
using GlobalVarList = ::llvm::Module::GlobalListType;

namespace
{
  std::stack<sprite::llvm::scope> module_stack;

  module_ module__enter__(module_ const & m)
  {
    auto && scope = sprite::llvm::scope(m);
    module_stack.emplace(std::move(scope));
    return m;
  }

  void module__exit__(module_ const &, object, object, object)
    { module_stack.pop(); }

  SymbolTable const & module_globals(module_ const & m)
    { return m.ptr()->getValueSymbolTable(); }

  value symboltable__getitem__(SymbolTable const & tab, std::string const & name)
  {
    if(Value * V = tab.lookup(name))
      return V;
    throw key_error(name);
  }

  bool symboltable__contains__(SymbolTable const & tab, std::string const & name)
    { return tab.lookup(name); }
}

namespace boost { namespace python
{
  // Specialize Boost.Python to iterate SymbolTable by keys, like a Python dict.
  template<> struct iterators<SymbolTable>
  {
    struct Transformer
    {
      std::string operator()(::llvm::StringMapEntry<Value*> const & item) const
        { return item.getKey(); }
    };
    using iterator = boost::transform_iterator<
        Transformer, SymbolTable::iterator, std::string, std::string
      >;
    static iterator begin(SymbolTable & C) { return iterator(C.begin()); }
    static iterator end(SymbolTable & C) { return iterator(C.end()); }
  };
}}

namespace sprite { namespace python
{
  void register_module()
  {
    // The .default module holds an instance targeted to the machine running
    // this program.
    auto && default_ = module_(".default");
    module_stack.emplace(std::move(default_));

    using self_ns::str;
    class_<module_>("module", init<std::string const &>())
        .add_property("id", &module_::id)
        .def_readonly("_count_", object_count<Module>::num)
        .def(repr(self))
        .def(str(self))

        .def(self == other<module_>())
        .def("__enter__", &module__enter__)
        .def("__exit__", &module__exit__)
        .add_property("globals"
          , make_function(&module_globals, return_internal_reference<>())
          )
        .def("def_", &module_::def
          , (arg("name"), arg("type"), arg("const")=false
              , arg("linkage")=GlobalValue::ExternalLinkage
              , arg("init")=value(nullptr)
              )
          )
      ;

    class_<SymbolTable, boost::noncopyable>("symboltable", no_init)
        .def("__contains__", &symboltable__contains__)
        .def("empty", &SymbolTable::empty)
        .def("__getitem__", &symboltable__getitem__, with_custodian_and_ward_postcall<1,0>())
        .def("__len__", &SymbolTable::size)
        .def("__nonzero__", &SymbolTable::size)
        .def("__iter__", iterator<SymbolTable>())
      ;
  }
}}

