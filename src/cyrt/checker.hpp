#pragma once
// The checker of the run-time invariants of the Fair Scheme: the checker
// mode of section 6.5 of the memo on the Fair Scheme proofs, behind the
// interpreter flag ``checker``.  This is the C++ mirror of the checker of
// the Python backend (backends/py/eval/checker.py).  The runtime state holds
// one Checker while the flag is on (RuntimeState::checker) and null
// otherwise; every hook in the runtime is one test of that pointer.  The
// checker observes.  It changes no step, no value and no counter.  A
// violation throws InvariantViolation, whose message names the invariant,
// the event, the configuration, the identifiers and the goal position; the
// bindings hand it to Python as an AssertionError of the same name.
//
// This header is outside the include closure of cyrt/cyrt.hpp: the
// generated code never sees it, and the hooks reach the checker through the
// pointer in the runtime state.  The events and the checks are those of the
// Python checker; its module documentation lists them, and the developer
// notes state where the two differ.
#include "cyrt/fwd.hpp"
#include "cyrt/graph/cursor.hpp"
#include "cyrt/graph/memory.hpp"
#include <cstddef>
#include <cstdint>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace cyrt
{
  // The number of cells one reduct comparison may read.  An event whose
  // reducts are larger is counted (over_budget) and not compared.
  static constexpr size_t CHECKER_SIGNATURE_BUDGET = 5000;
  // The number of cells the entry walk of a capsule may flag.  A capsule
  // with a larger argument is counted and its S0 checks are skipped.
  static constexpr size_t CHECKER_ENTRY_BUDGET = 50000;
  // The number of fresh cells one step, one pull-tab or one copy may flag.
  static constexpr size_t CHECKER_PROPAGATE_BUDGET = 1024;
  // The number of cells a description of an expression prints.
  static constexpr size_t CHECKER_TEXT_LIMIT = 48;

  // A run-time invariant of the Fair Scheme does not hold.
  struct InvariantViolation : std::logic_error
  {
    InvariantViolation(
        std::string invariant, std::string event, std::string detail
      , std::string const & message
      );
    std::string invariant;
    std::string event;
    std::string detail;
  };

  // A set of sets of set functions: small, unordered, without repetition.
  using SetList = std::vector<Set *>;
  // A path of successor indices.
  using PathList = std::vector<index_type>;
  // An entry of a fingerprint.
  using FpEntry = std::pair<xid_type, ChoiceState>;

  struct CheckerTree;

  struct Checker
  {
    explicit Checker(RuntimeState &);
    ~Checker();
    Checker(Checker const &) = delete;
    Checker & operator=(Checker const &) = delete;

    // The hooks, at the events of the Python checker.
    //
    // A fork (rts_fingerprint.cpp): after the clones went into the queue
    // and before the parent leaves it.  ``clones`` are the clones the
    // queue took.
    void fork(
        Queue *, Configuration * parent, Configuration * const * clones
      , size_t nclones
      );
    // An escape, rule SF.1 (allValues_step): after the split of ``kept``
    // on ``cid``; ``before`` lists its configurations before the split and
    // ``moved`` is the new queue.
    void escape(
        Queue * kept, xid_type cid, std::vector<Configuration *> const & before
      , Queue * moved
      );
    // A pull-tab (RuntimeState::pull_tab): before the copies of the spine
    // are made, with the scan of C at the target, and after the choice over
    // the copies is made.  The forms with a path serve the tests.
    void pulltab_begin(Configuration *, Node * source, Node * target);
    void pulltab_begin_at(
        Configuration *, Node * source, Node * target, PathList const & path
      );
    void pulltab_end(
        Configuration *, Node * source, Node * target, Node * lhs, Node * rhs
      , Node * result
      );
    void pulltab_end_at(
        Configuration *, Node * source, Node * target, PathList const & path
      , Node * lhs, Node * rhs, Node * result
      );
    // A yield (release_value): before the value is made.
    void yield_(Configuration *);
    // A fresh free variable (freshvar).
    void variable(Node *);
    // A generator for the variable ``x`` (_make_generator, clone_generator).
    void generator(Node * x, Node * gen);
    // The value bindings of a variable of a built-in type (replace_freevar).
    void value_bindings(Node * x, Node * tree);
    // The write of a generator into the slot of a variable, rule S.x
    // (instantiate, and the slot write of an existing generator in
    // replace_freevar): before and after the write.  ``event`` names the
    // site in a report.
    void instantiate_begin(
        Configuration *, Variable const *, Node * gen, char const * event
      );
    void instantiate_end(Configuration *, Variable const *, char const * event);
    // A private copy of the spine (rule N.x; replace_freevar): after the
    // copy is made and before it replaces the node in the slot ``root``,
    // which still holds ``old``.  ``end`` is the node at the end of the
    // copy and ``kind`` names the replacement.  The form with a path serves
    // the tests.
    void copied(
        Configuration *, Cursor root, Node * old_root, Node * new_root
      , Node * end, char const * kind
      );
    void copied_at(
        Configuration *, Node * old_root, Node * new_root, PathList const & path
      , Node * end, char const * kind
      );
    // A step (procS): before the step function runs, and after it returned
    // ``status``.  A status below E_RESTART is not a completed step.
    void step_begin(Configuration *);
    void step_end(Configuration *, tag_type status);
    // An inductive position (hnf, at entry).
    void hnf(Configuration *, Variable const * inductive);
    // The entry of a capsule (evalS_step): the goal of the new queue.
    void capsule_entry(Set *, Node * goal);

    // For the tests: the pieces of the checks on constructed objects.
    void check_clone(Configuration * clone, xid_type cid, Configuration * parent);
    void check_failed_step(
        Configuration *, InfoTable const *, std::vector<Node *> const & args
      );
    void tag(xid_type, Set *);
    void note_escape(Set *, xid_type);
    void attach_generator(Node * x, Node * gen);
    CheckerTree const * tree_of(InfoTable const *);
    std::vector<FpEntry> entries(Configuration const *) const;

    // The counts of the events, by name: forks, escapes, pulltabs, yields,
    // generators, instantiations, slot_writes, copies, steps, hnfs,
    // hnf_untracked, capsules, violations, over_budget, ...
    std::map<std::string, size_t> counts;

  private:
    friend struct CheckerTreeAccess;
    struct SigState;
    friend struct SigState;
    struct StepRecord
    {
      Node * redex;
      InfoTable const * info;
      size_t offset;
      size_t nargs;
    };
    struct ReductRecord
    {
      Configuration * cfg;
      uint64_t sig;
    };

    // Reporting.
    [[noreturn]] void violation(
        char const * invariant, char const * event, std::string const & detail
      , Configuration * cfg = nullptr, std::vector<xid_type> ids = {}
      , std::vector<std::string> extra = {}
      );
    std::vector<std::string> describe(Configuration *);
    std::string text(Node *, size_t limit = CHECKER_TEXT_LIMIT);
    std::string set_name(Set *);
    std::string set_names(SetList const &);

    // Read-only views of the state.
    Configuration * current();
    ChoiceState decision(xid_type, Configuration *);
    Node * binding(Configuration *, xid_type vid);
    SetList boxes_above();
    SetList const & flags_of(Node *);
    SetList const & tags_of(xid_type);
    std::vector<Configuration *> chain(bool include_current);
    void root_node(Node *);

    // B1.
    void check_fingerprint(
        Configuration *, char const * event
      , std::vector<Configuration *> const & chain
      );
    void check_escape_sets(char const * event, Configuration *);
    void check_spine_copy(
        Node * root, PathList const & path, Node * copy, Node * end
      , char const * invariant, char const * event, char const * side
      , Configuration *
      );
    void check_value(Configuration *);
    void check_decided_variables(Configuration *);

    // FS-x.
    bool reducts(Node * watch, std::vector<ReductRecord> &);
    void compare_reducts(
        std::vector<ReductRecord> const &, char const * event, xid_type vid
      );
    uint64_t sig(Node *, Configuration *, SigState &);

    // FS-S.
    void propagate(Node *, SetList const & flags, Node * stop_at);
    bool scan_path(Configuration *, Node * source, PathList &);

    // B2.
    void check_position(
        Node * redex, CheckerTree const *, PathList const &, Configuration *
      );
    void check_exempt(
        InfoTable const *, std::vector<Node *> const & args
      , CheckerTree const *, Configuration *
      );

    RuntimeState & rts;
    // The tags of an identifier: the sets of the boxes above its creation.
    std::unordered_map<xid_type, SetList> tags;
    // The kind of the creation of an identifier.
    std::unordered_map<xid_type, char const *> created;
    // The generator of a variable, by variable id (X1).
    std::unordered_map<xid_type, Node *> generators;
    // The shadow of every escape set: the insertions the hooks saw.
    std::unordered_map<Set *, std::unordered_set<xid_type>> escape_sets;
    // The sets whose entry walk exceeded its budget.
    std::unordered_set<Set *> unbounded_sets;
    // The flags of a cell: the capsules whose arguments reached it.
    std::unordered_map<Node *, SetList> flags;
    // The nodes the checker keeps alive: the flagged cells and a box of
    // every capsule it entered, so that the addresses in its tables stay
    // those of the objects they name.
    std::unordered_set<Node *> rooted;
    // A number per set, for the reports.
    std::unordered_map<Set *, size_t> set_serials;
    // The definitional trees, by the info table of the operation.
    std::unordered_map<InfoTable const *, std::unique_ptr<CheckerTree>> trees;
    // The steps in flight, innermost last, with the successors each redex
    // held before its step.
    std::vector<StepRecord> step_stack;
    std::vector<Node *> step_args;
    // The pull-tab in flight.
    PathList pt_path;
    // The queues an escape names, for the reports of its checks.
    std::vector<Queue *> describe_queues;
    // The slot write in flight.
    Variable const * inst_var = nullptr;
    Node * inst_gen = nullptr;
    xid_type inst_vid = NOXID;
    bool inst_valid = false;
    std::vector<ReductRecord> inst_reducts;
    // No node moves while the checker keys its tables by address.
    GcClamp clamp;
  };

  // A node of the definitional tree of an operation, rebuilt from the
  // bytecode of its ICurry body (cyrt/icurry.hpp): a case with the logical
  // path of its inductive variable and one subtree per constructor tag or
  // per literal value, or a leaf.  A return of a reference (RET_REF) is
  // told apart from a return of a built node: the redex forwards to the
  // node the reference denotes, which may be a failure, so a failure at the
  // redex after such a step is no replacement by failure.
  struct CheckerTree
  {
    enum Kind { CASE, EXEMPT, RETURN_REF, RETURN_NODE, UNKNOWN };
    Kind kind = UNKNOWN;
    // The inductive position, when the case variable is a position.
    bool position_known = false;
    PathList path;
    // A literal case, with the kind of its literals ('i', 'c', 'f').
    bool literal = false;
    char litkind = 0;
    std::map<uint64_t, std::unique_ptr<CheckerTree>> branches;
  };
}
