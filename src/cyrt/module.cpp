#include <algorithm>
#include <cstring>
#include "cyrt/builtins.hpp"
#include "cyrt/currylib/prelude.hpp"
#include "cyrt/currylib/setfunctions.hpp"
#include "cyrt/graph/infotable.hpp"
#include "cyrt/module.hpp"
#include <iostream>
#include <optional>
#include <unordered_map>

using namespace cyrt;
using SymbolTable = std::unordered_map<std::string, InfoTable const *>;
using TypeTable = std::unordered_map<std::string, DataType const *>;

namespace
{
  std::unordered_map<std::string, std::weak_ptr<Module>> g_modules;
}

namespace cyrt
{
  struct Module::Impl
  {
    SymbolTable symbols;
    TypeTable types;
    std::optional<SharedCurryModule> shlib;
  };

  SymbolTable const builtin_prelude_symbols{
      // Built-in types
      {"Char"                  , &Char_Info              }
    , {":"                     , &Cons_Info              }
    , {"False"                 , &False_Info             }
    , {"Float"                 , &Float_Info             }
    , {"Int"                   , &Int_Info               }
    , {"IO"                    , &IO_Info                }
    , {"[]"                    , &Nil_Info               }
    , {"(,)"                   , &Pair_Info              }
    , {"True"                  , &True_Info              }
    , {"()"                    , &Unit_Info              }
      // Built-in functions
    , {"constrEq"              , &constrEq_Info          }
    , {"$##"                   , &applygnf_Info          }
    , {"$!"                    , &applyhnf_Info          }
    , {"$!!"                   , &applynf_Info           }
    , {"?"                     , &choice_Info            }
    , {"&"                     , &concurrentAnd_Info     }
    , {"=:="                   , &constrEq_Info          }
    , {"=:<="                  , &nonstrictEq_Info       }
    , {"apply"                 , &apply_Info             }
    , {"bindIO"                , &bindIO_Info            }
    , {"catch"                 , &catch_Info             }
    , {"cond"                  , &cond_Info              }
    , {"constrEq"              , &constrEq_Info          }
    , {"divInt"                , &divInt_Info            }
    , {"ensureNotFree"         , &ensureNotFree_Info     }
    , {"eqChar"                , &eqChar_Info            }
    , {"eqFloat"               , &eqFloat_Info           }
    , {"eqInt"                 , &eqInt_Info             }
    , {"failed"                , &failed_Info            }
    , {"getChar"               , &getChar_Info           }
    , {"ltEqChar"              , &ltEqChar_Info          }
    , {"ltEqFloat"             , &ltEqFloat_Info         }
    , {"ltEqInt"               , &ltEqInt_Info           }
    , {"minusInt"              , &minusInt_Info          }
    , {"modInt"                , &modInt_Info            }
    , {"negateFloat"           , &negateFloat_Info       }
    , {"nonstrictEq"           , &nonstrictEq_Info       }
    , {"plusInt"               , &plusInt_Info           }
    , {"prim_acosFloat"        , &acosFloat_Info         }
    , {"prim_acoshFloat"       , &acoshFloat_Info        }
    , {"prim_appendFile"       , &appendFile_Info        }
    , {"prim_asinFloat"        , &asinFloat_Info         }
    , {"prim_asinhFloat"       , &asinhFloat_Info        }
    , {"prim_atanFloat"        , &atanFloat_Info         }
    , {"prim_atanhFloat"       , &atanhFloat_Info        }
    , {"prim_chr"              , &chr_Info               }
    // , {"prim_constrEq"         , &constrEq_Info          }
    , {"prim_cosFloat"         , &cosFloat_Info          }
    , {"prim_coshFloat"        , &coshFloat_Info         }
    , {"prim_divFloat"         , &divFloat_Info          }
    , {"prim_error"            , &error_Info             }
    , {"prim_expFloat"         , &expFloat_Info          }
    , {"prim_intToFloat"       , &intToFloat_Info        }
    , {"prim_ioError"          , &ioError_Info           }
    , {"prim_logFloat"         , &logFloat_Info          }
    , {"prim_minusFloat"       , &minusFloat_Info        }
    // , {"prim_nonstrictEq"      , &nonstrictEq_Info       }
    , {"prim_ord"              , &ord_Info               }
    , {"prim_plusFloat"        , &plusFloat_Info         }
    , {"prim_putChar"          , &putChar_Info           }
    , {"prim_readCharLiteral"  , &readCharLiteral_Info   }
    , {"prim_readFile"         , &readFile_Info          }
    , {"prim_readFloatLiteral" , &readFloatLiteral_Info  }
    , {"prim_readNatLiteral"   , &readNatLiteral_Info    }
    , {"prim_readStringLiteral", &readStringLiteral_Info }
    , {"prim_roundFloat"       , &roundFloat_Info        }
    , {"prim_showCharLiteral"  , &showCharLiteral_Info   }
    , {"prim_showFloatLiteral" , &showFloatLiteral_Info  }
    , {"prim_showIntLiteral"   , &showIntLiteral_Info    }
    , {"prim_showStringLiteral", &showStringLiteral_Info }
    , {"prim_sinFloat"         , &sinFloat_Info          }
    , {"prim_sinhFloat"        , &sinhFloat_Info         }
    , {"prim_sqrtFloat"        , &sqrtFloat_Info         }
    , {"prim_tanFloat"         , &tanFloat_Info          }
    , {"prim_tanhFloat"        , &tanhFloat_Info         }
    , {"prim_timesFloat"       , &timesFloat_Info        }
    , {"prim_truncateFloat"    , &truncateFloat_Info     }
    , {"prim_writeFile"        , &writeFile_Info         }
    , {"_PyGenerator"          , &_PyGenerator_Info      }
    , {"_PyString"             , &_PyString_Info         }
    , {"quotInt"               , &quotInt_Info           }
    , {"remInt"                , &remInt_Info            }
    , {"returnIO"              , &returnIO_Info          }
    , {"seqIO"                 , &seqIO_Info             }
    , {"timesInt"              , &timesInt_Info          }
    // Unused functions.
    , {"failure"               , &notused_Info           }
    , {"ifVar"                 , &notused_Info           }
    , {"letrec"                , &notused_Info           }
    , {"prim_readFileContents" , &notused_Info           }
    , {"unifEqLinear"          , &notused_Info           }
    };

  TypeTable const builtin_prelude_types{
      {"Bool" , &Bool_Type}
    , {"Char" , &Char_Type}
    , {"Float", &Float_Type}
    , {"Int"  , &Int_Type}
    , {"IO"   , &IO_Type}
    , {"[]"   , &List_Type}
    , {"(,)"  , &Pair_Type}
    , {"()"   , &Unit_Type}
    };

  SymbolTable const builtin_setfunction_symbols{
      {"PartialS", &PartialS_Info}
    , {"SetEval" , &SetEval_Info}
    , {"Values"  , &Values_Info}
    };

  std::shared_ptr<Module> Module::find_or_create(std::string name)
  {
    auto & slot = g_modules[name];
    if(auto handle = slot.lock())
      return handle;
    auto handle = std::make_shared<Module>(name);
    slot = handle;
    return handle;
  }

  std::map<std::string, std::shared_ptr<Module>> Module::getall()
  {
    std::map<std::string, std::shared_ptr<Module>> out;
    for(auto && item: g_modules)
    {
      if(auto p = item.second.lock())
        out[item.first] = p;
    }
    return out;
  }

  Module::Module(std::string name)
    : name(name), impl(new Impl)
  {
    if(name == "Prelude")
    {
      this->impl->symbols = builtin_prelude_symbols;
      this->impl->types = builtin_prelude_types;
    }
    else if(name == "Control.SetFunctions")
      this->impl->symbols = builtin_setfunction_symbols;
  }

  Module::~Module()
  {
    this->clear();
  }

  void Module::link(SharedCurryModule const * shlib)
  {
    if(shlib)
    {
      this->clear();
      this->impl->shlib = *shlib;
      for(auto && typedef_: shlib->bom->types)
      {
        DataType const * ty = std::get<2>(typedef_);
        this->impl->types[ty->name] = ty;
        for(size_t i=0; i<ty->size; ++i)
        {
          InfoTable const * info = ty->ctors[i];
          this->impl->symbols[info->name] = info;
        }
      }
      for(auto && funcdef: shlib->bom->functions)
      {
        InfoTable const * info = std::get<2>(funcdef);
        this->impl->symbols[info->name] = info;
      }
    }
  }

  void Module::clear()
  {
    for(auto & p_symbol: this->impl->symbols)
      if(!is_static(*p_symbol.second))
        delete[] (char *) p_symbol.second;
    this->impl->symbols.clear();

    for(auto & p_type: this->impl->types)
      if(!is_static(*p_type.second))
        delete[] (char *) p_type.second;
    this->impl->types.clear();
  }

  InfoTable const * Module::get_infotable(std::string const & name) const
  {
    auto p = this->impl->symbols.find(name);
    return (p != this->impl->symbols.end()) ? p->second : nullptr;
  }

  InfoTable const * Module::create_infotable(
      std::string const & name
    , index_type          arity
    , tag_type            tag
    , flag_type           flags
    )
  {
    assert(!this->get_infotable(name));
    size_t const bytes = sizeof(InfoTable) + name.size() + arity + 2;
    std::unique_ptr<char[]> mem(new char[bytes]);
    InfoTable * info = (InfoTable *) mem.get();
    char * info_name = (char *) (mem.get() + sizeof(InfoTable));
    char * format = info_name + name.size() + 1;
    info->tag        = tag;
    info->arity      = arity;
    info->alloc_size = sizeof(void *) * std::max(arity + 1, 2);
    info->flags      = flags;
    info->name       = info_name;
    info->format     = format;
    info->step       = nullptr;
    info->type       = nullptr;
    std::strcpy(info_name, name.c_str());
    index_type i=0;
    for(; i<arity; ++i)
      format[i] = 'p';
    format[i] = '\0';
    assert(&format[i+1] == mem.get() + bytes);
    this->impl->symbols[name] = (InfoTable const *) mem.release();
    return info;
  }

  DataType const * Module::get_type(std::string const & name) const
  {
    auto p = this->impl->types.find(name);
    return (p != this->impl->types.end()) ? p->second : nullptr;
  }

  DataType const * Module::create_type(
      std::string const & name
    , std::vector<InfoTable const *> constructors
    , flag_type flags
    )
  {
    assert(!this->get_type(name));
    size_t const bytes = sizeof(DataType) + sizeof(void *) * constructors.size() + name.size() + 1;
    std::unique_ptr<char[]> mem(new char[bytes]);
    DataType * type = (DataType *) mem.get();
    InfoTable const ** ctor_list = (InfoTable const **) (type + 1);
    char * type_name = (char *) &ctor_list[constructors.size()];
    type->ctors = ctor_list;
    type->size = constructors.size();
    type->kind = 't';
    type->flags = flags;
    type->name = type_name;
    size_t i=0;
    for(; i<constructors.size(); ++i)
    {
      auto ctor = const_cast<InfoTable *>(constructors[i]);
      ctor_list[i] = ctor;
      ctor->type = type;
    }
    std::strcpy(type_name, name.c_str());
    assert(type_name + name.size() + 1 == mem.get() + bytes);
    this->impl->types[name] = (DataType const *) mem.release();
    return type;
  }

  DataType const * Module::get_builtin_type(std::string const & name) const
  {
    auto * ty = this->get_type(name);
    return (ty && is_static(*ty)) ? ty : nullptr;
  }

  InfoTable const * Module::get_builtin_symbol(std::string const & name) const
  {
    auto * info = this->get_infotable(name);
    return (info && is_static(*info)) ? info : nullptr;
  }
}

