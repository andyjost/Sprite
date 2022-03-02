from ...generic.currylib import prelude as generic_prelude

PreludeSpecification = generic_prelude.PreludeSpecification

# def todo(*args, **kwds):
#   breakpoint()
#
# class Impl(object):
#   def __getattr__(self, name):
#     return todo
#
# impl = Impl()
#
# METADATA = {
#       '$##'                   : {'cxx.builtin': impl.apply_gnf          }
#     , '$!'                    : {'cxx.builtin': impl.apply_hnf          }
#     , '$!!'                   : {'cxx.builtin': impl.apply_nf           }
#     , '?'                     : {'cxx.builtin': impl.choice             }
#     , '&'                     : {'cxx.builtin': impl.concurrent_and     }
#     , '=:='                   : {'cxx.builtin': impl.constr_eq          }
#     , '=:<='                  : {'cxx.builtin': impl.nonstrict_eq       }
#     , 'apply'                 : {'cxx.builtin': impl.apply              }
#     , 'bindIO'                : {'cxx.builtin': impl.bindIO             }
#     , 'catch'                 : {'cxx.builtin': impl.catch              }
#     , 'cond'                  : {'cxx.builtin': impl.cond               }
#     , 'constrEq'              : {'cxx.builtin': impl.constr_eq          }
#     , 'divInt'                : {'cxx.builtin': impl.divInt             }
#     , 'ensureNotFree'         : {'cxx.builtin': impl.ensureNotFree      }
#     , 'eqChar'                : {'cxx.builtin': impl.eqChar             }
#     , 'eqFloat'               : {'cxx.builtin': impl.eqFloat            }
#     , 'eqInt'                 : {'cxx.builtin': impl.eqInt              }
#     , 'failed'                : {'cxx.builtin': impl.failed             }
#     , 'getChar'               : {'cxx.builtin': impl.getChar            }
#     , 'ltEqChar'              : {'cxx.builtin': impl.ltEqChar           }
#     , 'ltEqFloat'             : {'cxx.builtin': impl.ltEqFloat          }
#     , 'ltEqInt'               : {'cxx.builtin': impl.ltEqInt            }
#     , 'minusInt'              : {'cxx.builtin': impl.minusInt           }
#     , 'modInt'                : {'cxx.builtin': impl.modInt             }
#     , 'negateFloat'           : {'cxx.builtin': impl.negateFloat        }
#     , 'nonstrictEq'           : {'cxx.builtin': impl.nonstrict_eq       }
#     , 'plusInt'               : {'cxx.builtin': impl.plusInt            }
#     , 'prim_acosFloat'        : {'cxx.builtin': impl.acosFloat          }
#     , 'prim_acoshFloat'       : {'cxx.builtin': impl.acoshFloat         }
#     , 'prim_appendFile'       : {'cxx.builtin': impl.appendFile         }
#     , 'prim_asinFloat'        : {'cxx.builtin': impl.asinFloat          }
#     , 'prim_asinhFloat'       : {'cxx.builtin': impl.asinhFloat         }
#     , 'prim_atanFloat'        : {'cxx.builtin': impl.atanFloat          }
#     , 'prim_atanhFloat'       : {'cxx.builtin': impl.atanhfloat         }
#     , 'prim_constrEq'         : {'cxx.builtin': impl.constr_eq          }
#     , 'prim_cosFloat'         : {'cxx.builtin': impl.cosFloat           }
#     , 'prim_coshFloat'        : {'cxx.builtin': impl.coshFloat          }
#     , 'prim_divFloat'         : {'cxx.builtin': impl.prim_divFloat      }
#     , 'prim_error'            : {'cxx.builtin': impl.error              }
#     , 'prim_expFloat'         : {'cxx.builtin': impl.expFloat           }
#     , 'prim_intToFloat'       : {'cxx.builtin': impl.intToFloat         }
#     , 'prim_ioError'          : {'cxx.builtin': impl.ioError            }
#     , 'prim_logFloat'         : {'cxx.builtin': impl.logFloat           }
#     , 'prim_minusFloat'       : {'cxx.builtin': impl.minusFloat         }
#     , 'prim_nonstrictEq'      : {'cxx.builtin': impl.nonstrict_eq       }
#     , 'prim_ord'              : {'cxx.builtin': impl.ord                }
#     , 'prim_plusFloat'        : {'cxx.builtin': impl.plusFloat          }
#     , 'prim_putChar'          : {'cxx.builtin': impl.putChar            }
#     , 'prim_readCharLiteral'  : {'cxx.builtin': impl.readCharLiteral    }
#     , 'prim_readFile'         : {'cxx.builtin': impl.readFile           }
#     , 'prim_readFloatLiteral' : {'cxx.builtin': impl.readFloatLiteral   }
#     , 'prim_readNatLiteral'   : {'cxx.builtin': impl.readNatLiteral     }
#     , 'prim_readStringLiteral': {'cxx.builtin': impl.readStringLiteral  }
#     , 'prim_roundFloat'       : {'cxx.builtin': impl.prim_roundFloat    }
#     , 'prim_showCharLiteral'  : {'cxx.builtin': impl.showCharLiteral    }
#     , 'prim_showFloatLiteral' : {'cxx.builtin': impl.showFloatLiteral   }
#     , 'prim_showIntLiteral'   : {'cxx.builtin': impl.showIntLiteral     }
#     , 'prim_showStringLiteral': {'cxx.builtin': impl.showStringLiteral  }
#     , 'prim_sinFloat'         : {'cxx.builtin': impl.sinFloat           }
#     , 'prim_sinhFloat'        : {'cxx.builtin': impl.sinhFloat          }
#     , 'prim_sqrtFloat'        : {'cxx.builtin': impl.sqrtFloat          }
#     , 'prim_tanFloat'         : {'cxx.builtin': impl.tanFloat           }
#     , 'prim_tanhFloat'        : {'cxx.builtin': impl.tanhFloat          }
#     , 'prim_timesFloat'       : {'cxx.builtin': impl.timesFloat         }
#     , 'prim_truncateFloat'    : {'cxx.builtin': impl.truncateFloat      }
#     , 'prim_writeFile'        : {'cxx.builtin': impl.writeFile          }
#     , '_PyGenerator'          : {'cxx.builtin': impl._PyGenerator       }
#     , '_PyString'             : {'cxx.builtin': impl._PyString          }
#     , 'quotInt'               : {'cxx.builtin': impl.quotInt            }
#     , 'remInt'                : {'cxx.builtin': impl.remInt             }
#     , 'returnIO'              : {'cxx.builtin': impl.returnIO           }
#     , 'seqIO'                 : {'cxx.builtin': impl.seqIO              }
#     , 'timesInt'              : {'cxx.builtin': impl.timesInt           }
#     # Unused PAKCS functions.
#     , 'failure'               : {'cxx.builtin': impl.not_used           }
#     , 'ifVar'                 : {'cxx.builtin': impl.not_used           }
#     , 'letrec'                : {'cxx.builtin': impl.not_used           }
#     , 'prim_divInt'           : {'cxx.builtin': impl.not_used           }
#     , 'prim_eqChar'           : {'cxx.builtin': impl.not_used           }
#     , 'prim_eqFloat'          : {'cxx.builtin': impl.not_used           }
#     , 'prim_eqInt'            : {'cxx.builtin': impl.not_used           }
#     , 'prim_ltEqChar'         : {'cxx.builtin': impl.not_used           }
#     , 'prim_ltEqFloat'        : {'cxx.builtin': impl.not_used           }
#     , 'prim_ltEqInt'          : {'cxx.builtin': impl.not_used           }
#     , 'prim_minusInt'         : {'cxx.builtin': impl.not_used           }
#     , 'prim_modInt'           : {'cxx.builtin': impl.not_used           }
#     , 'prim_negateFloat'      : {'cxx.builtin': impl.not_used           }
#     , 'prim_plusInt'          : {'cxx.builtin': impl.not_used           }
#     , 'prim_quotInt'          : {'cxx.builtin': impl.not_used           }
#     , 'prim_readFileContents' : {'cxx.builtin': impl.not_used           }
#     , 'prim_remInt'           : {'cxx.builtin': impl.not_used           }
#     , 'prim_timesInt'         : {'cxx.builtin': impl.not_used           }
#     , 'unifEqLinear'          : {'cxx.builtin': impl.not_used           }
#     }
#
# for f in generic_prelude.FUNCTIONS:
#   if f.name in METADATA:
#     f.update_metadata(METADATA[f.name])
#
