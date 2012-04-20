/**
 * @file
 * @brief Temporary code to implement lists directly.
 *
 * This file will be removed once lists can be defined in Curry.
 */

#include "sprite/tests/test_common.hpp"
#include "sprite/operators.hpp"
#include "sprite/user_module.hpp"

/**
 * @brief The built-in list module.
 */
struct ListModule : sprite::UserModule
{
  // Constructor and operation ids.
  size_t c_Cons;
  size_t c_Nil;
  size_t op_concat;

  /// Initializes the module.
  ListModule(Loader & loader) : UserModule(loader)
  {
    c_Cons = install_ctor("Cons");
    c_Nil = install_ctor("Nil");
    op_concat = install_oper("concat", &ListModule::h_concat);
  }

  virtual ~ListModule() {}
  
private:

  // ====== H function(s) ======
  void h_concat(Node & node) const
  {
    assert(node.arity() == 2);
    NodePtr child = node[0];
    switch(child->tag())
    {
      // H.1
      case CHOICE: return pull_tab(node, child);
      // H.5
      case FAIL: return rewrite_fail(node);
      // H.2
      case OPER: return head_normalize(*child);
      // H.3
      case CTOR:
      {
        if(child->id() == c_Nil)
          return rewrite_fwd(node, node[1]);
        else
        {
          assert(child->id() == c_Cons);
          assert(child->arity() == 2);
          rewrite_ctor(
              node, c_Cons, (*child)[0]
            , Node::create<OPER>(op_concat, (*child)[1], node[1])
            );
          return;
        }
      }
      default: throw RuntimeError("Type error in concat");
    }
  }
};

/// Loads the list module.
shared_ptr<Module> load_list(sprite::Loader & loader)
  { return boost::make_shared<ListModule>(tr1::ref(loader)); }

// This is a sample program to demonstrate the use of concat.  The output is
// meant to be inspected visually.
int test_main(int, char**)
{
  // ====== DEFINE THE PROGRAM ======

  // Create a new program and make it the context for output.
  Program pgm;
  std::cout << setprogram(pgm);

  // Import the list module and capture a reference to it.
  shared_ptr<Module const> const _list = pgm.import("List");

  // Downcast the list module (alternatively, the abstract Module interface
  // could be used).
  shared_ptr<ListModule const> const list(
      dynamic_pointer_cast<ListModule const>(_list)
    );

  // DEBUG - print the linked program.
  std::cout << pgm << std::endl;

  // ====== FORM THE GOAL ======

  // Construct this goal: concat [1] [2]
  NodePtr lhs = Node::create<CTOR>(
      list->c_Cons, Node::create<INT>(1), Node::create<CTOR>(list->c_Nil)
    );
  NodePtr rhs = Node::create<CTOR>(
      list->c_Cons, Node::create<INT>(2), Node::create<CTOR>(list->c_Nil)
    );
  NodePtr goal = Node::create<OPER>(list->op_concat, lhs, rhs);
  std::cout << *goal << std::endl;

  // ====== EXECUTE THE GOAL ======

  execute(pgm, *goal, TRACE);
  std::cout << *goal << std::endl;

  return 0;
}

