#pragma once
#include "cyrt/fwd.hpp"
#include <cstddef>
#include <iosfwd>
#include <string>

// A Char node holds one Unicode code point.  Text crosses the boundary of the
// runtime as UTF-8: the string literals in generated code, the files that
// readFile, writeFile, and appendFile touch, the standard streams of putChar
// and getChar, and the error messages.  These functions convert between the
// two forms.

namespace cyrt
{
  static constexpr unboxed_char_type MAX_CODE_POINT = 0x10FFFF;

  // Stands in for a malformed byte sequence, as in other Curry systems.
  static constexpr unboxed_char_type REPLACEMENT_CHAR = 0xFFFD;

  // The greatest length of the UTF-8 encoding of one code point.
  static constexpr size_t MAX_UTF8_LENGTH = 4;

  // Writes the UTF-8 encoding of one code point to ``out``, which holds at
  // least MAX_UTF8_LENGTH bytes.  Returns the number of bytes written.  A
  // value above MAX_CODE_POINT is written as REPLACEMENT_CHAR.
  size_t utf8_encode(char * out, unboxed_char_type);
  void utf8_encode(std::string & out, unboxed_char_type);
  void utf8_encode(std::ostream & out, unboxed_char_type);

  // The length of the sequence that starts with ``lead``: 1 to 4, or 0 when
  // the byte cannot start a sequence.
  size_t utf8_sequence_length(unsigned char lead);

  // Decodes the code point at ``pos``, which lies in [pos, end), and moves
  // ``pos`` past it.  A malformed sequence yields REPLACEMENT_CHAR: a byte
  // that starts no sequence consumes one byte, and a sequence cut short, by
  // the end of the input or by a byte that cannot continue it, consumes the
  // bytes read so far.  That is the practice the Unicode standard
  // recommends, and what the 'replace' handler of Python does, so the two
  // backends decode a malformed file alike.
  unboxed_char_type utf8_decode(char const *& pos, char const * end);
}
