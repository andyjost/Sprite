" Vim syntax file
" Language: Sprite Curry Compiler trace and log output
"

if exists("b:current_syntax")
  finish
endif
let b:current_syntax = "spritelog"

" These patterns should be overridden by something below.
" The are used with nextgroup.
syn match cyTraceQueueBody '\S.*$'
syn match cyTraceYieldBody '\S.*$'
syn match cyTraceInfoBody 'at path=\S\+ of'

" Curry syntax.
syn keyword cySpecial _Failure _Choice _SetGuard _Fwd _Free _PartApplic _G
syn keyword cySpecial _StrictConstraint _NonStrictConstraint _ValueBinding
syn match cyFunction '\<[a-z]\w*\>'
syn match cyConstructor '\<[A-Z]\w*'
syn match cyFree '\<_\d\+\>'
syn match cyNumber '\<\d\+'
syn match cyNumber '\<\d\+\.'
syn match cyNumber '\<\d\+\.\d\+'
syn match cyOperator '\W'
syn match cyFingerprint '<\(\d[LR]\)*>'

" Trace log patterns.
syn match cyTraceInfo 'I :::' nextgroup=cyTraceInfoBody skipwhite
syn match cyTraceQueue 'Q :::' nextgroup=cyTraceQueueBody skipwhite
syn match cyTraceStepEnter 'S <<<'
syn match cyTraceStepExit 'S >>>'
syn match cyTraceYield 'Y :::' nextgroup=cyTraceYieldBody skipwhite

" Highlighting.
hi def link cyFunction Function
hi def link cyConstructor Constant
hi def link cyFree Keyword
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

" Anything not handled is program output.
syn match programOutput '^\(\([IQY] :::\|S <<<\|S >>>\)\@!.\)*$'
hi programOutput ctermfg=white


