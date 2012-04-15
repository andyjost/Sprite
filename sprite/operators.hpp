/**
 * @file
 * @brief Implements built-in operators used by the implementation.
 */
#include "sprite/common.hpp"
#include "sprite/exec.hpp"
#include "sprite/node.hpp"
#include <boost/mpl/has_xxx.hpp>

namespace sprite
{
  /// Defines I/O manipulators.
  namespace manipulators
  {
    namespace detail
    {
      Program const * & pgm_data(std::ios_base & stream)
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
    std::ios_base & clearprogram(std::ios_base & stream)
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
    /// Implements operator<< for nodes.
    template<typename Stream>
    struct StreamOut : static_visitor<Stream &>
    {
      typedef typename StreamOut::result_type result_type;
      StreamOut() {}

      /**
       * Handles built-in types, which define a value_type in the payload.  For
       * these, we don't print the constructor name, just the value instead.
       */
      template<typename Payload>
      typename enable_if<meta::has_value_type<Payload>, result_type>::type
      operator()(Stream & stream, Node_<Payload> const & node) const
        { return (stream << node.payload.value); }

      /**
       * Handles nodes without any value_type, such as user-defined
       * constructorss and defined operations.
       */
      template<typename NodeType>
      result_type operator()(Stream & stream, NodeType const & node) const
      {
        Program const * pgm = manipulators::detail::pgm_data(stream);

        // Print the label.
        if(pgm)
        {
          switch(node.tag())
          {
            case OPER: stream << pgm->oper_label[node.id()]; break;
            case CTOR: stream << pgm->ctor_label[node.id()]; break;
            case FAIL: stream << "**FAIL**"; break;
            case CHOICE: stream << "?_" << node.id(); break;
            default:
              throw RuntimeError("mishandled node in operator<<");
          }
        }
        else
          stream << "<unknown-ctor>";

        // Print children.
        BOOST_FOREACH(NodePtr const & child, node.iter())
          { stream << " " << *child; }
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
      return visit(tr1::bind<Stream &>(visitor, tr1::ref(stream), _1), node);
    }
  }
  using operators::operator<<;
}
