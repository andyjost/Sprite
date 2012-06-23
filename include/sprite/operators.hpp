/**
 * @file
 * @brief Implements built-in operators used by the implementation.
 */
#pragma once
#include "sprite/common.hpp"
#include "sprite/exec.hpp"
#include "sprite/node.hpp"
#include <boost/mpl/has_xxx.hpp>
#include <stack>

namespace sprite
{
  /// Defines I/O manipulators.
  namespace manipulators
  {
    namespace detail
    {
      inline Program const * & pgm_data(std::ios_base & stream)
      {
        static int const index = std::ios::xalloc();
        return (Program const * &)(stream.pword(index));
      }
    }

    /**
     * @brief I/O manipulator to set the program.
     *
     * The program is required to look up label names.  A pointer to the
     * program is contextual information stored with an output stream until
     * cleared and is requried to stream out Node objects.
     */
    struct setprogram
    {
      setprogram(Program const & pgm) : m_pgm(pgm) {}
    private:
      Program const & m_pgm;
      void * m_prev;
    public:
      template<typename Stream>
      friend Stream & operator<<(Stream & stream, setprogram const & manip)
      {
        detail::pgm_data(stream) = &manip.m_pgm;
        return stream;
      }
    };

    /// I/O manipulator to clear the program.
    inline std::ios_base & clearprogram(std::ios_base & stream)
    {
      detail::pgm_data(stream) = 0;
      return stream;
    }
  }
  using manipulators::setprogram;
  using manipulators::clearprogram;

  namespace meta
  {
    // Declare a metapredicate named has_value_type that tests for the
    // value_type nested typedef.
    BOOST_MPL_HAS_XXX_TRAIT_DEF(value_type);
  }

  namespace visitors
  {
    /**
     * @brief Implements operator<< for nodes.
     *
     * @param stream
     *   The output stream.
     * @param outer
     *   True if this is the outermost invocation (avoids surrounding the
     *   whole expression in parentheses.
     * @param node
     *   The head of the expression to print.
     */
    template<typename Stream>
    struct StreamOut : static_visitor<Stream &>
    {
      typedef typename StreamOut::result_type result_type;
      StreamOut() {}
    private:
      mutable std::stack<char> m_delim;
    public:

      /**
       * @brief Handles built-in types, which define a value_type in the payload.
       *
       * For these, don't print the constructor name, just the value instead.
       */
      template<typename Payload>
      typename enable_if<meta::has_value_type<Payload>, result_type>::type
      operator()(Stream & stream, bool, Node_<Payload> const & node) const
        { return (stream << node.payload.value); }

      /**
       * @brief Handles nodes without any value_type, such as user-defined
       * constructors and defined operations.
       */
      template<typename NodeType>
      result_type operator()(
          Stream & stream, bool outer, NodeType const & node
        ) const
      {
        // Get the program associated with this stream.
        Program const * pgm = manipulators::detail::pgm_data(stream);

        char close_char = '\0';
        m_delim.push(' ');

        // Print the label.
        if(pgm)
        {
          switch(node.tag())
          {
            case FAIL: stream << "**FAIL**"; break;

            case CHOICE:
              if(!outer)
              {
                stream << "(";
                close_char = ')';
              }
              stream << "?_" << node.id() << " ";
              break;

            case OPER:
                if(!outer && node.arity() > 0)
                {
                  stream << "(";
                  close_char = ')';
                }
                stream << pgm->oper_label[node.id()] << " ";
                break;

            case CTOR:
            default:
              // Handle certain built-in types specially.
              if(node.tag() >= CTOR)
              {
                switch(node.id())
                {
                  case CL_TUPLE2:
                  case CL_TUPLE3:
                  case CL_TUPLE4:
                  case CL_TUPLE5:
                  case CL_TUPLE6:
                  case CL_TUPLE7:
                  case CL_TUPLE8:
                  case CL_TUPLE9:
                    stream << "(";
                    close_char = ')';
                    m_delim.pop();
                    m_delim.push(',');
                    break;
                  case CL_CONS:
                  case CL_NIL:
                  {
                    stream << "[";
                    Node const * p = &node;
                    while(true)
                    {
                      visit(
                          tr1::bind<Stream &>(
                              *this, tr1::ref(stream), false, _1
                            )
                        , *(*p)[0]
                        );
                      p = (*p)[1].get();
                      if(p->id() == CL_NIL) break;
                      stream << ",";
                    }
                    stream << "]";
                    m_delim.pop();
                    return stream;
                  }
                  default:
                    if(!outer && node.arity() > 0)
                    {
                      stream << "(";
                      close_char = ')';
                    }
                    stream << pgm->ctor_label[node.id()] << " ";
                    break;
                }
                break;
              }
              else throw RuntimeError("mishandled node in operator<<");
          }
        }
        else
        {
          if(!outer)
          {
            stream << "(";
            close_char = ')';
          }
          stream << "<unknown-ctor> ";
        }

        // Print the children.
        bool first = true;
        BOOST_FOREACH(NodePtr const & child, node.iter())
        {
          if(!first) stream << m_delim.top();
          first = false;
          visit(
              tr1::bind<Stream &>(*this, tr1::ref(stream), false, _1)
            , *child
            );
        }

        m_delim.pop();
        if(close_char) stream << close_char;
        return stream;
      }
    };
  }

  namespace operators
  {
    /// Output a representation of the node to the given stream.
    template<typename Stream>
    Stream & operator<<(Stream & stream, Node const & node)
    {
      static visitors::StreamOut<Stream> const visitor;
      return visit(
          tr1::bind<Stream &>(visitor, tr1::ref(stream), true, _1), node
        );
    }
  }
  using operators::operator<<;
}
