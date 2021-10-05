" Vim syntax file
" Language: Sprite Curry Compiler trace and log output
"

if exists("b:current_syntax")
  finish
endif
let b:current_syntax = "spritelog"

" Patterns are matched in order.  These have the lowest priority and are capped
" by cyUnknown. The are used with nextgroup for context-specific highlighting.
syn match cyTraceQueueBody '\S.*$'
syn match cyTraceYieldBody '\S.*$'
syn match cyTraceInfoBody 'at path=\S\+ of'
syn match cyUnknown '\S*'

" Curry syntax.
syn keyword cySpecial _Failure _Choice _SetGuard _Fwd _Free _PartApplic _G
syn keyword cySpecial _StrictConstraint _NonStrictConstraint _ValueBinding
syn match cyOperator '\W'
syn match cyFunction '\<[a-z]\w*\>'
syn match cyConstructor '\<[A-Z]\w*'
syn match cyFree '\<_\d\+\>'
syn match cyFree '\<_[a-z]\+\d*\>'
syn match cyLambda '\<_#lambda\d\+\>'
syn match cyTypeClassMeth '\<_inst\S\+\>'
syn match cyTypeClassMeth '\<_super\S\+\>'
syn match cyTypeClassMeth '\<_def\S\+\>'
syn match cyNumber '\<\d\+'
syn match cyNumber '\<\d\+\.'
syn match cyNumber '\<\d\+\.\d\+'
syn match cyFingerprint '<\(\d[LR]\)*>'

" Trace log patterns.
syn match cyTraceInfo 'I :::' nextgroup=cyTraceInfoBody skipwhite
syn match cyTraceQueue 'Q :::' nextgroup=cyTraceQueueBody skipwhite
syn match cyTraceStepEnter 'S <<<'
syn match cyTraceStepExit 'S >>>'
syn match cyTraceYield 'Y :::' nextgroup=cyTraceYieldBody skipwhite

" Highlighting.
hi def link cyFunction Function
hi def link cyLambda Function
hi def link cyTypeClassMeth Function
hi def link cyConstructor Comment
hi def link cySpecial Keyword
hi def link cyNumber Constant
hi def link cyOperator Special
hi cyFingerprint    ctermfg=darkblue
hi cyTraceInfoBody  ctermfg=lightgrey cterm=underline
hi cyTraceInfo      ctermfg=lightgrey cterm=inverse
hi cyTraceQueueBody ctermfg=green     cterm=underline
hi cyTraceQueue     ctermfg=green     cterm=inverse
hi cyTraceStepEnter ctermfg=lightgrey cterm=inverse
hi cyTraceStepExit  ctermfg=cyan      cterm=inverse
hi cyTraceYieldBody ctermfg=green     cterm=inverse
hi cyTraceYield     ctermfg=green     cterm=inverse
hi cyUnknown        ctermfg=red       cterm=inverse

" Anything not handled is program output.
syn match programOutput '^\(\([IQY] :::\|S <<<\|S >>>\)\@!.\)*$'
hi programOutput ctermfg=white


