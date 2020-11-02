%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0_050).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0_050.main',main,0,'a0_050.main',nofix,'TCons'('a0_050.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0_050.A','A',0,'A',0,'TCons'('a0_050.T',[]),[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0_050.main'(_G482825,_G482826,_G482827):-freeze(_G482826,'blocked_a0_050.main'(_G482825,_G482826,_G482827)).
'blocked_a0_050.main'(_G483255,_G483258,_G483261):-makeShare(_G482870,_G483317),makeShare(_G482861,_G483327),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('a0_050.A',_G483317),'Prelude.=:='(_G483317,_G483327)),_G483327),_G483317),_G483255,_G483258,_G483261).

:-costCenters(['']).




%%%%% Number of shared variables: 2
