from ZODB import ConflictResolution, MappingStorage, POSException
from persistent import Persistent
import doctest
import unittest
import zc.queue

# TODO: this approach is useful, but fragile.  It also puts a dependency in
# this package on the ZODB, when otherwise it would only depend on persistent.
#
# Other discussed testing approaches include passing values explicitly to the
# queue's conflict resolution code, and having a simple database implemented in
# the persistent package.
#
# This approach is arguably useful in two ways.  First, it confirms that the
# conflict resolution code performs as expected in the desired environment,
# the ZODB.  Second, in the doctest it shows real examples of the queue usage,
# with transaction managers and all: this gives a clearer picture of the
# full context in which this conflict resolution code must dance.


class ConflictResolvingMappingStorage_38(
    MappingStorage.MappingStorage,
    ConflictResolution.ConflictResolvingStorage):

    def __init__(self, name='ConflictResolvingMappingStorage'):
        MappingStorage.MappingStorage.__init__(self, name)
        self._old = {}

    def loadSerial(self, oid, serial):
        self._lock_acquire()
        try:
            old_info = self._old[oid]
            try:
                return old_info[serial]
            except KeyError:
                raise POSException.POSKeyError(oid)
        finally:
            self._lock_release()

    def store(self, oid, serial, data, version, transaction):
        if transaction is not self._transaction:
            raise POSException.StorageTransactionError(self, transaction)

        if version:
            raise POSException.Unsupported("Versions aren't supported")

        self._lock_acquire()
        try:
            if oid in self._index:
                oserial = self._index[oid][:8]
                if serial != oserial:
                    rdata = self.tryToResolveConflict(
                        oid, oserial, serial, data)
                    if rdata is None:
                        raise POSException.ConflictError(
                            oid=oid, serials=(oserial, serial), data=data)
                    else:
                        data = rdata
            self._tindex[oid] = self._tid + data
        finally:
            self._lock_release()
        return self._tid

    def _finish(self, tid, user, desc, ext):
        self._index.update(self._tindex)
        self._ltid = self._tid
        for oid, record in self._tindex.items():
            self._old.setdefault(oid, {})[self._tid] = record[8:]


class ConflictResolvingMappingStorage_39(
    MappingStorage.MappingStorage,
    ConflictResolution.ConflictResolvingStorage):

    def store(self, oid, serial, data, version, transaction):
        assert not version, "Versions are not supported"
        if transaction is not self._transaction:
            raise POSException.StorageTransactionError(self, transaction)

        old_tid = None
        tid_data = self._data.get(oid)
        if tid_data:
            old_tid = tid_data.maxKey()
            if serial != old_tid:
                rdata = self.tryToResolveConflict(
                    oid, old_tid, serial, data)
                if rdata is None:
                    raise POSException.ConflictError(
                        oid=oid, serials=(old_tid, serial), data=data)
                else:
                    data = rdata
        self._tdata[oid] = data
        return self._tid


if hasattr(MappingStorage.MappingStorage, '_finish'):
    # ZODB 3.8
    ConflictResolvingMappingStorage = ConflictResolvingMappingStorage_38
else:
    ConflictResolvingMappingStorage = ConflictResolvingMappingStorage_39


def test_deleted_bucket():
    """As described in ZODB/ConflictResolution.txt, you need to be very
    careful of objects that are composites of other persistent objects.
    Without careful code, the following situation can cause an item in the
    queue to be lost.

        >>> import transaction # setup...
        >>> from ZODB import DB
        >>> db = DB(ConflictResolvingMappingStorage('test'))
        >>> transactionmanager_1 = transaction.TransactionManager()
        >>> transactionmanager_2 = transaction.TransactionManager()
        >>> connection_1 = db.open(transaction_manager=transactionmanager_1)
        >>> root_1 = connection_1.root()

        >>> q_1 = root_1["q"] = zc.queue.CompositeQueue()
        >>> q_1.put(1)
        >>> transactionmanager_1.commit()

        >>> transactionmanager_2 = transaction.TransactionManager()
        >>> connection_2 = db.open(transaction_manager=transactionmanager_2)
        >>> root_2 = connection_2.root()
        >>> q_2 = root_2["q"]
        >>> q_1.pull()
        1
        >>> q_2.put(2)
        >>> transactionmanager_2.commit()
        >>> transactionmanager_1.commit() # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        ConflictError: ...

    Without the behavior, the queue would be empty!

    With a simple queue, this will merge normally.

        >>> transactionmanager_1.abort()
        >>> q_1 = root_1["q"] = zc.queue.Queue()
        >>> q_1.put(1)
        >>> transactionmanager_1.commit()

        >>> transactionmanager_2 = transaction.TransactionManager()
        >>> connection_2 = db.open(transaction_manager=transactionmanager_2)
        >>> root_2 = connection_2.root()
        >>> q_2 = root_2["q"]
        >>> q_1.pull()
        1
        >>> q_2.put(2)
        >>> transactionmanager_2.commit()
        >>> transactionmanager_1.commit()
        >>> list(q_1)
        [2]

    """


def test_legacy():
    """We used to promote the names PersistentQueue and
    CompositePersistentQueue as the expected names for the classes in this
    package.  They are now shortened, but the older names should stay
    available in _queue in perpetuity.

        >>> import zc.queue._queue
        >>> zc.queue._queue.BucketQueue is zc.queue.PersistentQueue
        True
        >>> zc.queue.CompositeQueue is zc.queue.CompositePersistentQueue
        True

    """


class StubPersistentReference(ConflictResolution.PersistentReference):
    def __init__(self, oid):
        self.oid = oid

    def __cmp__(self, other):
        if self.oid == other.oid:
            return 0
        else:
            raise ValueError("Can't compare")

    def __repr__(self):
        return "SPR (%d)" % self.oid


class PersistentObject(Persistent):
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return self.value == other.value

    def __repr__(self):
        return "%s" % self.value


def test_suite():
    return unittest.TestSuite((
        doctest.DocFileSuite(
            'queue.txt',
            globs={
                'Queue': zc.queue.Queue,
                'Item': PersistentObject}),
        doctest.DocFileSuite(
            'queue.txt',
            globs={
                'Queue': lambda: zc.queue.CompositeQueue(2),
                'Item': PersistentObject}),
        doctest.DocFileSuite(
            'queue.txt',
            globs={
                'Queue': zc.queue.Queue,
                'Item': lambda x: x}),
        doctest.DocFileSuite(
            'queue.txt',
            globs={
                'Queue': lambda: zc.queue.CompositeQueue(2),
                'Item': lambda x: x}),
        doctest.DocTestSuite()
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
