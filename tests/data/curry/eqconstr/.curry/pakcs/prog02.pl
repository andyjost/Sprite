%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog02).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog02.main',main,0,'prog02.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog02.main'(_G481339,_G481340,_G481341):-freeze(_G481340,'blocked_prog02.main'(_G481339,_G481340,_G481341)).
'blocked_prog02.main'(_G481749,_G481752,_G481755):-hnf('Prelude.=:='([0,0],[0,0]),_G481749,_G481752,_G481755).

:-costCenters(['']).




%%%%% Number of shared variables: 0