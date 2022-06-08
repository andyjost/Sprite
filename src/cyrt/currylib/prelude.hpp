#pragma once
#include "cyrt/builtins.hpp"

// prelude/apply.cpp
#define apply_Info                   CyI7Prelude5apply
#define applygnf_Info                CyI7Prelude6_D_h_h    // ($##)
#define applyhnf_Info                CyI7Prelude4_D_B      // ($!)
#define applynf_Info                 CyI7Prelude6_D_B_B    // ($!!)
#define cond_Info                    CyI7Prelude4cond
#define ensureNotFree_Info           CyI7Prelude13ensureNotFree

// prelude/basic.cpp
#define choice_Info                  CyI7Prelude2_u        // (?)
#define prim_error_Info              CyI7Prelude11prim__error
#define prim_error2_Info             CyI7Prelude12prim__error2
#define failed_Info                  CyI7Prelude6failed
#define notused_Info                 CyI7Prelude7notused

// prelude/constr.cpp
#define concurrentAnd_Info           CyI7Prelude2_M        // (&)
#define constrEq_Info                CyI7Prelude8constrEq
#define nonstrictEq_Info             CyI7Prelude11nonstrictEq
#define seq_Info                     CyI7Prelude3seq

// prelude/io.cpp
#define prim_appendFile_Info         CyI7Prelude16prim__appendFile
#define bindIO_Info                  CyI7Prelude6bindIO
#define catch_Info                   CyI7Prelude5catch
#define getChar_Info                 CyI7Prelude7getChar
#define prim_ioError_Info            CyI7Prelude13prim__ioError
#define prim_putChar_Info            CyI7Prelude13prim__putChar
#define prim_readFile_Info           CyI7Prelude14prim__readFile
#define prim_readFileContents_Info   CyI7Prelude22prim__readFileContents
#define returnIO_Info                CyI7Prelude8returnIO
#define seqIO_Info                   CyI7Prelude5seqIO
#define prim_writeFile_Info          CyI7Prelude15prim__writeFile

// prelude/math.cpp
#define prim_acosFloat_Info          CyI7Prelude15prim__acosFloat
#define prim_acoshFloat_Info         CyI7Prelude16prim__acoshFloat
#define prim_asinFloat_Info          CyI7Prelude15prim__asinFloat
#define prim_asinhFloat_Info         CyI7Prelude16prim__asinhFloat
#define prim_atanFloat_Info          CyI7Prelude15prim__atanFloat
#define prim_atanhFloat_Info         CyI7Prelude16prim__atanhFloat
#define prim_cosFloat_Info           CyI7Prelude14prim__cosFloat
#define prim_coshFloat_Info          CyI7Prelude15prim__coshFloat
#define prim_divFloat_Info           CyI7Prelude14prim__divFloat
#define divInt_Info                  CyI7Prelude6divInt
#define eqChar_Info                  CyI7Prelude6eqChar
#define eqFloat_Info                 CyI7Prelude7eqFloat
#define eqInt_Info                   CyI7Prelude5eqInt
#define prim_expFloat_Info           CyI7Prelude14prim__expFloat
#define prim_intToFloat_Info         CyI7Prelude16prim__intToFloat
#define prim_logFloat_Info           CyI7Prelude14prim__logFloat
#define ltEqChar_Info                CyI7Prelude8ltEqChar
#define ltEqFloat_Info               CyI7Prelude9ltEqFloat
#define ltEqInt_Info                 CyI7Prelude7ltEqInt
#define prim_minusFloat_Info         CyI7Prelude16prim__minusFloat
#define minusInt_Info                CyI7Prelude8minusInt
#define modInt_Info                  CyI7Prelude6modInt
#define negateFloat_Info             CyI7Prelude11negateFloat
#define prim_plusFloat_Info          CyI7Prelude15prim__plusFloat
#define plusInt_Info                 CyI7Prelude7plusInt
#define quotInt_Info                 CyI7Prelude7quotInt
#define remInt_Info                  CyI7Prelude6remInt
#define prim_roundFloat_Info         CyI7Prelude16prim__roundFloat
#define prim_sinFloat_Info           CyI7Prelude14prim__sinFloat
#define prim_sinhFloat_Info          CyI7Prelude15prim__sinhFloat
#define prim_sqrtFloat_Info          CyI7Prelude15prim__sqrtFloat
#define prim_tanFloat_Info           CyI7Prelude14prim__tanFloat
#define prim_tanhFloat_Info          CyI7Prelude15prim__tanhFloat
#define prim_timesFloat_Info         CyI7Prelude16prim__timesFloat
#define timesInt_Info                CyI7Prelude8timesInt
#define prim_truncateFloat_Info      CyI7Prelude19prim__truncateFloat

// prelude/read.cpp
#define prim_readCharLiteral_Info    CyI7Prelude21prim__readCharLiteral
#define prim_readFloatLiteral_Info   CyI7Prelude22prim__readFloatLiteral
#define prim_readNatLiteral_Info     CyI7Prelude20prim__readNatLiteral
#define prim_readStringLiteral_Info  CyI7Prelude23prim__readStringLiteral

// prelude/show.cpp
#define prim_showCharLiteral_Info    CyI7Prelude21prim__showCharLiteral
#define prim_showFloatLiteral_Info   CyI7Prelude22prim__showFloatLiteral
#define prim_showIntLiteral_Info     CyI7Prelude20prim__showIntLiteral
#define prim_showStringLiteral_Info  CyI7Prelude23prim__showStringLiteral

// prelude/string.cpp
#define _biGenerator_Info            CyI7Prelude13__biGenerator
#define _biString_Info               CyI7Prelude10__biString
#define prim_chr_Info                CyI7Prelude9prim__chr
#define prim_ord_Info                CyI7Prelude9prim__ord

// prelude/unused.cpp
#define failure_Info                 CyI7Prelude7failure
#define ifVar_Info                   CyI7Prelude5ifVar
#define letrec_Info                  CyI7Prelude6letrec
#define unifEqLinear_Info            CyI7Prelude12unifEqLinear

extern "C"
{
  using namespace cyrt;

  // prelude/apply.cpp
  extern InfoTable const apply_Info;
  extern InfoTable const applygnf_Info;
  extern InfoTable const applyhnf_Info;
  extern InfoTable const applynf_Info;
  extern InfoTable const cond_Info;
  extern InfoTable const ensureNotFree_Info;

  // prelude/basic.cpp
  extern InfoTable const choice_Info;
  extern InfoTable const prim_error_Info;
  extern InfoTable const prim_error2_Info;
  extern InfoTable const failed_Info;
  extern InfoTable const notused_Info;

  // prelude/constr.cpp
  extern InfoTable const concurrentAnd_Info;
  extern InfoTable const constrEq_Info;
  extern InfoTable const nonstrictEq_Info;
  extern InfoTable const seq_Info;

  // prelude/io.cpp
  extern InfoTable const prim_appendFile_Info;
  extern InfoTable const bindIO_Info;
  extern InfoTable const catch_Info;
  extern InfoTable const getChar_Info;
  extern InfoTable const prim_ioError_Info;
  extern InfoTable const prim_putChar_Info;
  extern InfoTable const prim_readFile_Info;
  extern InfoTable const prim_readFileContents_Info;
  extern InfoTable const returnIO_Info;
  extern InfoTable const seqIO_Info;
  extern InfoTable const prim_writeFile_Info;

  // prelude/math.cpp
  extern InfoTable const prim_acosFloat_Info;
  extern InfoTable const prim_acoshFloat_Info;
  extern InfoTable const prim_asinFloat_Info;
  extern InfoTable const prim_asinhFloat_Info;
  extern InfoTable const prim_atanFloat_Info;
  extern InfoTable const prim_atanhFloat_Info;
  extern InfoTable const prim_cosFloat_Info;
  extern InfoTable const prim_coshFloat_Info;
  extern InfoTable const prim_divFloat_Info;
  extern InfoTable const divInt_Info;
  extern InfoTable const eqChar_Info;
  extern InfoTable const eqFloat_Info;
  extern InfoTable const eqInt_Info;
  extern InfoTable const prim_expFloat_Info;
  extern InfoTable const prim_intToFloat_Info;
  extern InfoTable const prim_logFloat_Info;
  extern InfoTable const ltEqChar_Info;
  extern InfoTable const ltEqFloat_Info;
  extern InfoTable const ltEqInt_Info;
  extern InfoTable const prim_minusFloat_Info;
  extern InfoTable const minusInt_Info;
  extern InfoTable const modInt_Info;
  extern InfoTable const negateFloat_Info;
  extern InfoTable const prim_plusFloat_Info;
  extern InfoTable const plusInt_Info;
  extern InfoTable const quotInt_Info;
  extern InfoTable const remInt_Info;
  extern InfoTable const prim_roundFloat_Info;
  extern InfoTable const prim_sinFloat_Info;
  extern InfoTable const prim_sinhFloat_Info;
  extern InfoTable const prim_sqrtFloat_Info;
  extern InfoTable const prim_tanFloat_Info;
  extern InfoTable const prim_tanhFloat_Info;
  extern InfoTable const prim_timesFloat_Info;
  extern InfoTable const timesInt_Info;
  extern InfoTable const prim_truncateFloat_Info;

  // prelude/read.cpp
  extern InfoTable const prim_readCharLiteral_Info;
  extern InfoTable const prim_readFloatLiteral_Info;
  extern InfoTable const prim_readNatLiteral_Info;
  extern InfoTable const prim_readStringLiteral_Info;

  // prelude/show.cpp
  extern InfoTable const prim_showCharLiteral_Info;
  extern InfoTable const prim_showFloatLiteral_Info;
  extern InfoTable const prim_showIntLiteral_Info;
  extern InfoTable const prim_showStringLiteral_Info;

  // prelude/string.cpp
  extern InfoTable const _biGenerator_Info;
  extern InfoTable const _biString_Info;
  extern InfoTable const prim_chr_Info;
  extern InfoTable const prim_ord_Info;

  // prelude/testing.cpp -- OK TO REMOVE
  extern InfoTable const not_Info;

  // prelude/unused.cpp
  extern InfoTable const failure_Info;
  extern InfoTable const ifVar_Info;
  extern InfoTable const letrec_Info;
  extern InfoTable const unifEqLinear_Info;
}
