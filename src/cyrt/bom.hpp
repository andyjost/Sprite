#pragma once
#include "cyrt/fwd.hpp"

// The bill of materials of a generated module, as the generated code spells
// it.
//
// A module names its imports, its data types with their constructors, its
// functions, and the metadata of each of them.  The generated code writes
// these as static arrays of the records below.  Every member of a record is
// an integer, a pointer, or a string literal.  So the compiler writes the
// arrays as data: it instantiates no template for them, and no constructor
// runs when the module loads.  The module exports one bom::Module record under
// the name _bom_.  The loader reads it, checks its version, and decodes it
// into a ModuleBOM (cyrt/dynload.hpp), the form the runtime and the Python
// bindings read.
namespace cyrt { namespace bom
{
  // The layout version of these records.  The generated code writes it into
  // the module record, and the loader refuses a module of another version.
  // Raise it with every change to a record of this header.
  static constexpr unsigned VERSION = 1;

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
  // of type->ctors (null when the type has no constructor), and the type.
  struct Type
  {
    Metadata const *         metadata;
    Metadata const * const * constructors;
    DataType const *         type;
  };

  // A function: its visibility, its metadata, and its info table.
  struct Function
  {
    Visibility        visibility;
    Metadata const *  metadata;
    InfoTable const * info;
  };

  // The module record.  Each array comes with its length; an empty array is
  // null.  filename is null when the module has no source file.
  struct Module
  {
    unsigned            version;
    char const *        fullname;
    char const *        filename;
    char const * const * imports;
    unsigned            n_imports;
    Metadata const *    metadata;
    Alias const *       aliases;
    unsigned            n_aliases;
    Type const *        types;
    unsigned            n_types;
    Function const *    functions;
    unsigned            n_functions;
  };
}}
