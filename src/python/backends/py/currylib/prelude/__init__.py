from ....generic.currylib import prelude as generic_prelude
from . import prelude as impl
import math, operator as op

FUNCTIONS = generic_prelude.PreludeSpecification.FUNCTIONS + [
    ('_PyGenerator'          , 1, {'py.boxedfunc'  : impl._PyGenerator})
  , ('_PyString'             , 1, {'py.boxedfunc'  : impl._PyString   })
  ]

CONSTRUCTOR_METADATA = {
    ('_Failure'   , 0): {'py.format': 'failure'                       }
  , ('_PartApplic', 0): {'py.format': '{2}'                           }
  , ('_Free'      , 0): {'py.format': '_{1}'                          }
  , ('_Fwd'       , 0): {'py.format': '{1}'                           }
  , ('Int'        , 0): {'py.format': '{1}'                           }
  , ('Float'      , 0): {'py.format': '{1}'                           }
  , ('Char'       , 0): {'py.format': '{1}'                           }
  , ('[]'         , 0): {'py.format': '({1}:{2})'                     }
  , ('[]'         , 1): {'py.format': '[]'                            }
  , ('()'         , 0): {'py.format': '()'                            }
  }

for i in range(2, generic_prelude.MAX_TUPLE_SIZE):
  name = '(%s)' % (','*(i-1))
  tuple_format = '(%s)' % ', '.join(['{%d}' % j for j in range(1,i+1)])
  CONSTRUCTOR_METADATA[(name, 0)] = {'py.format': tuple_format}

FUNCTION_METADATA = {
      '$##'                   : {'py.rawfunc'    : impl.apply_gnf          }
    , '$!'                    : {'py.rawfunc'    : impl.apply_hnf          }
    , '$!!'                   : {'py.rawfunc'    : impl.apply_nf           }
    , '?'                     : {'py.rawfunc'    : impl.choice             }
    , '&'                     : {'py.rawfunc'    : impl.concurrent_and     }
    , 'apply'                 : {'py.rawfunc'    : impl.apply              }
    , 'bindIO'                : {'py.rawfunc'    : impl.bindIO             }
    , 'catch'                 : {'py.rawfunc'    : impl.catch              }
    , 'cond'                  : {'py.rawfunc'    : impl.cond               }
    , 'constrEq'              : {'py.rawfunc'    : impl.constr_eq          }
    , 'divInt'                : {'py.unboxedfunc': op.floordiv             }
    , 'ensureNotFree'         : {'py.rawfunc'    : impl.ensureNotFree      }
    , 'eqChar'                : {'py.unboxedfunc': op.eq                   }
    , 'eqFloat'               : {'py.unboxedfunc': op.eq                   }
    , 'eqInt'                 : {'py.unboxedfunc': op.eq                   }
    , 'failed'                : {'py.boxedfunc'  : impl.failed             }
    , 'getChar'               : {'py.boxedfunc'  : impl.getChar            }
    , 'ltEqChar'              : {'py.unboxedfunc': op.le                   }
    , 'ltEqFloat'             : {'py.unboxedfunc': op.le                   }
    , 'ltEqInt'               : {'py.unboxedfunc': op.le                   }
    , 'minusInt'              : {'py.unboxedfunc': op.sub                  }
    , 'modInt'                : {'py.unboxedfunc': impl.modInt             }
    , 'negateFloat'           : {'py.unboxedfunc': op.neg                  }
    , 'nonstrictEq'           : {'py.rawfunc'    : impl.nonstrict_eq       }
    , 'plusInt'               : {'py.unboxedfunc': op.add                  }
    , 'prim_acosFloat'        : {'py.unboxedfunc': math.acos               }
    , 'prim_acoshFloat'       : {'py.unboxedfunc': math.acosh              }
    , 'prim_appendFile'       : {'py.rawfunc'    : impl.appendFile         }
    , 'prim_asinFloat'        : {'py.unboxedfunc': math.asin               }
    , 'prim_asinhFloat'       : {'py.unboxedfunc': math.asinh              }
    , 'prim_atanFloat'        : {'py.unboxedfunc': math.atan               }
    , 'prim_atanhFloat'       : {'py.unboxedfunc': math.atanh              }
    , 'prim_chr'              : {'py.unboxedfunc': chr                     }
    # , 'prim_constrEq'         : {'py.rawfunc'    : impl.constr_eq          }
    , 'prim_cosFloat'         : {'py.unboxedfunc': math.cos                }
    , 'prim_coshFloat'        : {'py.unboxedfunc': math.cosh               }
    , 'prim_divFloat'         : {'py.unboxedfunc': impl.prim_divFloat      }
    , 'prim_error'            : {'py.boxedfunc'  : impl.error              }
    , 'prim_expFloat'         : {'py.unboxedfunc': math.exp                }
    , 'prim_intToFloat'       : {'py.unboxedfunc': float                   }
    , 'prim_ioError'          : {'py.rawfunc'    : impl.ioError            }
    , 'prim_logFloat'         : {'py.unboxedfunc': math.log                }
    , 'prim_minusFloat'       : {'py.unboxedfunc': impl.prim_minusFloat    }
    # , 'prim_nonstrictEq'      : {'py.rawfunc'    : impl.nonstrict_eq       }
    , 'prim_ord'              : {'py.unboxedfunc': ord                     }
    , 'prim_plusFloat'        : {'py.unboxedfunc': op.add                  }
    , 'prim_putChar'          : {'py.boxedfunc'  : impl.putChar            }
    , 'prim_readCharLiteral'  : {'py.boxedfunc'  : impl.readCharLiteral    }
    , 'prim_readFile'         : {'py.boxedfunc'  : impl.readFile           }
    , 'prim_readFloatLiteral' : {'py.boxedfunc'  : impl.readFloatLiteral   }
    , 'prim_readNatLiteral'   : {'py.boxedfunc'  : impl.readNatLiteral     }
    , 'prim_readStringLiteral': {'py.boxedfunc'  : impl.readStringLiteral  }
    , 'prim_roundFloat'       : {'py.unboxedfunc': impl.prim_roundFloat    }
    , 'prim_showCharLiteral'  : {'py.boxedfunc'  : impl.show               }
    , 'prim_showFloatLiteral' : {'py.boxedfunc'  : impl.show               }
    , 'prim_showIntLiteral'   : {'py.boxedfunc'  : impl.show               }
    , 'prim_showStringLiteral': {'py.boxedfunc'  : impl.show               }
    , 'prim_sinFloat'         : {'py.unboxedfunc': math.sin                }
    , 'prim_sinhFloat'        : {'py.unboxedfunc': math.sinh               }
    , 'prim_sqrtFloat'        : {'py.unboxedfunc': math.sqrt               }
    , 'prim_tanFloat'         : {'py.unboxedfunc': math.tan                }
    , 'prim_tanhFloat'        : {'py.unboxedfunc': math.tanh               }
    , 'prim_timesFloat'       : {'py.unboxedfunc': op.mul                  }
    , 'prim_truncateFloat'    : {'py.unboxedfunc': int                     }
    , 'prim_writeFile'        : {'py.rawfunc'    : impl.writeFile          }
    , 'quotInt'               : {'py.unboxedfunc': impl.quotInt            }
    , 'remInt'                : {'py.unboxedfunc': impl.remInt             }
    , 'returnIO'              : {'py.rawfunc'    : impl.returnIO           }
    , 'seqIO'                 : {'py.rawfunc'    : impl.seqIO              }
    , 'timesInt'              : {'py.unboxedfunc': op.mul                  }
    # Unused PAKCS functions.
    , 'failure'               : {'py.rawfunc'    : impl.not_used           }
    , 'ifVar'                 : {'py.rawfunc'    : impl.not_used           }
    , 'letrec'                : {'py.rawfunc'    : impl.not_used           }
    , 'prim_readFileContents' : {'py.rawfunc'    : impl.not_used           }
    , 'unifEqLinear'          : {'py.rawfunc'    : impl.not_used           }
    }

class PreludeSpecification(generic_prelude.PreludeSpecification):
  FUNCTIONS = FUNCTIONS

  def exports(self):
    for sym in super(PreludeSpecification, self).exports():
      yield sym
    yield '?'
    yield '_PyGenerator'
    yield '_PyString'

  CONSTRUCTOR_METADATA = CONSTRUCTOR_METADATA
  FUNCTION_METADATA = FUNCTION_METADATA

