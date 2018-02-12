
#include "Prelude.hpp"
#include "Compare.hpp"

namespace _Prelude {

  Node* __0x2E::hfun() { // .
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new Engine::Partial(::_Prelude::__0x2E_0x2E__0x23lambda1::make(mvar_1, mvar_2), 1);
  }

  Node* __0x2E_0x2E__0x23lambda1::hfun() { // .._#lambda1
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    Node** mvar_3 = arg3;
    return new ::_Prelude::_apply(mvar_1, ::_Prelude::_apply::make(mvar_2, mvar_3));
  }

  Node* _id::hfun() { // id
    Node** mvar_1 = arg1;
    return *(mvar_1);
  }

  Node* _const::hfun() { // const
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return *(mvar_1);
  }

  Node* _curry::hfun() { // curry
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    Node** mvar_3 = arg3;
    return new ::_Prelude::_apply(mvar_1, ::_Prelude::__0x28_0x2C_0x29::make(mvar_2, mvar_3));
  }

  Node* _uncurry::hfun() { // uncurry
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x28_0x2C_0x29_1};
      goto *table_1[(*mvar_2)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_2, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_2)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_2);
      goto *table_1[(*mvar_2)->get_kind()];
    __0x28_0x2C_0x29_1: // "(,)"
      Node** mvar_3 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_2))->arg1;
      Node** mvar_4 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_2))->arg2;
      return new ::_Prelude::_apply(::_Prelude::_apply::make(mvar_1, mvar_3), mvar_4);
    return *(mvar_2);
  }

  Node* _flip::hfun() { // flip
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    Node** mvar_3 = arg3;
    return new ::_Prelude::_apply(::_Prelude::_apply::make(mvar_1, mvar_3), mvar_2);
  }

  Node* _until::hfun() { // until
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    Node** mvar_3 = arg3;
    return new ::_Prelude::_until_case__0x231(::_Prelude::_apply::make(mvar_1, mvar_3), mvar_1, mvar_3, mvar_2);
  }

  Node* _until_case__0x231::hfun() { // until_case_#1
    Node** mvar_4 = arg1;
    Node** mvar_1 = arg2;
    Node** mvar_3 = arg3;
    Node** mvar_2 = arg4;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_4)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_4, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_4)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_4);
      goto *table_1[(*mvar_4)->get_kind()];
    _False_1: // "False"
      return new ::_Prelude::_until(mvar_1, mvar_2, ::_Prelude::_apply::make(mvar_2, mvar_3));
    _True_1: // "True"
      return *(mvar_3);
    return *(mvar_4);
  }

  Node* _seq::hfun() { // seq
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::__0x24_0x21(Engine::Partial::make(::_Prelude::_const::make(mvar_2), 1), mvar_1);
  }

  // external Node* _ensureNotFree::hfun() { throw "External \"Prelude.ensureNotFree\" not implemented"; }

  Node* _ensureSpine::hfun() { // ensureSpine
    Node** mvar_1 = arg1;
    return new ::_Prelude::_ensureSpine_0x2EensureList_0x2E20(::_Prelude::_ensureNotFree::make(mvar_1));
  }

  Node* _ensureSpine_0x2EensureList_0x2E20::hfun() { // ensureSpine.ensureList.20
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::__0x5B_0x5D();
    __0x3A_1: // ":"
      Node** mvar_2 = ((::_Prelude::__0x3A*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_1))->arg2;
      return new ::_Prelude::__0x3A(mvar_2, ::_Prelude::_ensureSpine::make(mvar_3));
    return *(mvar_1);
  }

  Node* __0x24::hfun() { // $
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::_apply(mvar_1, mvar_2);
  }

  // external Node* __0x24_0x21::hfun() { throw "External \"Prelude.$!\" not implemented"; }

  // external Node* __0x24_0x21_0x21::hfun() { throw "External \"Prelude.$!!\" not implemented"; }

  Node* __0x24_0x23::hfun() { // $#
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::__0x24_0x21(mvar_1, ::_Prelude::_ensureNotFree::make(mvar_2));
  }

  // external Node* __0x24_0x23_0x23::hfun() { throw "External \"Prelude.$##\" not implemented"; }

  Node* _error::hfun() { // error
    Node** mvar_1 = arg1;
    return new ::_Prelude::__0x24_0x23_0x23(Engine::Partial::make(::_Prelude::_prim_error::make(), 1), mvar_1);
  }

  // external Node* _prim_error::hfun() { throw "External \"Prelude.prim_error\" not implemented"; }

  // external Node* _failed::hfun() { throw "External \"Prelude.failed\" not implemented"; }

  Node* __0x26_0x26::hfun() { // &&
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    _False_1: // "False"
      return new ::_Prelude::_False();
    _True_1: // "True"
      return *(mvar_2);
    return *(mvar_1);
  }

  Node* __0x7C_0x7C::hfun() { // ||
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    _False_1: // "False"
      return *(mvar_2);
    _True_1: // "True"
      return new ::_Prelude::_True();
    return *(mvar_1);
  }

  Node* _not::hfun() { // not
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    _False_1: // "False"
      return new ::_Prelude::_True();
    _True_1: // "True"
      return new ::_Prelude::_False();
    return *(mvar_1);
  }

  Node* _otherwise::hfun() { // otherwise
    return new ::_Prelude::_True();
  }

  Node* _if_then_else::hfun() { // if_then_else
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    Node** mvar_3 = arg3;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    _False_1: // "False"
      return *(mvar_3);
    _True_1: // "True"
      return *(mvar_2);
    return *(mvar_1);
  }

  Node* _solve::hfun() { // solve
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    _False_1: // "False"
      return DO_FAIL;
    _True_1: // "True"
      return new ::_Prelude::_True();
    return *(mvar_1);
  }

  Node* __0x26_0x3E::hfun() { // &>
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    _False_1: // "False"
      return DO_FAIL;
    _True_1: // "True"
      return *(mvar_2);
    return *(mvar_1);
  }

  // external Node* __0x3D_0x3D::hfun() { throw "External \"Prelude.==\" not implemented"; }

  Node* __0x2F_0x3D::hfun() { // /=
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::_not(::_Prelude::__0x3D_0x3D::make(mvar_1, mvar_2));
  }

  // external Node* __0x3D_0x3A_0x3D::hfun() { throw "External \"Prelude.=:=\" not implemented"; }

  // external Node* __0x26::hfun() { throw "External \"Prelude.&\" not implemented"; }

  // external Node* _compare::hfun() { throw "External \"Prelude.compare\" not implemented"; }

  Node* __0x3C::hfun() { // <
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    // [(3,[])]
    Node** mvar_3;
    mvar_3 = ::_Prelude::_False::make();
    return new ::_Prelude::__0x3C_case__0x231(mvar_1, mvar_2, mvar_3);
    return new ::_Prelude::__0x3C_case__0x231(mvar_1, mvar_2, mvar_3);
  }

  Node* __0x3C_case__0x231::hfun() { // <_case_#1
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    Node** mvar_3 = arg3;
    return new ::_Prelude::__0x3C_case__0x231_case__0x231(::_Prelude::_compare::make(mvar_1, mvar_2), mvar_1, mvar_2, mvar_3);
  }

  Node* __0x3C_case__0x231_case__0x231::hfun() { // <_case_#1_case_#1
    Node** mvar_4 = arg1;
    Node** mvar_1 = arg2;
    Node** mvar_2 = arg3;
    Node** mvar_3 = arg4;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_LT_1, &&_EQ_1, &&_GT_1};
      goto *table_1[(*mvar_4)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_4, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_4)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_4);
      goto *table_1[(*mvar_4)->get_kind()];
    _LT_1: // "LT"
      return new ::_Prelude::_True();
    _EQ_1: // "EQ"
      return *(mvar_3);
    _GT_1: // "GT"
      return *(mvar_3);
    return *(mvar_4);
  }

  Node* __0x3E::hfun() { // >
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    // [(3,[])]
    Node** mvar_3;
    mvar_3 = ::_Prelude::_False::make();
    return new ::_Prelude::__0x3E_case__0x231(mvar_1, mvar_2, mvar_3);
    return new ::_Prelude::__0x3E_case__0x231(mvar_1, mvar_2, mvar_3);
  }

  Node* __0x3E_case__0x231::hfun() { // >_case_#1
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    Node** mvar_3 = arg3;
    return new ::_Prelude::__0x3E_case__0x231_case__0x231(::_Prelude::_compare::make(mvar_1, mvar_2), mvar_1, mvar_2, mvar_3);
  }

  Node* __0x3E_case__0x231_case__0x231::hfun() { // >_case_#1_case_#1
    Node** mvar_4 = arg1;
    Node** mvar_1 = arg2;
    Node** mvar_2 = arg3;
    Node** mvar_3 = arg4;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_LT_1, &&_EQ_1, &&_GT_1};
      goto *table_1[(*mvar_4)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_4, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_4)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_4);
      goto *table_1[(*mvar_4)->get_kind()];
    _LT_1: // "LT"
      return *(mvar_3);
    _EQ_1: // "EQ"
      return *(mvar_3);
    _GT_1: // "GT"
      return new ::_Prelude::_True();
    return *(mvar_4);
  }

  Node* __0x3C_0x3D::hfun() { // <=
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::_not(::_Prelude::__0x3E::make(mvar_1, mvar_2));
  }

  Node* __0x3E_0x3D::hfun() { // >=
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::_not(::_Prelude::__0x3C::make(mvar_1, mvar_2));
  }

  Node* _max::hfun() { // max
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::_max_case__0x231(::_Prelude::__0x3E_0x3D::make(mvar_1, mvar_2), mvar_1, mvar_2);
  }

  Node* _max_case__0x231::hfun() { // max_case_#1
    Node** mvar_3 = arg1;
    Node** mvar_1 = arg2;
    Node** mvar_2 = arg3;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_3)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_3, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_3)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_3);
      goto *table_1[(*mvar_3)->get_kind()];
    _False_1: // "False"
      return *(mvar_2);
    _True_1: // "True"
      return *(mvar_1);
    return *(mvar_3);
  }

  Node* _min::hfun() { // min
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::_min_case__0x231(::_Prelude::__0x3C_0x3D::make(mvar_1, mvar_2), mvar_1, mvar_2);
  }

  Node* _min_case__0x231::hfun() { // min_case_#1
    Node** mvar_3 = arg1;
    Node** mvar_1 = arg2;
    Node** mvar_2 = arg3;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_3)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_3, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_3)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_3);
      goto *table_1[(*mvar_3)->get_kind()];
    _False_1: // "False"
      return *(mvar_2);
    _True_1: // "True"
      return *(mvar_1);
    return *(mvar_3);
  }

  Node* _fst::hfun() { // fst
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x28_0x2C_0x29_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x28_0x2C_0x29_1: // "(,)"
      Node** mvar_2 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg2;
      return *(mvar_2);
    return *(mvar_1);
  }

  Node* _snd::hfun() { // snd
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x28_0x2C_0x29_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x28_0x2C_0x29_1: // "(,)"
      Node** mvar_2 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg2;
      return *(mvar_3);
    return *(mvar_1);
  }

  Node* _head::hfun() { // head
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return DO_FAIL;
    __0x3A_1: // ":"
      Node** mvar_2 = ((::_Prelude::__0x3A*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_1))->arg2;
      return *(mvar_2);
    return *(mvar_1);
  }

  Node* _tail::hfun() { // tail
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return DO_FAIL;
    __0x3A_1: // ":"
      Node** mvar_2 = ((::_Prelude::__0x3A*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_1))->arg2;
      return *(mvar_3);
    return *(mvar_1);
  }

  Node* _null::hfun() { // null
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::_True();
    __0x3A_1: // ":"
      Node** mvar_2 = ((::_Prelude::__0x3A*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_1))->arg2;
      return new ::_Prelude::_False();
    return *(mvar_1);
  }

  Node* __0x2B_0x2B::hfun() { // ++
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return *(mvar_2);
    __0x3A_1: // ":"
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_1))->arg1;
      Node** mvar_4 = ((::_Prelude::__0x3A*) *(mvar_1))->arg2;
      return new ::_Prelude::__0x3A(mvar_3, ::_Prelude::__0x2B_0x2B::make(mvar_4, mvar_2));
    return *(mvar_1);
  }

  Node* _length::hfun() { // length
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new _Prelude::Litint(0);
    __0x3A_1: // ":"
      Node** mvar_2 = ((::_Prelude::__0x3A*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_1))->arg2;
      return new ::_Prelude::__0x2B(_Prelude::Litint::make(1), ::_Prelude::_length::make(mvar_3));
    return *(mvar_1);
  }

  Node* __0x21_0x21::hfun() { // !!
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return DO_FAIL;
    __0x3A_1: // ":"
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_1))->arg1;
      Node** mvar_4 = ((::_Prelude::__0x3A*) *(mvar_1))->arg2;
      return new ::_Prelude::__0x21_0x21_case__0x231(mvar_2, mvar_3, mvar_4);
    return *(mvar_1);
  }

  Node* __0x21_0x21_case__0x231::hfun() { // !!_case_#1
    Node** mvar_2 = arg1;
    Node** mvar_3 = arg2;
    Node** mvar_4 = arg3;
    return new ::_Prelude::__0x21_0x21_case__0x231_case__0x232(::_Prelude::__0x3D_0x3D::make(mvar_2, _Prelude::Litint::make(0)), mvar_2, mvar_3, mvar_4);
  }

  Node* __0x21_0x21_case__0x231_case__0x232::hfun() { // !!_case_#1_case_#2
    Node** mvar_5 = arg1;
    Node** mvar_2 = arg2;
    Node** mvar_3 = arg3;
    Node** mvar_4 = arg4;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_5)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_5, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_5)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_5);
      goto *table_1[(*mvar_5)->get_kind()];
    _False_1: // "False"
      return new ::_Prelude::__0x21_0x21_case__0x231_case__0x231(mvar_2, mvar_4);
    _True_1: // "True"
      return *(mvar_3);
    return *(mvar_5);
  }

  Node* __0x21_0x21_case__0x231_case__0x231::hfun() { // !!_case_#1_case_#1
    Node** mvar_2 = arg1;
    Node** mvar_4 = arg2;
    return new ::_Prelude::__0x21_0x21_case__0x231_case__0x231_case__0x231(::_Prelude::__0x3E::make(mvar_2, _Prelude::Litint::make(0)), mvar_2, mvar_4);
  }

  Node* __0x21_0x21_case__0x231_case__0x231_case__0x231::hfun() { // !!_case_#1_case_#1_case_#1
    Node** mvar_5 = arg1;
    Node** mvar_2 = arg2;
    Node** mvar_4 = arg3;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_5)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_5, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_5)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_5);
      goto *table_1[(*mvar_5)->get_kind()];
    _False_1: // "False"
      return new ::_Prelude::_failed();
    _True_1: // "True"
      return new ::_Prelude::__0x21_0x21(mvar_4, ::_Prelude::__0x2D::make(mvar_2, _Prelude::Litint::make(1)));
    return *(mvar_5);
  }

  Node* _map::hfun() { // map
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_2)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_2, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_2)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_2);
      goto *table_1[(*mvar_2)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::__0x5B_0x5D();
    __0x3A_1: // ":"
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_2))->arg1;
      Node** mvar_4 = ((::_Prelude::__0x3A*) *(mvar_2))->arg2;
      return new ::_Prelude::__0x3A(::_Prelude::_apply::make(mvar_1, mvar_3), ::_Prelude::_map::make(mvar_1, mvar_4));
    return *(mvar_2);
  }

  Node* _foldl::hfun() { // foldl
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    Node** mvar_3 = arg3;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_3)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_3, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_3)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_3);
      goto *table_1[(*mvar_3)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return *(mvar_2);
    __0x3A_1: // ":"
      Node** mvar_4 = ((::_Prelude::__0x3A*) *(mvar_3))->arg1;
      Node** mvar_5 = ((::_Prelude::__0x3A*) *(mvar_3))->arg2;
      return new ::_Prelude::_foldl(mvar_1, ::_Prelude::_apply::make(::_Prelude::_apply::make(mvar_1, mvar_2), mvar_4), mvar_5);
    return *(mvar_3);
  }

  Node* _foldl1::hfun() { // foldl1
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_2)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_2, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_2)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_2);
      goto *table_1[(*mvar_2)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return DO_FAIL;
    __0x3A_1: // ":"
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_2))->arg1;
      Node** mvar_4 = ((::_Prelude::__0x3A*) *(mvar_2))->arg2;
      return new ::_Prelude::_foldl(mvar_1, mvar_3, mvar_4);
    return *(mvar_2);
  }

  Node* _foldr::hfun() { // foldr
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    Node** mvar_3 = arg3;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_3)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_3, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_3)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_3);
      goto *table_1[(*mvar_3)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return *(mvar_2);
    __0x3A_1: // ":"
      Node** mvar_4 = ((::_Prelude::__0x3A*) *(mvar_3))->arg1;
      Node** mvar_5 = ((::_Prelude::__0x3A*) *(mvar_3))->arg2;
      return new ::_Prelude::_apply(::_Prelude::_apply::make(mvar_1, mvar_4), ::_Prelude::_foldr::make(mvar_1, mvar_2, mvar_5));
    return *(mvar_3);
  }

  Node* _foldr1::hfun() { // foldr1
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_2)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_2, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_2)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_2);
      goto *table_1[(*mvar_2)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return DO_FAIL;
    __0x3A_1: // ":"
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_2))->arg1;
      Node** mvar_4 = ((::_Prelude::__0x3A*) *(mvar_2))->arg2;
      return new ::_Prelude::_foldr1_case__0x231(mvar_4, mvar_3, mvar_1);
    return *(mvar_2);
  }

  Node* _foldr1_case__0x231::hfun() { // foldr1_case_#1
    Node** mvar_4 = arg1;
    Node** mvar_3 = arg2;
    Node** mvar_1 = arg3;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_4)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_4, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_4)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_4);
      goto *table_1[(*mvar_4)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return *(mvar_3);
    __0x3A_1: // ":"
      Node** mvar_5 = ((::_Prelude::__0x3A*) *(mvar_4))->arg1;
      Node** mvar_6 = ((::_Prelude::__0x3A*) *(mvar_4))->arg2;
      return new ::_Prelude::_apply(::_Prelude::_apply::make(mvar_1, mvar_3), ::_Prelude::_foldr1::make(mvar_1, ::_Prelude::__0x3A::make(mvar_5, mvar_6)));
    return *(mvar_4);
  }

  Node* _filter::hfun() { // filter
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_2)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_2, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_2)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_2);
      goto *table_1[(*mvar_2)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::__0x5B_0x5D();
    __0x3A_1: // ":"
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_2))->arg1;
      Node** mvar_4 = ((::_Prelude::__0x3A*) *(mvar_2))->arg2;
      return new ::_Prelude::_filter_case__0x231(mvar_1, mvar_3, mvar_4);
    return *(mvar_2);
  }

  Node* _filter_case__0x231::hfun() { // filter_case_#1
    Node** mvar_1 = arg1;
    Node** mvar_3 = arg2;
    Node** mvar_4 = arg3;
    return new ::_Prelude::_filter_case__0x231_case__0x231(::_Prelude::_apply::make(mvar_1, mvar_3), mvar_1, mvar_3, mvar_4);
  }

  Node* _filter_case__0x231_case__0x231::hfun() { // filter_case_#1_case_#1
    Node** mvar_5 = arg1;
    Node** mvar_1 = arg2;
    Node** mvar_3 = arg3;
    Node** mvar_4 = arg4;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_5)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_5, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_5)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_5);
      goto *table_1[(*mvar_5)->get_kind()];
    _False_1: // "False"
      return new ::_Prelude::_filter(mvar_1, mvar_4);
    _True_1: // "True"
      return new ::_Prelude::__0x3A(mvar_3, ::_Prelude::_filter::make(mvar_1, mvar_4));
    return *(mvar_5);
  }

  Node* _zip::hfun() { // zip
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::__0x5B_0x5D();
    __0x3A_1: // ":"
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_1))->arg1;
      Node** mvar_4 = ((::_Prelude::__0x3A*) *(mvar_1))->arg2;
      return new ::_Prelude::_zip_case__0x231(mvar_2, mvar_3, mvar_4);
    return *(mvar_1);
  }

  Node* _zip_case__0x231::hfun() { // zip_case_#1
    Node** mvar_2 = arg1;
    Node** mvar_3 = arg2;
    Node** mvar_4 = arg3;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_2)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_2, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_2)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_2);
      goto *table_1[(*mvar_2)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::__0x5B_0x5D();
    __0x3A_1: // ":"
      Node** mvar_5 = ((::_Prelude::__0x3A*) *(mvar_2))->arg1;
      Node** mvar_6 = ((::_Prelude::__0x3A*) *(mvar_2))->arg2;
      return new ::_Prelude::__0x3A(::_Prelude::__0x28_0x2C_0x29::make(mvar_3, mvar_5), ::_Prelude::_zip::make(mvar_4, mvar_6));
    return *(mvar_2);
  }

  Node* _zip3::hfun() { // zip3
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    Node** mvar_3 = arg3;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::__0x5B_0x5D();
    __0x3A_1: // ":"
      Node** mvar_4 = ((::_Prelude::__0x3A*) *(mvar_1))->arg1;
      Node** mvar_5 = ((::_Prelude::__0x3A*) *(mvar_1))->arg2;
      return new ::_Prelude::_zip3_case__0x231(mvar_2, mvar_3, mvar_4, mvar_5);
    return *(mvar_1);
  }

  Node* _zip3_case__0x231::hfun() { // zip3_case_#1
    Node** mvar_2 = arg1;
    Node** mvar_3 = arg2;
    Node** mvar_4 = arg3;
    Node** mvar_5 = arg4;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_2)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_2, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_2)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_2);
      goto *table_1[(*mvar_2)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::__0x5B_0x5D();
    __0x3A_1: // ":"
      Node** mvar_6 = ((::_Prelude::__0x3A*) *(mvar_2))->arg1;
      Node** mvar_7 = ((::_Prelude::__0x3A*) *(mvar_2))->arg2;
      return new ::_Prelude::_zip3_case__0x231_case__0x231(mvar_3, mvar_4, mvar_6, mvar_5, mvar_7);
    return *(mvar_2);
  }

  Node* _zip3_case__0x231_case__0x231::hfun() { // zip3_case_#1_case_#1
    Node** mvar_3 = arg1;
    Node** mvar_4 = arg2;
    Node** mvar_6 = arg3;
    Node** mvar_5 = arg4;
    Node** mvar_7 = arg5;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_3)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_3, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_3)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_3);
      goto *table_1[(*mvar_3)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::__0x5B_0x5D();
    __0x3A_1: // ":"
      Node** mvar_8 = ((::_Prelude::__0x3A*) *(mvar_3))->arg1;
      Node** mvar_9 = ((::_Prelude::__0x3A*) *(mvar_3))->arg2;
      return new ::_Prelude::__0x3A(::_Prelude::__0x28_0x2C_0x2C_0x29::make(mvar_4, mvar_6, mvar_8), ::_Prelude::_zip3::make(mvar_5, mvar_7, mvar_9));
    return *(mvar_3);
  }

  Node* _zipWith::hfun() { // zipWith
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    Node** mvar_3 = arg3;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_2)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_2, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_2)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_2);
      goto *table_1[(*mvar_2)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::__0x5B_0x5D();
    __0x3A_1: // ":"
      Node** mvar_4 = ((::_Prelude::__0x3A*) *(mvar_2))->arg1;
      Node** mvar_5 = ((::_Prelude::__0x3A*) *(mvar_2))->arg2;
      return new ::_Prelude::_zipWith_case__0x231(mvar_3, mvar_1, mvar_4, mvar_5);
    return *(mvar_2);
  }

  Node* _zipWith_case__0x231::hfun() { // zipWith_case_#1
    Node** mvar_3 = arg1;
    Node** mvar_1 = arg2;
    Node** mvar_4 = arg3;
    Node** mvar_5 = arg4;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_3)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_3, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_3)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_3);
      goto *table_1[(*mvar_3)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::__0x5B_0x5D();
    __0x3A_1: // ":"
      Node** mvar_6 = ((::_Prelude::__0x3A*) *(mvar_3))->arg1;
      Node** mvar_7 = ((::_Prelude::__0x3A*) *(mvar_3))->arg2;
      return new ::_Prelude::__0x3A(::_Prelude::_apply::make(::_Prelude::_apply::make(mvar_1, mvar_4), mvar_6), ::_Prelude::_zipWith::make(mvar_1, mvar_5, mvar_7));
    return *(mvar_3);
  }

  Node* _zipWith3::hfun() { // zipWith3
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    Node** mvar_3 = arg3;
    Node** mvar_4 = arg4;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_2)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_2, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_2)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_2);
      goto *table_1[(*mvar_2)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::__0x5B_0x5D();
    __0x3A_1: // ":"
      Node** mvar_5 = ((::_Prelude::__0x3A*) *(mvar_2))->arg1;
      Node** mvar_6 = ((::_Prelude::__0x3A*) *(mvar_2))->arg2;
      return new ::_Prelude::_zipWith3_case__0x231(mvar_3, mvar_4, mvar_1, mvar_5, mvar_6);
    return *(mvar_2);
  }

  Node* _zipWith3_case__0x231::hfun() { // zipWith3_case_#1
    Node** mvar_3 = arg1;
    Node** mvar_4 = arg2;
    Node** mvar_1 = arg3;
    Node** mvar_5 = arg4;
    Node** mvar_6 = arg5;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_3)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_3, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_3)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_3);
      goto *table_1[(*mvar_3)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::__0x5B_0x5D();
    __0x3A_1: // ":"
      Node** mvar_7 = ((::_Prelude::__0x3A*) *(mvar_3))->arg1;
      Node** mvar_8 = ((::_Prelude::__0x3A*) *(mvar_3))->arg2;
      return new ::_Prelude::_zipWith3_case__0x231_case__0x231(mvar_4, mvar_1, mvar_5, mvar_7, mvar_6, mvar_8);
    return *(mvar_3);
  }

  Node* _zipWith3_case__0x231_case__0x231::hfun() { // zipWith3_case_#1_case_#1
    Node** mvar_4 = arg1;
    Node** mvar_1 = arg2;
    Node** mvar_5 = arg3;
    Node** mvar_7 = arg4;
    Node** mvar_6 = arg5;
    Node** mvar_8 = arg6;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_4)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_4, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_4)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_4);
      goto *table_1[(*mvar_4)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::__0x5B_0x5D();
    __0x3A_1: // ":"
      Node** mvar_9 = ((::_Prelude::__0x3A*) *(mvar_4))->arg1;
      Node** mvar_10 = ((::_Prelude::__0x3A*) *(mvar_4))->arg2;
      return new ::_Prelude::__0x3A(::_Prelude::_apply::make(::_Prelude::_apply::make(::_Prelude::_apply::make(mvar_1, mvar_5), mvar_7), mvar_9), ::_Prelude::_zipWith3::make(mvar_1, mvar_6, mvar_8, mvar_10));
    return *(mvar_4);
  }

  Node* _unzip::hfun() { // unzip
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::__0x28_0x2C_0x29(::_Prelude::__0x5B_0x5D::make(), ::_Prelude::__0x5B_0x5D::make());
    __0x3A_1: // ":"
      Node** mvar_2 = ((::_Prelude::__0x3A*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_1))->arg2;
      return new ::_Prelude::_unzip_case__0x231(mvar_2, mvar_3);
    return *(mvar_1);
  }

  Node* _unzip_case__0x231::hfun() { // unzip_case_#1
    Node** mvar_2 = arg1;
    Node** mvar_3 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x28_0x2C_0x29_1};
      goto *table_1[(*mvar_2)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_2, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_2)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_2);
      goto *table_1[(*mvar_2)->get_kind()];
    __0x28_0x2C_0x29_1: // "(,)"
      Node** mvar_4 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_2))->arg1;
      Node** mvar_5 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_2))->arg2;
      // [(6,[]),(7,[]),(8,[])]
      Node** mvar_6;
      mvar_6 = ::_Prelude::_unzip::make(mvar_3);
      Node** mvar_7;
      mvar_7 = ::_Prelude::_unzip_0x2E__0x23selFP2_0x23xs::make(mvar_6);
      Node** mvar_8;
      mvar_8 = ::_Prelude::_unzip_0x2E__0x23selFP3_0x23ys::make(mvar_6);
      return new ::_Prelude::__0x28_0x2C_0x29(::_Prelude::__0x3A::make(mvar_4, mvar_7), ::_Prelude::__0x3A::make(mvar_5, mvar_8));
      return new ::_Prelude::__0x28_0x2C_0x29(::_Prelude::__0x3A::make(mvar_4, mvar_7), ::_Prelude::__0x3A::make(mvar_5, mvar_8));
    return *(mvar_2);
  }

  Node* _unzip_0x2E__0x23selFP2_0x23xs::hfun() { // unzip._#selFP2#xs
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x28_0x2C_0x29_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x28_0x2C_0x29_1: // "(,)"
      Node** mvar_2 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg2;
      return *(mvar_2);
    return *(mvar_1);
  }

  Node* _unzip_0x2E__0x23selFP3_0x23ys::hfun() { // unzip._#selFP3#ys
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x28_0x2C_0x29_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x28_0x2C_0x29_1: // "(,)"
      Node** mvar_2 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg2;
      return *(mvar_3);
    return *(mvar_1);
  }

  Node* _unzip3::hfun() { // unzip3
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::__0x28_0x2C_0x2C_0x29(::_Prelude::__0x5B_0x5D::make(), ::_Prelude::__0x5B_0x5D::make(), ::_Prelude::__0x5B_0x5D::make());
    __0x3A_1: // ":"
      Node** mvar_2 = ((::_Prelude::__0x3A*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_1))->arg2;
      return new ::_Prelude::_unzip3_case__0x231(mvar_2, mvar_3);
    return *(mvar_1);
  }

  Node* _unzip3_case__0x231::hfun() { // unzip3_case_#1
    Node** mvar_2 = arg1;
    Node** mvar_3 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x28_0x2C_0x2C_0x29_1};
      goto *table_1[(*mvar_2)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_2, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_2)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_2);
      goto *table_1[(*mvar_2)->get_kind()];
    __0x28_0x2C_0x2C_0x29_1: // "(,,)"
      Node** mvar_4 = ((::_Prelude::__0x28_0x2C_0x2C_0x29*) *(mvar_2))->arg1;
      Node** mvar_5 = ((::_Prelude::__0x28_0x2C_0x2C_0x29*) *(mvar_2))->arg2;
      Node** mvar_6 = ((::_Prelude::__0x28_0x2C_0x2C_0x29*) *(mvar_2))->arg3;
      // [(7,[]),(8,[]),(9,[]),(10,[])]
      Node** mvar_7;
      mvar_7 = ::_Prelude::_unzip3::make(mvar_3);
      Node** mvar_8;
      mvar_8 = ::_Prelude::_unzip3_0x2E__0x23selFP5_0x23xs::make(mvar_7);
      Node** mvar_9;
      mvar_9 = ::_Prelude::_unzip3_0x2E__0x23selFP6_0x23ys::make(mvar_7);
      Node** mvar_10;
      mvar_10 = ::_Prelude::_unzip3_0x2E__0x23selFP7_0x23zs::make(mvar_7);
      return new ::_Prelude::__0x28_0x2C_0x2C_0x29(::_Prelude::__0x3A::make(mvar_4, mvar_8), ::_Prelude::__0x3A::make(mvar_5, mvar_9), ::_Prelude::__0x3A::make(mvar_6, mvar_10));
      return new ::_Prelude::__0x28_0x2C_0x2C_0x29(::_Prelude::__0x3A::make(mvar_4, mvar_8), ::_Prelude::__0x3A::make(mvar_5, mvar_9), ::_Prelude::__0x3A::make(mvar_6, mvar_10));
    return *(mvar_2);
  }

  Node* _unzip3_0x2E__0x23selFP5_0x23xs::hfun() { // unzip3._#selFP5#xs
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x28_0x2C_0x2C_0x29_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x28_0x2C_0x2C_0x29_1: // "(,,)"
      Node** mvar_2 = ((::_Prelude::__0x28_0x2C_0x2C_0x29*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x28_0x2C_0x2C_0x29*) *(mvar_1))->arg2;
      Node** mvar_4 = ((::_Prelude::__0x28_0x2C_0x2C_0x29*) *(mvar_1))->arg3;
      return *(mvar_2);
    return *(mvar_1);
  }

  Node* _unzip3_0x2E__0x23selFP6_0x23ys::hfun() { // unzip3._#selFP6#ys
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x28_0x2C_0x2C_0x29_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x28_0x2C_0x2C_0x29_1: // "(,,)"
      Node** mvar_2 = ((::_Prelude::__0x28_0x2C_0x2C_0x29*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x28_0x2C_0x2C_0x29*) *(mvar_1))->arg2;
      Node** mvar_4 = ((::_Prelude::__0x28_0x2C_0x2C_0x29*) *(mvar_1))->arg3;
      return *(mvar_3);
    return *(mvar_1);
  }

  Node* _unzip3_0x2E__0x23selFP7_0x23zs::hfun() { // unzip3._#selFP7#zs
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x28_0x2C_0x2C_0x29_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x28_0x2C_0x2C_0x29_1: // "(,,)"
      Node** mvar_2 = ((::_Prelude::__0x28_0x2C_0x2C_0x29*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x28_0x2C_0x2C_0x29*) *(mvar_1))->arg2;
      Node** mvar_4 = ((::_Prelude::__0x28_0x2C_0x2C_0x29*) *(mvar_1))->arg3;
      return *(mvar_4);
    return *(mvar_1);
  }

  Node* _concat::hfun() { // concat
    Node** mvar_1 = arg1;
    return new ::_Prelude::_foldr(Engine::Partial::make(::_Prelude::__0x2B_0x2B::make(), 2), ::_Prelude::__0x5B_0x5D::make(), mvar_1);
  }

  Node* _concatMap::hfun() { // concatMap
    Node** mvar_1 = arg1;
    return new ::_Prelude::__0x2E(Engine::Partial::make(::_Prelude::_concat::make(), 1), Engine::Partial::make(::_Prelude::_map::make(mvar_1), 1));
  }

  Node* _iterate::hfun() { // iterate
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::__0x3A(mvar_2, ::_Prelude::_iterate::make(mvar_1, ::_Prelude::_apply::make(mvar_1, mvar_2)));
  }

  Node* _repeat::hfun() { // repeat
    Node** mvar_1 = arg1;
    return new ::_Prelude::__0x3A(mvar_1, ::_Prelude::_repeat::make(mvar_1));
  }

  Node* _replicate::hfun() { // replicate
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::_take(mvar_1, ::_Prelude::_repeat::make(mvar_2));
  }

  Node* _take::hfun() { // take
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::_take_case__0x231(::_Prelude::__0x3C_0x3D::make(mvar_1, _Prelude::Litint::make(0)), mvar_1, mvar_2);
  }

  Node* _take_case__0x231::hfun() { // take_case_#1
    Node** mvar_3 = arg1;
    Node** mvar_1 = arg2;
    Node** mvar_2 = arg3;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_3)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_3, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_3)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_3);
      goto *table_1[(*mvar_3)->get_kind()];
    _False_1: // "False"
      return new ::_Prelude::_take_0x2Etakep_0x2E220(mvar_1, mvar_2);
    _True_1: // "True"
      return new ::_Prelude::__0x5B_0x5D();
    return *(mvar_3);
  }

  Node* _take_0x2Etakep_0x2E220::hfun() { // take.takep.220
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_2)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_2, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_2)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_2);
      goto *table_1[(*mvar_2)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::__0x5B_0x5D();
    __0x3A_1: // ":"
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_2))->arg1;
      Node** mvar_4 = ((::_Prelude::__0x3A*) *(mvar_2))->arg2;
      return new ::_Prelude::__0x3A(mvar_3, ::_Prelude::_take::make(::_Prelude::__0x2D::make(mvar_1, _Prelude::Litint::make(1)), mvar_4));
    return *(mvar_2);
  }

  Node* _drop::hfun() { // drop
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::_drop_case__0x231(::_Prelude::__0x3C_0x3D::make(mvar_1, _Prelude::Litint::make(0)), mvar_1, mvar_2);
  }

  Node* _drop_case__0x231::hfun() { // drop_case_#1
    Node** mvar_3 = arg1;
    Node** mvar_1 = arg2;
    Node** mvar_2 = arg3;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_3)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_3, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_3)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_3);
      goto *table_1[(*mvar_3)->get_kind()];
    _False_1: // "False"
      return new ::_Prelude::_drop_0x2Edropp_0x2E229(mvar_1, mvar_2);
    _True_1: // "True"
      return *(mvar_2);
    return *(mvar_3);
  }

  Node* _drop_0x2Edropp_0x2E229::hfun() { // drop.dropp.229
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_2)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_2, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_2)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_2);
      goto *table_1[(*mvar_2)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::__0x5B_0x5D();
    __0x3A_1: // ":"
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_2))->arg1;
      Node** mvar_4 = ((::_Prelude::__0x3A*) *(mvar_2))->arg2;
      return new ::_Prelude::_drop(::_Prelude::__0x2D::make(mvar_1, _Prelude::Litint::make(1)), mvar_4);
    return *(mvar_2);
  }

  Node* _splitAt::hfun() { // splitAt
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::_splitAt_case__0x231(::_Prelude::__0x3C_0x3D::make(mvar_1, _Prelude::Litint::make(0)), mvar_1, mvar_2);
  }

  Node* _splitAt_case__0x231::hfun() { // splitAt_case_#1
    Node** mvar_3 = arg1;
    Node** mvar_1 = arg2;
    Node** mvar_2 = arg3;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_3)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_3, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_3)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_3);
      goto *table_1[(*mvar_3)->get_kind()];
    _False_1: // "False"
      return new ::_Prelude::_splitAt_0x2EsplitAtp_0x2E239(mvar_1, mvar_2);
    _True_1: // "True"
      return new ::_Prelude::__0x28_0x2C_0x29(::_Prelude::__0x5B_0x5D::make(), mvar_2);
    return *(mvar_3);
  }

  Node* _splitAt_0x2EsplitAtp_0x2E239::hfun() { // splitAt.splitAtp.239
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_2)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_2, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_2)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_2);
      goto *table_1[(*mvar_2)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::__0x28_0x2C_0x29(::_Prelude::__0x5B_0x5D::make(), ::_Prelude::__0x5B_0x5D::make());
    __0x3A_1: // ":"
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_2))->arg1;
      Node** mvar_4 = ((::_Prelude::__0x3A*) *(mvar_2))->arg2;
      return new ::_Prelude::_splitAt_0x2EsplitAtp_0x2E239_let__0x231(mvar_3, mvar_1, mvar_4);
    return *(mvar_2);
  }

  Node* _splitAt_0x2EsplitAtp_0x2E239_let__0x231::hfun() { // splitAt.splitAtp.239_let_#1
    Node** mvar_3 = arg1;
    Node** mvar_1 = arg2;
    Node** mvar_4 = arg3;
    // [(5,[]),(6,[]),(7,[])]
    Node** mvar_5;
    mvar_5 = ::_Prelude::_splitAt::make(::_Prelude::__0x2D::make(mvar_1, _Prelude::Litint::make(1)), mvar_4);
    Node** mvar_6;
    mvar_6 = ::_Prelude::_splitAt_0x2EsplitAtp_0x2E239_0x2E__0x23selFP9_0x23ys::make(mvar_5);
    Node** mvar_7;
    mvar_7 = ::_Prelude::_splitAt_0x2EsplitAtp_0x2E239_0x2E__0x23selFP10_0x23zs::make(mvar_5);
    return new ::_Prelude::__0x28_0x2C_0x29(::_Prelude::__0x3A::make(mvar_3, mvar_6), mvar_7);
    return new ::_Prelude::__0x28_0x2C_0x29(::_Prelude::__0x3A::make(mvar_3, mvar_6), mvar_7);
  }

  Node* _splitAt_0x2EsplitAtp_0x2E239_0x2E__0x23selFP9_0x23ys::hfun() { // splitAt.splitAtp.239._#selFP9#ys
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x28_0x2C_0x29_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x28_0x2C_0x29_1: // "(,)"
      Node** mvar_2 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg2;
      return *(mvar_2);
    return *(mvar_1);
  }

  Node* _splitAt_0x2EsplitAtp_0x2E239_0x2E__0x23selFP10_0x23zs::hfun() { // splitAt.splitAtp.239._#selFP10#zs
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x28_0x2C_0x29_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x28_0x2C_0x29_1: // "(,)"
      Node** mvar_2 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg2;
      return *(mvar_3);
    return *(mvar_1);
  }

  Node* _takeWhile::hfun() { // takeWhile
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_2)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_2, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_2)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_2);
      goto *table_1[(*mvar_2)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::__0x5B_0x5D();
    __0x3A_1: // ":"
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_2))->arg1;
      Node** mvar_4 = ((::_Prelude::__0x3A*) *(mvar_2))->arg2;
      return new ::_Prelude::_takeWhile_case__0x231(mvar_1, mvar_3, mvar_4);
    return *(mvar_2);
  }

  Node* _takeWhile_case__0x231::hfun() { // takeWhile_case_#1
    Node** mvar_1 = arg1;
    Node** mvar_3 = arg2;
    Node** mvar_4 = arg3;
    return new ::_Prelude::_takeWhile_case__0x231_case__0x231(::_Prelude::_apply::make(mvar_1, mvar_3), mvar_1, mvar_3, mvar_4);
  }

  Node* _takeWhile_case__0x231_case__0x231::hfun() { // takeWhile_case_#1_case_#1
    Node** mvar_5 = arg1;
    Node** mvar_1 = arg2;
    Node** mvar_3 = arg3;
    Node** mvar_4 = arg4;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_5)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_5, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_5)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_5);
      goto *table_1[(*mvar_5)->get_kind()];
    _False_1: // "False"
      return new ::_Prelude::__0x5B_0x5D();
    _True_1: // "True"
      return new ::_Prelude::__0x3A(mvar_3, ::_Prelude::_takeWhile::make(mvar_1, mvar_4));
    return *(mvar_5);
  }

  Node* _dropWhile::hfun() { // dropWhile
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_2)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_2, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_2)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_2);
      goto *table_1[(*mvar_2)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::__0x5B_0x5D();
    __0x3A_1: // ":"
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_2))->arg1;
      Node** mvar_4 = ((::_Prelude::__0x3A*) *(mvar_2))->arg2;
      return new ::_Prelude::_dropWhile_case__0x231(mvar_1, mvar_3, mvar_4);
    return *(mvar_2);
  }

  Node* _dropWhile_case__0x231::hfun() { // dropWhile_case_#1
    Node** mvar_1 = arg1;
    Node** mvar_3 = arg2;
    Node** mvar_4 = arg3;
    return new ::_Prelude::_dropWhile_case__0x231_case__0x231(::_Prelude::_apply::make(mvar_1, mvar_3), mvar_1, mvar_3, mvar_4);
  }

  Node* _dropWhile_case__0x231_case__0x231::hfun() { // dropWhile_case_#1_case_#1
    Node** mvar_5 = arg1;
    Node** mvar_1 = arg2;
    Node** mvar_3 = arg3;
    Node** mvar_4 = arg4;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_5)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_5, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_5)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_5);
      goto *table_1[(*mvar_5)->get_kind()];
    _False_1: // "False"
      return new ::_Prelude::__0x3A(mvar_3, mvar_4);
    _True_1: // "True"
      return new ::_Prelude::_dropWhile(mvar_1, mvar_4);
    return *(mvar_5);
  }

  Node* _span::hfun() { // span
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_2)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_2, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_2)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_2);
      goto *table_1[(*mvar_2)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::__0x28_0x2C_0x29(::_Prelude::__0x5B_0x5D::make(), ::_Prelude::__0x5B_0x5D::make());
    __0x3A_1: // ":"
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_2))->arg1;
      Node** mvar_4 = ((::_Prelude::__0x3A*) *(mvar_2))->arg2;
      return new ::_Prelude::_span_case__0x231(mvar_1, mvar_3, mvar_4);
    return *(mvar_2);
  }

  Node* _span_case__0x231::hfun() { // span_case_#1
    Node** mvar_1 = arg1;
    Node** mvar_3 = arg2;
    Node** mvar_4 = arg3;
    return new ::_Prelude::_span_case__0x231_case__0x232(::_Prelude::_apply::make(mvar_1, mvar_3), mvar_1, mvar_3, mvar_4);
  }

  Node* _span_case__0x231_case__0x232::hfun() { // span_case_#1_case_#2
    Node** mvar_8 = arg1;
    Node** mvar_1 = arg2;
    Node** mvar_3 = arg3;
    Node** mvar_4 = arg4;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_8)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_8, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_8)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_8);
      goto *table_1[(*mvar_8)->get_kind()];
    _False_1: // "False"
      return new ::_Prelude::_span_case__0x231_case__0x231(mvar_3, mvar_4);
    _True_1: // "True"
      // [(5,[]),(6,[]),(7,[])]
      Node** mvar_5;
      mvar_5 = ::_Prelude::_span::make(mvar_1, mvar_4);
      Node** mvar_6;
      mvar_6 = ::_Prelude::_span_0x2E__0x23selFP12_0x23ys::make(mvar_5);
      Node** mvar_7;
      mvar_7 = ::_Prelude::_span_0x2E__0x23selFP13_0x23zs::make(mvar_5);
      return new ::_Prelude::__0x28_0x2C_0x29(::_Prelude::__0x3A::make(mvar_3, mvar_6), mvar_7);
      return new ::_Prelude::__0x28_0x2C_0x29(::_Prelude::__0x3A::make(mvar_3, mvar_6), mvar_7);
    return *(mvar_8);
  }

  Node* _span_case__0x231_case__0x231::hfun() { // span_case_#1_case_#1
    Node** mvar_3 = arg1;
    Node** mvar_4 = arg2;
    return new ::_Prelude::_span_case__0x231_case__0x231_case__0x231(::_Prelude::_otherwise::make(), mvar_3, mvar_4);
  }

  Node* _span_case__0x231_case__0x231_case__0x231::hfun() { // span_case_#1_case_#1_case_#1
    Node** mvar_5 = arg1;
    Node** mvar_3 = arg2;
    Node** mvar_4 = arg3;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_5)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_5, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_5)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_5);
      goto *table_1[(*mvar_5)->get_kind()];
    _False_1: // "False"
      return new ::_Prelude::_failed();
    _True_1: // "True"
      return new ::_Prelude::__0x28_0x2C_0x29(::_Prelude::__0x5B_0x5D::make(), ::_Prelude::__0x3A::make(mvar_3, mvar_4));
    return *(mvar_5);
  }

  Node* _span_0x2E__0x23selFP12_0x23ys::hfun() { // span._#selFP12#ys
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x28_0x2C_0x29_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x28_0x2C_0x29_1: // "(,)"
      Node** mvar_2 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg2;
      return *(mvar_2);
    return *(mvar_1);
  }

  Node* _span_0x2E__0x23selFP13_0x23zs::hfun() { // span._#selFP13#zs
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x28_0x2C_0x29_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x28_0x2C_0x29_1: // "(,)"
      Node** mvar_2 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg2;
      return *(mvar_3);
    return *(mvar_1);
  }

  Node* _break::hfun() { // break
    Node** mvar_1 = arg1;
    return new Engine::Partial(::_Prelude::_span::make(::_Prelude::__0x2E::make(Engine::Partial::make(::_Prelude::_not::make(), 1), mvar_1)), 1);
  }

  Node* _lines::hfun() { // lines
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::__0x5B_0x5D();
    __0x3A_1: // ":"
      Node** mvar_2 = ((::_Prelude::__0x3A*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_1))->arg2;
      // [(4,[]),(5,[]),(6,[])]
      Node** mvar_4;
      mvar_4 = ::_Prelude::_lines_0x2Esplitline_0x2E271::make(::_Prelude::__0x3A::make(mvar_2, mvar_3));
      Node** mvar_5;
      mvar_5 = ::_Prelude::_lines_0x2E__0x23selFP18_0x23l::make(mvar_4);
      Node** mvar_6;
      mvar_6 = ::_Prelude::_lines_0x2E__0x23selFP19_0x23xs_l::make(mvar_4);
      return new ::_Prelude::__0x3A(mvar_5, ::_Prelude::_lines::make(mvar_6));
      return new ::_Prelude::__0x3A(mvar_5, ::_Prelude::_lines::make(mvar_6));
    return *(mvar_1);
  }

  Node* _lines_0x2Esplitline_0x2E271::hfun() { // lines.splitline.271
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::__0x28_0x2C_0x29(::_Prelude::__0x5B_0x5D::make(), ::_Prelude::__0x5B_0x5D::make());
    __0x3A_1: // ":"
      Node** mvar_2 = ((::_Prelude::__0x3A*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_1))->arg2;
      return new ::_Prelude::_lines_0x2Esplitline_0x2E271_case__0x231(mvar_2, mvar_3);
    return *(mvar_1);
  }

  Node* _lines_0x2Esplitline_0x2E271_case__0x231::hfun() { // lines.splitline.271_case_#1
    Node** mvar_2 = arg1;
    Node** mvar_3 = arg2;
    return new ::_Prelude::_lines_0x2Esplitline_0x2E271_case__0x231_case__0x231(::_Prelude::__0x3D_0x3D::make(mvar_2, _Prelude::Litchar::make('\n')), mvar_2, mvar_3);
  }

  Node* _lines_0x2Esplitline_0x2E271_case__0x231_case__0x231::hfun() { // lines.splitline.271_case_#1_case_#1
    Node** mvar_7 = arg1;
    Node** mvar_2 = arg2;
    Node** mvar_3 = arg3;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_7)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_7, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_7)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_7);
      goto *table_1[(*mvar_7)->get_kind()];
    _False_1: // "False"
      return new ::_Prelude::_lines_0x2Esplitline_0x2E271_case__0x231_case__0x231_let__0x231(mvar_2, mvar_3);
    _True_1: // "True"
      return new ::_Prelude::__0x28_0x2C_0x29(::_Prelude::__0x5B_0x5D::make(), mvar_3);
    return *(mvar_7);
  }

  Node* _lines_0x2Esplitline_0x2E271_case__0x231_case__0x231_let__0x231::hfun() { // lines.splitline.271_case_#1_case_#1_let_#1
    Node** mvar_2 = arg1;
    Node** mvar_3 = arg2;
    // [(4,[]),(5,[]),(6,[])]
    Node** mvar_4;
    mvar_4 = ::_Prelude::_lines_0x2Esplitline_0x2E271::make(mvar_3);
    Node** mvar_5;
    mvar_5 = ::_Prelude::_lines_0x2Esplitline_0x2E271_0x2E__0x23selFP15_0x23ds::make(mvar_4);
    Node** mvar_6;
    mvar_6 = ::_Prelude::_lines_0x2Esplitline_0x2E271_0x2E__0x23selFP16_0x23es::make(mvar_4);
    return new ::_Prelude::__0x28_0x2C_0x29(::_Prelude::__0x3A::make(mvar_2, mvar_5), mvar_6);
    return new ::_Prelude::__0x28_0x2C_0x29(::_Prelude::__0x3A::make(mvar_2, mvar_5), mvar_6);
  }

  Node* _lines_0x2Esplitline_0x2E271_0x2E__0x23selFP15_0x23ds::hfun() { // lines.splitline.271._#selFP15#ds
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x28_0x2C_0x29_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x28_0x2C_0x29_1: // "(,)"
      Node** mvar_2 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg2;
      return *(mvar_2);
    return *(mvar_1);
  }

  Node* _lines_0x2Esplitline_0x2E271_0x2E__0x23selFP16_0x23es::hfun() { // lines.splitline.271._#selFP16#es
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x28_0x2C_0x29_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x28_0x2C_0x29_1: // "(,)"
      Node** mvar_2 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg2;
      return *(mvar_3);
    return *(mvar_1);
  }

  Node* _lines_0x2E__0x23selFP18_0x23l::hfun() { // lines._#selFP18#l
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x28_0x2C_0x29_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x28_0x2C_0x29_1: // "(,)"
      Node** mvar_2 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg2;
      return *(mvar_2);
    return *(mvar_1);
  }

  Node* _lines_0x2E__0x23selFP19_0x23xs_l::hfun() { // lines._#selFP19#xs_l
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x28_0x2C_0x29_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x28_0x2C_0x29_1: // "(,)"
      Node** mvar_2 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg2;
      return *(mvar_3);
    return *(mvar_1);
  }

  Node* _unlines::hfun() { // unlines
    Node** mvar_1 = arg1;
    return new ::_Prelude::_apply(::_Prelude::_concatMap::make(Engine::Partial::make(::_Prelude::_flip::make(Engine::Partial::make(::_Prelude::__0x2B_0x2B::make(), 2), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('\n'), ::_Prelude::__0x5B_0x5D::make())), 1)), mvar_1);
  }

  Node* _words::hfun() { // words
    Node** mvar_1 = arg1;
    // [(2,[])]
    Node** mvar_2;
    mvar_2 = ::_Prelude::_dropWhile::make(Engine::Partial::make(::_Prelude::_words_0x2EisSpace_0x2E283::make(), 1), mvar_1);
    return new ::_Prelude::_words_case__0x231(mvar_2);
    return new ::_Prelude::_words_case__0x231(mvar_2);
  }

  Node* _words_case__0x231::hfun() { // words_case_#1
    Node** mvar_2 = arg1;
    return new ::_Prelude::_words_case__0x231_case__0x231(::_Prelude::__0x3D_0x3D::make(mvar_2, ::_Prelude::__0x5B_0x5D::make()), mvar_2);
  }

  Node* _words_case__0x231_case__0x231::hfun() { // words_case_#1_case_#1
    Node** mvar_6 = arg1;
    Node** mvar_2 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_6)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_6, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_6)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_6);
      goto *table_1[(*mvar_6)->get_kind()];
    _False_1: // "False"
      // [(3,[]),(4,[]),(5,[])]
      Node** mvar_3;
      mvar_3 = ::_Prelude::_apply::make(::_Prelude::_break::make(Engine::Partial::make(::_Prelude::_words_0x2EisSpace_0x2E283::make(), 1)), mvar_2);
      Node** mvar_4;
      mvar_4 = ::_Prelude::_words_0x2E__0x23selFP21_0x23w::make(mvar_3);
      Node** mvar_5;
      mvar_5 = ::_Prelude::_words_0x2E__0x23selFP22_0x23s2::make(mvar_3);
      return new ::_Prelude::__0x3A(mvar_4, ::_Prelude::_words::make(mvar_5));
      return new ::_Prelude::__0x3A(mvar_4, ::_Prelude::_words::make(mvar_5));
    _True_1: // "True"
      return new ::_Prelude::__0x5B_0x5D();
    return *(mvar_6);
  }

  Node* _words_0x2EisSpace_0x2E283::hfun() { // words.isSpace.283
    Node** mvar_1 = arg1;
    return new ::_Prelude::__0x7C_0x7C(::_Prelude::__0x3D_0x3D::make(mvar_1, _Prelude::Litchar::make(' ')), ::_Prelude::__0x7C_0x7C::make(::_Prelude::__0x3D_0x3D::make(mvar_1, _Prelude::Litchar::make('\t')), ::_Prelude::__0x7C_0x7C::make(::_Prelude::__0x3D_0x3D::make(mvar_1, _Prelude::Litchar::make('\n')), ::_Prelude::__0x3D_0x3D::make(mvar_1, _Prelude::Litchar::make('\r')))));
  }

  Node* _words_0x2E__0x23selFP21_0x23w::hfun() { // words._#selFP21#w
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x28_0x2C_0x29_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x28_0x2C_0x29_1: // "(,)"
      Node** mvar_2 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg2;
      return *(mvar_2);
    return *(mvar_1);
  }

  Node* _words_0x2E__0x23selFP22_0x23s2::hfun() { // words._#selFP22#s2
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x28_0x2C_0x29_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x28_0x2C_0x29_1: // "(,)"
      Node** mvar_2 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_1))->arg2;
      return *(mvar_3);
    return *(mvar_1);
  }

  Node* _unwords::hfun() { // unwords
    Node** mvar_1 = arg1;
    return new ::_Prelude::_unwords_case__0x231(::_Prelude::__0x3D_0x3D::make(mvar_1, ::_Prelude::__0x5B_0x5D::make()), mvar_1);
  }

  Node* _unwords_case__0x231::hfun() { // unwords_case_#1
    Node** mvar_2 = arg1;
    Node** mvar_1 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_2)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_2, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_2)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_2);
      goto *table_1[(*mvar_2)->get_kind()];
    _False_1: // "False"
      return new ::_Prelude::_foldr1(Engine::Partial::make(::_Prelude::_unwords_0x2E__0x23lambda5::make(), 2), mvar_1);
    _True_1: // "True"
      return new ::_Prelude::__0x5B_0x5D();
    return *(mvar_2);
  }

  Node* _unwords_0x2E__0x23lambda5::hfun() { // unwords._#lambda5
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::__0x2B_0x2B(mvar_1, ::_Prelude::__0x3A::make(_Prelude::Litchar::make(' '), mvar_2));
  }

  Node* _reverse::hfun() { // reverse
    return new Engine::Partial(::_Prelude::_foldl::make(Engine::Partial::make(::_Prelude::_flip::make(Engine::Partial::make(::_Prelude::__0x3A::make(), 2)), 2), ::_Prelude::__0x5B_0x5D::make()), 1);
  }

  Node* _and::hfun() { // and
    return new Engine::Partial(::_Prelude::_foldr::make(Engine::Partial::make(::_Prelude::__0x26_0x26::make(), 2), ::_Prelude::_True::make()), 1);
  }

  Node* _or::hfun() { // or
    return new Engine::Partial(::_Prelude::_foldr::make(Engine::Partial::make(::_Prelude::__0x7C_0x7C::make(), 2), ::_Prelude::_False::make()), 1);
  }

  Node* _any::hfun() { // any
    Node** mvar_1 = arg1;
    return new ::_Prelude::__0x2E(::_Prelude::_or::make(), Engine::Partial::make(::_Prelude::_map::make(mvar_1), 1));
  }

  Node* _all::hfun() { // all
    Node** mvar_1 = arg1;
    return new ::_Prelude::__0x2E(::_Prelude::_and::make(), Engine::Partial::make(::_Prelude::_map::make(mvar_1), 1));
  }

  Node* _elem::hfun() { // elem
    Node** mvar_1 = arg1;
    return new ::_Prelude::_any(Engine::Partial::make(::_Prelude::__0x3D_0x3D::make(mvar_1), 1));
  }

  Node* _notElem::hfun() { // notElem
    Node** mvar_1 = arg1;
    return new ::_Prelude::_all(Engine::Partial::make(::_Prelude::__0x2F_0x3D::make(mvar_1), 1));
  }

  Node* _lookup::hfun() { // lookup
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_2)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_2, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_2)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_2);
      goto *table_1[(*mvar_2)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::_Nothing();
    __0x3A_1: // ":"
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_2))->arg1;
      Node** mvar_4 = ((::_Prelude::__0x3A*) *(mvar_2))->arg2;
      return new ::_Prelude::_lookup_case__0x231(mvar_3, mvar_1, mvar_4);
    return *(mvar_2);
  }

  Node* _lookup_case__0x231::hfun() { // lookup_case_#1
    Node** mvar_3 = arg1;
    Node** mvar_1 = arg2;
    Node** mvar_4 = arg3;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x28_0x2C_0x29_1};
      goto *table_1[(*mvar_3)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_3, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_3)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_3);
      goto *table_1[(*mvar_3)->get_kind()];
    __0x28_0x2C_0x29_1: // "(,)"
      Node** mvar_5 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_3))->arg1;
      Node** mvar_6 = ((::_Prelude::__0x28_0x2C_0x29*) *(mvar_3))->arg2;
      return new ::_Prelude::_lookup_case__0x231_case__0x231(mvar_1, mvar_5, mvar_6, mvar_4);
    return *(mvar_3);
  }

  Node* _lookup_case__0x231_case__0x231::hfun() { // lookup_case_#1_case_#1
    Node** mvar_1 = arg1;
    Node** mvar_5 = arg2;
    Node** mvar_6 = arg3;
    Node** mvar_4 = arg4;
    return new ::_Prelude::_lookup_case__0x231_case__0x231_case__0x232(::_Prelude::__0x3D_0x3D::make(mvar_1, mvar_5), mvar_1, mvar_5, mvar_6, mvar_4);
  }

  Node* _lookup_case__0x231_case__0x231_case__0x232::hfun() { // lookup_case_#1_case_#1_case_#2
    Node** mvar_7 = arg1;
    Node** mvar_1 = arg2;
    Node** mvar_5 = arg3;
    Node** mvar_6 = arg4;
    Node** mvar_4 = arg5;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_7)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_7, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_7)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_7);
      goto *table_1[(*mvar_7)->get_kind()];
    _False_1: // "False"
      return new ::_Prelude::_lookup_case__0x231_case__0x231_case__0x231(mvar_1, mvar_4);
    _True_1: // "True"
      return new ::_Prelude::_Just(mvar_6);
    return *(mvar_7);
  }

  Node* _lookup_case__0x231_case__0x231_case__0x231::hfun() { // lookup_case_#1_case_#1_case_#1
    Node** mvar_1 = arg1;
    Node** mvar_4 = arg2;
    return new ::_Prelude::_lookup_case__0x231_case__0x231_case__0x231_case__0x231(::_Prelude::_otherwise::make(), mvar_1, mvar_4);
  }

  Node* _lookup_case__0x231_case__0x231_case__0x231_case__0x231::hfun() { // lookup_case_#1_case_#1_case_#1_case_#1
    Node** mvar_5 = arg1;
    Node** mvar_1 = arg2;
    Node** mvar_4 = arg3;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_5)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_5, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_5)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_5);
      goto *table_1[(*mvar_5)->get_kind()];
    _False_1: // "False"
      return new ::_Prelude::_failed();
    _True_1: // "True"
      return new ::_Prelude::_lookup(mvar_1, mvar_4);
    return *(mvar_5);
  }

  Node* _enumFrom::hfun() { // enumFrom
    Node** mvar_1 = arg1;
    return new ::_Prelude::__0x3A(mvar_1, ::_Prelude::_enumFrom::make(::_Prelude::__0x2B::make(mvar_1, _Prelude::Litint::make(1))));
  }

  Node* _enumFromThen::hfun() { // enumFromThen
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::_iterate(Engine::Partial::make(::_Prelude::__0x2B::make(::_Prelude::__0x2D::make(mvar_2, mvar_1)), 1), mvar_1);
  }

  Node* _enumFromTo::hfun() { // enumFromTo
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::_enumFromTo_case__0x231(::_Prelude::__0x3E::make(mvar_1, mvar_2), mvar_1, mvar_2);
  }

  Node* _enumFromTo_case__0x231::hfun() { // enumFromTo_case_#1
    Node** mvar_3 = arg1;
    Node** mvar_1 = arg2;
    Node** mvar_2 = arg3;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_3)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_3, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_3)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_3);
      goto *table_1[(*mvar_3)->get_kind()];
    _False_1: // "False"
      return new ::_Prelude::__0x3A(mvar_1, ::_Prelude::_enumFromTo::make(::_Prelude::__0x2B::make(mvar_1, _Prelude::Litint::make(1)), mvar_2));
    _True_1: // "True"
      return new ::_Prelude::__0x5B_0x5D();
    return *(mvar_3);
  }

  Node* _enumFromThenTo::hfun() { // enumFromThenTo
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    Node** mvar_3 = arg3;
    return new ::_Prelude::_takeWhile(Engine::Partial::make(::_Prelude::_enumFromThenTo_0x2Ep_0x2E321::make(mvar_3, mvar_1, mvar_2), 1), ::_Prelude::_enumFromThen::make(mvar_1, mvar_2));
  }

  Node* _enumFromThenTo_0x2Ep_0x2E321::hfun() { // enumFromThenTo.p.321
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    Node** mvar_3 = arg3;
    Node** mvar_4 = arg4;
    return new ::_Prelude::_enumFromThenTo_0x2Ep_0x2E321_case__0x232(::_Prelude::__0x3E_0x3D::make(mvar_3, mvar_2), mvar_3, mvar_2, mvar_4, mvar_1);
  }

  Node* _enumFromThenTo_0x2Ep_0x2E321_case__0x232::hfun() { // enumFromThenTo.p.321_case_#2
    Node** mvar_5 = arg1;
    Node** mvar_3 = arg2;
    Node** mvar_2 = arg3;
    Node** mvar_4 = arg4;
    Node** mvar_1 = arg5;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_5)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_5, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_5)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_5);
      goto *table_1[(*mvar_5)->get_kind()];
    _False_1: // "False"
      return new ::_Prelude::_enumFromThenTo_0x2Ep_0x2E321_case__0x231(mvar_4, mvar_1);
    _True_1: // "True"
      return new ::_Prelude::__0x3C_0x3D(mvar_4, mvar_1);
    return *(mvar_5);
  }

  Node* _enumFromThenTo_0x2Ep_0x2E321_case__0x231::hfun() { // enumFromThenTo.p.321_case_#1
    Node** mvar_4 = arg1;
    Node** mvar_1 = arg2;
    return new ::_Prelude::_enumFromThenTo_0x2Ep_0x2E321_case__0x231_case__0x231(::_Prelude::_otherwise::make(), mvar_4, mvar_1);
  }

  Node* _enumFromThenTo_0x2Ep_0x2E321_case__0x231_case__0x231::hfun() { // enumFromThenTo.p.321_case_#1_case_#1
    Node** mvar_5 = arg1;
    Node** mvar_4 = arg2;
    Node** mvar_1 = arg3;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_5)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_5, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_5)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_5);
      goto *table_1[(*mvar_5)->get_kind()];
    _False_1: // "False"
      return new ::_Prelude::_failed();
    _True_1: // "True"
      return new ::_Prelude::__0x3E_0x3D(mvar_4, mvar_1);
    return *(mvar_5);
  }

  // external Node* _ord::hfun() { throw "External \"Prelude.ord\" not implemented"; }

  // external Node* _chr::hfun() { throw "External \"Prelude.chr\" not implemented"; }

  // external Node* __0x2B::hfun() { throw "External \"Prelude.+\" not implemented"; }

  // external Node* __0x2D::hfun() { throw "External \"Prelude.-\" not implemented"; }

  // external Node* __0x2A::hfun() { throw "External \"Prelude.*\" not implemented"; }

  // external Node* _div::hfun() { throw "External \"Prelude.div\" not implemented"; }

  // external Node* _mod::hfun() { throw "External \"Prelude.mod\" not implemented"; }

  Node* _divMod::hfun() { // divMod
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::__0x28_0x2C_0x29(::_Prelude::_div::make(mvar_1, mvar_2), ::_Prelude::_mod::make(mvar_1, mvar_2));
  }

  // external Node* _quot::hfun() { throw "External \"Prelude.quot\" not implemented"; }

  // external Node* _rem::hfun() { throw "External \"Prelude.rem\" not implemented"; }

  Node* _quotRem::hfun() { // quotRem
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::__0x28_0x2C_0x29(::_Prelude::_quot::make(mvar_1, mvar_2), ::_Prelude::_rem::make(mvar_1, mvar_2));
  }

  Node* _negate::hfun() { // negate
    Node** mvar_1 = arg1;
    return new ::_Prelude::__0x2D(_Prelude::Litint::make(0), mvar_1);
  }

  Node* _negateFloat::hfun() { // negateFloat
    Node** mvar_1 = arg1;
    return new ::_Prelude::__0x24_0x23(Engine::Partial::make(::_Prelude::_prim_negateFloat::make(), 1), mvar_1);
  }

  // external Node* _prim_negateFloat::hfun() { throw "External \"Prelude.prim_negateFloat\" not implemented"; }

  Node* _success::hfun() { // success
    return new ::_Prelude::_True();
  }

  Node* _maybe::hfun() { // maybe
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    Node** mvar_3 = arg3;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_Nothing_1, &&_Just_1};
      goto *table_1[(*mvar_3)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_3, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_3)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_3);
      goto *table_1[(*mvar_3)->get_kind()];
    _Nothing_1: // "Nothing"
      return *(mvar_1);
    _Just_1: // "Just"
      Node** mvar_4 = ((::_Prelude::_Just*) *(mvar_3))->arg1;
      return new ::_Prelude::_apply(mvar_2, mvar_4);
    return *(mvar_3);
  }

  Node* _either::hfun() { // either
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    Node** mvar_3 = arg3;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_Left_1, &&_Right_1};
      goto *table_1[(*mvar_3)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_3, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_3)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_3);
      goto *table_1[(*mvar_3)->get_kind()];
    _Left_1: // "Left"
      Node** mvar_4 = ((::_Prelude::_Left*) *(mvar_3))->arg1;
      return new ::_Prelude::_apply(mvar_1, mvar_4);
    _Right_1: // "Right"
      Node** mvar_5 = ((::_Prelude::_Right*) *(mvar_3))->arg1;
      return new ::_Prelude::_apply(mvar_2, mvar_5);
    return *(mvar_3);
  }

  // external Node* __0x3E_0x3E_0x3D::hfun() { throw "External \"Prelude.>>=\" not implemented"; }

  // external Node* _return::hfun() { throw "External \"Prelude.return\" not implemented"; }

  Node* __0x3E_0x3E::hfun() { // >>
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::__0x3E_0x3E_0x3D(mvar_1, Engine::Partial::make(::_Prelude::__0x3E_0x3E_0x2E__0x23lambda6::make(mvar_2), 1));
  }

  Node* __0x3E_0x3E_0x2E__0x23lambda6::hfun() { // >>._#lambda6
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return *(mvar_1);
  }

  Node* _done::hfun() { // done
    return new ::_Prelude::_return(::_Prelude::__0x28_0x29::make());
  }

  Node* _putChar::hfun() { // putChar
    Node** mvar_1 = arg1;
    return new ::_Prelude::__0x24_0x23(Engine::Partial::make(::_Prelude::_prim_putChar::make(), 1), mvar_1);
  }

  // external Node* _prim_putChar::hfun() { throw "External \"Prelude.prim_putChar\" not implemented"; }

  // external Node* _getChar::hfun() { throw "External \"Prelude.getChar\" not implemented"; }

  Node* _readFile::hfun() { // readFile
    Node** mvar_1 = arg1;
    return new ::_Prelude::__0x24_0x23_0x23(Engine::Partial::make(::_Prelude::_prim_readFile::make(), 1), mvar_1);
  }

  // external Node* _prim_readFile::hfun() { throw "External \"Prelude.prim_readFile\" not implemented"; }

  // external Node* _prim_readFileContents::hfun() { throw "External \"Prelude.prim_readFileContents\" not implemented"; }

  Node* _writeFile::hfun() { // writeFile
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::_apply(::_Prelude::__0x24_0x23_0x23::make(Engine::Partial::make(::_Prelude::_prim_writeFile::make(), 2), mvar_1), mvar_2);
  }

  // external Node* _prim_writeFile::hfun() { throw "External \"Prelude.prim_writeFile\" not implemented"; }

  Node* _appendFile::hfun() { // appendFile
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::_apply(::_Prelude::__0x24_0x23_0x23::make(Engine::Partial::make(::_Prelude::_prim_appendFile::make(), 2), mvar_1), mvar_2);
  }

  // external Node* _prim_appendFile::hfun() { throw "External \"Prelude.prim_appendFile\" not implemented"; }

  Node* _putStr::hfun() { // putStr
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::_done();
    __0x3A_1: // ":"
      Node** mvar_2 = ((::_Prelude::__0x3A*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_1))->arg2;
      return new ::_Prelude::__0x3E_0x3E(::_Prelude::_putChar::make(mvar_2), ::_Prelude::_putStr::make(mvar_3));
    return *(mvar_1);
  }

  Node* _putStrLn::hfun() { // putStrLn
    Node** mvar_1 = arg1;
    return new ::_Prelude::__0x3E_0x3E(::_Prelude::_putStr::make(mvar_1), ::_Prelude::_putChar::make(_Prelude::Litchar::make('\n')));
  }

  Node* _getLine::hfun() { // getLine
    return new ::_Prelude::__0x3E_0x3E_0x3D(::_Prelude::_getChar::make(), Engine::Partial::make(::_Prelude::_getLine_0x2E__0x23lambda7::make(), 1));
  }

  Node* _getLine_0x2E__0x23lambda7::hfun() { // getLine._#lambda7
    Node** mvar_1 = arg1;
    return new ::_Prelude::_getLine_0x2E__0x23lambda7_case__0x231(::_Prelude::__0x3D_0x3D::make(mvar_1, _Prelude::Litchar::make('\n')), mvar_1);
  }

  Node* _getLine_0x2E__0x23lambda7_case__0x231::hfun() { // getLine._#lambda7_case_#1
    Node** mvar_2 = arg1;
    Node** mvar_1 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_2)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_2, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_2)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_2);
      goto *table_1[(*mvar_2)->get_kind()];
    _False_1: // "False"
      return new ::_Prelude::__0x3E_0x3E_0x3D(::_Prelude::_getLine::make(), Engine::Partial::make(::_Prelude::_getLine_0x2E__0x23lambda7_0x2E__0x23lambda8::make(mvar_1), 1));
    _True_1: // "True"
      return new ::_Prelude::_return(::_Prelude::__0x5B_0x5D::make());
    return *(mvar_2);
  }

  Node* _getLine_0x2E__0x23lambda7_0x2E__0x23lambda8::hfun() { // getLine._#lambda7._#lambda8
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::_return(::_Prelude::__0x3A::make(mvar_1, mvar_2));
  }

  Node* _userError::hfun() { // userError
    Node** mvar_1 = arg1;
    return new ::_Prelude::_UserError(mvar_1);
  }

  Node* _ioError::hfun() { // ioError
    Node** mvar_1 = arg1;
    return new ::_Prelude::_error(::_Prelude::_showError::make(mvar_1));
  }

  Node* _showError::hfun() { // showError
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_IOError_1, &&_UserError_1, &&_FailError_1, &&_NondetError_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    _IOError_1: // "IOError"
      Node** mvar_2 = ((::_Prelude::_IOError*) *(mvar_1))->arg1;
      return new ::_Prelude::__0x2B_0x2B(::_Prelude::__0x3A::make(_Prelude::Litchar::make('i'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('/'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('o'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make(' '), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('e'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('r'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('r'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('o'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('r'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make(':'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make(' '), ::_Prelude::__0x5B_0x5D::make()))))))))))), mvar_2);
    _UserError_1: // "UserError"
      Node** mvar_3 = ((::_Prelude::_UserError*) *(mvar_1))->arg1;
      return new ::_Prelude::__0x2B_0x2B(::_Prelude::__0x3A::make(_Prelude::Litchar::make('u'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('s'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('e'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('r'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make(' '), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('e'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('r'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('r'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('o'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('r'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make(':'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make(' '), ::_Prelude::__0x5B_0x5D::make())))))))))))), mvar_3);
    _FailError_1: // "FailError"
      Node** mvar_4 = ((::_Prelude::_FailError*) *(mvar_1))->arg1;
      return new ::_Prelude::__0x2B_0x2B(::_Prelude::__0x3A::make(_Prelude::Litchar::make('f'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('a'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('i'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('l'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make(' '), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('e'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('r'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('r'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('o'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('r'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make(':'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make(' '), ::_Prelude::__0x5B_0x5D::make())))))))))))), mvar_4);
    _NondetError_1: // "NondetError"
      Node** mvar_5 = ((::_Prelude::_NondetError*) *(mvar_1))->arg1;
      return new ::_Prelude::__0x2B_0x2B(::_Prelude::__0x3A::make(_Prelude::Litchar::make('n'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('o'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('n'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('d'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('e'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('t'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make(' '), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('e'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('r'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('r'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('o'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make('r'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make(':'), ::_Prelude::__0x3A::make(_Prelude::Litchar::make(' '), ::_Prelude::__0x5B_0x5D::make())))))))))))))), mvar_5);
    return *(mvar_1);
  }

  // external Node* _catch::hfun() { throw "External \"Prelude.catch\" not implemented"; }

  Node* _show::hfun() { // show
    Node** mvar_1 = arg1;
    return new ::_Prelude::__0x24_0x23_0x23(Engine::Partial::make(::_Prelude::_prim_show::make(), 1), mvar_1);
  }

  // external Node* _prim_show::hfun() { throw "External \"Prelude.prim_show\" not implemented"; }

  Node* _print::hfun() { // print
    Node** mvar_1 = arg1;
    return new ::_Prelude::_putStrLn(::_Prelude::_show::make(mvar_1));
  }

  Node* _doSolve::hfun() { // doSolve
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    _False_1: // "False"
      return new ::_Prelude::_failed();
    _True_1: // "True"
      return new ::_Prelude::_done();
    return *(mvar_1);
  }

  Node* _sequenceIO::hfun() { // sequenceIO
    Node** mvar_1 = arg1;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::_return(::_Prelude::__0x5B_0x5D::make());
    __0x3A_1: // ":"
      Node** mvar_2 = ((::_Prelude::__0x3A*) *(mvar_1))->arg1;
      Node** mvar_3 = ((::_Prelude::__0x3A*) *(mvar_1))->arg2;
      return new ::_Prelude::__0x3E_0x3E_0x3D(mvar_2, Engine::Partial::make(::_Prelude::_sequenceIO_0x2E__0x23lambda9::make(mvar_3), 1));
    return *(mvar_1);
  }

  Node* _sequenceIO_0x2E__0x23lambda9::hfun() { // sequenceIO._#lambda9
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::__0x3E_0x3E_0x3D(::_Prelude::_sequenceIO::make(mvar_1), Engine::Partial::make(::_Prelude::_sequenceIO_0x2E__0x23lambda9_0x2E__0x23lambda10::make(mvar_2), 1));
  }

  Node* _sequenceIO_0x2E__0x23lambda9_0x2E__0x23lambda10::hfun() { // sequenceIO._#lambda9._#lambda10
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::_return(::_Prelude::__0x3A::make(mvar_1, mvar_2));
  }

  Node* _sequenceIO_::hfun() { // sequenceIO_
    return new Engine::Partial(::_Prelude::_foldr::make(Engine::Partial::make(::_Prelude::__0x3E_0x3E::make(), 2), ::_Prelude::_done::make()), 1);
  }

  Node* _mapIO::hfun() { // mapIO
    Node** mvar_1 = arg1;
    return new ::_Prelude::__0x2E(Engine::Partial::make(::_Prelude::_sequenceIO::make(), 1), Engine::Partial::make(::_Prelude::_map::make(mvar_1), 1));
  }

  Node* _mapIO_::hfun() { // mapIO_
    Node** mvar_1 = arg1;
    return new ::_Prelude::__0x2E(::_Prelude::_sequenceIO_::make(), Engine::Partial::make(::_Prelude::_map::make(mvar_1), 1));
  }

  Node* _foldIO::hfun() { // foldIO
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    Node** mvar_3 = arg3;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&__0x5B_0x5D_1, &&__0x3A_1};
      goto *table_1[(*mvar_3)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_3, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_3)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_3);
      goto *table_1[(*mvar_3)->get_kind()];
    __0x5B_0x5D_1: // "[]"
      return new ::_Prelude::_return(mvar_2);
    __0x3A_1: // ":"
      Node** mvar_4 = ((::_Prelude::__0x3A*) *(mvar_3))->arg1;
      Node** mvar_5 = ((::_Prelude::__0x3A*) *(mvar_3))->arg2;
      return new ::_Prelude::__0x3E_0x3E_0x3D(::_Prelude::_apply::make(::_Prelude::_apply::make(mvar_1, mvar_2), mvar_4), Engine::Partial::make(::_Prelude::_foldIO_0x2E__0x23lambda11::make(mvar_1, mvar_5), 1));
    return *(mvar_3);
  }

  Node* _foldIO_0x2E__0x23lambda11::hfun() { // foldIO._#lambda11
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    Node** mvar_3 = arg3;
    return new ::_Prelude::_foldIO(mvar_1, mvar_3, mvar_2);
  }

  Node* _liftIO::hfun() { // liftIO
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::__0x3E_0x3E_0x3D(mvar_2, ::_Prelude::__0x2E::make(Engine::Partial::make(::_Prelude::_return::make(), 1), mvar_1));
  }

  Node* _forIO::hfun() { // forIO
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::_apply(::_Prelude::_mapIO::make(mvar_2), mvar_1);
  }

  Node* _forIO_::hfun() { // forIO_
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    return new ::_Prelude::_apply(::_Prelude::_mapIO_::make(mvar_2), mvar_1);
  }

  Node* _unless::hfun() { // unless
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    _False_1: // "False"
      return *(mvar_2);
    _True_1: // "True"
      return new ::_Prelude::_done();
    return *(mvar_1);
  }

  Node* _when::hfun() { // when
    Node** mvar_1 = arg1;
    Node** mvar_2 = arg2;
    static void* table_1[]
      = {&&fail_1, &&var_1, &&choice_1, &&oper_1, &&_False_1, &&_True_1};
      goto *table_1[(*mvar_1)->get_kind()];
    fail_1:
      return DO_FAIL;
    var_1:
      // Engine::narrow(mvar_1, generator());
      throw "No narrowing yet";
      goto *table_1[(*mvar_1)->get_kind()];
    choice_1:
    oper_1:
      Engine::hfun(mvar_1);
      goto *table_1[(*mvar_1)->get_kind()];
    _False_1: // "False"
      return new ::_Prelude::_done();
    _True_1: // "True"
      return *(mvar_2);
    return *(mvar_1);
  }

  // external Node* __0x3F::hfun() { throw "External \"Prelude.?\" not implemented"; }

  Node* _anyOf::hfun() { // anyOf
    return new Engine::Partial(::_Prelude::_foldr1::make(Engine::Partial::make(::_Prelude::__0x3F::make(), 2)), 1);
  }

  Node* _unknown::hfun() { // unknown
    Node** mvar_1 = ::Engine::Variable::make();
    return *(mvar_1);
  }

  Node* _PEVAL::hfun() { // PEVAL
    Node** mvar_1 = arg1;
    return *(mvar_1);
  }

  Node* _normalForm::hfun() { // normalForm
    Node** mvar_1 = arg1;
    return new ::_Prelude::__0x24_0x21_0x21(Engine::Partial::make(::_Prelude::_id::make(), 1), mvar_1);
  }

  Node* _groundNormalForm::hfun() { // groundNormalForm
    Node** mvar_1 = arg1;
    return new ::_Prelude::__0x24_0x23_0x23(Engine::Partial::make(::_Prelude::_id::make(), 1), mvar_1);
  }

  // external Node* _apply::hfun() { throw "External \"Prelude.apply\" not implemented"; }

  // external Node* _cond::hfun() { throw "External \"Prelude.cond\" not implemented"; }

  // external Node* _letrec::hfun() { throw "External \"Prelude.letrec\" not implemented"; }

  // external Node* __0x3D_0x3A_0x3C_0x3D::hfun() { throw "External \"Prelude.=:<=\" not implemented"; }

  // external Node* __0x3D_0x3A_0x3C_0x3C_0x3D::hfun() { throw "External \"Prelude.=:<<=\" not implemented"; }

  // external Node* _ifVar::hfun() { throw "External \"Prelude.ifVar\" not implemented"; }

  // external Node* _failure::hfun() { throw "External \"Prelude.failure\" not implemented"; }

  Node* __0x28_0x29::boolequal(Node** right) { // () 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x29};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  __0x28_0x29:
    return new ::_Prelude::_True();
  }

  Node* __0x28_0x29::compare(Node** right) { // () 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x29};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  __0x28_0x29:
    return new ::_Prelude::_EQ();
  }

  Node* __0x5B_0x5D::boolequal(Node** right) { // [] 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x5B_0x5D, &&__0x3A};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  __0x5B_0x5D:
    return new ::_Prelude::_True();
  __0x3A:
    return new ::_Prelude::_False();
  }

  Node* __0x5B_0x5D::compare(Node** right) { // [] 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x5B_0x5D, &&__0x3A};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  __0x5B_0x5D:
    return new ::_Prelude::_EQ();
  __0x3A:
    return new ::_Prelude::_LT();
  }

  Node* __0x3A::boolequal(Node** right) { // : 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x5B_0x5D, &&__0x3A};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  __0x5B_0x5D:
    return new ::_Prelude::_False();
  __0x3A:
    return new ::_Prelude::__0x26_0x26(::_Prelude::__0x3D_0x3D::make(arg1,((::_Prelude::__0x3A*) (*right))->arg1), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg2,((::_Prelude::__0x3A*) (*right))->arg2), ::_Prelude::_True::make()));
  }

  Node* __0x3A::compare(Node** right) { // : 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x5B_0x5D, &&__0x3A};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  __0x5B_0x5D:
    return new ::_Prelude::_GT();
  __0x3A:
    return new ::_Prelude::_descend_compare(::_Prelude::_compare::make(arg1,((::_Prelude::__0x3A*) (*right))->arg1),::_Prelude::_compare::make(arg2,((::_Prelude::__0x3A*) (*right))->arg2));
  }

  Node* __0x28_0x2C_0x29::boolequal(Node** right) { // (,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x29};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  __0x28_0x2C_0x29:
    return new ::_Prelude::__0x26_0x26(::_Prelude::__0x3D_0x3D::make(arg1,((::_Prelude::__0x28_0x2C_0x29*) (*right))->arg1), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg2,((::_Prelude::__0x28_0x2C_0x29*) (*right))->arg2), ::_Prelude::_True::make()));
  }

  Node* __0x28_0x2C_0x29::compare(Node** right) { // (,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x29};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  __0x28_0x2C_0x29:
    return new ::_Prelude::_descend_compare(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x29*) (*right))->arg1),::_Prelude::_compare::make(arg2,((::_Prelude::__0x28_0x2C_0x29*) (*right))->arg2));
  }

  Node* __0x28_0x2C_0x2C_0x29::boolequal(Node** right) { // (,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x29};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  __0x28_0x2C_0x2C_0x29:
    return new ::_Prelude::__0x26_0x26(::_Prelude::__0x3D_0x3D::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x29*) (*right))->arg1), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg2,((::_Prelude::__0x28_0x2C_0x2C_0x29*) (*right))->arg2), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg3,((::_Prelude::__0x28_0x2C_0x2C_0x29*) (*right))->arg3), ::_Prelude::_True::make())));
  }

  Node* __0x28_0x2C_0x2C_0x29::compare(Node** right) { // (,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x29};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  __0x28_0x2C_0x2C_0x29:
    return new ::_Prelude::_descend_compare(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_compare::make(arg3,((::_Prelude::__0x28_0x2C_0x2C_0x29*) (*right))->arg3)));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x29::boolequal(Node** right) { // (,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x29};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  __0x28_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::__0x26_0x26(::_Prelude::__0x3D_0x3D::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x29*) (*right))->arg1), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg2,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x29*) (*right))->arg2), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg3,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x29*) (*right))->arg3), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg4,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x29*) (*right))->arg4), ::_Prelude::_True::make()))));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x29::compare(Node** right) { // (,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x29};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  __0x28_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::_descend_compare(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_compare::make(arg4,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x29*) (*right))->arg4))));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x2C_0x29::boolequal(Node** right) { // (,,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x2C_0x29};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  __0x28_0x2C_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::__0x26_0x26(::_Prelude::__0x3D_0x3D::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg2,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg2), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg3,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg3), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg4,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg4), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg5,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg5), ::_Prelude::_True::make())))));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x2C_0x29::compare(Node** right) { // (,,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x2C_0x29};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  __0x28_0x2C_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::_descend_compare(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_compare::make(arg5,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg5)))));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x29::boolequal(Node** right) { // (,,,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x29};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::__0x26_0x26(::_Prelude::__0x3D_0x3D::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg2,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg2), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg3,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg3), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg4,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg4), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg5,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg5), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg6,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg6), ::_Prelude::_True::make()))))));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x29::compare(Node** right) { // (,,,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x29};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::_descend_compare(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_compare::make(arg6,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg6))))));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29::boolequal(Node** right) { // (,,,,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::__0x26_0x26(::_Prelude::__0x3D_0x3D::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg2,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg2), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg3,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg3), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg4,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg4), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg5,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg5), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg6,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg6), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg7,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg7), ::_Prelude::_True::make())))))));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29::compare(Node** right) { // (,,,,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::_descend_compare(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_compare::make(arg7,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg7)))))));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29::boolequal(Node** right) { // (,,,,,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::__0x26_0x26(::_Prelude::__0x3D_0x3D::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg2,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg2), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg3,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg3), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg4,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg4), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg5,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg5), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg6,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg6), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg7,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg7), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg8,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg8), ::_Prelude::_True::make()))))))));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29::compare(Node** right) { // (,,,,,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::_descend_compare(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_compare::make(arg8,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg8))))))));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29::boolequal(Node** right) { // (,,,,,,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::__0x26_0x26(::_Prelude::__0x3D_0x3D::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg2,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg2), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg3,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg3), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg4,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg4), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg5,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg5), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg6,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg6), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg7,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg7), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg8,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg8), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg9,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg9), ::_Prelude::_True::make())))))))));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29::compare(Node** right) { // (,,,,,,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::_descend_compare(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_compare::make(arg9,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg9)))))))));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29::boolequal(Node** right) { // (,,,,,,,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::__0x26_0x26(::_Prelude::__0x3D_0x3D::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg2,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg2), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg3,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg3), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg4,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg4), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg5,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg5), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg6,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg6), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg7,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg7), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg8,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg8), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg9,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg9), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg10,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg10), ::_Prelude::_True::make()))))))))));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29::compare(Node** right) { // (,,,,,,,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::_descend_compare(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_compare::make(arg10,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg10))))))))));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29::boolequal(Node** right) { // (,,,,,,,,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::__0x26_0x26(::_Prelude::__0x3D_0x3D::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg2,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg2), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg3,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg3), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg4,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg4), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg5,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg5), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg6,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg6), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg7,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg7), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg8,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg8), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg9,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg9), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg10,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg10), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg11,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg11), ::_Prelude::_True::make())))))))))));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29::compare(Node** right) { // (,,,,,,,,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::_descend_compare(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_compare::make(arg11,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg11)))))))))));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29::boolequal(Node** right) { // (,,,,,,,,,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::__0x26_0x26(::_Prelude::__0x3D_0x3D::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg2,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg2), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg3,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg3), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg4,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg4), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg5,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg5), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg6,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg6), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg7,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg7), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg8,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg8), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg9,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg9), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg10,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg10), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg11,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg11), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg12,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg12), ::_Prelude::_True::make()))))))))))));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29::compare(Node** right) { // (,,,,,,,,,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::_descend_compare(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_compare::make(arg12,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg12))))))))))));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29::boolequal(Node** right) { // (,,,,,,,,,,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::__0x26_0x26(::_Prelude::__0x3D_0x3D::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg2,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg2), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg3,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg3), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg4,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg4), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg5,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg5), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg6,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg6), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg7,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg7), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg8,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg8), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg9,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg9), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg10,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg10), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg11,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg11), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg12,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg12), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg13,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg13), ::_Prelude::_True::make())))))))))))));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29::compare(Node** right) { // (,,,,,,,,,,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::_descend_compare(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_compare::make(arg13,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg13)))))))))))));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29::boolequal(Node** right) { // (,,,,,,,,,,,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::__0x26_0x26(::_Prelude::__0x3D_0x3D::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg2,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg2), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg3,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg3), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg4,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg4), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg5,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg5), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg6,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg6), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg7,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg7), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg8,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg8), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg9,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg9), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg10,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg10), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg11,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg11), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg12,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg12), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg13,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg13), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg14,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg14), ::_Prelude::_True::make()))))))))))))));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29::compare(Node** right) { // (,,,,,,,,,,,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::_descend_compare(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_compare::make(arg14,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg14))))))))))))));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29::boolequal(Node** right) { // (,,,,,,,,,,,,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::__0x26_0x26(::_Prelude::__0x3D_0x3D::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg2,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg2), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg3,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg3), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg4,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg4), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg5,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg5), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg6,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg6), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg7,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg7), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg8,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg8), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg9,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg9), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg10,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg10), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg11,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg11), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg12,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg12), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg13,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg13), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg14,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg14), ::_Prelude::__0x26_0x26::make(::_Prelude::__0x3D_0x3D::make(arg15,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg15), ::_Prelude::_True::make())))))))))))))));
  }

  Node* __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29::compare(Node** right) { // (,,,,,,,,,,,,,,) 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  __0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29:
    return new ::_Prelude::_descend_compare(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_descend_compare::make(::_Prelude::_compare::make(arg1,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg1),::_Prelude::_compare::make(arg15,((::_Prelude::__0x28_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x2C_0x29*) (*right))->arg15)))))))))))))));
  }

  Node* _False::boolequal(Node** right) { // False 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_False, &&_True};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  _False:
    return new ::_Prelude::_True();
  _True:
    return new ::_Prelude::_False();
  }

  Node* _False::compare(Node** right) { // False 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_False, &&_True};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  _False:
    return new ::_Prelude::_EQ();
  _True:
    return new ::_Prelude::_LT();
  }

  Node* _True::boolequal(Node** right) { // True 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_False, &&_True};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  _False:
    return new ::_Prelude::_False();
  _True:
    return new ::_Prelude::_True();
  }

  Node* _True::compare(Node** right) { // True 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_False, &&_True};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  _False:
    return new ::_Prelude::_GT();
  _True:
    return new ::_Prelude::_EQ();
  }

  Node* _LT::boolequal(Node** right) { // LT 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_LT, &&_EQ, &&_GT};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  _LT:
    return new ::_Prelude::_True();
  _EQ:
    return new ::_Prelude::_False();
  _GT:
    return new ::_Prelude::_False();
  }

  Node* _LT::compare(Node** right) { // LT 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_LT, &&_EQ, &&_GT};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  _LT:
    return new ::_Prelude::_EQ();
  _EQ:
    return new ::_Prelude::_LT();
  _GT:
    return new ::_Prelude::_LT();
  }

  Node* _EQ::boolequal(Node** right) { // EQ 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_LT, &&_EQ, &&_GT};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  _LT:
    return new ::_Prelude::_False();
  _EQ:
    return new ::_Prelude::_True();
  _GT:
    return new ::_Prelude::_False();
  }

  Node* _EQ::compare(Node** right) { // EQ 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_LT, &&_EQ, &&_GT};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  _LT:
    return new ::_Prelude::_GT();
  _EQ:
    return new ::_Prelude::_EQ();
  _GT:
    return new ::_Prelude::_LT();
  }

  Node* _GT::boolequal(Node** right) { // GT 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_LT, &&_EQ, &&_GT};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  _LT:
    return new ::_Prelude::_False();
  _EQ:
    return new ::_Prelude::_False();
  _GT:
    return new ::_Prelude::_True();
  }

  Node* _GT::compare(Node** right) { // GT 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_LT, &&_EQ, &&_GT};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  _LT:
    return new ::_Prelude::_GT();
  _EQ:
    return new ::_Prelude::_GT();
  _GT:
    return new ::_Prelude::_EQ();
  }

  Node* _Nothing::boolequal(Node** right) { // Nothing 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_Nothing, &&_Just};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  _Nothing:
    return new ::_Prelude::_True();
  _Just:
    return new ::_Prelude::_False();
  }

  Node* _Nothing::compare(Node** right) { // Nothing 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_Nothing, &&_Just};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  _Nothing:
    return new ::_Prelude::_EQ();
  _Just:
    return new ::_Prelude::_LT();
  }

  Node* _Just::boolequal(Node** right) { // Just 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_Nothing, &&_Just};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  _Nothing:
    return new ::_Prelude::_False();
  _Just:
    return new ::_Prelude::__0x26_0x26(::_Prelude::__0x3D_0x3D::make(arg1,((::_Prelude::_Just*) (*right))->arg1), ::_Prelude::_True::make());
  }

  Node* _Just::compare(Node** right) { // Just 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_Nothing, &&_Just};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  _Nothing:
    return new ::_Prelude::_GT();
  _Just:
    return new ::_Prelude::_compare(arg1,((::_Prelude::_Just*) (*right))->arg1);
  }

  Node* _Left::boolequal(Node** right) { // Left 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_Left, &&_Right};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  _Left:
    return new ::_Prelude::__0x26_0x26(::_Prelude::__0x3D_0x3D::make(arg1,((::_Prelude::_Left*) (*right))->arg1), ::_Prelude::_True::make());
  _Right:
    return new ::_Prelude::_False();
  }

  Node* _Left::compare(Node** right) { // Left 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_Left, &&_Right};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  _Left:
    return new ::_Prelude::_compare(arg1,((::_Prelude::_Left*) (*right))->arg1);
  _Right:
    return new ::_Prelude::_LT();
  }

  Node* _Right::boolequal(Node** right) { // Right 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_Left, &&_Right};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  _Left:
    return new ::_Prelude::_False();
  _Right:
    return new ::_Prelude::__0x26_0x26(::_Prelude::__0x3D_0x3D::make(arg1,((::_Prelude::_Right*) (*right))->arg1), ::_Prelude::_True::make());
  }

  Node* _Right::compare(Node** right) { // Right 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_Left, &&_Right};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  _Left:
    return new ::_Prelude::_GT();
  _Right:
    return new ::_Prelude::_compare(arg1,((::_Prelude::_Right*) (*right))->arg1);
  }

  Node* _IOError::boolequal(Node** right) { // IOError 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_IOError, &&_UserError, &&_FailError, &&_NondetError};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  _IOError:
    return new ::_Prelude::__0x26_0x26(::_Prelude::__0x3D_0x3D::make(arg1,((::_Prelude::_IOError*) (*right))->arg1), ::_Prelude::_True::make());
  _UserError:
    return new ::_Prelude::_False();
  _FailError:
    return new ::_Prelude::_False();
  _NondetError:
    return new ::_Prelude::_False();
  }

  Node* _IOError::compare(Node** right) { // IOError 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_IOError, &&_UserError, &&_FailError, &&_NondetError};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  _IOError:
    return new ::_Prelude::_compare(arg1,((::_Prelude::_IOError*) (*right))->arg1);
  _UserError:
    return new ::_Prelude::_LT();
  _FailError:
    return new ::_Prelude::_LT();
  _NondetError:
    return new ::_Prelude::_LT();
  }

  Node* _UserError::boolequal(Node** right) { // UserError 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_IOError, &&_UserError, &&_FailError, &&_NondetError};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  _IOError:
    return new ::_Prelude::_False();
  _UserError:
    return new ::_Prelude::__0x26_0x26(::_Prelude::__0x3D_0x3D::make(arg1,((::_Prelude::_UserError*) (*right))->arg1), ::_Prelude::_True::make());
  _FailError:
    return new ::_Prelude::_False();
  _NondetError:
    return new ::_Prelude::_False();
  }

  Node* _UserError::compare(Node** right) { // UserError 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_IOError, &&_UserError, &&_FailError, &&_NondetError};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  _IOError:
    return new ::_Prelude::_GT();
  _UserError:
    return new ::_Prelude::_compare(arg1,((::_Prelude::_UserError*) (*right))->arg1);
  _FailError:
    return new ::_Prelude::_LT();
  _NondetError:
    return new ::_Prelude::_LT();
  }

  Node* _FailError::boolequal(Node** right) { // FailError 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_IOError, &&_UserError, &&_FailError, &&_NondetError};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  _IOError:
    return new ::_Prelude::_False();
  _UserError:
    return new ::_Prelude::_False();
  _FailError:
    return new ::_Prelude::__0x26_0x26(::_Prelude::__0x3D_0x3D::make(arg1,((::_Prelude::_FailError*) (*right))->arg1), ::_Prelude::_True::make());
  _NondetError:
    return new ::_Prelude::_False();
  }

  Node* _FailError::compare(Node** right) { // FailError 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_IOError, &&_UserError, &&_FailError, &&_NondetError};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  _IOError:
    return new ::_Prelude::_GT();
  _UserError:
    return new ::_Prelude::_GT();
  _FailError:
    return new ::_Prelude::_compare(arg1,((::_Prelude::_FailError*) (*right))->arg1);
  _NondetError:
    return new ::_Prelude::_LT();
  }

  Node* _NondetError::boolequal(Node** right) { // NondetError 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_IOError, &&_UserError, &&_FailError, &&_NondetError};
  start:
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto start;
  _IOError:
    return new ::_Prelude::_False();
  _UserError:
    return new ::_Prelude::_False();
  _FailError:
    return new ::_Prelude::_False();
  _NondetError:
    return new ::_Prelude::__0x26_0x26(::_Prelude::__0x3D_0x3D::make(arg1,((::_Prelude::_NondetError*) (*right))->arg1), ::_Prelude::_True::make());
  }

  Node* _NondetError::compare(Node** right) { // NondetError 
    static void* table[] = {&&fail, &&var, &&choice, &&oper, &&_IOError, &&_UserError, &&_FailError, &&_NondetError};
    goto *table[(*right)->get_kind()];
  fail:
    return DO_FAIL;
  var:
    throw "Program flounders";
  choice:
  oper:
    Engine::hfun(right);
    goto *table[(*right)->get_kind()];
  _IOError:
    return new ::_Prelude::_GT();
  _UserError:
    return new ::_Prelude::_GT();
  _FailError:
    return new ::_Prelude::_GT();
  _NondetError:
    return new ::_Prelude::_compare(arg1,((::_Prelude::_NondetError*) (*right))->arg1);
  }
}
