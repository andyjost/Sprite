%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0b0c0_001).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0b0c0_001.main',main,0,'a0b0c0_001.main',nofix,'TCons'('a0b0c0_001.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0b0c0_001.A','A',0,'A',0,'TCons'('a0b0c0_001.T',[]),['a0b0c0_001.B'/0,'a0b0c0_001.C'/0]).
constructortype('a0b0c0_001.B','B',0,'B',1,'TCons'('a0b0c0_001.T',[]),['a0b0c0_001.A'/0,'a0b0c0_001.C'/0]).
constructortype('a0b0c0_001.C','C',0,'C',2,'TCons'('a0b0c0_001.T',[]),['a0b0c0_001.A'/0,'a0b0c0_001.B'/0]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0b0c0_001.main'(_G486677,_G486678,_G486679):-freeze(_G486678,'blocked_a0b0c0_001.main'(_G486677,_G486678,_G486679)).
'blocked_a0b0c0_001.main'(_G486876,_G486879,_G486882):-makeShare(_G486713,_G486908),hnf('Prelude.&>'('Prelude.=:='(_G486908,'a0b0c0_001.B'),_G486908),_G486876,_G486879,_G486882).

:-costCenters(['']).




%%%%% Number of shared variables: 1