/**
 * @file
 * @brief Implements the Program structure.
 */
#pragma once
#include "sprite/builtins.hpp"
#include "sprite/common.hpp"
#include "sprite/system.hpp"
#include <iomanip>
#include <boost/tr1/unordered_map.hpp>
#include <boost/format.hpp>

namespace sprite
{
  /// The table of built-in H routines.
  extern h_func_type builtin_h[OP_END];

  /// The tables of built-in constructor labels.
  extern std::string builtin_ctor[C_END];

  /// The tables of built-in operation labels.
  extern std::string builtin_oper[OP_END];
}

// TODO remove this hard reference
extern boost::shared_ptr<sprite::Module> load_list(sprite::Loader &);

namespace sprite
{
  /// A program definition.
  struct Program : Loader
  {
    Program();
  private:
    tr1::unordered_map<std::string, shared_ptr<Module> > m_imported;
  public:
    /// Import the named module.
    shared_ptr<Module const> import(std::string name);

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
    virtual size_t insert_ctor(std::string const & name);

    /// Add an operation to the program definition.
    virtual size_t insert_oper(std::string const & name, h_func_type h);

    template<typename Stream>
    friend Stream & operator<<(Stream & out, Program const & pgm)
    {
      boost::format fmt("%6d \"%s\"\n");
      out << "Program @ " << &pgm;
      
      out << "\n====== CONSTRUCTORS ======\n";
      for(size_t i=0; i<pgm.ctor_label.size(); ++i)
        { out << fmt % i % pgm.ctor_label.at(i); } 

      out << "\n====== OPERATIONS ======\n";
      for(size_t i=0; i<pgm.oper_label.size(); ++i)
        { out << fmt % i % pgm.oper_label.at(i); }

      return (out << std::endl);
    }
  };
}

