from sha import sha
import bisect
from utils import size_rounder

def between (i, a, b):
    if a < b:
        return a < i and i < b
    if a == b:
        return a == i
    if a > b:
        return i > a or i < b
    
class node:
    """A subsidiary class for DHash nodes"""
    def __init__ (my, id):
        my.id = id
        my.blocks = {}
        my.alive = 1
        my.bytes = 0

        my.last_alive = 0
        my.lifetime = 0
        
        my.nrpc = 0
        my.sent_bytes = 0

    def start (my):
        my.alive = 1
    def stop (my):
        my.alive = 0
    
    def crash (my):
        my.stop ()
        my.blocks = {}
        my.bytes  = 0

    def store (my, block, size):
        assert my.alive
        if block not in my.blocks:
            my.blocks[block] = size
            my.bytes += size
        
    def __cmp__ (my, other):
        return cmp (my.id, other.id)
    def __repr__ (my):
        return "%d" % my.id
    def __str__ (my):
        # return hex(long(my.id)).lower()[2:-1]
        return "%d" % my.id

class dhash:
    """A Global View DHash simulator.  Subclass to actually store stuff.
    Provides a simple paramterizable insert and lazy repair implementation.
    The repair implementation does not delete excess fragments from nodes.
    Repair happens at the end of each observed time step.

    Time is maintained by the external simulator.  The simulator calls
    time_changed whenever time is updated because of an additional event.
    """
    def __init__ (my):
        my.nodes = []
        my.deadnodes = {}
        my.allnodes = {}
        my.blocks = {}
        
        my.now_nodes = [] # nodes that changed liveness this time step.

    def add_node (my, id):
        # Find or create the node
        if id in my.allnodes:
            nnode = my.allnodes[id]
        else:
            nnode = node (id)
            my.allnodes[id] = nnode

        if not nnode.alive:
            # This might be a re-join of some sort
            nnode.start ()
            del my.deadnodes[id]
            
        # Maintain sorted order for nodes.            
        if nnode not in my.nodes:
            bisect.insort (my.nodes, nnode)
        else:
            raise KeyError, "Duplicate insert of %d" % id

        if nnode not in my.now_nodes: my.now_nodes.append (nnode)
    
    def _failure (my, id, crash):
        n = my.allnodes[id]
        if n.alive:
            if crash:
                n.crash ()
            else:
                n.stop ()
            d = bisect.bisect (my.nodes, n)
            assert my.nodes[d - 1] == n
            my.nodes.pop (d - 1)
            my.deadnodes[n.id] = n
            if n not in my.now_nodes: my.now_nodes.append (n)
        
    def fail_node (my, id):
        my._failure (id, 0)

    def crash_node (my, id):
        my._failure (id, 1)

    def find_successor_index (my, id):
        # if id in my.nodes, returns the index of id.
	dummy = node (id)
        n = bisect.bisect_left (my.nodes, dummy)
        if n >= len(my.nodes):
            n = 0            
        return n
    def find_predecessor_index (my, id):
	dummy = node (id)
        n = bisect.bisect_left (my.nodes, dummy)
        if n == 0:
            n = len (my.nodes)
        n -= 1
        return n

    def succ (my, o, num = 1):
        """Return successor of o from active nodes. If o is active node,
        returns o. If num not specified, returns immediate successor.
        Otherwise, returns list of num immediate successors."""
        id = o
        if isinstance (o, node): id = o.id
        n = my.find_successor_index (id)
        diff = n + num - len (my.nodes)
        if diff > 0:
            if diff > n: diff = n
            return my.nodes[n:] + my.nodes[:diff]
        return my.nodes[n:n+num]

    def pred (my, o, num = 1):
        """Returns num predecessor's of o, not including o if o in nodes."""
        id = o
        if isinstance (o, node): id = o.id
        n = my.find_predecessor_index (id)
        diff = n - num
        if diff < 0:
            diff += len (my.nodes)
            if diff < n: diff = n
            return my.nodes[diff+1:] + my.nodes[:n+1]
        return my.nodes[diff+1:n+1]

    # Subclass and redefine these methods to produce more interesting
    # storage and repair behavior.
    def insert_block (my, id, block, size):
        """Basic insertion code to store insert_pieces() pieces on
        successors of key, via id.  Returns the successor."""
        if block not in my.blocks:
            my.blocks[block] = size
        succs = my.succ (block, my.insert_pieces ())
        isz   = my.insert_piece_size (size)
        for s in succs:
            s.store (block, isz)
        n = my.allnodes[id]
        n.nrpc += len (succs)
        n.sent_bytes += isz * len (succs)

        return succs[0]

    def _repair (my, an, succs, resp_blocks):
        desc = "failure"
        if an.alive: desc = "join"
        for b in resp_blocks:
            # Check their availability
            avail = 0
            fixer = None
            for s in succs:
                if b in s.blocks:
                    if fixer is None: fixer = s
                    avail += 1
            # Lazy repair waits until last possible moment.
            if avail == 0:
		# print "# LOST block", b, "after", desc, "of", an, "|", succs
		pass
            elif avail < my.min_pieces ():
		# print "# REPAIR block", b, "after", desc, "of", an
                isz = my.insert_piece_size (my.blocks[b])
                for s in succs:
                    if b not in s.blocks:
                        s.store (b, isz)
                        fixer.nrpc += 1
                        fixer.sent_bytes += isz

    # XXX How long to wait until we do repair?
    def repair (my, affected_node):
        count = my.insert_pieces ()
        preds = my.pred (affected_node, count)
        succs = my.succ (affected_node, count)
        # succ's does not include affected_node if it is dead.
        slice = preds + succs
	k = my.blocks.keys ()
	k.sort ()
        for i in range(1,len(slice) - count):
            p = slice[i - 1]
            s = slice[i:i+count]
	    if (p.id <= s[0].id):
		start = bisect.bisect_left (k, p.id)
		stop  = bisect.bisect_right (k, s[0].id)
		r = k[start:stop]
	    else:
		start = bisect.bisect_right (k, p.id)
		stop  = bisect.bisect_left  (k, s[0].id)
		r = k[start:] + k[:stop]
            my._repair (affected_node, s, r)
    
    def available_blocks (my):
	inserted = my.insert_pieces ()
        needed = my.read_pieces ()
	k = my.blocks.keys ()
	k.sort ()
	avail = 0
	succs = []
	for b in k:
	    extant = 0
	    if not succs or b > succs[0].id:
		succs = my.succ (b, inserted)
	    for s in succs:
		if b in s.blocks:
		    extant += 1
	    if extant >= needed:
		avail += 1
	return avail
	    
    def time_changed (my, last_time, new_time):
        for n in my.now_nodes:
            if n.alive:
                n.last_alive = last_time
            else:
                n.lifetime += last_time - n.last_alive
            my.repair (n)
        my.now_nodes = []
    
    # Subclass and redefine these methods to explore basic changes.
    def min_pieces (my):
        """The minimum number of pieces we need before repairing.
        Probably should be at least as big as read_pieces."""
        return 0
    def read_pieces (my):
        """The number of pieces on different nodes needed to for successful read."""
        return 0
    def insert_pieces (my):
        """The number of pieces to write into the system initially."""
        return 0
    def insert_piece_size (my, whole_size):
        """How big is each piece that gets inserted?"""
        return 0

class dhash_replica_norepair (dhash):
    def __init__ (my, replicas = 3):
        dhash.__init__ (my)
        my.bytes = 0
        my.replicas = replicas
    def min_pieces (my):
        return 0
    def read_pieces (my):
        return 1
    def insert_pieces (my):
        return my.replicas
    def insert_piece_size (my, size):
        return size

class dhash_replica (dhash_replica_norepair):
    def min_pieces (my):
        return my.replicas

class dhash_fragments (dhash):
    def __init__ (my, dfrags, efrags):
        dhash.__init__ (my)
        my.dfrags = dfrags
        my.efrags = efrags

    def min_pieces (my):
        # Should this by dfrags?
        return my.efrags
    def read_pieces (my):
        return my.dfrags
    def insert_pieces (my):
        return my.efrags
    def insert_piece_size (my, size):
        # A vague estimate of overhead from encoding... 2%-ish
        return int (1.02 * (size / my.dfrags))
                        
if __name__ == '__main__':
    gdh = dhash_replica_norepair()
    gdh.add_node (55)
    gdh.add_node (4)
    gdh.add_node (23)
    gdh.add_node (30)
    gdh.add_node (17)
    gdh.add_node (42)
    gdh.add_node (63)
    try:
        gdh.add_node (4)
        assert 0, "Should not allow duplicate insert!"
    except KeyError:
        pass

    # Make sure list is sorted
    start = 0
    for n in gdh.nodes:
        assert n.id > start
        start = n.id

    # Do blocks go to the right place?
    assert gdh.insert_block (73, 8192).id == 4
    assert gdh.insert_block (3, 8192).id == 4
    assert gdh.insert_block (4, 8192).id == 4
    assert gdh.insert_block (20, 8192).id == 23
    assert gdh.insert_block (56, 8192).id == 63

    assert gdh.find_predecessor_index (4) == 6
    assert gdh.find_predecessor_index (66) == 6
    assert gdh.find_predecessor_index (10) == 0
    assert gdh.find_predecessor_index (25) == 2

    assert len(gdh.succ(0, 3)) == 3
    assert len(gdh.succ(63, 3)) == 3
    assert len(gdh.succ(24, 3)) == 3
    assert len(gdh.succ(35, 3)) == 3

    assert gdh.pred (5).id == 4
    assert gdh.pred (31).id == 30
    assert gdh.pred (30).id == 23
    assert gdh.pred (3).id == 63
    assert len(gdh.pred(5, 3)) == 3

