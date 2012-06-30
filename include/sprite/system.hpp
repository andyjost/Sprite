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

  extern void const * g_context;
  extern Node * g_redex;

  /// The type of an H function.
  // DEBUG
  // typedef tr1::function<void(Node &)> h_func_type;

  struct HFunc
  {
    // Null H function or one with no context.
    explicit HFunc(void (*fp_)() = 0)
      : context(0), fp(fp_)
    {
    }

    // H function with context.
    template<typename T>
    HFunc(T const * context_, void (*fp_)())
      : context(reinterpret_cast<void const *>(context_)), fp(fp_)
    {
    }

    void operator()(Node & node) const
    {
      g_context = context;
      g_redex = &node;
      return fp();
    }
  private:
    void const * context;
    void (*fp)();
  };

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
    #if 0
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
    #endif

    /// Installs an operation as an h_func_type.
    size_t install_oper(std::string const & label, HFunc const & h);
  
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
    typedef std::vector<HFunc> oper_t;

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
    size_t insert_oper(std::string const & name, HFunc=HFunc());

    /// Invoke the H routine associted with the given redex.
    void call_h(Node & node) const
      { return this->oper[node.id()](node); }

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

  /**
   * @brief An lvalue of type NodePtr that will hold the parent node; used as
   * the source for pull-tab steps
   */
  extern NodePtr g_parent;
  
  /**
   * @brief An lvalue of type NodePtr * that will hold the inductive node; used
   * as the target for pull-tab steps
   */
  extern Node * g_inductive;
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
 * This macro modifies the global variables g_parent and g_inductive.
 *
 * @param start
 *     an rvalue of type NodePtr or Node; the node where indexing starts
 * @param path
 *     a preprocessor sequence of path components (size_t) that specifies the
 *     path from @p start to the inductive node; must not be empty
 */
#define SPRITE_SWITCH_BEGIN(start, path)                                     \
    g_parent = (start) BOOST_PP_SEQ_FOR_EACH(                                \
        SPRITE_index_step,,BOOST_PP_SEQ_POP_BACK(path)                       \
      );                                                                     \
    static const size_t idx = BOOST_PP_SEQ_HEAD(BOOST_PP_SEQ_REVERSE(path)); \
    g_inductive = g_parent[idx].remove_fwd().get();                          \
    switch((int)(g_inductive->tag()))                                        \
    {                                                                        \
      case FAIL: return rewrite_fail(*g_redex);                              \
      case CHOICE: return pull_tab(g_parent.get(), g_inductive, idx);        \
      case OPER: return head_normalize(g_inductive);                         \
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
#define SPRITE_VALUE_SWITCH_BEGIN(type, start, path)           \
    SPRITE_SWITCH_BEGIN(start, path)                           \
    case type:                                                 \
    {                                                          \
      switch((static_cast<meta::NodeOf<type,-1>::type const &> \
          (*inductive)).value()                                \
        )                                                      \
      {                                                        \
    /**/
      
/// Generates code to close a switch opened by SPRITE_VALUE_SWITCH_BEGIN.
#define SPRITE_VALUE_SWITCH_END \
      }                         \
    }                           \
    SPRITE_SWITCH_END           \
    /**/
