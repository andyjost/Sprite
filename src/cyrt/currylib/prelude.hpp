#pragma once
#include "cyrt/builtins.hpp"

namespace cyrt
{
  // prelude/apply.cpp
  extern InfoTable const apply_Info;
  extern InfoTable const applygnf_Info;
  extern InfoTable const applyhnf_Info;
  extern InfoTable const applynf_Info;
  extern InfoTable const cond_Info;
  extern InfoTable const ensureNotFree_Info;

  // prelude/basic.cpp
  extern InfoTable const choice_Info;
  extern InfoTable const error_Info;
  extern InfoTable const failed_Info;
  extern InfoTable const notused_Info;

  // prelude/constr.cpp
  extern InfoTable const concurrentAnd_Info;
  extern InfoTable const constrEq_Info;
  extern InfoTable const nonstrictEq_Info;
  extern InfoTable const seq_Info;

  // prelude/io.cpp
  extern InfoTable const appendFile_Info;
  extern InfoTable const bindIO_Info;
  extern InfoTable const catch_Info;
  extern InfoTable const getChar_Info;
  extern InfoTable const ioError_Info;
  extern InfoTable const putChar_Info;
  extern InfoTable const readFile_Info;
  extern InfoTable const returnIO_Info;
  extern InfoTable const seqIO_Info;
  extern InfoTable const writeFile_Info;

  // prelude/math.cpp
  extern InfoTable const acosFloat_Info;
  extern InfoTable const acoshFloat_Info;
  extern InfoTable const asinFloat_Info;
  extern InfoTable const asinhFloat_Info;
  extern InfoTable const atanFloat_Info;
  extern InfoTable const atanhFloat_Info;
  extern InfoTable const cosFloat_Info;
  extern InfoTable const coshFloat_Info;
  extern InfoTable const divFloat_Info;
  extern InfoTable const divInt_Info;
  extern InfoTable const eqChar_Info;
  extern InfoTable const eqFloat_Info;
  extern InfoTable const eqInt_Info;
  extern InfoTable const expFloat_Info;
  extern InfoTable const intToFloat_Info;
  extern InfoTable const logFloat_Info;
  extern InfoTable const ltEqChar_Info;
  extern InfoTable const ltEqFloat_Info;
  extern InfoTable const ltEqInt_Info;
  extern InfoTable const minusFloat_Info;
  extern InfoTable const minusInt_Info;
  extern InfoTable const modInt_Info;
  extern InfoTable const negateFloat_Info;
  extern InfoTable const plusFloat_Info;
  extern InfoTable const plusInt_Info;
  extern InfoTable const quotInt_Info;
  extern InfoTable const remInt_Info;
  extern InfoTable const roundFloat_Info;
  extern InfoTable const sinFloat_Info;
  extern InfoTable const sinhFloat_Info;
  extern InfoTable const sqrtFloat_Info;
  extern InfoTable const tanFloat_Info;
  extern InfoTable const tanhFloat_Info;
  extern InfoTable const timesFloat_Info;
  extern InfoTable const timesInt_Info;
  extern InfoTable const truncateFloat_Info;

  // prelude/read.cpp
  extern InfoTable const readCharLiteral_Info;
  extern InfoTable const readFloatLiteral_Info;
  extern InfoTable const readNatLiteral_Info;
  extern InfoTable const readStringLiteral_Info;

  // prelude/show.cpp
  extern InfoTable const showCharLiteral_Info;
  extern InfoTable const showFloatLiteral_Info;
  extern InfoTable const showIntLiteral_Info;
  extern InfoTable const showStringLiteral_Info;

  // prelude/string.cpp
  extern InfoTable const _PyGenerator_Info;
  extern InfoTable const _PyString_Info;
  extern InfoTable const chr_Info;
  extern InfoTable const ord_Info;

  // prelude/testing.cpp -- OK TO REMOVE
  extern InfoTable const not_Info;
}
