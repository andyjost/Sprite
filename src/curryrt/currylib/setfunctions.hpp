#pragma once
#include "curryrt/export.hpp"
#include "curryrt/builtins.hpp"
#include "curryrt/graph/infotable.hpp"

#define PartialS_Type        CyD7Control12SetFunctions8PartialS
#define SetEval_Type         CyD7Control12SetFunctions7SetEval
#define Values_Type          CyD7Control12SetFunctions6Values

#define allValues_Info       CyI7Control12SetFunctions9allValues
#define applyS_Info          CyI7Control12SetFunctions6applyS
#define captureS_Info        CyI7Control12SetFunctions8captureS
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

using namespace curryrt;

extern "C"
{
  extern CURRYRT_DATA DataType const PartialS_Type;
  extern CURRYRT_DATA DataType const SetEval_Type;
  extern CURRYRT_DATA DataType const Values_Type;

  extern CURRYRT_DATA InfoTable const allValues_Info;
  extern CURRYRT_DATA InfoTable const applyS_Info;
  extern CURRYRT_DATA InfoTable const captureS_Info;
  extern CURRYRT_DATA InfoTable const evalS_Info;
  extern CURRYRT_DATA InfoTable const exprS_Info;
  extern CURRYRT_DATA InfoTable const PartialS_Info;
  extern CURRYRT_DATA InfoTable const set0_Info;
  extern CURRYRT_DATA InfoTable const set1_Info;
  extern CURRYRT_DATA InfoTable const set2_Info;
  extern CURRYRT_DATA InfoTable const set3_Info;
  extern CURRYRT_DATA InfoTable const set4_Info;
  extern CURRYRT_DATA InfoTable const set5_Info;
  extern CURRYRT_DATA InfoTable const set6_Info;
  extern CURRYRT_DATA InfoTable const set7_Info;
  extern CURRYRT_DATA InfoTable const SetEval_Info;
  extern CURRYRT_DATA InfoTable const set_Info;
  extern CURRYRT_DATA InfoTable const Values_Info;
}

namespace curryrt
{
  // The family of Control.SetFunctions.PartialS: the layout of
  // PartApplicNode under its own info tables (see builtins.hpp).
  extern CURRYRT_DATA PartialInfoFamily g_partials_infos;
  inline InfoTable const * partials_info(index_type nargs)
    { return g_partials_infos.get(nargs); }
}

