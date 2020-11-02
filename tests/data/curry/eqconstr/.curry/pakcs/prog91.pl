%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog91).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog91.main',main,0,'prog91.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog91.main'(_G483127,_G483128,_G483129):-freeze(_G483128,'blocked_prog91.main'(_G483127,_G483128,_G483129)).
'blocked_prog91.main'(_G483637,_G483640,_G483643):-makeShare(_G483172,_G483705),makeShare(_G483163,_G483715),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='('Prelude.False',_G483705),'Prelude.&'('Prelude.=:='(_G483705,_G483715),'Prelude.=:='(_G483715,'Prelude.True'))),_G483715),_G483637,_G483640,_G483643).

:-costCenters(['']).




%%%%% Number of shared variables: 2
