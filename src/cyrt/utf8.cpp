#include "cyrt/utf8.hpp"
#include <cassert>
#include <ostream>

namespace cyrt
{
  size_t utf8_encode(char * out, unboxed_char_type cp)
  {
    if(cp > MAX_CODE_POINT)
      cp = REPLACEMENT_CHAR;
    if(cp < 0x80)
    {
      out[0] = (char) cp;
      return 1;
    }
    else if(cp < 0x800)
    {
      out[0] = (char) (0xC0 | (cp >> 6));
      out[1] = (char) (0x80 | (cp & 0x3F));
      return 2;
    }
    else if(cp < 0x10000)
    {
      out[0] = (char) (0xE0 | (cp >> 12));
      out[1] = (char) (0x80 | ((cp >> 6) & 0x3F));
      out[2] = (char) (0x80 | (cp & 0x3F));
      return 3;
    }
    else
    {
      out[0] = (char) (0xF0 | (cp >> 18));
      out[1] = (char) (0x80 | ((cp >> 12) & 0x3F));
      out[2] = (char) (0x80 | ((cp >> 6) & 0x3F));
      out[3] = (char) (0x80 | (cp & 0x3F));
      return 4;
    }
  }

  void utf8_encode(std::string & out, unboxed_char_type cp)
  {
    char buf[MAX_UTF8_LENGTH];
    out.append(buf, utf8_encode(buf, cp));
  }

  void utf8_encode(std::ostream & out, unboxed_char_type cp)
  {
    char buf[MAX_UTF8_LENGTH];
    out.write(buf, utf8_encode(buf, cp));
  }

  size_t utf8_sequence_length(unsigned char lead)
  {
    if(lead < 0x80) return 1;
    if(lead < 0xC0) return 0; // a continuation byte
    if(lead < 0xE0) return 2;
    if(lead < 0xF0) return 3;
    if(lead < 0xF8) return 4;
    return 0;
  }

  unboxed_char_type utf8_decode(char const *& pos, char const * end)
  {
    unsigned char const lead = (unsigned char) *pos++;
    size_t const length = utf8_sequence_length(lead);
    if(length == 1)
      return lead;
    if(length == 0)
      return REPLACEMENT_CHAR;
    // The range of the second byte.  It is narrower than 80..BF after a
    // lead that could begin an overlong encoding (E0, F0), a surrogate
    // (ED), or a value above MAX_CODE_POINT (F4).  C0, C1, and F5..F7 begin
    // no valid sequence.
    unsigned char lo = 0x80, hi = 0xBF;
    switch(lead)
    {
      case 0xC0: case 0xC1: case 0xF5: case 0xF6: case 0xF7:
        return REPLACEMENT_CHAR;
      case 0xE0: lo = 0xA0; break;
      case 0xED: hi = 0x9F; break;
      case 0xF0: lo = 0x90; break;
      case 0xF4: hi = 0x8F; break;
    }
    unboxed_char_type cp = lead & (0x7F >> length);
    char const * p = pos;
    for(size_t i=1; i<length; ++i, ++p)
    {
      // Cut short: the bytes read so far form one malformed sequence.
      if(p == end || (unsigned char) *p < lo || (unsigned char) *p > hi)
      {
        pos = p;
        return REPLACEMENT_CHAR;
      }
      cp = (cp << 6) | (*p & 0x3F);
      lo = 0x80;
      hi = 0xBF;
    }
    assert(cp <= MAX_CODE_POINT && !(0xD800 <= cp && cp <= 0xDFFF));
    pos = p;
    return cp;
  }
}
