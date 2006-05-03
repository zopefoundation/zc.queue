import unittest
from zope.testing import doctest, module
from ZODB import ConflictResolution, MappingStorage, POSException

from zc import queue

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

class ConflictResolvingMappingStorage(
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

def test_suite():
    return unittest.TestSuite((
        doctest.DocFileSuite(
            'queue.txt', globs={'Queue':queue.PersistentQueue}),
        doctest.DocFileSuite(
            'queue.txt',
            globs={'Queue':lambda: queue.CompositePersistentQueue(2)}),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
