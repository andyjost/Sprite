from .....common import T_CHOICE, T_CTOR, T_FREE
from .freevars import freshvar
from .. import graph
from ...sprite import LEFT, RIGHT, UNDETERMINED


def follow_3choice(rts, arg, config):
  # Follows the choices in (a ? b) ? c based on the fingerprint.
  # Returns the node reached, or None if some choice is not made.
  cid,l,r = arg
  lr = rts.read_fp(cid, config)
  if lr == LEFT:
    cid,l,r = l
    lr = rts.read_fp(cid, config)
    if lr == LEFT:
      return l
    elif lr == RIGHT:
      return r
  elif lr == RIGHT:
    return r

def narrowed_int_value(rts, arg=None, config=None):
  config = config or rts.C
  arg = config.root if arg is None else arg
  vid = rts.obj_id(arg, config=config)
  if vid in rts.vmap:
    x_al = rts.vmap[vid]
    if rts.has_generator(x_al, config):
      tree = rts.get_generator(x_al, config)
      tree = follow_3choice(rts, tree, config)
      if tree is None:
        return None
      elif tree.info == rts.integer.Pos.info:
        nat = tree[0]
        sign = 1
      elif tree.info == rts.integer.Zero.info:
        return 0
      elif tree.info == rts.integer.Neg.info:
        nat = tree[0]
        sign = -1
      # post: nat is a Curry Nat
      value = 0
      bit = 1
      while True:
        tag = nat.info.tag
        if tag == T_FREE:
          vid = nat[0]
          if rts.read_fp(vid, config) == UNDETERMINED:
            return None
          else:
            nat = nat[1]
        elif tag == T_CHOICE:
          cid,l,r = nat
          lr = rts.read_fp(cid, config)
          if lr == LEFT:
            nat = l
          elif lr == RIGHT:
            nat = r
          else:
            return None
        elif tag >= T_CTOR:
          if nat.info == rts.integer.IHi.info:
            return sign * (value | bit)
          else:
            if nat.info == rts.integer.I.info:
              value |= bit
            nat = nat[0]
          bit <<= 1
        else:
          assert False
      assert False

def compile_iset(rts, ints):
  # This code is disabled for now.
  return list(ints)

  # Sort by (Zero Pos Neg) then sort the natural number parts by IHi|I|O on the
  # remaining bits.  This puts the integers in right-to-left order according to
  # Integer.ISet.
  #
  # E.g., [4, 7, 12] -> [7, 12, 4]
  if not ints:
    return None
  zero, pos, neg = _partition(ints)
  def key(n):
    yield '0' if n == 0 else '1' if n > 0 else '2'
    if n == 0:
      return
    n = abs(n)
    while n:
      if n == 1:
        yield '0'
        break
      yield '1' if n & 0x1 else '2'
      n >>= 1
  def sort(xs):
    if len(xs) > 1:
      _, xs = zip(*sorted(zip([''.join(key(x)) for x in xs], xs), reverse=True))
    return map(abs, xs)
  pos, neg = map(sort, (pos, neg))

  T = graph.Node(rts.prelude.True)
  F = graph.Node(rts.prelude.False)
  ISet = rts.integer.ISet
  Empty = graph.Node(rts.integer.Empty)

  def nat(ints, n=0, i=1):
    if not ints:
      return Empty
    if ints[-1] == n+i:
      left = T
      ints.pop()
    else:
      left = F
    more = lambda sense: ints and ints[-1] & (i-1) == n and (ints[-1] & i == 0) == sense
    return graph.Node(
        ISet, left
      , nat(ints, n+i, i<<1) if more(False) else Empty
      , nat(ints, n, i<<1) if more(True) else Empty
      )
  result = graph.Node(ISet, T if zero else F, nat(pos), nat(neg))
  assert not pos
  assert not neg
  return result

def _partition(ints):
  zero = False
  pos = []
  neg = []
  for i in ints:
    if i == 0:
      zero = True
    elif i > 0:
      pos.append(i)
    else:
      neg.append(-i)
  return zero, pos, neg
