%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0_034).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0_034.main',main,0,'a0_034.main',nofix,'TCons'('a0_034.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0_034.A','A',0,'A',0,'TCons'('a0_034.T',[]),[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0_034.main'(_G482825,_G482826,_G482827):-freeze(_G482826,'blocked_a0_034.main'(_G482825,_G482826,_G482827)).
'blocked_a0_034.main'(_G483255,_G483258,_G483261):-makeShare(_G482870,_G483323),makeShare(_G482861,_G483333),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('a0_034.A',_G483323),'Prelude.=:='(_G483323,_G483333)),_G483333),_G483333),_G483255,_G483258,_G483261).

:-costCenters(['']).




%%%%% Number of shared variables: 2
