/**
 * @file
 * @brief Defines the system interface.
 */

#pragma once
#include "sprite/builtins.hpp"
#include "sprite/common.hpp"
#include <iomanip>
#include <boost/assign.hpp>
#include <boost/bimap.hpp>
#include <boost/format.hpp>
#include <boost/tr1/unordered_map.hpp>

namespace sprite
{
  struct Node;

  /// The type of an H function.
  typedef tr1::function<void(Node &)> h_func_type;

  struct Program;

  /**
   * @brief Represents a program module.
   * 
   * Derived classes may use the install_* members to conveniently define a
   * module.
   */
  struct Module
  {
  protected:
    Module(Program & pgm) : m_pgm(pgm) {}

    // Polymorphism needed for dynamic_pointer_cast.
    virtual ~Module() {}
  private:
  
    /**
     * The program instance loading this instance of the module.
     *
     * @note This is only referenced during construction.
     */
    Program & m_pgm;

    /// The type of a bidirectional label-to-ID map.
    typedef boost::bimap<std::string, size_t> map_type;
  
    /// The map of operation names to IDs (and the reverse).
    map_type m_opers;
  
    /// The map of constructor names to IDs (and the reverse).
    map_type m_ctors;
  
  protected:

    Program & get_program() const { return m_pgm; }
  
    /// Installs an operation as a member function.
    template<typename Derived>
    size_t install_oper(
        std::string const & label, void (Derived::*memfun)(Node &) const
      )
    {
      return this->install_oper(
          label
        , tr1::bind<void>(memfun, static_cast<Derived *>(this), _1)
        );
    }

    /// Installs an operation as an h_func_type.
    size_t install_oper(std::string const & label, h_func_type const & h);
  
    /// Installs a constructor.
    size_t install_ctor(std::string const & label);
  
  private:
    size_t _lookup(std::string const & label, map_type const & map) const;

  public:
    size_t find_ctor(std::string const & label) const
      { return _lookup(label, this->m_ctors); }
  
    size_t find_oper(std::string const & label) const
      { return _lookup(label, this->m_opers); }
  };

  /// A program definition.
  struct Program
  {
    Program();
  private:
    tr1::unordered_map<std::string, shared_ptr<Module const> > m_imported;
  public:
    #if 0
    /// Get the named module, which must have been previously added.
    shared_ptr<Module const> get_module(std::string const & name)
    {
      if(m_imported.count(name) > 0)
        return m_imported[name];
      else
      {
        throw RuntimeError("Module " + name + " was not found");
      }
    }
    #endif

    /**
     * @brief Adds a module to the program.
     *
     * If the module was previously added, a reference is returned.  Otherwise,
     * the module is instantiated and added to the program.
     */
    template<typename ModuleType>
    shared_ptr<ModuleType const> import()
    {
      std::string const name = ModuleType::name();
      if(m_imported.count(name) > 0)
      {
        // The return value may be null for the prelude because the prelude
        // recursively imports itself.  It's easier to simply return a null
        // pointer than to special-case the translator for module Prelude.
        shared_ptr<ModuleType const> const m =
            dynamic_pointer_cast<ModuleType const>(m_imported[name]);

        if(name != "SpritePrelude" && !m)
          throw RuntimeError("Inconsistent imports for module " + name);
        return m;
      }
      else
      {
        // Create the module.  Initialize its slot to null first to properly
        // handle circular imports.
        m_imported[name] = shared_ptr<Module const>();
        shared_ptr<ModuleType const> const m(new ModuleType(*this));
        m_imported[name] = m;
        return m;
      }
    }

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
    size_t insert_ctor(std::string const & name);

    /// Add an operation to the program definition.
    size_t insert_oper(std::string const & name, h_func_type h);

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

/// @brief (private) Expands to [elem].
#define SPRITE_index_step(r,_,elem) [elem]

/**
 * @brief Generates code to process one level of a definitional tree.
 *
 * Expands to statements that index the inductive node, begin a switch, and
 * handle all default cases that do not depend on the user program.  A
 * user-defined H function will normally generate additional cases to
 * exhaustively handle the constructors of one type.
 *
 * In the case a pull-tab step is applied, the parent and inductive node are
 * both needed, so this requires the names of two variables to hold the
 * inductive node and its parent.  The inductive node is indexed relative to
 * node @p start along path @path.
 *
 * @param root
 *     an lvalue of type Node &, which marks the root of the entire expression;
 *     used as the target of rewrite actions
 * @param parent
 *     an lvalue of type NodePtr that will hold the parent node; used as the
 *     source for pull-tab steps
 * @param inductive
 *     an lvalue of type NodePtr * that will hold the inductive node; used
 *     as the target for pull-tab steps
 * @param start
 *     an rvalue of type NodePtr or Node; the node where indexing starts
 * @param path
 *     a preprocessor sequence of path components (size_t) that specifies the
 *     path from @p start to the inductive node; must not be empty
 */
#define SPRITE_SWITCH_BEGIN(root, parent, inductive, start, path)        \
    parent = (start) BOOST_PP_SEQ_FOR_EACH(                              \
        SPRITE_index_step,,BOOST_PP_SEQ_POP_BACK(path)                   \
      );                                                                 \
    inductive = &parent [BOOST_PP_SEQ_HEAD(BOOST_PP_SEQ_REVERSE(path))]; \
    switch((int)(*inductive)->tag())                                     \
    {                                                                    \
      case FAIL: return rewrite_fail(root);                              \
      case CHOICE: return pull_tab(*parent, *inductive);                 \
      case OPER: return head_normalize(**inductive);                     \
    /**/

/// Generates code to close a switch opened by SPRITE_SWITCH_BEGIN.
#define SPRITE_SWITCH_END                                                    \
      default: throw RuntimeError("unhandled case in generated H function"); \
    }                                                                        \
    /**/
  
/**
 * @brief Generates code to process one level of a definitional tree for a
 * built-in type.
 *
 * This is similar to SPRITE_SWITCH_BEGIN, except that the node value (rather
 * than tag()) is used in the switch.  The type should be either INT or CHAR.
 */
#define SPRITE_VALUE_SWITCH_BEGIN(type, root, parent, inductive, start, path) \
    SPRITE_SWITCH_BEGIN(root, parent, inductive, start, path)                 \
    case type:                                                                \
    {                                                                         \
      switch((static_cast<meta::NodeOf<type,-1>::type const &>                \
          (*inductive)).value()                                               \
        )                                                                     \
      {                                                                       \
    /**/
      
/// Generates code to close a switch opened by SPRITE_VALUE_SWITCH_BEGIN.
#define SPRITE_VALUE_SWITCH_END                                              \
      }                                                                      \
    }                                                                        \
    SPRITE_SWITCH_END                                                        \
    /**/
