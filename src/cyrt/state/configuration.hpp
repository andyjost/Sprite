#pragma once
#include <cassert>
#include "cyrt/builtins.hpp"
#include "cyrt/fingerprint.hpp"
#include "cyrt/fingerprint.hpp"
#include "cyrt/graph/cursor.hpp"
#include "cyrt/state/scan.hpp"
#include "cyrt/unionfind.hpp"
#include <iosfwd>
#include <memory>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>

namespace cyrt
{
  using StrictConstraints = std::shared_ptr<UnionFind>;
  using BindingMap = std::unordered_map<xid_type, Node *>;
  using Bindings = std::shared_ptr<BindingMap>;
  using Residuals = std::unordered_set<xid_type>;

  // A configuration belongs to the queues that hold it (see queue.hpp): one
  // queue, except after the escape of a choice from a set function, which
  // puts every configuration that has not made the choice into both queues
  // of the split.  A queue clones a shared configuration before it
  // evaluates it, and the last queue to let go of a configuration destroys
  // it.  The collector counts the live configurations: for the
  // leak checks of the tests, and to run a collection when they pile up in
  // the queues of set functions consumed only in part (see gc/wdgc.cpp).
  struct Configuration
  {
    Configuration(Node * root=nullptr)
      : root_storage(root)
      , root(this->root_storage)
      , scan(this->root)
      , strict_constraints(new UnionFind())
      , bindings(new BindingMap())
    { gc_configuration_created(); }

    Configuration(Node * root, Configuration const & obj)
      : root_storage(root)
      , root(this->root_storage)
      , scan(this->root)
      , fingerprint(obj.fingerprint)
      , strict_constraints(obj.strict_constraints)
      , bindings(obj.bindings)
      , residuals()
      , escape_all(obj.escape_all)
    { gc_configuration_created(); }

    ~Configuration() { gc_configuration_destroyed(); }

    // A configuration is cloned (clone), never copied.
    Configuration(Configuration const &) = delete;
    Configuration & operator=(Configuration const &) = delete;

    // Configurations come and go with every fork, so their blocks come from
    // a free list of the runtime instead of malloc (see configuration.cpp).
    static void * operator new(size_t);
    static void operator delete(void *, size_t);

    template<typename ... Args>
    static std::unique_ptr<Configuration> create(Args && ... args)
    {
      return std::unique_ptr<Configuration>(
          new Configuration(std::forward<Args>(args)...)
        );
    }

    std::unique_ptr<Configuration> clone(Node * root)
      { return Configuration::create(root, *this); }

    // The number of queues that hold this configuration.  See Queue.
    size_t            holders = 0;
    Node *            root_storage;
    Cursor            root;
    Scan              scan;
    Fingerprint       fingerprint;
    StrictConstraints strict_constraints;
    Bindings          bindings;
    Residuals         residuals;
    bool              escape_all = false;
    bool              forced_rotate = false;
    // The number of rewrite steps taken for this configuration.  Steps of a
    // nested set-function evaluation count as well.  See
    // RuntimeState::count_step.
    size_t            steps = 0;
    // The values of ``steps`` and of RuntimeState::steps_total when this
    // configuration last reached the stack limit.  NOLIMIT means never.  See
    // RuntimeState::unwind.
    size_t            unwind_steps = NOLIMIT;
    size_t            unwind_total = NOLIMIT;
    std::pair<Node *, std::string> error; // pair of (error_object, message)
    #ifdef SPRITE_SCHEDULER_COUNTERS
    // The serial number of this configuration, unique in the process and
    // never zero.  The nodes a step allocates carry it (see graph/memory.hpp)
    // for the shared-work counter of state/counters.hpp.  The field is last,
    // so the layout generated code reads is that of a plain build.
    size_t            serial = next_configuration_serial();
    static size_t next_configuration_serial();
    #endif

    Cursor cursor() const { return this->scan.cursor(); }
    xid_type grp_id(xid_type id) const
      { return this->strict_constraints->root(id); }
    xid_type grp_id() const;
    bool has_binding(xid_type id) const { return this->bindings->count(id); }
    std::string str() const;
    void str(std::ostream &) const;

    void clear_error();
    std::pair<Node *, std::string> pop_error();
    void set_error(std::string const &);
    void set_error(Node *, std::string const &);
    void raise_error();

    // Records a free variable the configuration waits on, with its group,
    // and takes both back.  See RuntimeState::ready and hnf_or_free.
    void add_residual(xid_type vid);
    void remove_residual(xid_type vid);
  };

  inline xid_type obj_id(Node * node) { return NodeU{node}.choice->cid; }

  template<typename T>
  inline T & write(std::shared_ptr<T> & shared)
  {
    if(shared.use_count() != 1)
      shared = std::shared_ptr<T>(new T(*shared));
    assert(shared.use_count() == 1);
    return *shared;
  }

  std::ostream & operator<<(std::ostream &, BindingMap const &);
  inline xid_type Configuration::grp_id() const { return this->grp_id(obj_id(this->root)); }
}

