import cytest # from ./lib; must be first
from copy import copy
from curry.backends.cpp.runtime import pybindings
from curry.common import LEFT, RIGHT, UNDETERMINED
import itertools, unittest

try:
  import numpy as np
except ImportError:
  np = None

BASIC_SIZE = pybindings.Fingerprint.BASIC_SIZE()
BRANCHING_FACTOR = pybindings.Fingerprint.BRANCHING_FACTOR()

class Fingerprint(cytest.TestCase):
  def testTreeShape(self):
    # The fingerprint is an efficient data structure for storing choice states.
    #
    # It is implemented as a tree consisting of nodes.  A node is a union of a
    # pointer-to-branch or block (leaf).  Branches are shared.  Each choice
    # uses two bits to encode a choice state (left, right, or undetermined).
    # Since the space of one pointer is available (due to the branch), a block
    # on a 64-bit system contains 32 choices.  The fingerprint automatically
    # resizes itself based on the largest index ever used.  To expand, it adds
    # a level of branches.  The branching factor can be adjusted in the source,
    # but these diagrams are all drawn assuming a branching factor of four.

    zero = [0] * BASIC_SIZE # A zero block.
    allzero = lambda blocks: all(block.values() == zero for block in blocks)
    assertAllZero = lambda *args: self.assertTrue(allzero(itertools.chain(*args)))

    # Depth=0.
    # There is simply one block.
    fp = pybindings.Fingerprint()
    self.assertEqual(fp.capacity, BASIC_SIZE)
    self.assertEqual(fp.depth, 0)
    self.assertEqual([int(fp[i]) for i in range(8)], [0]*8)
    self.assertEqual(fp.capacity, BASIC_SIZE)
    self.assertEqual(fp.depth, 0)
    assertAllZero([fp.tree()])

    # Depth=1.
    # All blocks are unique.
    #            B
    #          /| |\
    #         / | | \
    #        a  b c  d
    #
    # Increase the size.
    self.assertEqual(fp[BASIC_SIZE], UNDETERMINED)
    self.assertEqual(fp.capacity, BASIC_SIZE * BRANCHING_FACTOR)
    self.assertEqual(fp.depth, 1)
    # Accessing the last available element does not changne the capacity.
    self.assertEqual(fp[fp.capacity - 1], UNDETERMINED)
    self.assertEqual(fp.capacity, BASIC_SIZE * BRANCHING_FACTOR)
    self.assertEqual(fp.depth, 1)

    tree = fp.tree()
    self.assertEqual(len(set(id(x) for x in tree)), BRANCHING_FACTOR) # all different addresses
    assertAllZero(tree)

    # Depth=2.
    #                 o        (w,x,y,z)
    #               /   \\\
    #             /       \\\
    #            o          o
    #          /| |\      /| |\
    #         / | | \    / | | \
    #        a  b c  d  e  f g  h
    #
    # Increase the size.
    self.assertEqual(fp[fp.capacity], UNDETERMINED)
    self.assertEqual(fp.capacity, BASIC_SIZE * BRANCHING_FACTOR ** 2)
    self.assertEqual(fp.depth, 2)
    # Accessing the last available element does not changne the capacity.
    self.assertEqual(fp[fp.capacity - 1], UNDETERMINED)
    self.assertEqual(fp.capacity, BASIC_SIZE * BRANCHING_FACTOR ** 2)
    self.assertEqual(fp.depth, 2)

    tree = fp.tree()
    ids = [id(x) for x in tree]
    self.assertFalse(any(ids[0]==_ for _ in ids[1:]))
    self.assertTrue(ids[1:-1] == ids[2:])
    assertAllZero(tree[0], tree[1])

    # Depth=3.
    #
    #                          o (u,v,w,x)
    #                         / \\\
    #                       /     \\\
    #                     /         \\\
    #                   /             o (q,r,s,t)
    #                 o (m,n,o,p)    ||||
    #               /   \\\          ||||
    #             /       \\\        ||||
    #            o          o         o
    #          /| |\      /| |\     /| |\
    #         / | | \    / | | \   / | | \
    #        a  b c  d  e  f g  h i  j k  l
    #
    # Increase the size.
    self.assertEqual(fp[fp.capacity], UNDETERMINED)
    self.assertEqual(fp.capacity, BASIC_SIZE * BRANCHING_FACTOR ** 3)
    self.assertEqual(fp.depth, 3)
    # Accessing the last available element does not changne the capacity.
    self.assertEqual(fp[fp.capacity - 1], UNDETERMINED)
    self.assertEqual(fp.capacity, BASIC_SIZE * BRANCHING_FACTOR ** 3)
    self.assertEqual(fp.depth, 3)

    tree = fp.tree()
    abcd = [id(x) for x in tree[0][0]]
    efgh = [id(x) for x in tree[0][1]]
    ijkl = [id(x) for x in tree[1][0]]
    mnop = [id(x) for x in tree[0]]
    qrst = [id(x) for x in tree[1]]
    uvwx = [id(x) for x in tree]
    self.assertFalse(any(uvwx[0]==_ for _ in uvwx[1:]))
    self.assertTrue(uvwx[1:-1] == uvwx[2:])
    self.assertFalse(any(mnop[0]==_ for _ in mnop[1:]))
    self.assertTrue(mnop[1:-1] == mnop[2:])
    self.assertTrue(qrst[:-1] == qrst[1:])
    assertAllZero(tree[0][0], tree[0][1], tree[1][0])

    # Now, set a choice in one of the shared branches to check the
    # copy-on-write semantic.  The path below will clone an instance of "j".
    blockid = lambda path: sum(
        i * BRANCHING_FACTOR ** n
            for i,n in zip(path, reversed(range(len(path)-1)))
      )
    choiceid = lambda path: BASIC_SIZE * blockid(path) + path[-1]
    path = [2,0,1,17]
    cid = choiceid(path)
    fp[cid] = LEFT
    tree = fp.tree()
    #
    uvwx = [id(x) for x in tree]
    self.assertTrue(len(set(uvwx)) == 3)
    self.assertTrue(all(uvwx[1] == _ for _ in uvwx[3:]))
    assertAllZero(tree[0][0], tree[0][1], tree[1][0])
    qrst = [id(x) for x in tree[2]]
    self.assertTrue(qrst[0] != qrst[1] and qrst[1:-1] == qrst[2:])
    assertAllZero(tree[2][1])
    ijkl = [id(x) for x in tree[2][0]]
    assertAllZero([tree[2][0][_] for _ in [x for x in range(BRANCHING_FACTOR) if x != 1]])
    self.assertEqual(
        tree[2][0][1].values()
      , [-1 if _ == 17 else 0 for _ in range(BASIC_SIZE)]
      )

    # One last check: set one more arbitrary element and then sweep through all
    # indices to check.
    cidR = choiceid([0,3,0,5])
    fp[cidR] = RIGHT
    self.assertTrue(all(
        fp[i] == (LEFT if i == cid else RIGHT if i == cidR else UNDETERMINED)
            for i in range(fp.capacity)
      ))

  def testGetSetItem(self):
    fp = pybindings.Fingerprint()
    self.assertEqual(fp[3], pybindings.UNDETERMINED)
    with self.assertRaisesRegex(ValueError, 'expected LEFT or RIGHT'):
      fp[3] = pybindings.UNDETERMINED
    for value in [15, None, 'left', -1, 0, 1]:
      with self.assertRaises(TypeError):
        fp[3] = value
    fp[3] = LEFT
    self.assertEqual(fp[3], LEFT)
    fp[3] = RIGHT
    self.assertEqual(fp[3], RIGHT)

  @unittest.skipIf(np is None, 'NumPy not available')
  def testRandom(self):
    '''Set and test random choice IDs, checking for consistent behavior.'''
    choice = np.random.choice
    def choose_dataset(data):
      n = choice(len(data))
      return data[n]
    def commit(data, maxindex):
      '''Commit a random choice in a random fingerprint.'''
      fp,memory = choose_dataset(data)
      while True:
        cid = choice(maxindex)
        if cid not in memory:
          break
      lr = LEFT if np.random.random() < 0.5 else RIGHT
      fp[cid] = memory[cid] = lr
    def clone(data, maxindex):
      fp,memory = choose_dataset(data)
      data.append((copy(fp), dict(memory)))
    def test(data, maxindex):
      fp,memory = choose_dataset(data)
      if not memory or np.random.random() < 0.5:
        # Test a value not already determined.
        while True:
          cid = choice(maxindex)
          if cid not in memory:
            break
        self.assertEqual(fp[cid], UNDETERMINED)
      else:
        # Test a value already determined.
        cid = choice(list(memory.keys()))
        self.assertEqual(fp[cid], memory[cid])
    ITERATIONS = 200
    NUM_ACTIONS = 100
    MAXINDEX = [int(x) for x in [1e2, 1e4, 1e6, 1e8, 1e10]]
    ACTIONS = [commit, test, clone]
    WEIGHTS = [
        [0.50, 0.00, 0.50] # commit and test only.
      , [0.25, 0.25, 0.50] # half testing, the other half commit or clone.
      , [0.10, 0.80, 0.10] # mostly cloning.
      , [0.80, 0.10, 0.10] # mostly committing.
      , [0.10, 0.10, 0.80] # mostly testing.
      ]
    for _ in range(ITERATIONS):
      # The first element (data) is a list of pairs of a fingerprint and a
      # dict.  Choice are remembered in the dict for cross-checking.
      args = [(pybindings.Fingerprint(), {})], choice(MAXINDEX)
      p = WEIGHTS[choice(len(WEIGHTS))]
      for _ in range(NUM_ACTIONS):
        choice(ACTIONS, p=p)(*args)

