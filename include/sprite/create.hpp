/**
 * @file
 * @brief Defines the Node::create function.
 */
#pragma once
#include "sprite/node.hpp"

namespace sprite
{
  // The create function is defined in a separate file to facilitate debugging.
  #define BOOST_PP_FILENAME_1 "sprite/detail/create.hpp"
  // Add 3 for the 3 arguments that rewrite_ctor takes, then subtract 1, since
  // the iteration limits are inclusive of the bounds.
  #define BOOST_PP_ITERATION_LIMITS (0,BOOST_PP_ADD(2,SPRITE_REWRITE_ARG_BOUND))
  #include BOOST_PP_ITERATE()
}
