#include "curryrt/image.hpp"
#include "curryrt/icurry.hpp"
#include "curryrt/bigint.hpp"
#include <cstring>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <unordered_map>

namespace
{
  using namespace curryrt;

  struct Reader
  {
    ModuleRegistry registry;
    std::string data;
    size_t pos = 0;
    std::unordered_map<std::string, Node *> integers;
    std::unordered_map<uint32_t, Node *> characters;
    std::unordered_map<uint64_t, Node *> floats;
    explicit Reader(ModuleRegistry registry, std::string const & path) : registry(std::move(registry))
    {
      std::ifstream in(path, std::ios::binary);
      if(!in) fail("cannot open file");
      data.assign(std::istreambuf_iterator<char>(in), {});
    }
    [[noreturn]] static void fail(char const * reason)
      { throw std::invalid_argument(std::string("invalid module image: ") + reason); }
    void need(size_t n)
      { if(n > data.size() - pos) fail("truncated section"); }
    uint32_t word()
    {
      need(4);
      uint32_t n = 0;
      for(unsigned i=0; i<4; ++i)
        n |= uint32_t((unsigned char)data[pos++]) << (8*i);
      return n;
    }
    uint32_t count()
    {
      auto n = word();
      if(n > data.size() - pos) fail("invalid count");
      return n;
    }
    std::string text()
    {
      auto n = word();
      need(n);
      auto out = data.substr(pos, n);
      pos += n;
      return out;
    }
    double real()
    {
      need(8);
      uint64_t bits = 0;
      for(unsigned i=0; i<8; ++i)
        bits |= uint64_t((unsigned char)data[pos++]) << (8*i);
      double out;
      std::memcpy(&out, &bits, 8);
      return out;
    }
    Metadata metadata()
    {
      Metadata out;
      for(auto n=count(); n; --n)
      {
        auto key = text();
        auto kind = word();
        if(kind == 0) out.emplace(key, text());
        else if(kind == 1) out.emplace(key, int(word()));
        else if(kind == 2) out.emplace(key, word() != 0);
        else fail("unknown metadata kind");
      }
      return out;
    }
    Metadata const * metadata(ModuleBOM & bom)
    {
      bom.metadata_store.push_back(metadata());
      return &bom.metadata_store.back();
    }
    InfoTable const * symbol()
    {
      auto module = text();
      auto name = text();
      auto info = Module::find_symbol(registry, module, name);
      if(!info)
      {
        auto builtin = Module::builtin_symbol(module, name);
        if(builtin && builtin->tag != T_FUNC) info = builtin;
      }
      if(!info) throw std::invalid_argument(
          "invalid module image: unresolved symbol " + module + "." + name);
      return info;
    }
    void skip_constant()
    {
      switch(word())
      {
        case 'R': case 'T': text(); text(); break;
        case 'P': text(); text(); word(); break;
        case 'I': case 'S': text(); break;
        case 'C': word(); break;
        case 'F': real(); break;
        case 'V':
        {
          auto kind = word();
          for(auto n=count(); n; --n)
          {
            if(kind == 'i' || kind == 'p') text();
            else if(kind == 'c') word();
            else if(kind == 'f') real();
            else fail("unknown literal case kind");
          }
          break;
        }
        default: fail("unknown constant kind");
      }
    }
    void const * constant(Bytecode & bc)
    {
      auto kind = word();
      switch(kind)
      {
        case 'R': return symbol();
        case 'T':
        {
          auto info = symbol();
          if(!info->type) fail("symbol has no data type");
          return info->type;
        }
        case 'I':
        {
          auto digits = text();
          Node *& node = integers[digits];
          if(!node)
          {
            try
            {
              auto value = unboxed_int_type(std::stoll(digits));
              node = SMALL_INT_MIN <= value && value <= SMALL_INT_MAX
                  ? int_(value) : literal_node(&Int_Info, Arg(value));
            }
            catch(std::out_of_range const &)
              { node = integer(digits.c_str(), true); }
          }
          return node;
        }
        case 'C':
        {
          auto value = word();
          Node *& node = characters[value];
          if(!node) node = value <= SMALL_CHAR_MAX ? char_(value)
              : literal_node(&Char_Info, Arg(unboxed_char_type(value)));
          return node;
        }
        case 'F':
        {
          auto value = real();
          uint64_t bits;
          std::memcpy(&bits, &value, sizeof(bits));
          Node *& node = floats[bits];
          if(!node) node = literal_node(&Float_Info, Arg(value));
          return node;
        }
        case 'S':
          bc.strings.push_back(text());
          return bc.strings.back().c_str();
        case 'P':
        {
          auto info = symbol();
          auto missing = word();
          return partial_node(info, missing);
        }
        case 'V':
        {
          auto vkind = word();
          bc.valuesets.emplace_back();
          auto & vs = bc.valuesets.back();
          for(auto n=count(); n; --n)
          {
            if(vkind == 'i') vs.args.emplace_back(unboxed_int_type(std::stoll(text())));
            else if(vkind == 'p') vs.args.emplace_back(integer(text().c_str(), true));
            else if(vkind == 'c') vs.args.emplace_back(unboxed_char_type(word()));
            else if(vkind == 'f') vs.args.emplace_back(real());
            else fail("unknown literal case kind");
          }
          vs.set.args = vs.args.data();
          vs.set.size = vs.args.size();
          vs.set.kind = vkind;
          return &vs.set;
        }
        default: fail("unknown constant kind");
      }
    }
  };
}

namespace curryrt
{
  std::unique_ptr<ModuleBOM> load_image(Module & owner, std::string const & path,
      std::string const & expected_header, bool attach_code, ModuleRegistry const * references)
  {
    Reader r(references ? *references : owner.registry, path);
    r.need(8);
    if(r.data.compare(0, 8, "SPRTIMG\0", 8)) Reader::fail("bad magic");
    r.pos = 8;
    if(r.word() != IMAGE_VERSION) Reader::fail("unsupported format version");
    // Header is validated by the plan before attachment, in Python.
    auto header = r.text();
    if(!expected_header.empty() && header != expected_header)
      Reader::fail("image changed before attachment");
    auto bom = std::make_unique<ModuleBOM>();
    bom->fullname = r.text();
    if(bom->fullname != owner.name) Reader::fail("wrong module name");
    for(auto n=r.count(); n; --n) bom->imports.push_back(r.text());
    for(auto n=r.count(); n; --n)
    {
      auto name = r.text();
      bom->aliases.emplace(name, r.text());
    }
    bom->metadata = r.metadata();
    if(attach_code) owner.keep_tables();
    for(auto n=r.count(); n; --n)
    {
      auto name = r.text();
      auto flags = r.word();
      auto md = r.metadata(*bom);
      std::vector<InfoTable const *> ctors;
      std::vector<Metadata const *> cmd;
      for(auto k=r.count(), i=0u; i<k; ++i)
      {
        auto cname = r.text();
        auto arity = r.word();
        auto cflags = r.word();
        cmd.push_back(r.metadata(*bom));
        auto info = owner.get_builtin_symbol(cname);
        if(!info) info = owner.get_infotable(cname);
        if(!info && attach_code) info = owner.create_infotable(cname, arity, i, cflags);
        if(!info) Reader::fail("missing summary constructor");
        ctors.push_back(info);
      }
      auto type = owner.get_builtin_type(name);
      if(!type) type = owner.get_type(name);
      if(!type && attach_code) type = owner.create_type(name, ctors, flags);
      if(!type) Reader::fail("missing summary type");
      bom->types.emplace_back(md, std::move(cmd), type);
    }
    std::vector<InfoTable const *> functions;
    for(auto n=r.count(); n; --n)
    {
      auto name = r.text();
      auto arity = r.word();
      auto flags = r.word();
      auto visibility = r.word();
      auto md = r.metadata(*bom);
      auto info = (flags & F_BUILTIN) ? owner.bind_builtin_symbol(name, arity) : nullptr;
      if(info && info->arity != arity) Reader::fail("primitive arity does not match external");
      if(!info && (flags & F_BUILTIN))
        Reader::fail(("primitive " + owner.name + "." + name + " is not registered in this runtime").c_str());
      if(!info) info = owner.get_infotable(name);
      if(!info && attach_code) info = owner.create_infotable(name, arity, T_FUNC, flags);
      if(!info) Reader::fail("missing summary function");
      functions.push_back(info);
      bom->functions.emplace_back(bool(visibility), md, info);
    }
    for(auto info: functions)
    {
      if(!attach_code)
      {
        r.word(); r.word(); r.word();
        auto bytes = size_t(r.count()) * 4;
        r.need(bytes);
        r.pos += bytes;
        for(auto n=r.count(); n; --n) r.skip_constant();
        continue;
      }
      auto bc = std::make_unique<Bytecode>();
      bc->nregs = r.word();
      bc->nvars = r.word();
      bc->nstack = r.word();
      for(auto n=r.count(); n; --n) bc->code.push_back(r.word());
      for(auto n=r.count(); n; --n) bc->consts.push_back(r.constant(*bc));
      // A table with code keeps it, as the materializer keeps it
      // (materialize.py): the function of a module of this name that
      // another incarnation interpreted or swapped to compiled code runs as
      // it did.  The trap step of the compile on first use is no code
      // (curryrt/module.hpp): the bytecode replaces it, as icurry_attach
      // allows, else a module that left an interpreter under interpret:off
      // while an object of it was alive keeps its trap into an import under
      // interpret:new, and its first use compiles where it must interpret.
      if(!bc->code.empty() && (!info->step || is_trapped(info)))
        icurry_attach(owner.registry, const_cast<InfoTable *>(info), std::move(bc));
    }
    if(r.word() != bom->functions.size()) Reader::fail("wrong summary count");
    for(auto & function: bom->functions)
      *const_cast<Metadata *>(std::get<1>(function)) = r.metadata();
    if(r.pos != r.data.size()) Reader::fail("trailing bytes");
    return bom;
  }
}
