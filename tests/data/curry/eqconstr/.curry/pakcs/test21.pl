%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test21).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test21.main',main,0,'test21.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test21.main'(_G477198,_G477199,_G477200):-freeze(_G477199,'blocked_test21.main'(_G477198,_G477199,_G477200)).
'blocked_test21.main'(_G477499,_G477502,_G477505):-hnf('Prelude.=:='([_G477234|_G477252],[_G477243|_G477261]),_G477499,_G477502,_G477505).

:-costCenters(['']).




%%%%% Number of shared variables: 0