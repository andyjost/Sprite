/**
 * @file
 * @brief Defines the Fingerprint type.
 */
#pragma once
#include <boost/dynamic_bitset.hpp>

namespace sprite
{
  enum ChoiceDirection { LEFT=0, RIGHT=1 };

  /**
   * @brief A fingerprint specification.
   *
   * A fingerprint is an array of a known number of slots.  Each slot may be
   * used or unused and used slots may have the value LEFT or RIGHT.
   */
  struct Fingerprint
  {
    /**
     * Build an empty fingerprint.
     *
     * @param sz
     *   The size (number of slots) in the fingerprint.  Initially, they will
     *   all be valueless.
     */
    Fingerprint(size_t sz=0) : m_has(sz), m_at(sz) {}

    /// Returns true if the fingerprint contains the given id.
    bool has(size_t id) const { return this->m_has[id]; }

    /// Returns the value at id.  Precondition: this->has(id).
    ChoiceDirection at(size_t id) const
    {
      assert(this->has(id));
      return this->m_at[id] ? RIGHT : LEFT;
    }

    /// Extend or shrink the fingerprint without changing any values.
    void resize(size_t sz)
    {
      m_has.resize(sz);
      m_at.resize(sz);
    }

    /// Set the value at id.
    void set(size_t id, ChoiceDirection x)
    {
      this->m_has.set(id);
      this->m_at.set(id, x==LEFT ? false : true);
    }

    /// Returns the size of the fingerprint (largest id + 1).
    size_t size() const
    {
      assert(this->m_has.size() == this->m_at.size());
      return this->m_has.size();
    }
  private:
    typedef boost::dynamic_bitset<> storage_type;
    storage_type m_has, m_at;
  };
}
