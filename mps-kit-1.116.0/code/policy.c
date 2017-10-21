/* policy.c: POLICY DECISIONS
 *
 * $Id: //info.ravenbrook.com/project/mps/version/1.116/code/policy.c#1 $
 * Copyright (c) 2001-2016 Ravenbrook Limited.  See end of file for license.
 *
 * This module collects the decision-making code for the MPS, so that
 * policy can be maintained and adjusted.
 *
 * .sources: <design/strategy/>.
 */

#include "locus.h"
#include "mpm.h"

SRCID(policy, "$Id: //info.ravenbrook.com/project/mps/version/1.116/code/policy.c#1 $");


/* PolicyAlloc -- allocation policy
 *
 * This is the code responsible for making decisions about where to allocate
 * memory.
 *
 * pref describes the address space preferences for the allocation.
 * size is the amount of memory requested to be allocated, in bytes.
 * pool is the pool that is requresting the memory.
 *
 * If successful, update *tractReturn to point to the initial tract of
 * the allocated memory and return ResOK. Otherwise return a result
 * code describing the problem.
 */

Res PolicyAlloc(Tract *tractReturn, Arena arena, LocusPref pref,
                Size size, Pool pool)
{
  Res res;
  Tract tract;
  ZoneSet zones, moreZones, evenMoreZones;

  AVER(tractReturn != NULL);
  AVERT(Arena, arena);
  AVERT(LocusPref, pref);
  AVER(size > (Size)0);
  AVER(SizeIsArenaGrains(size, arena));
  AVERT(Pool, pool);
  AVER(arena == PoolArena(pool));

  /* Don't attempt to allocate if doing so would definitely exceed the
   * commit limit. */
  if (arena->spareCommitted < size) {
    Size necessaryCommitIncrease = size - arena->spareCommitted;
    if (arena->committed + necessaryCommitIncrease > arena->commitLimit
        || arena->committed + necessaryCommitIncrease < arena->committed) {
      return ResCOMMIT_LIMIT;
    }
  }

  /* Plan A: allocate from the free land in the requested zones */
  zones = ZoneSetDiff(pref->zones, pref->avoid);
  if (zones != ZoneSetEMPTY) {
    res = ArenaFreeLandAlloc(&tract, arena, zones, pref->high, size, pool);
    if (res == ResOK)
      goto found;
  }

  /* Plan B: add free zones that aren't blacklisted */
  /* TODO: Pools without ambiguous roots might not care about the blacklist. */
  /* TODO: zones are precious and (currently) never deallocated, so we
   * should consider extending the arena first if address space is plentiful.
   * See also job003384. */
  moreZones = ZoneSetUnion(pref->zones, ZoneSetDiff(arena->freeZones, pref->avoid));
  if (moreZones != zones) {
    res = ArenaFreeLandAlloc(&tract, arena, moreZones, pref->high, size, pool);
    if (res == ResOK)
      goto found;
  }

  /* Plan C: Extend the arena, then try A and B again. */
  if (moreZones != ZoneSetEMPTY) {
    res = Method(Arena, arena, grow)(arena, pref, size);
    /* If we can't extend because we hit the commit limit, try purging
       some spare committed memory and try again.*/
    /* TODO: This would be a good time to *remap* VM instead of
       returning it to the OS. */
    if (res == ResCOMMIT_LIMIT) {
      if (Method(Arena, arena, purgeSpare)(arena, size) >= size)
        res = Method(Arena, arena, grow)(arena, pref, size);
    }
    if (res == ResOK) {
      if (zones != ZoneSetEMPTY) {
        res = ArenaFreeLandAlloc(&tract, arena, zones, pref->high, size, pool);
        if (res == ResOK)
          goto found;
      }
      if (moreZones != zones) {
        res = ArenaFreeLandAlloc(&tract, arena, moreZones, pref->high,
                                 size, pool);
        if (res == ResOK)
          goto found;
      }
    }
    /* TODO: Log an event here, since something went wrong, before
       trying the next plan anyway. */
  }

  /* Plan D: add every zone that isn't blacklisted.  This might mix GC'd
   * objects with those from other generations, causing the zone check
   * to give false positives and slowing down the collector. */
  /* TODO: log an event for this */
  evenMoreZones = ZoneSetDiff(ZoneSetUNIV, pref->avoid);
  if (evenMoreZones != moreZones) {
    res = ArenaFreeLandAlloc(&tract, arena, evenMoreZones, pref->high,
                             size, pool);
    if (res == ResOK)
      goto found;
  }

  /* Last resort: try anywhere.  This might put GC'd objects in zones where
   * common ambiguous bit patterns pin them down, causing the zone check
   * to give even more false positives permanently, and possibly retaining
   * garbage indefinitely. */
  res = ArenaFreeLandAlloc(&tract, arena, ZoneSetUNIV, pref->high, size, pool);
  if (res == ResOK)
    goto found;

  /* Uh oh. */
  return res;

found:
  *tractReturn = tract;
  return ResOK;
}


/* policyCollectionTime -- estimate time to collect the world, in seconds */

static double policyCollectionTime(Arena arena)
{
  Size collectableSize;
  double collectionRate;
  double collectionTime;
  
  AVERT(Arena, arena);

  collectableSize = ArenaCollectable(arena);
  /* The condition arena->tracedTime >= 1.0 ensures that the division
   * can't overflow. */
  if (arena->tracedTime >= 1.0)
    collectionRate = arena->tracedWork / arena->tracedTime;
  else
    collectionRate = ARENA_DEFAULT_COLLECTION_RATE;
  collectionTime = collectableSize / collectionRate;
  collectionTime += ARENA_DEFAULT_COLLECTION_OVERHEAD;

  return collectionTime;
}


/* PolicyShouldCollectWorld -- should we collect the world now?
 *
 * Return TRUE if we should try collecting the world now, FALSE if
 * not.
 *
 * This is the policy behind mps_arena_step, and so the client
 * must have provided us with enough time to collect the world, and
 * enough time must have passed since the last time we did that
 * opportunistically.
 */

Bool PolicyShouldCollectWorld(Arena arena, double availableTime,
                              Clock now, Clock clocks_per_sec)
{
  Size collectableSize;
  double collectionTime, sinceLastWorldCollect;

  AVERT(Arena, arena);
  /* Can't collect the world if we're already collecting. */
  AVER(arena->busyTraces == TraceSetEMPTY);

  if (availableTime <= 0.0)
    /* Can't collect the world if we're not given any time. */
    return FALSE;

  /* Don't collect the world if it's very small. */
  collectableSize = ArenaCollectable(arena);
  if (collectableSize < ARENA_MINIMUM_COLLECTABLE_SIZE)
    return FALSE;

  /* How long would it take to collect the world? */
  collectionTime = policyCollectionTime(arena);

  /* How long since we last collected the world? */
  sinceLastWorldCollect = ((now - arena->lastWorldCollect) /
                           (double) clocks_per_sec);

  /* Offered enough time, and long enough since we last did it? */
  return availableTime > collectionTime
    && sinceLastWorldCollect > collectionTime / ARENA_MAX_COLLECT_FRACTION;
}


/* policyCondemnChain -- condemn approriate parts of this chain
 *
 * If successful, set *mortalityReturn to an estimate of the mortality
 * of the condemned parts of this chain and return ResOK.
 *
 * This is only called if ChainDeferral returned a value sufficiently
 * low that we decided to start the collection. (Usually such values
 * are less than zero; see <design/strategy/#policy.start.chain>.)
 */

static Res policyCondemnChain(double *mortalityReturn, Chain chain, Trace trace)
{
  Res res;
  size_t topCondemnedGen, i;
  GenDesc gen;
  Size condemnedSize = 0, survivorSize = 0, genNewSize, genTotalSize;

  AVERT(Chain, chain);
  AVERT(Trace, trace);

  /* Find the highest generation that's over capacity. We will condemn
   * this and all lower generations in the chain. */
  topCondemnedGen = chain->genCount;
  for (;;) {
    /* It's an error to call this function unless some generation is
     * over capacity as reported by ChainDeferral. */
    AVER(topCondemnedGen > 0);
    if (topCondemnedGen == 0)
      return ResFAIL;
    -- topCondemnedGen;
    gen = &chain->gens[topCondemnedGen];
    AVERT(GenDesc, gen);
    genNewSize = GenDescNewSize(gen);
    if (genNewSize >= gen->capacity * (Size)1024)
      break;
  }

  /* At this point, we've decided to condemn topCondemnedGen and all
   * lower generations. */
  TraceCondemnStart(trace);
  for (i = 0; i <= topCondemnedGen; ++i) {
    Ring node, next;
    gen = &chain->gens[i];
    AVERT(GenDesc, gen);
    RING_FOR(node, &gen->segRing, next) {
      GCSeg gcseg = RING_ELT(GCSeg, genRing, node);
      res = TraceAddWhite(trace, &gcseg->segStruct);
      if (res != ResOK)
        goto failBegin;
    }
    genTotalSize = GenDescTotalSize(gen);
    genNewSize = GenDescNewSize(gen);
    condemnedSize += genTotalSize;
    survivorSize += (Size)(genNewSize * (1.0 - gen->mortality))
                    /* predict survivors will survive again */
                    + (genTotalSize - genNewSize);
  }
  TraceCondemnEnd(trace);

  EVENT3(ChainCondemnAuto, chain, topCondemnedGen, chain->genCount);
  
  *mortalityReturn = 1.0 - (double)survivorSize / condemnedSize;
  return ResOK;

failBegin:
  AVER(TraceIsEmpty(trace));    /* See <code/trace.c#whiten.fail> */
  TraceCondemnEnd(trace);
  return res;
}


/* PolicyStartTrace -- consider starting a trace
 *
 * If collectWorldAllowed is TRUE, consider starting a collection of
 * the world. Otherwise, consider only starting collections of individual
 * chains or generations.
 *
 * If a collection of the world was started, set *collectWorldReturn
 * to TRUE. Otherwise leave it unchanged.
 *
 * If a trace was started, update *traceReturn and return TRUE.
 * Otherwise, leave *traceReturn unchanged and return FALSE.
 */

Bool PolicyStartTrace(Trace *traceReturn, Bool *collectWorldReturn,
                      Arena arena, Bool collectWorldAllowed)
{
  Res res;
  Trace trace;

  AVER(traceReturn != NULL);
  AVERT(Arena, arena);

  if (collectWorldAllowed) {
    Size sFoundation, sCondemned, sSurvivors, sConsTrace;
    double tTracePerScan; /* tTrace/cScan */
    double dynamicDeferral;

    /* Compute dynamic criterion.  See strategy.lisp-machine. */
    sFoundation = (Size)0; /* condemning everything, only roots @@@@ */
    /* @@@@ sCondemned should be scannable only */
    sCondemned = ArenaCommitted(arena) - ArenaSpareCommitted(arena);
    sSurvivors = (Size)(sCondemned * (1 - arena->topGen.mortality));
    tTracePerScan = sFoundation + (sSurvivors * (1 + TraceCopyScanRATIO));
    AVER(TraceWorkFactor >= 0);
    AVER(sSurvivors + tTracePerScan * TraceWorkFactor <= (double)SizeMAX);
    sConsTrace = (Size)(sSurvivors + tTracePerScan * TraceWorkFactor);
    dynamicDeferral = (double)ArenaAvail(arena) - (double)sConsTrace;

    if (dynamicDeferral < 0.0) {
      /* Start full collection. */
      res = TraceStartCollectAll(&trace, arena, TraceStartWhyDYNAMICCRITERION);
      if (res != ResOK)
        goto failStart;
      *collectWorldReturn = TRUE;
      *traceReturn = trace;
      return TRUE;
    }
  }
  {
    /* Find the chain most over its capacity. */
    Ring node, nextNode;
    double firstTime = 0.0;
    Chain firstChain = NULL;

    RING_FOR(node, &arena->chainRing, nextNode) {
      Chain chain = RING_ELT(Chain, chainRing, node);
      double time;

      AVERT(Chain, chain);
      time = ChainDeferral(chain);
      if (time < firstTime) {
        firstTime = time; firstChain = chain;
      }
    }

    /* If one was found, start collection on that chain. */
    if(firstTime < 0) {
      double mortality;

      res = TraceCreate(&trace, arena, TraceStartWhyCHAIN_GEN0CAP);
      AVER(res == ResOK);
      trace->chain = firstChain;
      ChainStartTrace(firstChain, trace);
      res = policyCondemnChain(&mortality, firstChain, trace);
      if (res != ResOK) /* should try some other trace, really @@@@ */
        goto failCondemn;
      if (TraceIsEmpty(trace))
        goto nothingCondemned;
      res = TraceStart(trace, mortality, trace->condemned * TraceWorkFactor);
      /* We don't expect normal GC traces to fail to start. */
      AVER(res == ResOK);
      *traceReturn = trace;
      return TRUE;
    }
  } /* (dynamicDeferral > 0.0) */
  return FALSE;

nothingCondemned:
failCondemn:
  TraceDestroyInit(trace);
failStart:
  return FALSE;
}


/* PolicyPoll -- do some tracing work?
 *
 * Return TRUE if the MPS should do some tracing work; FALSE if it
 * should return to the mutator.
 */

Bool PolicyPoll(Arena arena)
{
  Globals globals;
  AVERT(Arena, arena);
  globals = ArenaGlobals(arena);
  return globals->pollThreshold <= globals->fillMutatorSize;
}


/* PolicyPollAgain -- do another unit of work?
 *
 * Return TRUE if the MPS should do another unit of work; FALSE if it
 * should return to the mutator.
 *
 * start is the clock time when the MPS was entered.
 * moreWork and tracedWork are the results of the last call to TracePoll.
 */

Bool PolicyPollAgain(Arena arena, Clock start, Bool moreWork, Work tracedWork)
{
  Bool moreTime;
  Globals globals;
  double nextPollThreshold;

  AVERT(Arena, arena);
  UNUSED(tracedWork);

  if (ArenaEmergency(arena))
    return TRUE;

  /* Is there more work to do and more time to do it in? */
  moreTime = (ClockNow() - start) < ArenaPauseTime(arena) * ClocksPerSec();
  if (moreWork && moreTime)
    return TRUE;

  /* We're not going to do more work now, so calculate when to come back. */

  globals = ArenaGlobals(arena);

  if (moreWork) {
    /* We did one quantum of work; consume one unit of 'time'. */
    nextPollThreshold = globals->pollThreshold + ArenaPollALLOCTIME;
  } else {
    /* No more work to do.  Sleep until NOW + a bit. */
    nextPollThreshold = globals->fillMutatorSize + ArenaPollALLOCTIME;
  }

  /* Advance pollThreshold; check: enough precision? */
  AVER(nextPollThreshold > globals->pollThreshold);
  globals->pollThreshold = nextPollThreshold;

  return FALSE;
}


/* C. COPYRIGHT AND LICENSE
 *
 * Copyright (C) 2001-2016 Ravenbrook Limited <http://www.ravenbrook.com/>.
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
