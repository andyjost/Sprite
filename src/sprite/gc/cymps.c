/**
 * @file An instance of the  Memory Pool System (MPS) compiled with the Sprite
 * object format inlined.
 */

#include "mps.c" // All of MPS; the Sprite object format is defined below.

#include "sprite/gc/cymps.h"
#include "sprite/gc/defs.h"
#include "sprite/gc/globals.h"
#include "stdio.h"
#include "stdlib.h"
#define ASADDR(addr) (*({mps_addr_t * tmp = (mps_addr_t*)(&addr); tmp;}))
#define ASOBJ(addr) (*({heapobj_t** tmp = (heapobj_t**)(&addr); tmp;}))
#define SIZE_BOUND (1<<16)
#define error(what) do { fprintf(stderr, what); exit(1); } while(0)

/**
 * @brief An info table.  Every heap object begins with an info pointer, whose
 * type is info_t*.
 */
typedef struct info_t
{
  int tag;
  size_t size; // heap object size in bytes offset from *payload*.
} info_t;

/// The basic object used for any Curry expression.
typedef struct heapobj_t
{
  info_t * info;
  char payload[]; // dynamically sized.
} heapobj_t;

/// Used internally by MPS to fill unused space.
typedef struct pad_t
{
  info_t * info;
  size_t bytes; // in total bytes (including the info pointer).
} pad_t;

static info_t pad1_info = {PAD1, 0};
static info_t pad_info = {PAD, 0};

/**
 * @brief Indicates whether an object is a Curry object.
 *
 * Curry objects are the node types appearing in the Fair Scheme: failure,
 * choice, operation, and constructor.  Other objects are used by MPS for
 * administration (padding and forwarding).
 */
int is_curry_object(heapobj_t * obj)
{
  return !HASBIT(obj->info, FLAGMASK)
      && obj->info->tag != PAD
      && obj->info->tag != PAD1;
}

/// Gets the size of a forwarding object.
size_t fwd_obj_size(heapobj_t * obj)
{
  assert(HASBIT(obj->info, FLAGMASK));
  return ((size_t)(obj->info)) >> 48;
}

/// Get the size of a padding object.
size_t pad_obj_size(heapobj_t * obj)
{
  assert(obj->info->tag == PAD);
  pad_t * pad = (pad_t *)(obj);
  return pad->bytes;
}

// MPS object format "scan" method.
mps_res_t obj_scan(mps_ss_t ss, mps_addr_t base, mps_addr_t limit)
{
  MPS_SCAN_BEGIN(ss)
  {
    while(base<limit)
    {
      heapobj_t * obj = (heapobj_t *)(base);
      if(HASBIT(obj->info, FLAGMASK))
      {
        if(!HASBIT(obj->info, MPSFWDBIT))
        {
          assert(HASBIT(obj->info, CYFWDBIT));
          size_t mask = HASBIT(obj->info, FLAGMASK);
          heapobj_t * obj2 = (heapobj_t *)(CLEARFLAGS(obj->info));
          FIX(obj2);
          obj->info = (info_t *)(SETBIT(obj2, mask));
        }
        base = (char *)(base) + fwd_obj_size(obj);
      }
      else if(obj->info->tag == PAD)
        base = (char *)(base) + pad_obj_size(obj);
      else
      {
        for(size_t i=0; i<obj->info->size; i+=PTRSZ)
          FIX(ASADDR(obj->payload[i]));
        base = &obj->payload[obj->info->size];
      }
    }
  }
  MPS_SCAN_END(ss);
  return MPS_RES_OK;
}

// MPS object format "skip" method.
mps_addr_t obj_skip(mps_addr_t addr)
{
  heapobj_t * obj = (heapobj_t *)(addr);
  if(HASBIT(obj->info, FLAGMASK))
    return (char *)(addr) + fwd_obj_size(obj);
  else if(obj->info->tag == PAD)
    return (char *)(addr) + pad_obj_size(obj);
  else
    return &obj->payload[obj->info->size];
}

// MPS object format "fwd" method.
void obj_fwd(mps_addr_t old, mps_addr_t _new)
{
  heapobj_t * obj = (heapobj_t *)(old);
  assert(!HASBIT(obj->info, MPSFWDBIT));
  size_t const size =
    (HASBIT(obj->info, FLAGMASK))
      ? fwd_obj_size(obj)
      : (obj->info->tag == PAD)
        ? pad_obj_size(obj)
        : PTRSZ + obj->info->size;
  assert(size < SIZE_BOUND);
  obj->info = (info_t *)(SETBIT(_new, MPSFWDBIT|(size<<48)));
}

// MPS object format "isfwd" method.
mps_addr_t obj_isfwd(mps_addr_t addr)
{
  heapobj_t * obj = (heapobj_t *)(addr);
  return HASBIT(obj->info, MPSFWDBIT) ? CLEARFLAGS(obj->info) : 0;
}

// MPS object format "pad" method.
void obj_pad(mps_addr_t addr, size_t size)
{
  heapobj_t * obj = (heapobj_t *)(addr);
  if(size == PTRSZ)
    obj->info = &pad1_info;
  else
  {
    pad_t * pad = (pad_t *)(addr);
    pad->info = &pad_info;
    pad->bytes = size;
  }
}

///@{
/// Iteration support for heap objects.
heapobj_t ** begin(heapobj_t * obj)
{
  SKIPFWD(obj);
  return &ASOBJ(obj->payload[0]);
}
heapobj_t ** end(heapobj_t * obj)
{
  SKIPFWD(obj);
  return &ASOBJ(obj->payload[obj->info->size]);
}
///@}

static mps_arena_t arena;
static mps_fmt_t obj_fmt;
static mps_pool_t obj_pool;
static mps_root_t globals_root;
static mps_thr_t thread;
static mps_root_t stack_root;
static mps_ap_t obj_ap;

/**
 * @brief Initializes MPS.
 *
 * Must be called after "main" begins.  @p top_of_stack should be passed the
 * address of a stack variable that remains valid until main returns.
 */
void init_memory_system(void * top_of_stack)
{
  mps_res_t res;

  // Arena
  res = mps_arena_create_k(&arena, mps_arena_class_vm(), mps_args_none);
  if(res != MPS_RES_OK) error("Couldn't create arena");

  // Object format
  MPS_ARGS_BEGIN(args)
  {
    MPS_ARGS_ADD(args, MPS_KEY_FMT_ALIGN, PTRSZ);
    MPS_ARGS_ADD(args, MPS_KEY_FMT_SCAN, obj_scan);
    MPS_ARGS_ADD(args, MPS_KEY_FMT_SKIP, obj_skip);
    MPS_ARGS_ADD(args, MPS_KEY_FMT_FWD, obj_fwd);
    MPS_ARGS_ADD(args, MPS_KEY_FMT_ISFWD, obj_isfwd);
    MPS_ARGS_ADD(args, MPS_KEY_FMT_PAD, obj_pad);
    res = mps_fmt_create_k(&obj_fmt, arena, args);
  }
  MPS_ARGS_END(args);
  if(res != MPS_RES_OK) error("Couldn't create object format");

  // Pool
  MPS_ARGS_BEGIN(args)
  {
    MPS_ARGS_ADD(args, MPS_KEY_FORMAT, obj_fmt);
    res = mps_pool_create_k(&obj_pool, arena, mps_class_amc(), args);
  }
  MPS_ARGS_END(args);
  if(res != MPS_RES_OK) error("Couldn't create obj_pool");

  // Roots
  res = mps_root_create(
      &globals_root, arena, mps_rank_exact(), 0, globals_scan, NULL, 0
    );
  if(res != MPS_RES_OK) error("Couldn't register globals root");

  // Thread
  res = mps_thread_reg(&thread, arena);
  if(res != MPS_RES_OK) error("Couldn't register thread");

  // Stack
  res = mps_root_create_thread(&stack_root, arena, thread, top_of_stack);
  if(res != MPS_RES_OK) error("Couldn't create root");

  // Allocation point.
  res = mps_ap_create_k(&obj_ap, obj_pool, mps_args_none);
  if(res != MPS_RES_OK) error("Couldn't create obj allocation point");
}

void destroy_memory_system()
{
  globals_clear();

  mps_arena_park(arena);          /* ensure no collection is running */
  mps_ap_destroy(obj_ap);         /* destroy ap before pool */
  mps_pool_destroy(obj_pool);     /* destroy pool before fmt */
  mps_root_destroy(globals_root); /* destroy roots before thread */
  mps_root_destroy(stack_root);   /* destroy roots before thread */
  mps_thread_dereg(thread);       /* deregister thread before arena */
  mps_fmt_destroy(obj_fmt);       /* destroy fmt before arena */
  mps_arena_destroy(arena);       /* last of all */
}

