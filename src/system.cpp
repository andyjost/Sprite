#include "sprite/system.hpp"

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

  #if 0
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
  #endif

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

  size_t Module::install_oper(std::string const & label, h_func_type const & h)
  {
    // Register the operation with the program.
    size_t const id = m_pgm.insert_oper(label, h);
  
    // Install the label and ID in the symbol table for this module.
    boost::assign::insert(this->m_opers.left)(label,id);
  
    // Return the ID.
    return id;
  }
  
  size_t Module::install_ctor(std::string const & label)
  {
    // Register the constructor with the program.
    size_t const id = m_pgm.insert_ctor(label);
  
    // Install the label and ID in the symbol table for this module.
    boost::assign::insert(this->m_ctors.left)(label,id);
  
    // Return the ID.
    return id;
  }

  size_t Module::_lookup(std::string const & label, map_type const & map) const
  {
    typedef map_type::left_map::const_iterator iterator;
    iterator const p = map.left.find(label);
    if(p == map.left.end())
      { throw RuntimeError("Failed constructor or operation lookup."); }
    return p->second;
  }
}
