/* prmci6xc.c: PROTECTION MUTATOR CONTEXT x64 (OS X)
 *
 * $Id: //info.ravenbrook.com/project/mps/version/1.116/code/prmci6xc.c#1 $
 * Copyright (c) 2001-2014 Ravenbrook Limited.  See end of file for license.
 *
 * .purpose: This module implements the part of the protection module
 * that decodes the MutatorFaultContext. 
 *
 *
 * SOURCES
 *
 *
 * ASSUMPTIONS
 *
 * .sp: The stack pointer in the context is RSP.
 *
 * .context.regroots: The root regs are assumed to be recorded in the context
 * at pointer-aligned boundaries.
 *
 * .assume.regref: The registers in the context can be modified by
 * storing into an MRef pointer.
 */

#include "prmcxc.h"
#include "prmci6.h"

SRCID(prmci6xc, "$Id: //info.ravenbrook.com/project/mps/version/1.116/code/prmci6xc.c#1 $");

#if !defined(MPS_OS_XC) || !defined(MPS_ARCH_I6)
#error "prmci6xc.c is specific to MPS_OS_XC and MPS_ARCH_I6"
#endif


/* Prmci6AddressHoldingReg -- return an address of a register in a context */

MRef Prmci6AddressHoldingReg(MutatorFaultContext mfc, unsigned int regnum)
{
  THREAD_STATE_S *threadState;

  AVER(mfc != NULL);
  AVER(NONNEGATIVE(regnum));
  AVER(regnum <= 15);
  AVER(mfc->threadState != NULL);
  threadState = mfc->threadState;

  /* .assume.regref */
  /* The register numbers (REG_RAX etc.) are defined in <ucontext.h>
     but only if _XOPEN_SOURCE is defined: see .feature.xc in
     config.h. */
  /* MRef (a Word *) is not compatible with pointers to the register
     types (actually a __uint64_t). To avoid aliasing optimization
     problems, the registers are cast through (void *). */
  switch (regnum) {
    case  0: return (void *)&threadState->__rax;
    case  1: return (void *)&threadState->__rcx;
    case  2: return (void *)&threadState->__rdx;
    case  3: return (void *)&threadState->__rbx;
    case  4: return (void *)&threadState->__rsp;
    case  5: return (void *)&threadState->__rbp;
    case  6: return (void *)&threadState->__rsi;
    case  7: return (void *)&threadState->__rdi;
    case  8: return (void *)&threadState->__r8;
    case  9: return (void *)&threadState->__r9;
    case 10: return (void *)&threadState->__r10;
    case 11: return (void *)&threadState->__r11;
    case 12: return (void *)&threadState->__r12;
    case 13: return (void *)&threadState->__r13;
    case 14: return (void *)&threadState->__r14;
    case 15: return (void *)&threadState->__r15;
    default:
      NOTREACHED;
      return NULL;  /* Avoids compiler warning. */
  }
}


/* Prmci6DecodeFaultContext -- decode fault to find faulting address and IP */

void Prmci6DecodeFaultContext(MRef *faultmemReturn,
                              Byte **insvecReturn,
                              MutatorFaultContext mfc)
{
  *faultmemReturn = (MRef)mfc->address;
  *insvecReturn = (Byte*)mfc->threadState->__rip;
}


/* Prmci6StepOverIns -- modify context to step over instruction */

void Prmci6StepOverIns(MutatorFaultContext mfc, Size inslen)
{
  mfc->threadState->__rip += (Word)inslen;
}


Addr MutatorFaultContextSP(MutatorFaultContext mfc)
{
  return (Addr)mfc->threadState->__rsp;
}


Res MutatorFaultContextScan(ScanState ss, MutatorFaultContext mfc,
                            mps_area_scan_t scan_area,
                            void *closure)
{
  x86_thread_state64_t *mc;
  Res res;

  /* This scans the root registers (.context.regroots).  It also
     unnecessarily scans the rest of the context.  The optimisation
     to scan only relevant parts would be machine dependent. */
  mc = mfc->threadState;
  res = TraceScanArea(ss,
                      (Word *)mc,
                      (Word *)((char *)mc + sizeof(*mc)),
                      scan_area, closure);
  return res;
}


/* C. COPYRIGHT AND LICENSE
 *
 * Copyright (C) 2001-2014 Ravenbrook Limited <http://www.ravenbrook.com/>.
 * All rights reserved.  This is an open source license.  Contact
 * Ravenbrook for commercial licensing options.
 * 
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met:
 * 
 * 1. Redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer.
 * 
 * 2. Redistributions in binary form must reproduce the above copyright
 * notice, this list of conditions and the following disclaimer in the
 * documentation and/or other materials provided with the distribution.
 * 
 * 3. Redistributions in any form must be accompanied by information on how
 * to obtain complete source code for this software and any accompanying
 * software that uses this software.  The source code must either be
 * included in the distribution or be available for no more than the cost
 * of distribution plus a nominal fee, and must be freely redistributable
 * under reasonable conditions.  For an executable file, complete source
 * code means the source code for all modules it contains. It does not
 * include source code for modules or files that typically accompany the
 * major components of the operating system on which the executable file
 * runs.
 * 
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
 * IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
 * TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
 * PURPOSE, OR NON-INFRINGEMENT, ARE DISCLAIMED. IN NO EVENT SHALL THE
 * COPYRIGHT HOLDERS AND CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
 * INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
 * NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
 * USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
 * ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
 * THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */
