from ...generic.currylib import prelude as generic_prelude
from .. import cyrtbindings as impl

PreludeSpecification = generic_prelude.PreludeSpecification

TYPE_METADATA = {
      'Bool'                  : {'cxx.symbolname': 'Bool_Type'  }
    , 'Char'                  : {'cxx.symbolname': 'Char_Type'  }
    , '[]'                    : {'cxx.symbolname': 'List_Type'  }
    , 'Float'                 : {'cxx.symbolname': 'Float_Type' }
    , 'Int'                   : {'cxx.symbolname': 'Int_Type'   }
    , 'IO'                    : {'cxx.symbolname': 'IO_Type'    }
    , 'Pair'                  : {'cxx.symbolname': 'Pair_Type'  }
    , 'Unit'                  : {'cxx.symbolname': 'Unit_Type'  }
  }

SYMBOL_METADATA = {
    # Constructors
      '_Failure'              : {'cxx.symbolname': 'Fail_Info'                }
    , '_StrictConstraint'     : {'cxx.symbolname': 'StrictConstraint_Info'    }
    , '_NonStrictConstraint'  : {'cxx.symbolname': 'NonStrictConstraint_Info' }
    , '_ValueBinding'         : {'cxx.symbolname': 'ValueBinding_Info'        }
    , '_Free'                 : {'cxx.symbolname': 'Free_Info'                }
    , '_Fwd'                  : {'cxx.symbolname': 'Fwd_Info'                 }
    , '_Choice'               : {'cxx.symbolname': 'Choice_Info'              }
    , '_PartApplic'           : {'cxx.symbolname': 'PartApplic_Info'          }
    , 'False'                 : {'cxx.symbolname': 'False_Info'               }
    , 'True'                  : {'cxx.symbolname': 'True_Info'                }
    , 'Char'                  : {'cxx.symbolname': 'Char_Info'                }
    , 'Float'                 : {'cxx.symbolname': 'Float_Info'               }
    , 'Int'                   : {'cxx.symbolname': 'Int_Info'                 }
    , 'IO'                    : {'cxx.symbolname': 'IO_Info'                  }
    , '()'                    : {'cxx.symbolname': 'Unit_Info'                }
    , '(,)'                   : {'cxx.symbolname': 'Pair_Info'                }
    , '[]'                    : {'cxx.symbolname': 'Nil_Info'                 }
    , ':'                     : {'cxx.symbolname': 'Cons_Info'                }

    # Constructors
    , '$##'                   : {'cxx.symbolname': 'applygnf_Info'         }
    , '$!'                    : {'cxx.symbolname': 'applyhnf_Info'         }
    , '$!!'                   : {'cxx.symbolname': 'applynf_Info'          }
    , '?'                     : {'cxx.symbolname': 'choice_Info'           }
    , '&'                     : {'cxx.symbolname': 'concurrentAnd_Info'    }
    , '=:='                   : {'cxx.symbolname': 'constrEq_Info'         }
    , '=:<='                  : {'cxx.symbolname': 'nonstrictEq_Info'      }
    , 'apply'                 : {'cxx.symbolname': 'apply_Info'            }
    , 'bindIO'                : {'cxx.symbolname': 'bindIO_Info'           }
    , 'catch'                 : {'cxx.symbolname': 'catch_Info'            }
    , 'cond'                  : {'cxx.symbolname': 'cond_Info'             }
    , 'constrEq'              : {'cxx.symbolname': 'constrEq_Info'         }
    , 'divInt'                : {'cxx.symbolname': 'divInt_Info'           }
    , 'ensureNotFree'         : {'cxx.symbolname': 'ensureNotFree_Info'    }
    , 'eqChar'                : {'cxx.symbolname': 'eqChar_Info'           }
    , 'eqFloat'               : {'cxx.symbolname': 'eqFloat_Info'          }
    , 'eqInt'                 : {'cxx.symbolname': 'eqInt_Info'            }
    , 'failed'                : {'cxx.symbolname': 'failed_Info'           }
    , 'getChar'               : {'cxx.symbolname': 'getChar_Info'          }
    , 'ltEqChar'              : {'cxx.symbolname': 'ltEqChar_Info'         }
    , 'ltEqFloat'             : {'cxx.symbolname': 'ltEqFloat_Info'        }
    , 'ltEqInt'               : {'cxx.symbolname': 'ltEqInt_Info'          }
    , 'minusInt'              : {'cxx.symbolname': 'minusInt_Info'         }
    , 'modInt'                : {'cxx.symbolname': 'modInt_Info'           }
    , 'negateFloat'           : {'cxx.symbolname': 'negateFloat_Info'      }
    , 'nonstrictEq'           : {'cxx.symbolname': 'nonstrictEq_Info'      }
    , 'plusInt'               : {'cxx.symbolname': 'plusInt_Info'          }
    , 'prim_acosFloat'        : {'cxx.symbolname': 'acosFloat_Info'        }
    , 'prim_acoshFloat'       : {'cxx.symbolname': 'acoshFloat_Info'       }
    , 'prim_appendFile'       : {'cxx.symbolname': 'appendFile_Info'       }
    , 'prim_asinFloat'        : {'cxx.symbolname': 'asinFloat_Info'        }
    , 'prim_asinhFloat'       : {'cxx.symbolname': 'asinhFloat_Info'       }
    , 'prim_atanFloat'        : {'cxx.symbolname': 'atanFloat_Info'        }
    , 'prim_atanhFloat'       : {'cxx.symbolname': 'atanhFloat_Info'       }
    , 'prim_constrEq'         : {'cxx.symbolname': 'constrEq_Info'         }
    , 'prim_cosFloat'         : {'cxx.symbolname': 'cosFloat_Info'         }
    , 'prim_coshFloat'        : {'cxx.symbolname': 'coshFloat_Info'        }
    , 'prim_divFloat'         : {'cxx.symbolname': 'divFloat_Info'         }
    , 'prim_error'            : {'cxx.symbolname': 'error_Info'            }
    , 'prim_expFloat'         : {'cxx.symbolname': 'expFloat_Info'         }
    , 'prim_intToFloat'       : {'cxx.symbolname': 'intToFloat_Info'       }
    , 'prim_ioError'          : {'cxx.symbolname': 'ioError_Info'          }
    , 'prim_logFloat'         : {'cxx.symbolname': 'logFloat_Info'         }
    , 'prim_minusFloat'       : {'cxx.symbolname': 'minusFloat_Info'       }
    , 'prim_nonstrictEq'      : {'cxx.symbolname': 'nonstrictEq_Info'      }
    , 'prim_ord'              : {'cxx.symbolname': 'ord_Info'              }
    , 'prim_plusFloat'        : {'cxx.symbolname': 'plusFloat_Info'        }
    , 'prim_putChar'          : {'cxx.symbolname': 'putChar_Info'          }
    , 'prim_readCharLiteral'  : {'cxx.symbolname': 'readCharLiteral_Info'  }
    , 'prim_readFile'         : {'cxx.symbolname': 'readFile_Info'         }
    , 'prim_readFloatLiteral' : {'cxx.symbolname': 'readFloatLiteral_Info' }
    , 'prim_readNatLiteral'   : {'cxx.symbolname': 'readNatLiteral_Info'   }
    , 'prim_readStringLiteral': {'cxx.symbolname': 'readStringLiteral_Info'}
    , 'prim_roundFloat'       : {'cxx.symbolname': 'roundFloat_Info'       }
    , 'prim_showCharLiteral'  : {'cxx.symbolname': 'showCharLiteral_Info'  }
    , 'prim_showFloatLiteral' : {'cxx.symbolname': 'showFloatLiteral_Info' }
    , 'prim_showIntLiteral'   : {'cxx.symbolname': 'showIntLiteral_Info'   }
    , 'prim_showStringLiteral': {'cxx.symbolname': 'showStringLiteral_Info'}
    , 'prim_sinFloat'         : {'cxx.symbolname': 'sinFloat_Info'         }
    , 'prim_sinhFloat'        : {'cxx.symbolname': 'sinhFloat_Info'        }
    , 'prim_sqrtFloat'        : {'cxx.symbolname': 'sqrtFloat_Info'        }
    , 'prim_tanFloat'         : {'cxx.symbolname': 'tanFloat_Info'         }
    , 'prim_tanhFloat'        : {'cxx.symbolname': 'tanhFloat_Info'        }
    , 'prim_timesFloat'       : {'cxx.symbolname': 'timesFloat_Info'       }
    , 'prim_truncateFloat'    : {'cxx.symbolname': 'truncateFloat_Info'    }
    , 'prim_writeFile'        : {'cxx.symbolname': 'writeFile_Info'        }
    , '_PyGenerator'          : {'cxx.symbolname': '_PyGenerator_Info'     }
    , '_PyString'             : {'cxx.symbolname': '_PyString_Info'        }
    , 'quotInt'               : {'cxx.symbolname': 'quotInt_Info'          }
    , 'remInt'                : {'cxx.symbolname': 'remInt_Info'           }
    , 'returnIO'              : {'cxx.symbolname': 'returnIO_Info'         }
    , 'seqIO'                 : {'cxx.symbolname': 'seqIO_Info'            }
    , 'timesInt'              : {'cxx.symbolname': 'timesInt_Info'         }
    # Unused PAKCS functions.
    , 'failure'               : {'cxx.symbolname': 'notused_Info'          }
    , 'ifVar'                 : {'cxx.symbolname': 'notused_Info'          }
    , 'letrec'                : {'cxx.symbolname': 'notused_Info'          }
    , 'prim_divInt'           : {'cxx.symbolname': 'notused_Info'          }
    , 'prim_eqChar'           : {'cxx.symbolname': 'notused_Info'          }
    , 'prim_eqFloat'          : {'cxx.symbolname': 'notused_Info'          }
    , 'prim_eqInt'            : {'cxx.symbolname': 'notused_Info'          }
    , 'prim_ltEqChar'         : {'cxx.symbolname': 'notused_Info'          }
    , 'prim_ltEqFloat'        : {'cxx.symbolname': 'notused_Info'          }
    , 'prim_ltEqInt'          : {'cxx.symbolname': 'notused_Info'          }
    , 'prim_minusInt'         : {'cxx.symbolname': 'notused_Info'          }
    , 'prim_modInt'           : {'cxx.symbolname': 'notused_Info'          }
    , 'prim_negateFloat'      : {'cxx.symbolname': 'notused_Info'          }
    , 'prim_plusInt'          : {'cxx.symbolname': 'notused_Info'          }
    , 'prim_quotInt'          : {'cxx.symbolname': 'notused_Info'          }
    , 'prim_readFileContents' : {'cxx.symbolname': 'notused_Info'          }
    , 'prim_remInt'           : {'cxx.symbolname': 'notused_Info'          }
    , 'prim_timesInt'         : {'cxx.symbolname': 'notused_Info'          }
    , 'unifEqLinear'          : {'cxx.symbolname': 'notused_Info'          }
    }

for f in generic_prelude.FUNCTIONS:
  if f.name in SYMBOL_METADATA:
    f.update_metadata(SYMBOL_METADATA[f.name])

for ty in generic_prelude.TYPES:
  for ctor in ty.constructors:
    if ctor.name in SYMBOL_METADATA:
      ctor.update_metadata(SYMBOL_METADATA[ctor.name])
  if ty.name in TYPE_METADATA:
    ty.update_metadata(TYPE_METADATA[ty.name])

