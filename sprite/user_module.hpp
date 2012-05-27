/**
 * @file
 * @brief Defines a basic implementation of the Module interface.
 */
#pragma once
#include "sprite/system.hpp"
#include <boost/assign.hpp>
#include <boost/bimap.hpp>

namespace sprite
{
  // typedef std::tr1::function<void(Node &, Node &)> DTree;

  /**
   * @brief A basic implementation of the Module interface.
   * 
   * Derived classes may use the install_* members to conveniently define a
   * module.
   */
  struct UserModule : Module
  {
  protected:
    UserModule(Program & pgm) : m_pgm(pgm) {}
    virtual ~UserModule() {}
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
    size_t install_oper(std::string const & label, h_func_type const & h)
    {
      // Register the operation with the program.
      size_t const id = m_pgm.insert_oper(label, h);
  
      // Install the label and ID in the symbol table for this module.
      boost::assign::insert(this->m_opers.left)(label,id);
  
      // Return the ID.
      return id;
    }
  
    /// Installs a constructor.
    size_t install_ctor(std::string const & label)
    {
      // Register the constructor with the program.
      size_t const id = m_pgm.insert_ctor(label);
  
      // Install the label and ID in the symbol table for this module.
      boost::assign::insert(this->m_ctors.left)(label,id);
  
      // Return the ID.
      return id;
    }
  
  private:
    size_t _lookup(std::string const & label, map_type const & map) const
    {
      typedef map_type::left_map::const_iterator iterator;
      iterator const p = map.left.find(label);
      if(p == map.left.end())
        { throw RuntimeError("Failed constructor or operation lookup."); }
      return p->second;
    }
  public:
  
    // ====== Module API ======
    virtual size_t find_ctor(std::string const & label) const
      { return _lookup(label, this->m_ctors); }
  
    virtual size_t find_oper(std::string const & label) const
      { return _lookup(label, this->m_opers); }
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
    switch((*inductive)->tag())                                          \
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
