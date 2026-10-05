#pragma once
#include "cyrt/builtins.hpp"
#include "cyrt/graph/infotable.hpp"

#define PartialS_Type        CyD7Control12SetFunctions8PartialS
#define SetEval_Type         CyD7Control12SetFunctions7SetEval
#define Values_Type          CyD7Control12SetFunctions6Values

#define allValues_Info       CyI7Control12SetFunctions9allValues
#define applyS_Info          CyI7Control12SetFunctions6applyS
#define captureS_Info        CyI7Control12SetFunctions8captureS
#define eagerApplyS_Info     CyI7Control12SetFunctions11eagerApplyS
#define evalS_Info           CyI7Control12SetFunctions5evalS
#define exprS_Info           CyI7Control12SetFunctions5exprS
#define PartialS_Info        CyI7Control12SetFunctions8PartialS
#define set0_Info            CyI7Control12SetFunctions4set0
#define set1_Info            CyI7Control12SetFunctions4set1
#define set2_Info            CyI7Control12SetFunctions4set2
#define set3_Info            CyI7Control12SetFunctions4set3
#define set4_Info            CyI7Control12SetFunctions4set4
#define set5_Info            CyI7Control12SetFunctions4set5
#define set6_Info            CyI7Control12SetFunctions4set6
#define set7_Info            CyI7Control12SetFunctions4set7
#define SetEval_Info         CyI7Control12SetFunctions7SetEval
#define set_Info             CyI7Control12SetFunctions3set
#define Values_Info          CyI7Control12SetFunctions6Values

using namespace cyrt;

extern "C"
{
  extern DataType const PartialS_Type;
  extern DataType const SetEval_Type;
  extern DataType const Values_Type;

  extern InfoTable const allValues_Info;
  extern InfoTable const applyS_Info;
  extern InfoTable const captureS_Info;
  extern InfoTable const eagerApplyS_Info;
  extern InfoTable const evalS_Info;
  extern InfoTable const exprS_Info;
  extern InfoTable const PartialS_Info;
  extern InfoTable const set0_Info;
  extern InfoTable const set1_Info;
  extern InfoTable const set2_Info;
  extern InfoTable const set3_Info;
  extern InfoTable const set4_Info;
  extern InfoTable const set5_Info;
  extern InfoTable const set6_Info;
  extern InfoTable const set7_Info;
  extern InfoTable const SetEval_Info;
  extern InfoTable const set_Info;
  extern InfoTable const Values_Info;
}

namespace cyrt
{
  // The family of Control.SetFunctions.PartialS: the layout of
  // PartApplicNode under its own info tables (see builtins.hpp).
  extern PartialInfoFamily g_partials_infos;
  inline InfoTable const * partials_info(index_type nargs)
    { return g_partials_infos.get(nargs); }
}

