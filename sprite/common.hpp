/**
 * @file
 * @brief Common includes and definitions.
 */
#pragma once

#include <algorithm>
#include <exception>
#include <iostream>
#include <string>
#include <boost/current_function.hpp>
#include <boost/foreach.hpp>
#include <boost/integer.hpp>
#include <boost/make_shared.hpp>
#include <boost/mpl/identity.hpp>
#include <boost/mpl/size_t.hpp>
#include <boost/preprocessor.hpp>
#include <boost/scope_exit.hpp>
#include <boost/shared_ptr.hpp>
#include <boost/static_assert.hpp>
#include <boost/tr1/functional.hpp>
#include <boost/type_traits/is_pointer.hpp>
#include <boost/type_traits/is_same.hpp>
#include <boost/utility/enable_if.hpp>
#include <boost/variant/static_visitor.hpp>

/// The main namespace for sprite.
namespace sprite
{
  namespace mpl = boost::mpl;
  namespace tr1 = std::tr1;

  using boost::disable_if;
  using boost::disable_if_c;
  using boost::enable_if;
  using boost::enable_if_c;
  using boost::is_pointer;
  using boost::is_same;
  using boost::shared_ptr;
  using boost::static_visitor;
  using boost::dynamic_pointer_cast;

  /// @brief Thrown to indicate a runtime error in the execution system.
  struct RuntimeError : std::exception
  {
    explicit RuntimeError(std::string const & msg = std::string())
      : m_msg("a runtime error occurred")
    {
      if(msg.size() > 0) { m_msg += ": " + msg; }
    }
    virtual char const * what() const throw() { return m_msg.c_str(); }
    virtual ~RuntimeError() throw() {}
  private:
    std::string m_msg;
  };

  typedef boost::uint_t<32>::exact uint32;

  /// Identifies the type of a node.
  enum TagValue { FAIL, CTOR, OPER, CHOICE, FWD, INT, FLOAT };

  /// Indicates whether a tag represents a constructor.
  inline bool is_ctor(TagValue x)
  {
    switch(x)
    {
      case CTOR: case INT: case FLOAT: return true;
      default: return false;
    }
  }

  /// Indicates whether a tag represents a built-in type.
  inline bool is_builtin(TagValue x)
  {
    switch(x)
    {
      case INT: case FLOAT: return true;
      default: return false;
    }
  }

  /// Contains template metaprogramming constructs.
  namespace meta
  {
    /**
     * @brief A TagValue metaconstant.
     *
     * This is a type that represents a compile-time constant of type TagValue.
     */
    template<sprite::TagValue C> struct TagValue
    {
      static sprite::TagValue const value = C;
      typedef TagValue<C> type;
      typedef sprite::TagValue value_type;
      operator sprite::TagValue() const { return value; }
    };
  
    /// Computes the value type associated with a TagValue (for builtin types).
    template<sprite::TagValue> struct ValueType;
    template<> struct ValueType<INT> { typedef boost::int_t<64>::exact type; };
    template<> struct ValueType<FLOAT> { typedef double type; };
  }
}

