#include "sprite/program.hpp"

namespace sprite
{
  Program::Program() : oper(), /*ctor_label(),*/ oper_label()
  {
    // Copy the built-in H functions to the operation table.
    oper.reserve(OP_END);
    std::copy(&builtin_h[0], &builtin_h[OP_END], std::back_inserter(oper));

    // Same for the labels.
    // ctor_label.reserve(C_END);
    // std::copy(
    //     &builtin_ctor[0], &builtin_ctor[C_END]
    //   , std::back_inserter(ctor_label)
    //   );

    oper_label.reserve(OP_END);
    std::copy(
        &builtin_oper[0], &builtin_oper[OP_END]
      , std::back_inserter(oper_label)
      );
  }

  shared_ptr<Module const> Program::import(std::string name)
  {
    // Only import if the named module was not previously imported.
    if(m_imported.count(name) == 0)
    {
      // Magic.  The name lookup needs to be generalized and eventually
      // trigger a dlopen, but for now we just look up the module name in a
      // hard-coded step.

      typedef shared_ptr<Module> module_ptr_type;
      tr1::function<module_ptr_type(Program &)> module_initializer;
      if(name == "List")
        { module_initializer = load_list; }
      else
        throw RuntimeError("Unknown module: " + name);

      assert(module_initializer);

      // Load the module into this program.
      module_ptr_type const module = module_initializer(*this);
      m_imported[name] = module;
      return module;
    }
    return m_imported[name];
  }

  size_t Program::insert_ctor(std::string const & name)
  {
    // TODO: find name collisions?
    ctor_label.push_back(name);
    return ctor_label.size() - 1;
  }

  size_t Program::insert_oper(std::string const & name, h_func_type h)
  {
    // TODO: find name collisions?
    assert(oper.size() == oper_label.size());

    oper.push_back(h);
    oper_label.push_back(name);
    return oper_label.size() - 1;
  }
}
