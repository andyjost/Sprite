#include "cyrt/currylib/prelude.hpp"
#include "cyrt/module.hpp"

using namespace cyrt;

static int register_prelude_builtins()
{
  TypeTable && builtin_prelude_types{
      {"Bool" , &Bool_Type}
    , {"Char" , &Char_Type}
    , {"Float", &Float_Type}
    , {"Int"  , &Int_Type}
    , {"IO"   , &IO_Type}
    , {"[]"   , &List_Type}
    , {"(,)"  , &Pair_Type}
    , {"()"   , &Unit_Type}
    };

  SymbolTable && builtin_prelude_symbols{
      // Built-in types
      {"Char"                  , &Char_Info                   }
    , {":"                     , &Cons_Info                   }
    , {"False"                 , &False_Info                  }
    , {"Float"                 , &Float_Info                  }
    , {"Int"                   , &Int_Info                    }
    , {"IO"                    , &IO_Info                     }
    , {"[]"                    , &Nil_Info                    }
    , {"(,)"                   , &Pair_Info                   }
    , {"True"                  , &True_Info                   }
    , {"()"                    , &Unit_Info                   }
      // Built-in functions
    , {"$##"                   , &applygnf_Info               }
    , {"$!"                    , &applyhnf_Info               }
    , {"$!!"                   , &applynf_Info                }
    , {"?"                     , &choice_Info                 }
    , {"&"                     , &concurrentAnd_Info          }
    , {"apply"                 , &apply_Info                  }
    , {"bindIO"                , &bindIO_Info                 }
    , {"catch"                 , &catch_Info                  }
    , {"cond"                  , &cond_Info                   }
    , {"constrEq"              , &constrEq_Info               }
    , {"divInt"                , &divInt_Info                 }
    , {"ensureNotFree"         , &ensureNotFree_Info          }
    , {"eqChar"                , &eqChar_Info                 }
    , {"eqFloat"               , &eqFloat_Info                }
    , {"eqInt"                 , &eqInt_Info                  }
    , {"failed"                , &failed_Info                 }
    , {"getChar"               , &getChar_Info                }
    , {"ltEqChar"              , &ltEqChar_Info               }
    , {"ltEqFloat"             , &ltEqFloat_Info              }
    , {"ltEqInt"               , &ltEqInt_Info                }
    , {"minusInt"              , &minusInt_Info               }
    , {"modInt"                , &modInt_Info                 }
    , {"negateFloat"           , &negateFloat_Info            }
    , {"nonstrictEq"           , &nonstrictEq_Info            }
    , {"plusInt"               , &plusInt_Info                }
    , {"prim_acosFloat"        , &prim_acosFloat_Info         }
    , {"prim_acoshFloat"       , &prim_acoshFloat_Info        }
    , {"prim_appendFile"       , &prim_appendFile_Info        }
    , {"prim_asinFloat"        , &prim_asinFloat_Info         }
    , {"prim_asinhFloat"       , &prim_asinhFloat_Info        }
    , {"prim_atanFloat"        , &prim_atanFloat_Info         }
    , {"prim_atanhFloat"       , &prim_atanhFloat_Info        }
    , {"prim_chr"              , &prim_chr_Info               }
    , {"prim_cosFloat"         , &prim_cosFloat_Info          }
    , {"prim_coshFloat"        , &prim_coshFloat_Info         }
    , {"prim_divFloat"         , &prim_divFloat_Info          }
    , {"prim_error"            , &prim_error_Info             }
    , {"prim_expFloat"         , &prim_expFloat_Info          }
    , {"prim_intToFloat"       , &prim_intToFloat_Info        }
    , {"prim_ioError"          , &prim_ioError_Info           }
    , {"prim_logFloat"         , &prim_logFloat_Info          }
    , {"prim_minusFloat"       , &prim_minusFloat_Info        }
    , {"prim_ord"              , &prim_ord_Info               }
    , {"prim_plusFloat"        , &prim_plusFloat_Info         }
    , {"prim_putChar"          , &prim_putChar_Info           }
    , {"prim_readCharLiteral"  , &prim_readCharLiteral_Info   }
    , {"prim_readFile"         , &prim_readFile_Info          }
    , {"prim_readFloatLiteral" , &prim_readFloatLiteral_Info  }
    , {"prim_readNatLiteral"   , &prim_readNatLiteral_Info    }
    , {"prim_readStringLiteral", &prim_readStringLiteral_Info }
    , {"prim_roundFloat"       , &prim_roundFloat_Info        }
    , {"prim_showCharLiteral"  , &prim_showCharLiteral_Info   }
    , {"prim_showFloatLiteral" , &prim_showFloatLiteral_Info  }
    , {"prim_showIntLiteral"   , &prim_showIntLiteral_Info    }
    , {"prim_showStringLiteral", &prim_showStringLiteral_Info }
    , {"prim_sinFloat"         , &prim_sinFloat_Info          }
    , {"prim_sinhFloat"        , &prim_sinhFloat_Info         }
    , {"prim_sqrtFloat"        , &prim_sqrtFloat_Info         }
    , {"prim_tanFloat"         , &prim_tanFloat_Info          }
    , {"prim_tanhFloat"        , &prim_tanhFloat_Info         }
    , {"prim_timesFloat"       , &prim_timesFloat_Info        }
    , {"prim_truncateFloat"    , &prim_truncateFloat_Info     }
    , {"prim_writeFile"        , &prim_writeFile_Info         }
    , {"_cGenerator"           , &_cGenerator_Info            }
    , {"_cString"              , &_cString_Info               }
    , {"quotInt"               , &quotInt_Info                }
    , {"remInt"                , &remInt_Info                 }
    , {"returnIO"              , &returnIO_Info               }
    , {"seqIO"                 , &seqIO_Info                  }
    , {"timesInt"              , &timesInt_Info               }
    // Unused functions.
    , {"failure"               , &failure_Info                }
    , {"ifVar"                 , &ifVar_Info                  }
    , {"letrec"                , &letrec_Info                 }
    , {"prim_readFileContents" , &prim_readFileContents_Info  }
    , {"unifEqLinear"          , &unifEqLinear_Info           }
    };

  Module::register_builtin_module(
      "Prelude"
    , std::move(builtin_prelude_types)
    , std::move(builtin_prelude_symbols)
    );
  return 0;
}

static int _ = register_prelude_builtins();
