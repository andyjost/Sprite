/**
 * @file
 * @brief Implements the Program structure.
 */
#pragma once
#include "sprite/common.hpp"
#include <functional>
#include <boost/tr1/unordered_map.hpp>

namespace sprite
{
  /// Type of a pointer to an H (callback) function.
  // typedef void (*h_func_type)(Node &);
  typedef tr1::function<void(Node &)> h_func_type;

  /// The table of built-in H routines.
  extern h_func_type builtin_h[OP_END];

  /// The tables of built-in constructor labels.
  extern std::string builtin_ctor[C_END];

  /// The tables of built-in operation labels.
  extern std::string builtin_oper[OP_END];

  /// Interface to a module loader.
  struct Loader
  {
    virtual size_t add_ctor(std::string const & name) = 0;
    virtual size_t add_oper(std::string const & name, h_func_type) = 0;
    virtual ~Loader() {}
  };

  struct Module
  {
    virtual ~Module() {}
  };
}

// TODO remove hard reference
extern boost::shared_ptr<sprite::Module> load_list(sprite::Loader &);

namespace sprite
{
  /// A program definition.
  struct Program : Loader
  {
    Program() : oper(), ctor_label(), oper_label()
    {
      // Copy the built-in H functions to the operation table.
      oper.reserve(OP_END);
      std::copy(&builtin_h[0], &builtin_h[OP_END], std::back_inserter(oper));

      // Same for the labels.
      ctor_label.reserve(C_END);
      std::copy(&
          builtin_ctor[0], &builtin_ctor[C_END]
        , std::back_inserter(ctor_label)
        );

      oper_label.reserve(OP_END);
      std::copy(&
          builtin_oper[0], &builtin_oper[OP_END]
        , std::back_inserter(oper_label)
        );
    }

  private:
    tr1::unordered_map<std::string, shared_ptr<Module> > m_imported;
  public:
    /// Import the named module.
    shared_ptr<Module const> import(std::string name)
    {
      // Only import if the named module was not previously imported.
      if(m_imported.count(name) == 0)
      {
        // Magic.  The name lookup needs to be generalized and eventually
        // trigger a dlopen, but for now we just look up the module name in a
        // hard-coded step.

        typedef shared_ptr<Module> module_ptr_type;
        tr1::function<module_ptr_type(Loader &)> module_initializer;
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

    virtual ~Program() {}

    /// Type of a dynamically-sized table of H functions.
    typedef std::vector<h_func_type> oper_t;

    /// The table of H functions.
    oper_t oper;

    /// Type of a dynamically-sized table of labels.
    typedef std::vector<std::string> label_t;

    /// The table of constructor labels.
    label_t ctor_label;

    /// The table of operation labels.
    label_t oper_label;

    /// Add a constructor to the program definition.
    virtual size_t add_ctor(std::string const & name)
    {
      // TODO: find name collisions?
      ctor_label.push_back(name);
      return ctor_label.size() - 1;
    }

    /// Add an operation to the program definition.
    virtual size_t add_oper(std::string const & name, h_func_type h)
    {
      // TODO: find name collisions?
      assert(oper.size() == oper_label.size());

      oper.push_back(h);
      oper_label.push_back(name);
      return oper_label.size() - 1;
    }
  };
}

