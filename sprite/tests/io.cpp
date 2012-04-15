/**
 * @file
 * @brief Tests for built-in I/O operations.
 */

#include "sprite/tests/test_common.hpp"
#include "sprite/operators.hpp"

// TODO Null stub.  Will be removed.
shared_ptr<Module> load_list(sprite::Loader &)
  { return shared_ptr<Module>(); }

int test_main(int, char**)
{
  Program pgm;
  std::cout << setprogram(pgm);

  NodePtr a = Node::create<INT>(1);
  NodePtr b = Node::create<INT>(2);
  NodePtr goal = Node::create<OPER>(OP_INT_ADD, a, b);

  std::cout << *goal << std::endl;
  execute(pgm, *goal);

  std::cout << *goal << std::endl;

  goal = Node::create<FAIL>();
  std::cout << *goal << std::endl;
  // BOOST_CHECK(*goal == 3);

  return 0;
}

