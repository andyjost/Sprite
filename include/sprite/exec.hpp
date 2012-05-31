/**
 * @file
 * @brief Interface to the execution components.
 */
#pragma once
#include "sprite/builtins.hpp"
#include "sprite/common.hpp"
#include "sprite/fingerprint.hpp"
#include "sprite/node.hpp"
#include "sprite/rewrite.hpp"
#include "sprite/system.hpp"

namespace sprite
{
  struct Program;

  /// Global pointer to the currently executing program.
  extern Program const * g_program;

  /// Indicates whether tracing is enabled.
  enum TraceOption { NO_TRACE=false, TRACE=true };

  /**
   * @brief Base of a class that handles computation results as they are
   * generated.
   *
   * Whenever execution yields a result in constructor normal form, this
   * handler will be called to handle it.
   */
  struct YieldHandler
  {
    virtual void yield(Node const & result) const = 0;
    virtual ~YieldHandler() {}
  };

  /**
   * @brief A concrete YieldHandler for a particular output iterator type.
   *
   * The result is simply written to the specified output location.
   */
  template<typename OutputIterator>
  struct YieldHandler_ : YieldHandler
  {
    explicit YieldHandler_(OutputIterator out) : m_out(out) {}
  private:
    OutputIterator m_out;
  public:
    virtual void yield(Node const & result) const
      { *m_out++ = result; }
    virtual ~YieldHandler_() {}
  };

  /// A yield handler that simply discards the output.
  template<> struct YieldHandler_<void> : YieldHandler
  {
    virtual void yield(Node const &) const {}
    virtual ~YieldHandler_() {}
  };

  /**
   * @brief Execute a goal in the context of the given program.
   *
   * This is the the primary entry point to the execution system. Execution
   * proceeds in-place, meaning that the goal expression will likely be
   * modified.
   *
   * @param program
   *   The program definition.  This provides the necessary information to
   *   carry out execution as a series of rewrite steps.
   * @param goal
   *   The goal statement.  Modified in place.
   * @param handler
   *   (optional) Defaults to a handler that discards the generated results.
   *   The object that handles output as it is generated.
   * @param trace
   *   (optional) Defaults to true.
   *   Enables debug tracing.
   */
  void execute(
      Program const & program, Node & goal
    , YieldHandler const & handler = YieldHandler_<void>()
    , TraceOption trace=NO_TRACE
    );

  inline void execute(
      Program const & program, Node & goal, TraceOption trace
    )
  { execute(program, goal, YieldHandler_<void>(), trace); }
  
  /// Alternate form of execute; results are written to the given iterator.
  template<typename OutputIterator>
  inline void execute(
      Program const & pgm, Node & goal, OutputIterator out
    , TraceOption trace=NO_TRACE
    )
  {
    YieldHandler_<OutputIterator> handler(out);
    execute(pgm, goal, static_cast<YieldHandler const &>(handler), trace);
  }

  /// Traverses an expression and returns true if it is found to be in cnf.
  inline bool is_norm(Node const & node)
  {
    if(!is_ctor(node.tag())) return false;

    BOOST_FOREACH(NodePtr const & child, node.iter())
      { if(!is_norm(*child)) return false; }

    return true;
  }

  /**
   * @brief Performs the pull-tab transformation.
   *
   * @param g
   *   The source of the transformation.
   * @param p
   *   The target of the transformation.  Must be a direct descendant of g.
   */
  inline void pull_tab(Node & g, NodePtr const & p)
  {
    size_t const i = g.position(p);
    assert(p->tag() == CHOICE);
    NodePtr lhs = g.clone();
    lhs[i] = p[0];
    NodePtr rhs = g.clone();
    rhs[i] = p[1];
    rewrite_choice(g, p->id(), lhs, rhs);
  }

  /**
   * @brief The head-normalizing (H) function from the fair scheme.
   *
   * This is a generic H function that dispatches to the correct implementation
   * for the given operation.  The H.6 rule, which ignors constructor-rooted
   * expressions, is implemented here so that user-compiled H rules can ignore
   * it.
   */
  inline void head_normalize(Node & node)
  {
    switch(node.tag())
    {
      // For operations, call the H function.
      case OPER:
        return g_program->oper[node.id()](node);

      // For non-constructors, throw.
      case FAIL: case CHOICE: case FWD:
        throw RuntimeError(
            "defined operation or constructor expected in "
              + std::string(BOOST_CURRENT_FUNCTION)
          );

      // Ignore constructor types.
      case INT: case FLOAT: case CTOR: default:
        return; // H.6
    }
  }

  /// The normalizing (N) function from the fair scheme.
  inline void fair_normalize(Fingerprint const & fp, Node & node)
  {
    switch(node.tag())
    {
      case OPER:
        return head_normalize(node);

      case INT: // Always a cnf.
      case FLOAT: // Always a cnf.
        return;

      default:
      {
        // TODO: must rewrite this section to match the paper.
        // In particular, the choice and fail rules must be applied
        // BEFORE any recursive calls to fair_normalize.
        BOOST_FOREACH(NodePtr & child, node.iter())
        {
          switch(child->tag())
          {
            case FAIL: return rewrite_fail(node);
            case OPER: head_normalize(*child); break;
            case CHOICE: return pull_tab(node, child);
            case INT: case FLOAT: break;
            case FWD: throw RuntimeError("Unexpected FWD node.");
            default: case CTOR:
              assert(child->tag() >= CTOR);
              fair_normalize(fp, *child);
          }
        }
      }
    }
  }

  /**
   * @brief Print an expression.
   *
   * @note Alias for operator<<, callable from the debugger.
   */
  void print_node(Node const &);
}
