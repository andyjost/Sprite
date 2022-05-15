#pragma once
#include "cyrt/builtins.hpp"

// prelude/apply.cpp
#define apply_Info              CyI7Prelude5apply
#define applygnf_Info           CyI7Prelude6_D_h_h    // ($##)
#define applyhnf_Info           CyI7Prelude4_D_B      // ($!)
#define applynf_Info            CyI7Prelude6_D_B_B    // ($!!)
#define cond_Info               CyI7Prelude4cond
#define ensureNotFree_Info      CyI7Prelude13ensureNotFree

// prelude/basic.cpp
#define choice_Info             CyI7Prelude2_u        // (?)
#define error_Info              CyI7Prelude11prim__error
#define error2_Info              CyI7Prelude12prim__error2
#define failed_Info             CyI7Prelude6failed
#define notused_Info            CyI7Prelude7notused

// prelude/constr.cpp
#define concurrentAnd_Info      CyI7Prelude2_M        // (&)
#define constrEq_Info           CyI7Prelude8constrEq
#define nonstrictEq_Info        CyI7Prelude11nonstrictEq
#define seq_Info                CyI7Prelude3seq

// prelude/io.cpp
#define appendFile_Info         CyI7Prelude16prim__appendFile
#define bindIO_Info             CyI7Prelude6bindIO
#define catch_Info              CyI7Prelude5catch
#define getChar_Info            CyI7Prelude7getChar
#define ioError_Info            CyI7Prelude13prim__ioError
#define putChar_Info            CyI7Prelude13prim__putChar
#define readFile_Info           CyI7Prelude14prim__readFile
#define readFileContents_Info   CyI7Prelude22prim__readFileContents
#define returnIO_Info           CyI7Prelude8returnIO
#define seqIO_Info              CyI7Prelude5seqIO
#define writeFile_Info          CyI7Prelude15prim__writeFile

// prelude/math.cpp
#define acosFloat_Info          CyI7Prelude15prim__acosFloat
#define acoshFloat_Info         CyI7Prelude16prim__acoshFloat
#define asinFloat_Info          CyI7Prelude15prim__asinFloat
#define asinhFloat_Info         CyI7Prelude16prim__asinhFloat
#define atanFloat_Info          CyI7Prelude15prim__atanFloat
#define atanhFloat_Info         CyI7Prelude16prim__atanhFloat
#define cosFloat_Info           CyI7Prelude14prim__cosFloat
#define coshFloat_Info          CyI7Prelude15prim__coshFloat
#define divFloat_Info           CyI7Prelude14prim__divFloat
#define divInt_Info             CyI7Prelude6divInt
#define eqChar_Info             CyI7Prelude6eqChar
#define eqFloat_Info            CyI7Prelude7eqFloat
#define eqInt_Info              CyI7Prelude5eqInt
#define expFloat_Info           CyI7Prelude14prim__expFloat
#define intToFloat_Info         CyI7Prelude16prim__intToFloat
#define logFloat_Info           CyI7Prelude14prim__logFloat
#define ltEqChar_Info           CyI7Prelude8ltEqChar
#define ltEqFloat_Info          CyI7Prelude9ltEqFloat
#define ltEqInt_Info            CyI7Prelude7ltEqInt
#define minusFloat_Info         CyI7Prelude16prim__minusFloat
#define minusInt_Info           CyI7Prelude8minusInt
#define modInt_Info             CyI7Prelude6modInt
#define negateFloat_Info        CyI7Prelude11negateFloat
#define plusFloat_Info          CyI7Prelude15prim__plusFloat
#define plusInt_Info            CyI7Prelude7plusInt
#define quotInt_Info            CyI7Prelude7quotInt
#define remInt_Info             CyI7Prelude6remInt
#define roundFloat_Info         CyI7Prelude16prim__roundFloat
#define sinFloat_Info           CyI7Prelude14prim__sinFloat
#define sinhFloat_Info          CyI7Prelude15prim__sinhFloat
#define sqrtFloat_Info          CyI7Prelude15prim__sqrtFloat
#define tanFloat_Info           CyI7Prelude14prim__tanFloat
#define tanhFloat_Info          CyI7Prelude15prim__tanhFloat
#define timesFloat_Info         CyI7Prelude16prim__timesFloat
#define timesInt_Info           CyI7Prelude8timesInt
#define truncateFloat_Info      CyI7Prelude19prim__truncateFloat

// prelude/read.cpp
#define readCharLiteral_Info    CyI7Prelude21prim__readCharLiteral
#define readFloatLiteral_Info   CyI7Prelude22prim__readFloatLiteral
#define readNatLiteral_Info     CyI7Prelude20prim__readNatLiteral
#define readStringLiteral_Info  CyI7Prelude23prim__readStringLiteral

// prelude/show.cpp
#define showCharLiteral_Info    CyI7Prelude21prim__showCharLiteral
#define showFloatLiteral_Info   CyI7Prelude22prim__showFloatLiteral
#define showIntLiteral_Info     CyI7Prelude20prim__showIntLiteral
#define showStringLiteral_Info  CyI7Prelude23prim__showStringLiteral

// prelude/string.cpp
#define _cGenerator_Info        CyI7Prelude12__cGenerator
#define _cString_Info           CyI7Prelude9__cString
#define chr_Info                CyI7Prelude9prim__chr
#define ord_Info                CyI7Prelude9prim__ord

// prelude/testing.cpp -- OK TO REMOVE
#define not_Info                CyI7Prelude3not

// prelude/unused.cpp
#define failure_Info            CyI7Prelude7failure
#define ifVar_Info              CyI7Prelude5ifVar
#define letrec_Info             CyI7Prelude6letrec
#define unifEqLinear_Info       CyI7Prelude12unifEqLinear

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
  extern InfoTable const error_Info;
  extern InfoTable const error2_Info;
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
  extern InfoTable const readFileContents_Info;
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
  extern InfoTable const _cGenerator_Info;
  extern InfoTable const _cString_Info;
  extern InfoTable const chr_Info;
  extern InfoTable const ord_Info;

  // prelude/testing.cpp -- OK TO REMOVE
  extern InfoTable const not_Info;

  // prelude/unused.cpp
  extern InfoTable const failure_Info;
  extern InfoTable const ifVar_Info;
  extern InfoTable const letrec_Info;
  extern InfoTable const unifEqLinear_Info;
}
