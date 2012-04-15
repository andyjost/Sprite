/**
 * @file
 * @brief Tests for the built-in int module (incomplete).
 */

#include "sprite/tests/test_common.hpp"
#include "sprite/operators.hpp"

// TODO Null stub.  Will be removed.
shared_ptr<Module> load_list(sprite::Loader &)
  { return shared_ptr<Module>(); }

int test_main(int, char**)
{
  Program pgm;

  // ====== Test addition ======
  NodePtr a = Node::create<INT>(1);
  NodePtr b = Node::create<INT>(2);
  NodePtr goal = Node::create<OPER>(OP_INT_ADD, a, b);
  execute(pgm, *goal);
  std::cout << setprogram(pgm) << *goal << std::endl;
  // BOOST_CHECK(*goal == 3);

  return 0;
}

