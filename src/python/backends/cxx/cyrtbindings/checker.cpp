#include <string>
#include <memory>
#include <vector>
#include "cyrt/builtins.hpp"
#include "cyrt/checker.hpp"
#include "cyrt/currylib/setfunctions.hpp"
#include "cyrt/graph/indexing.hpp"
#include "cyrt/graph/memory.hpp"
#include "cyrt/graph/node.hpp"
#include "cyrt/state/rts.hpp"
#include "pybind11/pybind11.h"
#include "pybind11/stl.h"

namespace py = pybind11;
static auto constexpr reference = py::return_value_policy::reference;

// The bindings of the checker of the run-time invariants (cyrt/checker.hpp):
// the counts, and the debug entry points of its tests.  A debug entry corrupts
// one configuration of a runtime state on purpose, or calls one check of the
// checker on constructed nodes, so that the tests can provoke each report
// (tests/unit_cxx_checker.py).  Every entry needs the flag ``checker`` on
// for the state; the tests alone use them.
namespace
{
  using namespace cyrt;

  Checker & require(RuntimeState & rts)
  {
    if(!rts.checker)
      throw py::value_error("the checker is off for this runtime state");
    return *rts.checker;
  }

  Configuration * front(RuntimeState & rts, size_t index = 0)
  {
    Queue * Q = rts.Q();
    size_t k = 0;
    for(Configuration * C: *Q)
      if(k++ == index)
        return C;
    throw py::index_error("no configuration at that index of the current queue");
  }

  Queue * queue_at(RuntimeState & rts, size_t depth)
  {
    if(depth >= rts.qstack.size())
      throw py::index_error("no queue at that depth of the queue stack");
    return rts.qstack[rts.qstack.size() - 1 - depth];
  }

  Set * set_at(RuntimeState & rts, size_t depth)
  {
    Set * set = queue_at(rts, depth)->set;
    if(!set)
      throw py::value_error("the queue at that depth has no set");
    return set;
  }

  void set_side(Fingerprint & fp, xid_type cid, int side)
  {
    if(side == LEFT)
      fp.set_left(cid);
    else if(side == RIGHT)
      fp.set_right(cid);
    else
      throw py::value_error("the side is LEFT (-1) or RIGHT (1)");
  }

  PathList to_path(std::vector<size_t> const & path)
  {
    return PathList(path.begin(), path.end());
  }

  // The variable at ``path`` from the root of the front configuration.
  Variable variable_at(RuntimeState & rts, std::vector<size_t> const & path)
  {
    if(path.empty())
      throw py::value_error("the path is empty");
    Node * root = *rts.C()->root;
    Variable var(root, (index_type) path[0], false);
    for(size_t i = 1; i < path.size(); ++i)
      var = var[(index_type) path[i]];
    return var;
  }

  // Takes the queue of the innermost capsule off the queue stack for the
  // split of a debug entry, as allValues_step runs the split after the
  // nested evaluation returned, and puts it back on exit.
  struct Popped
  {
    explicit Popped(RuntimeState & rts) : rts(rts), Q(rts.Q())
    {
      if(rts.qstack.size() < 2)
        throw py::value_error("no capsule on the queue stack");
      rts.pop_queue();
    }
    ~Popped() { this->rts.push_queue(this->Q); }
    Popped(Popped const &) = delete;
    Popped & operator=(Popped const &) = delete;
    RuntimeState & rts;
    Queue * Q;
  };

  py::object tree_object(CheckerTree const * tree)
  {
    if(!tree)
      return py::none();
    py::dict d;
    switch(tree->kind)
    {
      case CheckerTree::CASE:        d["kind"] = "case"; break;
      case CheckerTree::EXEMPT:      d["kind"] = "exempt"; break;
      case CheckerTree::RETURN_REF:  d["kind"] = "return_ref"; break;
      case CheckerTree::RETURN_NODE: d["kind"] = "return"; break;
      default:                       d["kind"] = "unknown"; break;
    }
    if(tree->kind == CheckerTree::CASE)
    {
      if(tree->position_known)
        d["path"] = std::vector<size_t>(tree->path.begin(), tree->path.end());
      else
        d["path"] = py::none();
      d["literal"] = tree->literal;
      py::dict branches;
      for(auto const & branch: tree->branches)
        branches[py::int_(branch.first)] = tree_object(branch.second.get());
      d["branches"] = branches;
    }
    return std::move(d);
  }
}

namespace cyrt { namespace python
{
  void register_checker(pybind11::module_ mod)
  {
    mod.def("checker_enabled"
      , [](RuntimeState & rts) { return rts.checker != nullptr; }
      , "Whether the runtime state holds a checker (the flag ``checker``).");
    mod.def("checker_counts"
      , [](RuntimeState & rts)
        {
          py::dict d;
          for(auto const & entry: require(rts).counts)
            d[py::str(entry.first)] = entry.second;
          return d;
        }
      , "The counts of the events the checker saw, by name.");

    // The corruptions of the state.
    mod.def("checker_debug_set_fp"
      , [](RuntimeState & rts, xid_type cid, int side, size_t index)
        { require(rts); set_side(front(rts, index)->fingerprint, cid, side); }
      , py::arg("rts"), py::arg("cid"), py::arg("side"), py::arg("index") = 0
      , "Writes the decision of ``cid`` into the fingerprint of the "
        "configuration at ``index`` of the current queue.");
    mod.def("checker_debug_unite"
      , [](RuntimeState & rts, xid_type i, xid_type j)
        {
          require(rts);
          Configuration * C = front(rts);
          write(C->strict_constraints).unite(i, j);
          return C->grp_id(i);
        }
      , "Unites the groups of two identifiers in the front configuration and "
        "returns the root of the group.");
    mod.def("checker_debug_united"
      , [](RuntimeState & rts)
        { require(rts); return front(rts)->strict_constraints->united; }
      , "The ids the union-find of the front configuration united, in order "
        "and with repetitions (the ids the group check of B1 reads).");
    mod.def("checker_debug_bind"
      , [](RuntimeState & rts, xid_type vid, Node * node)
        { require(rts); write(front(rts)->bindings)[vid] = node; }
      , "Writes ``node`` as the binding of ``vid`` into the front "
        "configuration.");
    mod.def("checker_debug_set_root"
      , [](RuntimeState & rts, Node * node)
        {
          require(rts);
          Configuration * C = front(rts);
          *C->root = node;
          C->scan.reset();
        }
      , "Replaces the root of the front configuration.");
    mod.def("checker_debug_append"
      , [](RuntimeState & rts, Node * node)
        { require(rts); rts.append(Configuration::create(node)); }
      , "Appends a configuration over ``node`` to the current queue.");
    mod.def("checker_debug_push_capsule"
      , [](RuntimeState & rts, Node * goal) -> Node *
        {
          Checker & checker = require(rts);
          Set * set = new Set();
          Queue * Q = new Queue(set, goal);
          Node * seteval = Node::create(&SetEval_Info, set, Q);
          gc_register_seteval(seteval);
          rts.push_queue(Q);
          checker.capsule_entry(set, goal);
          return seteval;
        }
      , reference
      , "Pushes the queue of a new capsule over ``goal`` onto the queue stack "
        "and returns its SetEval node, which keeps the queue alive while the "
        "caller holds it.  checker_debug_pop_capsule takes the queue off.");
    mod.def("checker_debug_pop_capsule"
      , [](RuntimeState & rts)
        {
          require(rts);
          if(rts.qstack.size() < 2)
            throw py::value_error("no capsule to pop");
          rts.pop_queue();
        }
      , "Takes the queue of the innermost capsule off the queue stack.");
    mod.def("checker_debug_guard"
      , [](RuntimeState & rts, Node * value, size_t depth) -> Node *
        {
          require(rts);
          return Node::create(&SetGuard_Info, set_at(rts, depth), value);
        }
      , py::arg("rts"), py::arg("value"), py::arg("depth") = 0, reference
      , "A set guard of the set of the queue ``depth`` levels below the top "
        "of the queue stack, over ``value``.");
    mod.def("checker_debug_escape_insert"
      , [](RuntimeState & rts, xid_type cid, size_t depth, bool seen)
        {
          Checker & checker = require(rts);
          Set * set = set_at(rts, depth);
          set->escape_set.insert(cid);
          if(seen)
            checker.note_escape(set, cid);
        }
      , py::arg("rts"), py::arg("cid"), py::arg("depth") = 0
      , py::arg("seen") = false
      , "Inserts ``cid`` into the escape set of the set of the queue at "
        "``depth``: behind the back of the checker, or, with ``seen``, as an "
        "insertion the checker saw.");
    mod.def("checker_debug_escape_discard"
      , [](RuntimeState & rts, xid_type cid, size_t depth)
        { require(rts); set_at(rts, depth)->escape_set.erase(cid); }
      , py::arg("rts"), py::arg("cid"), py::arg("depth") = 0
      , "Removes ``cid`` from the escape set of the set of the queue at "
        "``depth``.");
    mod.def("checker_debug_tag"
      , [](RuntimeState & rts, xid_type cid, size_t depth)
        { require(rts).tag(cid, set_at(rts, depth)); }
      , py::arg("rts"), py::arg("cid"), py::arg("depth") = 0
      , "Tags ``cid`` as argument-derived for the set of the queue at "
        "``depth``.");

    // The checks on the live state.
    mod.def("checker_debug_check_yield"
      , [](RuntimeState & rts) { require(rts).yield_(front(rts)); }
      , "Runs the checks of a yield on the front configuration.");
    mod.def("checker_debug_check_fork"
      , [](RuntimeState & rts, std::vector<int> const & sides)
        {
          Checker & checker = require(rts);
          Configuration * C = front(rts);
          Node * root = *C->root;
          if(!root || root->info->tag != T_CHOICE)
            throw py::value_error("the root of the front configuration is not a choice");
          ChoiceNode * choice = NodeU{root}.choice;
          std::vector<std::unique_ptr<Configuration>> owned;
          std::vector<Configuration *> clones;
          for(int side: sides)
          {
            owned.push_back(C->clone(side == RIGHT ? choice->rhs : choice->lhs));
            if(side == LEFT || side == RIGHT)
              set_side(owned.back()->fingerprint, choice->cid, side);
            clones.push_back(owned.back().get());
          }
          checker.fork(rts.Q(), C, clones.data(), clones.size());
        }
      , py::arg("rts"), py::arg("sides") = std::vector<int>()
      , "Runs the checks of a fork on the front configuration, whose root "
        "must be a choice, with one clone per entry of ``sides``: a clone of "
        "the front configuration that decides the choice LEFT (-1) or RIGHT "
        "(1), or not at all (0).");
    mod.def("checker_debug_split"
      , [](RuntimeState & rts, xid_type cid)
        {
          Checker & checker = require(rts);
          Popped popped(rts);
          Queue * Q = popped.Q;
          std::vector<Configuration *> before(Q->begin(), Q->end());
          Queue * R = new Queue(Q->set);
          Q->split(cid, *R);
          checker.escape(Q, cid, before, R);
        }
      , "Splits the queue of the innermost capsule on ``cid`` (rule SF.1) and "
        "runs the checks of the escape, with the queue off the stack as at "
        "the escape of the runtime.");
    mod.def("checker_debug_check_escape_shared"
      , [](RuntimeState & rts, xid_type cid, bool record, bool foreign
          , bool other_set)
        {
          Checker & checker = require(rts);
          Popped popped(rts);
          Queue * Q = popped.Q;
          std::vector<Configuration *> before(Q->begin(), Q->end());
          Queue * R = new Queue(other_set ? new Set() : Q->set);
          Q->clone(*R, NOXID, nullptr);
          R->absorbed.erase(NOXID);
          if(foreign)
            R->push_back(Configuration::create(*Q->front()->root));
          if(record)
          {
            Q->decisions.push_back(cid);
            R->decisions.push_back(cid);
          }
          checker.escape(Q, cid, before, R);
        }
      , py::arg("rts"), py::arg("cid"), py::arg("record") = true
      , py::arg("foreign") = false, py::arg("other_set") = false
      , "Runs the checks of an escape on ``cid`` with a new queue that holds "
        "every configuration of the queue of the innermost capsule, decided "
        "or not.  Without ``record`` neither queue records the identifier; "
        "with ``foreign`` the new queue holds a configuration that was not "
        "in the queue; with ``other_set`` it names another set.");
    mod.def("checker_debug_check_clone"
      , [](RuntimeState & rts, std::vector<std::pair<xid_type, int>> const & parent
          , std::vector<std::pair<xid_type, int>> const & clone, xid_type cid)
        {
          Checker & checker = require(rts);
          Node * node = *front(rts)->root;
          Configuration P(node), C(node);
          for(auto const & entry: parent)
            set_side(P.fingerprint, entry.first, entry.second);
          for(auto const & entry: clone)
            set_side(C.fingerprint, entry.first, entry.second);
          checker.check_clone(&C, cid, &P);
        }
      , "Runs the check of rule D.2 on a parent and a clone with the given "
        "fingerprints, forked on ``cid``.");
    mod.def("checker_debug_pulltab_begin"
      , [](RuntimeState & rts, Node * source, Node * target
          , std::vector<size_t> const & path)
        { require(rts).pulltab_begin_at(front(rts), source, target, to_path(path)); }
      , "Runs the checks before a pull-tab of ``target`` at ``path`` of "
        "``source``.");
    mod.def("checker_debug_pulltab_end"
      , [](RuntimeState & rts, Node * source, Node * target
          , std::vector<size_t> const & path, Node * lhs, Node * rhs, Node * result)
        {
          require(rts).pulltab_end_at(
              front(rts), source, target, to_path(path), lhs, rhs, result
            );
        }
      , py::arg("rts"), py::arg("source"), py::arg("target"), py::arg("path")
      , py::arg("lhs"), py::arg("rhs"), py::arg("result") = nullptr
      , "Runs the checks after a pull-tab: ``lhs`` and ``rhs`` are the copies "
        "and ``result`` the created choice (None skips its check).");
    mod.def("checker_debug_freshvar"
      , [](RuntimeState & rts) -> Node * { require(rts); return rts.freshvar(); }
      , reference, "A fresh free variable of the state.");
    mod.def("checker_debug_generator"
      , [](RuntimeState & rts, Node * x, Node * gen) { require(rts).generator(x, gen); }
      , "Runs the checks of the creation of the generator ``gen`` for ``x``.");
    mod.def("checker_debug_attach_generator"
      , [](RuntimeState & rts, Node * x, Node * gen)
        { require(rts).attach_generator(x, gen); }
      , "Makes ``gen`` the generator of the free variable ``x`` and runs the "
        "checks of its creation.");
    mod.def("checker_debug_copied"
      , [](RuntimeState & rts, Node * old_root, Node * new_root
          , std::vector<size_t> const & path, Node * end, std::string const & kind)
        {
          require(rts).copied_at(
              front(rts), old_root, new_root, to_path(path), end, kind.c_str()
            );
        }
      , "Runs the checks of a private copy of the spine (rule N.x).");
    mod.def("checker_debug_instantiate_begin"
      , [](RuntimeState & rts, std::vector<size_t> const & path, Node * gen)
        {
          Variable var = variable_at(rts, path);
          require(rts).instantiate_begin(front(rts), &var, gen, "instantiation");
        }
      , "Runs the checks before the write of ``gen`` into the slot at ``path`` "
        "of the root of the front configuration.");
    mod.def("checker_debug_instantiate_end"
      , [](RuntimeState & rts, std::vector<size_t> const & path)
        {
          Variable var = variable_at(rts, path);
          require(rts).instantiate_end(front(rts), &var, "instantiation");
        }
      , "Runs the checks after the write into the slot at ``path``.");
    mod.def("checker_debug_check_hnf"
      , [](RuntimeState & rts, std::vector<size_t> const & path)
        {
          Variable var = variable_at(rts, path);
          require(rts).hnf(front(rts), &var);
        }
      , "Runs the check of an inductive position at ``path`` of the root of "
        "the front configuration, which must be an operation.");
    mod.def("checker_debug_check_failed_step"
      , [](RuntimeState & rts, Node * node)
        {
          if(!node)
            throw py::value_error("a null node");
          std::vector<Node *> args;
          for(index_type i = 0; i < node->info->arity; ++i)
            args.push_back(node->info->format[i] == 'p' ? node->successors()[i].node : nullptr);
          require(rts).check_failed_step(front(rts), node->info, args);
        }
      , "Runs the check of a step that replaced ``node`` by a failure.");
    mod.def("checker_debug_tree"
      , [](RuntimeState & rts, InfoTable const * info)
        { return tree_object(require(rts).tree_of(info)); }
      , "The definitional tree of an operation as nested dicts, or None for "
        "a built-in or a compiled function.");
  }
}}
