from ...generic.currylib.prelude import PreludeSpecification

# from ...generic.currylib import prelude as generic_prelude
# 
# class PreludeSpecification(generic_prelude.PreludeSpecification):
#   TYPE_METADATA = {
#       'Bool'                  : {'cxx.symbolname': 'cyrt::Bool_Type'  }
#     , 'Char'                  : {'cxx.symbolname': 'cyrt::Char_Type'  }
#     , '[]'                    : {'cxx.symbolname': 'cyrt::List_Type'  }
#     , 'Float'                 : {'cxx.symbolname': 'cyrt::Float_Type' }
#     , 'Int'                   : {'cxx.symbolname': 'cyrt::Int_Type'   }
#     , 'IO'                    : {'cxx.symbolname': 'cyrt::IO_Type'    }
#     , 'Pair'                  : {'cxx.symbolname': 'cyrt::Pair_Type'  }
#     , 'Unit'                  : {'cxx.symbolname': 'cyrt::Unit_Type'  }
#     }
# 
#   CONSTRUCTOR_METADATA = {
#       ('_Failure'   , 0)  : {'cxx.symbolname': 'cyrt::Fail_Info'                }
#     , ('_Constraint', 0)  : {'cxx.symbolname': 'cyrt::StrictConstraint_Info'    }
#     , ('_Constraint', 1)  : {'cxx.symbolname': 'cyrt::NonStrictConstraint_Info' }
#     , ('_Constraint', 2)  : {'cxx.symbolname': 'cyrt::ValueBinding_Info'        }
#     , ('_PartApplic', 0)  : {'cxx.symbolname': 'cyrt::PartApplic_Info'          }
#     , ('_Free'      , 0)  : {'cxx.symbolname': 'cyrt::Free_Info'                }
#     , ('_Fwd'       , 0)  : {'cxx.symbolname': 'cyrt::Fwd_Info'                 }
#     , ('Int'        , 0)  : {'cxx.symbolname': 'cyrt::Int_Info'                 }
#     , ('Float'      , 0)  : {'cxx.symbolname': 'cyrt::Float_Info'               }
#     , ('Char'       , 0)  : {'cxx.symbolname': 'cyrt::Char_Info'                }
#     , ('[]'         , 0)  : {'cxx.symbolname': 'cyrt::Cons_Info'                }
#     , ('[]'         , 1)  : {'cxx.symbolname': 'cyrt::Nil_Info'                 }
#     , ('()'         , 0)  : {'cxx.symbolname': 'cyrt::Unit_Info'                }
#     , ('_Choice'    , 0)  : {'cxx.symbolname': 'cyrt::Choice_Info'              }
#     , ('Bool'       , 0)  : {'cxx.symbolname': 'cyrt::False_Info'               }
#     , ('Bool'       , 1)  : {'cxx.symbolname': 'cyrt::True_Info'                }
#     , ('IO'         , 0)  : {'cxx.symbolname': 'cyrt::IO_Info'                  }
#     , ('(,)'        , 0)  : {'cxx.symbolname': 'cyrt::Pair_Info'                }
#     }
# 
#   FUNCTION_METADATA = {
#       '$##'                   : {'cxx.symbolname': 'cyrt::applygnf_Info'         }
#     , '$!'                    : {'cxx.symbolname': 'cyrt::applyhnf_Info'         }
#     , '$!!'                   : {'cxx.symbolname': 'cyrt::applynf_Info'          }
#     , '?'                     : {'cxx.symbolname': 'cyrt::choice_Info'           }
#     , '&'                     : {'cxx.symbolname': 'cyrt::concurrentAnd_Info'    }
#     , '=:='                   : {'cxx.symbolname': 'cyrt::constrEq_Info'         }
#     , '=:<='                  : {'cxx.symbolname': 'cyrt::nonstrictEq_Info'      }
#     , 'apply'                 : {'cxx.symbolname': 'cyrt::apply_Info'            }
#     , 'bindIO'                : {'cxx.symbolname': 'cyrt::bindIO_Info'           }
#     , 'catch'                 : {'cxx.symbolname': 'cyrt::catch_Info'            }
#     , 'cond'                  : {'cxx.symbolname': 'cyrt::cond_Info'             }
#     , 'constrEq'              : {'cxx.symbolname': 'cyrt::constrEq_Info'         }
#     , 'divInt'                : {'cxx.symbolname': 'cyrt::divInt_Info'           }
#     , 'ensureNotFree'         : {'cxx.symbolname': 'cyrt::ensureNotFree_Info'    }
#     , 'eqChar'                : {'cxx.symbolname': 'cyrt::eqChar_Info'           }
#     , 'eqFloat'               : {'cxx.symbolname': 'cyrt::eqFloat_Info'          }
#     , 'eqInt'                 : {'cxx.symbolname': 'cyrt::eqInt_Info'            }
#     , 'failed'                : {'cxx.symbolname': 'cyrt::failed_Info'           }
#     , 'getChar'               : {'cxx.symbolname': 'cyrt::getChar_Info'          }
#     , 'ltEqChar'              : {'cxx.symbolname': 'cyrt::ltEqChar_Info'         }
#     , 'ltEqFloat'             : {'cxx.symbolname': 'cyrt::ltEqFloat_Info'        }
#     , 'ltEqInt'               : {'cxx.symbolname': 'cyrt::ltEqInt_Info'          }
#     , 'minusInt'              : {'cxx.symbolname': 'cyrt::minusInt_Info'         }
#     , 'modInt'                : {'cxx.symbolname': 'cyrt::modInt_Info'           }
#     , 'negateFloat'           : {'cxx.symbolname': 'cyrt::negateFloat_Info'      }
#     , 'nonstrictEq'           : {'cxx.symbolname': 'cyrt::nonstrictEq_Info'      }
#     , 'plusInt'               : {'cxx.symbolname': 'cyrt::plusInt_Info'          }
#     , 'prim_acosFloat'        : {'cxx.symbolname': 'cyrt::acosFloat_Info'        }
#     , 'prim_acoshFloat'       : {'cxx.symbolname': 'cyrt::acoshFloat_Info'       }
#     , 'prim_appendFile'       : {'cxx.symbolname': 'cyrt::appendFile_Info'       }
#     , 'prim_asinFloat'        : {'cxx.symbolname': 'cyrt::asinFloat_Info'        }
#     , 'prim_asinhFloat'       : {'cxx.symbolname': 'cyrt::asinhFloat_Info'       }
#     , 'prim_atanFloat'        : {'cxx.symbolname': 'cyrt::atanFloat_Info'        }
#     , 'prim_atanhFloat'       : {'cxx.symbolname': 'cyrt::atanhFloat_Info'       }
#     , 'prim_chr'              : {'cxx.symbolname': 'cyrt::chr_Info'              }
#     # , 'prim_constrEq'         : {'cxx.symbolname': 'cyrt::constrEq_Info'         }
#     , 'prim_cosFloat'         : {'cxx.symbolname': 'cyrt::cosFloat_Info'         }
#     , 'prim_coshFloat'        : {'cxx.symbolname': 'cyrt::coshFloat_Info'        }
#     , 'prim_divFloat'         : {'cxx.symbolname': 'cyrt::divFloat_Info'         }
#     , 'prim_error'            : {'cxx.symbolname': 'cyrt::error_Info'            }
#     , 'prim_expFloat'         : {'cxx.symbolname': 'cyrt::expFloat_Info'         }
#     , 'prim_intToFloat'       : {'cxx.symbolname': 'cyrt::intToFloat_Info'       }
#     , 'prim_ioError'          : {'cxx.symbolname': 'cyrt::ioError_Info'          }
#     , 'prim_logFloat'         : {'cxx.symbolname': 'cyrt::logFloat_Info'         }
#     , 'prim_minusFloat'       : {'cxx.symbolname': 'cyrt::minusFloat_Info'       }
#     # , 'prim_nonstrictEq'      : {'cxx.symbolname': 'cyrt::nonstrictEq_Info'      }
#     , 'prim_ord'              : {'cxx.symbolname': 'cyrt::ord_Info'              }
#     , 'prim_plusFloat'        : {'cxx.symbolname': 'cyrt::plusFloat_Info'        }
#     , 'prim_putChar'          : {'cxx.symbolname': 'cyrt::putChar_Info'          }
#     , 'prim_readCharLiteral'  : {'cxx.symbolname': 'cyrt::readCharLiteral_Info'  }
#     , 'prim_readFile'         : {'cxx.symbolname': 'cyrt::readFile_Info'         }
#     , 'prim_readFloatLiteral' : {'cxx.symbolname': 'cyrt::readFloatLiteral_Info' }
#     , 'prim_readNatLiteral'   : {'cxx.symbolname': 'cyrt::readNatLiteral_Info'   }
#     , 'prim_readStringLiteral': {'cxx.symbolname': 'cyrt::readStringLiteral_Info'}
#     , 'prim_roundFloat'       : {'cxx.symbolname': 'cyrt::roundFloat_Info'       }
#     , 'prim_showCharLiteral'  : {'cxx.symbolname': 'cyrt::showCharLiteral_Info'  }
#     , 'prim_showFloatLiteral' : {'cxx.symbolname': 'cyrt::showFloatLiteral_Info' }
#     , 'prim_showIntLiteral'   : {'cxx.symbolname': 'cyrt::showIntLiteral_Info'   }
#     , 'prim_showStringLiteral': {'cxx.symbolname': 'cyrt::showStringLiteral_Info'}
#     , 'prim_sinFloat'         : {'cxx.symbolname': 'cyrt::sinFloat_Info'         }
#     , 'prim_sinhFloat'        : {'cxx.symbolname': 'cyrt::sinhFloat_Info'        }
#     , 'prim_sqrtFloat'        : {'cxx.symbolname': 'cyrt::sqrtFloat_Info'        }
#     , 'prim_tanFloat'         : {'cxx.symbolname': 'cyrt::tanFloat_Info'         }
#     , 'prim_tanhFloat'        : {'cxx.symbolname': 'cyrt::tanhFloat_Info'        }
#     , 'prim_timesFloat'       : {'cxx.symbolname': 'cyrt::timesFloat_Info'       }
#     , 'prim_truncateFloat'    : {'cxx.symbolname': 'cyrt::truncateFloat_Info'    }
#     , 'prim_writeFile'        : {'cxx.symbolname': 'cyrt::writeFile_Info'        }
#     , '_PyGenerator'          : {'cxx.symbolname': 'cyrt::_PyGenerator_Info'     }
#     , '_PyString'             : {'cxx.symbolname': 'cyrt::_PyString_Info'        }
#     , 'quotInt'               : {'cxx.symbolname': 'cyrt::quotInt_Info'          }
#     , 'remInt'                : {'cxx.symbolname': 'cyrt::remInt_Info'           }
#     , 'returnIO'              : {'cxx.symbolname': 'cyrt::returnIO_Info'         }
#     , 'seqIO'                 : {'cxx.symbolname': 'cyrt::seqIO_Info'            }
#     , 'timesInt'              : {'cxx.symbolname': 'cyrt::timesInt_Info'         }
#     # Unused PAKCS functions.
#     , 'failure'               : {'cxx.symbolname': 'cyrt::notused_Info'          }
#     , 'ifVar'                 : {'cxx.symbolname': 'cyrt::notused_Info'          }
#     , 'letrec'                : {'cxx.symbolname': 'cyrt::notused_Info'          }
#     , 'prim_readFileContents' : {'cxx.symbolname': 'cyrt::notused_Info'          }
#     , 'unifEqLinear'          : {'cxx.symbolname': 'cyrt::notused_Info'          }
#     }
# 
