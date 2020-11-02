%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog16).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog16.main',main,0,'prog16.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog16.main'(_G477523,_G477524,_G477525):-freeze(_G477524,'blocked_prog16.main'(_G477523,_G477524,_G477525)).
'blocked_prog16.main'(_G477649,_G477652,_G477655):-hnf('Prelude._impl\'23\'3D\'3D\'23Prelude.Eq\'23Prelude.Bool'('Prelude.True',_G477559),_G477649,_G477652,_G477655).

:-costCenters(['']).




%%%%% Number of shared variables: 0
