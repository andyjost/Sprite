%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog79).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog79.main',main,0,'prog79.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog79.main'(_G483115,_G483116,_G483117):-freeze(_G483116,'blocked_prog79.main'(_G483115,_G483116,_G483117)).
'blocked_prog79.main'(_G483625,_G483628,_G483631):-makeShare(_G483151,_G483687),makeShare(_G483160,_G483697),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='(_G483687,_G483697),'Prelude.&'('Prelude.=:='(_G483687,'Prelude.True'),'Prelude.=:='('Prelude.False',_G483697))),_G483687),_G483625,_G483628,_G483631).

:-costCenters(['']).




%%%%% Number of shared variables: 2
