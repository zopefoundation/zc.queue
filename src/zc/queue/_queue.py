
from persistent import Persistent
from ZODB.POSException import ConflictError
from zope import interface

from zc.queue import interfaces

class PersistentQueue(Persistent):

    interface.implements(interfaces.IQueue)

    def __init__(self):
        self._data = ()

    def pull(self, index=0):
        if index < 0:
            len_self = len(self._data)
            index += len_self
            if index < 0:
                raise IndexError(index-len_self)
        res = self._data[index]
        self._data = self._data[:index] + self._data[index+1:]
        return res

    def put(self, item):
        self._data += (item,)

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, index):
        return self._data[index] # works with passing a slice too

    def __nonzero__(self):
        return bool(self._data)

    def _p_resolveConflict(self, oldstate, committedstate, newstate):
        return resolveQueueConflict(oldstate, committedstate, newstate)

def resolveQueueConflict(oldstate, committedstate, newstate):
    # we only know how to merge _data.  If anything else is different,
    # puke.
    if set(committedstate.keys()) != set(newstate.keys()):
        raise ConflictError
    for key, val in newstate.items():
        if key != '_data' and val != committedstate[key]:
            raise ConflictError
    # basically, we are ok with anything--willing to merge--
    # unless committedstate and newstate have one or more of the
    # same *deletions* from the oldstate.
    old = oldstate['_data']
    committed = committedstate['_data']
    new = newstate['_data']

    old_set = set(old)
    committed_set = set(committed)
    new_set = set(new)

    committed_added = committed_set - old_set
    committed_removed = old_set - committed_set
    new_added = new_set - old_set
    new_removed = old_set - new_set

    if new_removed & committed_removed:
        # they both removed (claimed) the same one.  Puke.
        raise ConflictError
    elif new_added & committed_added:
        # they both added the same one.  Puke.
        raise ConflictError
    # Now we do the merge.  We'll merge into the committed state and
    # return it.
    mod_committed = []
    for v in committed:
        if v not in new_removed:
            mod_committed.append(v)
    if new_added:
        ordered_new_added = new[-len(new_added):]
        assert set(ordered_new_added) == new_added
        mod_committed.extend(ordered_new_added)
    committedstate['_data'] = tuple(mod_committed)
    return committedstate

class CompositePersistentQueue(Persistent):
    """Appropriate for queues that may become large"""

    interface.implements(interfaces.IQueue)

    def __init__(self, compositeSize=15, subfactory=PersistentQueue):
        # the compositeSize value is a ballpark.  Because of the merging
        # policy, a composite queue might get as big as 2n under unusual
        # circumstances.
        self.subfactory = subfactory
        self._data = ()
        self.compositeSize = compositeSize

    def __nonzero__(self):
        return bool(self._data)

    def pull(self, index=0):
        ct = 0
        if index < 0:
            len_self = len(self)
            rindex = index + len_self # not efficient, but quick and easy
            if rindex < 0:
                raise IndexError(index)
        else:
            rindex = index
        for cix, q in enumerate(self._data):
            for ix, item in enumerate(q):
                if rindex == ct:
                    q.pull(ix)
                    # take this opportunity to weed out empty
                    # composite queues that may have been introduced
                    # by conflict resolution merges or by this pull.
                    self._data = tuple(q for q in self._data if q)
                    return item
                ct += 1
        raise IndexError(index)

    def put(self, item):
        if not self._data:
            self._data = (self.subfactory(),)
        last = self._data[-1]
        if len(last) >= self.compositeSize:
            last = self.subfactory()
            self._data += (last,)
        last.put(item)

    def __len__(self):
        res = 0
        for q in self._data:
            res += len(q)
        return res

    def __iter__(self):
        for q in self._data:
            for i in q:
                yield i

    def __getitem__(self, index):
        if isinstance(index, slice):
            start, stop, stride = slice.indices(len(self))
            res = []
            stride_ct = 1
            for ix, v in enumerate(self):
                if ix >= stop:
                    break
                if ix < start:
                    continue
                stride_ct -= 1
                if stride_ct == 0:
                    res.append(v)
                    stride_ct = stride
            return res
        else:
            if index < 0: # not efficient, but quick and easy
                len_self = len(self)
                rindex = index + len_self
                if rindex < 0:
                    raise IndexError(index)
            else:
                rindex = index
            for ix, v in enumerate(self):
                if ix == rindex:
                    return v
            raise IndexError(index)

    def _p_resolveConflict(self, oldstate, committedstate, newstate):
        return resolveQueueConflict(oldstate, committedstate, newstate)

