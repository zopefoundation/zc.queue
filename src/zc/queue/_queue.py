from persistent import Persistent
from ZODB.ConflictResolution import PersistentReference
from ZODB.POSException import ConflictError
from zope import interface

from zc.queue import interfaces


class Queue(Persistent):

    interface.implements(interfaces.IQueue)

    def __init__(self):
        self._data = ()

    def pull(self, index=0):
        if index < 0:
            len_self = len(self._data)
            index += len_self
            if index < 0:
                raise IndexError(index - len_self)
        res = self._data[index]
        self._data = self._data[:index] + self._data[index + 1:]
        return res

    def put(self, item):
        self._data += (item,)

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, index):
        return self._data[index]  # works with passing a slice too

    def __nonzero__(self):
        return bool(self._data)

    def _p_resolveConflict(self, oldstate, committedstate, newstate):
        return resolveQueueConflict(
            oldstate, committedstate, newstate)


class BucketQueue(Queue):

    def _p_resolveConflict(self, oldstate, committedstate, newstate):
        return resolveQueueConflict(
            oldstate, committedstate, newstate, True)

PersistentQueue = BucketQueue  # for legacy instances, be conservative


class PersistentReferenceSet(object):
    """PersistentReferenceSet

    `ZODB.ConflictResolution.PersistentReference` doesn't get handled correctly
    in the resolveQueueConflict function due to lack of the `__hash__` method.
    So we make workaround here to utilize `__cmp__` method of
    `PersistentReference`.

    """
    def __init__(self, seq):
        assert isinstance(seq, tuple)
        self._data = self._dedup(seq)

    def _dedup(self, seq):
        seq = list(seq)
        cnt = 0
        while len(seq) > cnt:
            remove = []
            for idx, item in enumerate(seq[cnt + 1:]):
                try:
                    if item == seq[cnt]:
                        remove.append(cnt + idx + 1)
                except ValueError:
                    pass
            for idx in reversed(remove):
                seq.pop(idx)
            cnt += 1
        return tuple(seq)

    def __cmp__(self, other):
        if len(self._data) == len(other._data):
            other_data = list(other._data[:])
            for item in self._data:
                for index, other_item in enumerate(other_data):
                    try:
                        if item == other_item:
                            other_data.pop(index)
                    except ValueError:
                        pass
                    else:
                        break
                else:
                    break
            else:
                assert len(other_data) == 0
                return 0
        raise ValueError(
            "can't reliably compare against different "
            "PersistentReferences")

    def __sub__(self, other):
        self_data = list(self._data[:])
        for other_item in other._data:
            for index, item in enumerate(self_data):
                try:
                    if other_item == item:
                        self_data.pop(index)
                except ValueError:
                    pass
                else:
                    break
        return PersistentReferenceSet(tuple(self_data))

    def __and__(self, other):
        self_data = list(self._data[:])
        intersection = []
        for other_item in other._data:
            for index, item in enumerate(self_data):
                try:
                    if other_item == item:
                        self_data.pop(index)
                        intersection.append(item)
                except ValueError:
                    pass
                else:
                    break
        return PersistentReferenceSet(tuple(intersection))

    def __iter__(self):
        for item in self._data:
            yield item

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return "PRSet(%s)" % str(self._data)

    def __contains__(self, item):
        for data in self._data:
            try:
                if item == data:
                    return True
            except ValueError:
                pass
        return False


def resolveQueueConflict(oldstate, committedstate, newstate, bucket=False):
    # we only know how to merge _data.  If anything else is different,
    # puke.
    if set(committedstate.keys()) != set(newstate.keys()):
        print "ZCQUEUE WRONG ATTR"
        raise ConflictError  # can't resolve
    for key, val in newstate.items():
        if key != '_data' and val != committedstate[key]:
            print "ZCQUEUE ATTR DIFF"
            raise ConflictError  # can't resolve
    # basically, we are ok with anything--willing to merge--
    # unless committedstate and newstate have one or more of the
    # same deletions or additions in comparison to the oldstate.
    old = oldstate['_data']
    committed = committedstate['_data']
    new = newstate['_data']

    # If items in the queue are persistent object, we can't use set().
    # see 'queue.txt'
    for item in (old + committed + new):
        if not isinstance(item, PersistentReference):
            Set = set
            break
    else:
        Set = PersistentReferenceSet

    old_set = Set(old)
    committed_set = Set(committed)
    new_set = Set(new)

    if bucket and bool(old_set) and (bool(committed_set) ^ bool(new_set)):
        # This is a bucket, part of a CompositePersistentQueue.  The old set
        # of this bucket had items, and one of the two transactions cleaned
        # it out.  There's a reasonable chance that this bucket will be
        # cleaned out by the parent in one of the two new transactions.
        # We can't know for sure, so we take the conservative route of
        # refusing to be resolvable.
        print "ZCQUEUE EMPTYING BUCKET"
        raise ConflictError

    committed_added = committed_set - old_set
    committed_removed = old_set - committed_set
    new_added = new_set - old_set
    new_removed = old_set - new_set

    if new_removed & committed_removed:
        # they both removed (claimed) the same one.  Puke.
        print "ZCQUEUE BOTH REMOVED"
        raise ConflictError  # can't resolve
    elif new_added & committed_added:
        # they both added the same one.  Puke.
        print "ZCQUEUE BOTH ADDED"
        raise ConflictError  # can't resolve
    # Now we do the merge.  We'll merge into the committed state and
    # return it.
    mod_committed = []
    for v in committed:
        if v not in new_removed:
            mod_committed.append(v)
    if new_added:
        ordered_new_added = new[-len(new_added):]
        assert Set(ordered_new_added) == new_added
        mod_committed.extend(ordered_new_added)
    committedstate['_data'] = tuple(mod_committed)
    return committedstate


class CompositeQueue(Persistent):
    """Appropriate for queues that may become large.

    Using this queue has one advantage and two possible disadvantages.

    The advantage is that adding items to a large queue does not require
    writing the entire queue out to the database, since only one or two parts
    of it actually changes.  This can be a win for time, memory, and database
    size.

    One disadvantage is that multiple concurrent adds may intermix the adds in
    a surprising way: see queue.txt for more details.

    Another possible disadvantage is that this queue does not consistently
    enforce the policy that concurrent adds of the same item are not
    allowed: because one instance may go in two different composite buckets,
    the conflict resolution cannot look in both buckets to see that they were
    both added.

    If either of these are an issue, consider using the simpler PersistentQueue
    instead, foregoing the advantages of the composite approach.
    """

    # design note: one rejected strategy to try and enforce the
    # "concurrent adds of the same object are not allowed" policy is
    # to set a persistent flag on a queue when it reaches or exceeds
    # the target size, and to start a new bucket only on the following
    # transaction.  This would work in some scenarios, but breaks down
    # when two transactions happen sequentially *while* a third
    # transaction happens concurrently to both.

    interface.implements(interfaces.IQueue)

    def __init__(self, compositeSize=15, subfactory=BucketQueue):
        # the compositeSize value is a ballpark.  Because of the merging
        # policy, a composite queue might get as big as 2n under unusual
        # circumstances.  A better name for this might be "splitSize"...
        self.subfactory = subfactory
        self._data = ()
        self.compositeSize = compositeSize

    def __nonzero__(self):
        return bool(self._data)

    def pull(self, index=0):
        ct = 0
        if index < 0:
            len_self = len(self)
            rindex = index + len_self  # not efficient, but quick and easy
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
            if index < 0:  # not efficient, but quick and easy
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

CompositePersistentQueue = CompositeQueue  # legacy
