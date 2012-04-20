/**
 * @file
 * @brief Defines a basic implementation of the Module interface.
 */
#pragma once
#include "sprite/system.hpp"
#include <boost/assign.hpp>
#include <boost/bimap.hpp>

namespace sprite
{
  /**
   * @brief A basic implementation of the Module interface.
   * 
   * Derived classes may use the install_* members to conveniently define a
   * module.
   */
  struct UserModule : Module
  {
  protected:
    UserModule(Loader & loader) : m_loader(loader) {}
    virtual ~UserModule() {}
  private:
  
    /**
     * The module loader.
     *
     * @note This is only referenced during construction.
     */
    Loader & m_loader;
  
    /// The type of a bidirectional label-to-ID map.
    typedef boost::bimap<std::string, size_t> map_type;
  
    /// The map of operation names to IDs (and the reverse).
    map_type m_opers;
  
    /// The map of constructor names to IDs (and the reverse).
    map_type m_ctors;
  
  protected:
  
    /// Installs an operation as a member function.
    template<typename Derived>
    size_t install_oper(
        std::string const & label, void (Derived::*memfun)(Node &) const
      )
    {
      return this->install_oper(
          label
        , tr1::bind<void>(memfun, static_cast<Derived const *>(this), _1)
        );
    }
  
    /// Installs an operation as an h_func_type.
    size_t install_oper(std::string const & label, h_func_type h)
    {
      // Register the operation with the program.
      size_t const id = m_loader.insert_oper(label, h);
  
      // Install the label and ID in the symbol table for this module.
      boost::assign::insert(this->m_opers.left)(label,id);
  
      // Return the ID.
      return id;
    }
  
    /// Installs a constructor.
    size_t install_ctor(std::string const & label)
    {
      // Register the constructor with the program.
      size_t const id = m_loader.insert_ctor(label);
  
      // Install the label and ID in the symbol table for this module.
      boost::assign::insert(this->m_ctors.left)(label,id);
  
      // Return the ID.
      return id;
    }
  
  private:
    size_t _lookup(std::string const & label, map_type & map) const
    {
      typedef map_type::left_map::const_iterator iterator;
      iterator const p = map.left.find(label);
      if(p == map.left.end())
        { throw RuntimeError("Failed constructor or operation lookup."); }
      return p->second;
    }
  public:
  
    // ====== Module API ======
    virtual size_t find_ctor(std::string const & label)
      { return _lookup(label, this->m_ctors); }
  
    virtual size_t find_oper(std::string const & label)
      { return _lookup(label, this->m_opers); }
  };
}
