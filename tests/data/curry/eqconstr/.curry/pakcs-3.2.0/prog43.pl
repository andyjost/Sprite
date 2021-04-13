%PAKCS3.2 swi8 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog43).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog43.main',main,0,'prog43.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog43.main'(_3587940,_3587942,_3587944):-freeze(_3587942,'blocked_prog43.main'(_3587940,_3587942,_3587944)).
'blocked_prog43.main'(_3588470,_3588476,_3588482):-makeShare(_3588012,_3588558),hnf('Prelude.?'('Prelude.&>'('Prelude.=:='(_3588558,_3588558),_3588558),_3588558),_3588470,_3588476,_3588482).

:-costCenters(['']).




%%%%% Number of shared variables: 1

