#pragma once
#include "curryrt/fwd.hpp"

// The bill of materials of a generated module, as the generated code spells
// it.
//
// A module names its imports, its data types with their constructors, its
// functions, and the metadata of each of them.  The generated code writes
// these as static arrays of the records below.  Every member of a record is
// an integer, a pointer, or a string literal.  So the compiler writes the
// arrays as data: it instantiates no template for them, and no constructor
// runs when the module loads.  The module exports one bom::Module record under
// the name _bom_.  The loader reads it, checks its version, binds the slots
// of the module, and decodes it into a ModuleBOM (curryrt/dynload.hpp), the
// form the runtime and the Python bindings read.
//
// The slots.  The code of a module reads every info table and data type it
// names through a slot: a static pointer of the module, null until the
// loader fills it (the binding in curryrt/dynload.hpp).  A symbol the module
// defines has its table in the object and a slot beside it (Function::slot,
// Type::slot, Type::ctor_slots); the loader points the slot at the table of
// the symbol in this process, which is the table of the object unless the
// module was interpreted first, when it is the table the interpreter made.
// A symbol of another module, or a built-in of the runtime, has a slot alone
// (InfoSlot, TypeSlot), which the loader fills from the registry of the
// loaded modules.  So one table serves a symbol for the life of the
// process, on every platform: the object binds to no table by dynamic
// symbol, and the dynamic linker never needs to interpose one.
namespace curryrt { namespace bom
{
  // The layout version of these records.  The generated code writes it into
  // the module record, and the loader refuses a module of another version.
  // Raise it with every change to a record of this header.  Version 2: the
  // slots (issue #163).
  static constexpr unsigned VERSION = 2;

  // The kind of a metadata value.  MDValue holds a string, an int, or a bool.
  enum Kind : int { STRING = 0, INTEGER = 1, BOOLEAN = 2 };

  // One metadata entry.  A STRING entry holds its value in text; an INTEGER
  // or BOOLEAN entry holds it in number (0 or 1 for a BOOLEAN).
  struct Entry
  {
    char const * key;
    Kind         kind;
    int          number;
    char const * text;
  };

  // A metadata object: size entries.  entries is null when size is 0.
  struct Metadata
  {
    Entry const * entries;
    unsigned      size;
  };

  // An alias of a symbol.
  struct Alias
  {
    char const * name;
    char const * target;
  };

  // A data type: its metadata, the metadata of each constructor in the order
  // of type->ctors (null when the type has no constructor), the type as the
  // object defines it, the slot of the type, and the slot of each
  // constructor, in the order of type->ctors (null when the type has no
  // constructor).
  struct Type
  {
    Metadata const *          metadata;
    Metadata const * const *  constructors;
    DataType const *          type;
    DataType const * *        slot;
    InfoTable const * * const * ctor_slots;
  };

  // A function: its visibility, its metadata, its info table as the object
  // defines it, and the slot of the table.
  struct Function
  {
    Visibility         visibility;
    Metadata const *   metadata;
    InfoTable const *  info;
    InfoTable const ** slot;
  };

  // The slot of a symbol the module does not define: the module that
  // defines the symbol, its name there, and the slot.  An InfoSlot names a
  // function or a constructor, a TypeSlot a data type.
  struct InfoSlot
  {
    char const *       module;
    char const *       name;
    InfoTable const ** slot;
  };

  struct TypeSlot
  {
    char const *      module;
    char const *      name;
    DataType const ** slot;
  };

  // The module record.  Each array comes with its length; an empty array is
  // null.  filename is null when the module has no source file.
  struct Module
  {
    unsigned             version;
    char const *         fullname;
    char const *         filename;
    char const * const * imports;
    unsigned             n_imports;
    Metadata const *     metadata;
    Alias const *        aliases;
    unsigned             n_aliases;
    Type const *         types;
    unsigned             n_types;
    Function const *     functions;
    unsigned             n_functions;
    InfoSlot const *     info_slots;
    unsigned             n_info_slots;
    TypeSlot const *     type_slots;
    unsigned             n_type_slots;
  };
}}
