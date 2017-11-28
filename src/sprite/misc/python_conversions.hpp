#pragma once
#include <boost/python.hpp>
#include <boost/python/stl_iterator.hpp>

#define DECL_PYTHON_CONVERSION(name, type, prereqs)              \
    struct name {                                                \
      /* Register this converter. */                             \
      static void init()                                         \
        { prereqs; ::sprite::register_conversion<name,type>(); } \
                                                                 \
      /* C++ to Python. */                                       \
      static PyObject * convert(type const &);                   \
                                                                 \
      /* Python to C++. */                                       \
      static void * check(PyObject *);                           \
      static void construct(                                     \
          PyObject *                                             \
        , converter::rvalue_from_python_stage1_data *            \
        );                                                       \
    }                                                            \
  /**/



namespace sprite
{
  using namespace ::boost::python;

  template<typename Converter, typename T>
  void register_conversion()
  {
    type_info const ty = type_id<T>();
    converter::registration const * reg = converter::registry::query(ty);
    if(!reg || !(*reg).m_to_python)
    {
      to_python_converter<T, Converter>();
      converter::registry::push_back(
          &Converter::check, &Converter::construct, ty
        );
    }
  }

  // ====== IterableRangeConversion ======

  // Handles conversions from a Python iterable to C++.
  template<typename ValueType>
  struct IterableRange
  {
    typedef stl_input_iterator<ValueType> iterator;
    typedef iterator const_iterator;
    IterableRange(object obj) : m_obj(obj) {}
    iterator begin() const { return iterator(m_obj); }
    iterator end() const { return iterator(); }
  private:
    object m_obj;
  };

  /// Registers a converter for an iterable range.
  template<typename ValueType>
  DECL_PYTHON_CONVERSION(
      IterableRangeConversion, IterableRange<ValueType>,
    );

  template<typename T>
  PyObject * IterableRangeConversion<T>::convert(
      IterableRange<T> const & range
    )
  {
    ::boost::python::list lst;
    for(auto && item: range)
      lst.append(item);
    return incref(lst.ptr());
  }

  template<typename ValueType>
  void * IterableRangeConversion<ValueType>::check(PyObject * obj)
    { return PyObject_HasAttrString(obj, "__iter__") ? obj : 0; }

  template<typename ValueType>
  void IterableRangeConversion<ValueType>::construct(
      PyObject * obj
    , converter::rvalue_from_python_stage1_data * data
    )
  {
    typedef converter::rvalue_from_python_storage<
        IterableRange<ValueType>
      > * storage_type;
    void * storage = (reinterpret_cast<storage_type>(data))->storage.bytes;

    object const o(borrowed(obj));
    data->convertible = new(storage) IterableRange<ValueType>(o);
  }

  // ====== VectorConversion ======

  template<typename T>
  DECL_PYTHON_CONVERSION(
      VectorConversion, std::vector<T>, IterableRangeConversion<T>::init();
    );

  template<typename T>
  PyObject * VectorConversion<T>::convert(std::vector<T> const & vec)
  {
    ::boost::python::list lst;
    for(auto && item: vec)
      lst.append(item);
    return incref(lst.ptr());
  }

  template<typename T>
  void * VectorConversion<T>::check(PyObject * obj)
    { return IterableRangeConversion<T>::check(obj); }

  template<typename T>
  void VectorConversion<T>::construct(
      PyObject * obj
    , converter::rvalue_from_python_stage1_data * data
    )
  {
    using vec_t = std::vector<T>;
    using storage_type = converter::rvalue_from_python_storage<vec_t> *;
    void * storage = (reinterpret_cast<storage_type>(data))->storage.bytes;
    vec_t * vec = new(storage) vec_t();
    try
    {
      // Getting the length could fail, e.g., for a generator, and that's OK.
      auto n = PySequence_Length(obj);
      if(n >= 0) vec->reserve(n);
      IterableRange<T> range = extract<IterableRange<T>>(obj);
      for(auto && item: range)
        vec->push_back(item);
      data->convertible = vec;
    }
    catch(...)
    {
      vec->~vec_t();
      throw;
    }
  }
}
