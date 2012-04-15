/**
 * @file
 * @brief Temporary code to implement lists directly.
 *
 * This file will be removed once lists can be defined in Curry.
 */

#include "sprite/tests/test_common.hpp"
#include "sprite/operators.hpp"
#include "sprite/program.hpp"

/**
 * @brief The built-in list module.
 */
struct ListModule : sprite::Module
{
  size_t c_Cons;
  size_t c_Nil;
  size_t op_concat;

  ListModule(Loader & loader)
    : c_Cons(loader.add_ctor("Cons"))
    , c_Nil(loader.add_ctor("Nil"))
    , op_concat(
          loader.add_oper(
              "concat"
            , tr1::bind<void>(&ListModule::h_concat, this, _1)
            )
        )
  {}

  virtual ~ListModule() {}
  
  void h_concat(Node & node)
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
      case CTOR:
      {
        if(child->id() == c_Nil)
        {
          rewrite_fwd(node, node[1]);
          return;
        }
        else
        {
          assert(child->id() == c_Cons);
          assert(child->arity() == 2);
          rewrite_oper(
              node, c_Cons, (*child)[0]
            , Node::create<OPER>(op_concat, (*child)[1], node[1])
            );
          return;
        }
      }
      default:;
    }
  }
};

shared_ptr<Module> load_list(sprite::Loader & loader)
{
  shared_ptr<sprite::Module> module(
      boost::make_shared<ListModule>(tr1::ref(loader))
    );

  return module;
}


int test_main(int, char**)
{
  Program pgm;
  shared_ptr<ListModule const> const list(
      dynamic_pointer_cast<ListModule const>(pgm.import("List"))
    );

  // ====== Test addition ======
  // concat [1] [2]
  NodePtr lhs = Node::create<CTOR>(
      list->c_Cons, Node::create<INT>(1), Node::create<CTOR>(list->c_Nil)
    );
  NodePtr rhs = Node::create<CTOR>(
      list->c_Cons, Node::create<INT>(2), Node::create<CTOR>(list->c_Nil)
    );
  NodePtr goal = Node::create<OPER>(list->op_concat, lhs, rhs);
  execute(pgm, *goal);
  std::cout << setprogram(pgm) << *goal << std::endl;

  return 0;
}

