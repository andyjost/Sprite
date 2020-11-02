%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0b0c0_008).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0b0c0_008.main',main,0,'a0b0c0_008.main',nofix,'TCons'('a0b0c0_008.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0b0c0_008.A','A',0,'A',0,'TCons'('a0b0c0_008.T',[]),['a0b0c0_008.B'/0,'a0b0c0_008.C'/0]).
constructortype('a0b0c0_008.B','B',0,'B',1,'TCons'('a0b0c0_008.T',[]),['a0b0c0_008.A'/0,'a0b0c0_008.C'/0]).
constructortype('a0b0c0_008.C','C',0,'C',2,'TCons'('a0b0c0_008.T',[]),['a0b0c0_008.A'/0,'a0b0c0_008.B'/0]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0b0c0_008.main'(_G487900,_G487901,_G487902):-freeze(_G487901,'blocked_a0b0c0_008.main'(_G487900,_G487901,_G487902)).
'blocked_a0b0c0_008.main'(_G488172,_G488175,_G488178):-makeShare(_G487936,_G488210),hnf('Prelude.?'('Prelude.&>'('Prelude.=:='(_G488210,'a0b0c0_008.C'),_G488210),_G488210),_G488172,_G488175,_G488178).

:-costCenters(['']).




%%%%% Number of shared variables: 1
