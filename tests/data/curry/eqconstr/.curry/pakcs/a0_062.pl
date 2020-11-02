%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0_062).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0_062.main',main,0,'a0_062.main',nofix,'TCons'('a0_062.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0_062.A','A',0,'A',0,'TCons'('a0_062.T',[]),[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0_062.main'(_G484030,_G484031,_G484032):-freeze(_G484031,'blocked_a0_062.main'(_G484030,_G484031,_G484032)).
'blocked_a0_062.main'(_G484533,_G484536,_G484539):-makeShare(_G484075,_G484607),makeShare(_G484066,_G484617),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('a0_062.A',_G484607),'Prelude.=:='(_G484617,_G484607)),_G484617),'Prelude.?'(_G484617,_G484607)),_G484533,_G484536,_G484539).

:-costCenters(['']).




%%%%% Number of shared variables: 2
