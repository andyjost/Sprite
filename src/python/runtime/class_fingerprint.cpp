#include <boost/python.hpp>
#include <boost/python/enum.hpp>
#include "python/runtime/_runtime.hpp"
#include "sprite/fingerprint.hpp"
#include <functional>
#include <map>

using namespace boost::python;
using namespace sprite;

namespace
{
  void Fingerprint__setitem__(Fingerprint & self, size_t id, ChoiceState lr)
  {
    switch(lr)
    {
      case ChoiceState::LEFT:  self.set_left(id); break;
      case ChoiceState::RIGHT: self.set_right(id); break;
      default: throw std::invalid_argument("expected LEFT or RIGHT");
    }
  }
  object Fingerprint__tree__(Fingerprint const & self)
  {
    std::map<fingerprints::Branch const *, object> branches;
    std::function<object(fingerprints::Node const *, size_t)> buildtree;
    buildtree = [&](fingerprints::Node const * node, size_t depth) -> object
    {
      if(depth == self.depth())
        return object(node->block);
      auto const * branch = node->branch;
      if(branches.count(branch) == 0)
      {
        boost::python::list args;
        for(size_t i=0; i<FP_BRANCH_SIZE; ++i)
          args.append(buildtree(&branch->next[i], depth+1));
        branches[branch] = boost::python::tuple(args);
      }
      return branches[branch];
    };
    return buildtree(&self.root(), 0);
  }
}

namespace sprite { namespace python
{
  void register_fingerprint()
  {
    enum_<ChoiceState>("ChoiceState")
        .value("UNDETERMINED", ChoiceState::UNDETERMINED)
        .value("LEFT", ChoiceState::LEFT)
        .value("RIGHT", ChoiceState::RIGHT)
        .export_values();

    class_<Fingerprint>("Fingerprint", init<>())
      .def(init<Fingerprint const &>())
      .def("clone", +[](Fingerprint const & self)->Fingerprint{return self;})
      .def("get", +[](Fingerprint & self, size_t id, ChoiceState default_)
          -> ChoiceState
          {
            auto lr = self.test(id);
            return lr == ChoiceState::UNDETERMINED ? default_ : lr;
          }
        , (arg("self"), arg("id"), arg("default")=ChoiceState::UNDETERMINED)
        )
      .def("set_left", &Fingerprint::set_left)
      .def("set_right", &Fingerprint::set_right)
      .def("__setitem__", &Fingerprint__setitem__)
      .def("__getitem__", &Fingerprint::test)
      .def_readonly("capacity", &Fingerprint::capacity)
      .def_readonly("depth", &Fingerprint::depth)
      .def("BASIC_SIZE", +[]{return FP_BLOCK_SIZE;})
      .staticmethod("BASIC_SIZE")
      .def("BRANCHING_FACTOR", +[]{return FP_BRANCH_SIZE;})
      .staticmethod("BRANCHING_FACTOR")
      .def("tree", Fingerprint__tree__
        , "Builds a Python representation of the internal tree.  For testing."
        )
      ;

    // For testing.
    class_<fingerprints::Block>("Block", no_init)
      .def_readonly("used", &fingerprints::Block::used)
      .def_readonly("lr", &fingerprints::Block::lr)
      .def("values", +[](fingerprints::Block const & self) -> object
        {
          boost::python::list values;
          for(size_t i=0; i<FP_BLOCK_SIZE; ++i)
            values.append(
                (self.used & (1<<i)) ? (self.lr & (1<<i)) ? 1 : -1 : 0
              );
          return values;
        })
      .def("__eq__", +[](
          fingerprints::Block const & lhs, fingerprints::Block const & rhs
        ) -> bool
        { return lhs.used == rhs.used && lhs.lr == rhs.lr; })
      .def("__repr__", +[](object const & self) -> object
        {
          return boost::python::str(self.attr("values")());
        })
      ;
  }
}}

