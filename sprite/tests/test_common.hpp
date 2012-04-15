/**
 * @file
 * @brief Common statements for test files.
 *
 * This file defines a main() function.  Test files should include this header
 * and then define a function test_main.  The following asserts may be used:
 *
 *     - BOOST_CHECK(predicate)
 *     - BOOST_REQUIRE(predicate)
 *     - BOOST_ERROR(message)
 *     - BOOST_FAIL(message)
 *
 * For more information, refer to the Boost.Test documentation at
 * www.boost.org.
 */

#pragma once
#include <boost/test/minimal.hpp>
#include <iostream>
#include "sprite/create.hpp"
#include "sprite/exec.hpp"
#include "sprite/node.hpp"

using namespace sprite;

