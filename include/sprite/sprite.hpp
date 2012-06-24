/**
 * @file
 * @brief Top-level include to get all of Sprite.
 */

#pragma once
#include "sprite/cmdline.hpp"
#include "sprite/create.hpp"
#include "sprite/exec.hpp"
#include "sprite/node.hpp"
#include "sprite/operators.hpp"
#include "sprite/rewrite.hpp"
#include "sprite/system.hpp"

// This file is created during the Sprite installation.
#include "sprite/currylib/SpritePrelude.hpp"



// Make "Prelude" an alias for "SpritePrelude"
//
// Note: there is a circular dependency between this file and SpritePrelude.hpp.
// This section will work regarless of the include order.
namespace sprite { namespace user
{
  namespace m_13SpritePrelude {}
  namespace m_7Prelude = m_13SpritePrelude;
}}

