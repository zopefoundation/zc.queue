=================
Persistent Queues
=================

Persistent queues are simply queues that are optimized for persistency via the
ZODB. They assume that the ZODB is using MVCC to avoid read conflicts. They
attempt to resolve write conflicts so that transactions that add and remove
objects simultaneously are merged, unless the transactions are trying to
remove the same value from the queue.

An important characteristic of these queues is that they do not expect to
hold more than one reference to any given equivalent item at a time.  For
instance, some of the conflict resolution features will not perform
desirably if it is reasonable for your application to hold two copies of the
string "hello" within the same queue at once [#why]_.

The module provides two flavors: a simple persistent queue that keeps all
contained objects in one persistent object (`Queue`), and a
persistent queue that divides up its contents into multiple composite
elements (`CompositeQueue`). They should be equivalent in terms of
API and so are mostly examined in the abstract in this document: we'll generate
instances with a representative `Queue` factory, that could be either class.
They only differ in an aspect of their write conflict resolution behavior,
which is discussed below.

Queues can be instantiated with no arguments.

    >>> q = Queue()
    >>> from zc.queue.interfaces import IQueue
    >>> from zope.interface.verify import verifyObject
    >>> verifyObject(IQueue, q)
    True

The basic API is simple: use `put` to add items to the back of the queue, and
`pull` to pull things off the queue, defaulting to the front of the queue.
Note that `Item` could be either persistent or non persistent object.

    >>> q.put(Item(1))
    >>> q.put(Item(2))
    >>> q.pull()
    1
    >>> q.put(Item(3))
    >>> q.pull()
    2
    >>> q.pull()
    3

The `pull` method takes an optional zero-based index argument, and can accept
negative values.

    >>> q.put(Item(4))
    >>> q.put(Item(5))
    >>> q.put(Item(6))
    >>> q.pull(-1)
    6
    >>> q.pull(1)
    5
    >>> q.pull(0)
    4

Requesting an item from an empty queue raises an IndexError.

    >>> q.pull() # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    IndexError: ...

Requesting an invalid index value does the same.

    >>> q.put(Item(7))
    >>> q.put(Item(8))
    >>> q.pull(2) # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    IndexError: ...

Beyond these core queue operations, queues support len...

    >>> len(q)
    2
    >>> q.pull()
    7
    >>> len(q)
    1
    >>> q.pull()
    8
    >>> len(q)
    0

...iter (which does *not* empty the queue)...

    >>> next(iter(q))
    Traceback (most recent call last):
    ...
    StopIteration
    >>> q.put(Item(9))
    >>> q.put(Item(10))
    >>> q.put(Item(11))
    >>> next(iter(q))
    9
    >>> [i for i in q]
    [9, 10, 11]
    >>> q.pull()
    9
    >>> [i for i in q]
    [10, 11]

...bool...

    >>> bool(q)
    True
    >>> q.pull()
    10
    >>> q.pull()
    11
    >>> bool(q)
    False

...and list-like bracket access (which again does *not* empty the queue).

    >>> q.put(Item(12))
    >>> q[0]
    12
    >>> q.pull()
    12
    >>> q[0] # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    IndexError: ...
    >>> for i in range (13, 23):
    ...     q.put(Item(i))
    ...
    >>> q[0]
    13
    >>> q[1]
    14
    >>> q[2]
    15
    >>> q[-1]
    22
    >>> q[-10]
    13

That's it--there's no additional way to add anything beyond `put`, and no
additional way to remove anything beyond `pull`.

The only other wrinkle is the conflict resolution code.  Conflict
resolution in ZODB has some general caveats of which you should be aware
[#caveats]_.

These general caveats aside, we'll now examine some examples of zc.queue
conflict resolution at work.  To show this, we will have to have two
copies of the same queue, from two different connections.

NOTE: this testing approach has known weaknesses.  See discussion in tests.py.

    >>> import transaction
    >>> from zc.queue.tests import ConflictResolvingMappingStorage
    >>> from ZODB import DB
    >>> db = DB(ConflictResolvingMappingStorage('test'))
    >>> transactionmanager_1 = transaction.TransactionManager()
    >>> transactionmanager_2 = transaction.TransactionManager()
    >>> connection_1 = db.open(transaction_manager=transactionmanager_1)
    >>> root_1 = connection_1.root()

    >>> q_1 = root_1["queue"] = Queue()
    >>> transactionmanager_1.commit()

    >>> transactionmanager_2 = transaction.TransactionManager()
    >>> connection_2 = db.open(transaction_manager=transactionmanager_2)
    >>> root_2 = connection_2.root()
    >>> q_2 = root_2['queue']

Now we have two copies of the same queue, with separate transaction managers
and connections about the same way two threads would have them. The '_1'
suffix identifies the objects for user 1, in thread 1; and the '_2' suffix
identifies the objects for user 2, in a concurrent thread 2.

First, let's have the two users add some items to the queue concurrently.
For concurrent commits of only putting a single new item (one each in two
transactions), in both types of queue the user who commits first gets the
lower position in the queue--that is, the position that will leave the queue
sooner using default `pull` calls.

In this example, even though q_1 is modified first, q_2's transaction is
committed first, so q_2's addition is first after the merge.

    >>> q_1.put(Item(1001))
    >>> q_2.put(Item(1000))
    >>> transactionmanager_2.commit()
    >>> transactionmanager_1.commit()
    >>> connection_1.sync()
    >>> connection_2.sync()
    >>> list(q_1)
    [1000, 1001]
    >>> list(q_2)
    [1000, 1001]

For commits of more than one additions per connection of two, or of more than
two concurrent adding transactions, the behavior is the same for the
Queue: the first commit's additions will go before the second
commit's.

    >>> from zc import queue
    >>> if isinstance(q_1, queue.Queue):
    ...     for i in range(5):
    ...         q_1.put(Item(i))
    ...     for i in range(1002, 1005):
    ...         q_2.put(Item(i))
    ...     transactionmanager_2.commit()
    ...     transactionmanager_1.commit()
    ...     connection_1.sync()
    ...     connection_2.sync()
    ...

As we'll see below, that will again reliably put all the values from the first
commit earlier in the queue, to result in
[1000, 1001, 1002, 1003, 1004, 0, 1, 2, 3, 4].

For the CompositeQueue, the behavior is different.  The order
will be maintained with a set of additions in a transaction, but the values
may be merged between the two transactions' additions.  We will compensate
for that here to get a reliable queue state.

    >>> if isinstance(q_1, queue.CompositeQueue):
    ...     for i1, i2 in ((1002, 1003), (1004, 0), (1, 2), (3, 4)):
    ...         q_1.put(Item(i1))
    ...         q_2.put(Item(i2))
    ...         transactionmanager_1.commit()
    ...         transactionmanager_2.commit()
    ...         connection_1.sync()
    ...         connection_2.sync()
    ...

Whichever kind of queue we have, we now have the following values.

    >>> list(q_1)
    [1000, 1001, 1002, 1003, 1004, 0, 1, 2, 3, 4]
    >>> list(q_2)
    [1000, 1001, 1002, 1003, 1004, 0, 1, 2, 3, 4]

If two users try to add the same item, then a conflict error is raised.

    >>> five = Item(5)
    >>> q_1.put(five)
    >>> q_2.put(five)
    >>> transactionmanager_1.commit()
    >>> from ZODB.POSException import ConflictError, InvalidObjectReference
    >>> try:
    ...     transactionmanager_2.commit() # doctest: +ELLIPSIS
    ... except (ConflictError, InvalidObjectReference):
    ...     print("Conflict Error")
    Conflict Error
    >>> transactionmanager_2.abort()
    >>> connection_1.sync()
    >>> connection_2.sync()
    >>> list(q_1)
    [1000, 1001, 1002, 1003, 1004, 0, 1, 2, 3, 4, 5]
    >>> list(q_2)
    [1000, 1001, 1002, 1003, 1004, 0, 1, 2, 3, 4, 5]

Users can also concurrently remove items from a queue...

    >>> q_1.pull()
    1000
    >>> q_1[0]
    1001

    >>> q_2.pull(5)
    0
    >>> q_2[5]
    1

    >>> q_2[0] # 1000 value still there in this connection
    1000

    >>> q_1[4] # 0 value still there in this connection.
    0

    >>> transactionmanager_1.commit()
    >>> transactionmanager_2.commit()
    >>> connection_1.sync()
    >>> connection_2.sync()
    >>> list(q_1)
    [1001, 1002, 1003, 1004, 1, 2, 3, 4, 5]
    >>> list(q_2)
    [1001, 1002, 1003, 1004, 1, 2, 3, 4, 5]

...as long as they don't remove the same item.

    >>> q_1.pull()
    1001
    >>> q_2.pull()
    1001
    >>> transactionmanager_1.commit()
    >>> transactionmanager_2.commit() # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    ConflictError: ...
    >>> transactionmanager_2.abort()
    >>> connection_1.sync()
    >>> connection_2.sync()
    >>> list(q_1)
    [1002, 1003, 1004, 1, 2, 3, 4, 5]
    >>> list(q_2)
    [1002, 1003, 1004, 1, 2, 3, 4, 5]

There's actually a special case: the composite queue's buckets will refuse to
merge if they started with a non-empty state, and one of the two new states
is empty.  This is to prevent the loss of an addition to the queue.  See
tests.py for an example.

Also importantly, users can concurrently remove and add items to a queue.

    >>> q_1.pull()
    1002
    >>> q_1.pull()
    1003
    >>> q_1.pull()
    1004
    >>> q_2.put(Item(6))
    >>> q_2.put(Item(7))
    >>> transactionmanager_1.commit()
    >>> transactionmanager_2.commit()
    >>> connection_1.sync()
    >>> connection_2.sync()
    >>> list(q_1)
    [1, 2, 3, 4, 5, 6, 7]
    >>> list(q_2)
    [1, 2, 3, 4, 5, 6, 7]

As a final example, we'll show the conflict resolution code under extreme
duress, with multiple simultaneous puts and pulls.

    >>> res_1 = []
    >>> for i in range(6, -1, -2):
    ...     res_1.append(q_1.pull(i))
    ...
    >>> res_1
    [7, 5, 3, 1]
    >>> res_2 = []
    >>> for i in range(5, 0, -2):
    ...     res_2.append(q_2.pull(i))
    ...
    >>> res_2
    [6, 4, 2]
    >>> for i in range(8, 12):
    ...     q_1.put(Item(i))
    ...
    >>> for i in range(12, 16):
    ...     q_2.put(Item(i))
    ...
    >>> list(q_1)
    [2, 4, 6, 8, 9, 10, 11]
    >>> list(q_2)
    [1, 3, 5, 7, 12, 13, 14, 15]
    >>> transactionmanager_1.commit()
    >>> transactionmanager_2.commit()
    >>> connection_1.sync()
    >>> connection_2.sync()

After these commits, if the queue is a Queue, the new values are
in the order of their commit.  However, as discussed above, if the queue is
a CompositeQueue the behavior is different. While the order will be
maintained comparitively--so if object `A` is ahead of object `B` in the queue
on commit then `A` will still be ahead of `B` after a merge of the conflicting
transactions--values may be interspersed between the two transactions.

For instance, if our example queue were a Queue, the values would
be [8, 9, 10, 11, 12, 13, 14, 15].  However, if it were a
CompositeQueue, the values might be the same, or might be any
combination in which [8, 9, 10, 11] and [12, 13, 14, 15], from the two
transactions, are still in order.  One ordering might be
[8, 9, 12, 13, 10, 11, 14, 15], for instance.

    >>> if isinstance(q_1, queue.Queue):
    ...     res_1 = list(q_1)
    ...     res_2 = list(q_2)
    ... elif isinstance(q_1, queue.CompositeQueue):
    ...     firstsrc_1 = list(q_1)
    ...     firstsrc_2 = list(q_2)
    ...     secondsrc_1 = firstsrc_1[:]
    ...     secondsrc_2 = firstsrc_2[:]
    ...     for val in [12, 13, 14, 15]:
    ...         firstsrc_1.remove(Item(val))
    ...         firstsrc_2.remove(Item(val))
    ...     for val in [8, 9, 10, 11]:
    ...         secondsrc_1.remove(Item(val))
    ...         secondsrc_2.remove(Item(val))
    ...     res_1 = firstsrc_1 + secondsrc_1
    ...     res_2 = firstsrc_2 + secondsrc_2
    ...
    >>> res_1
    [8, 9, 10, 11, 12, 13, 14, 15]
    >>> res_2
    [8, 9, 10, 11, 12, 13, 14, 15]

    >>> db.close() # cleanup


========================
PersistentReferenceProxy
========================

As `ZODB.ConflictResolution.PersistentReference` doesn't get handled
properly in `set` due to lack of `__hash__` method, we define a class
utilizing `__cmp__` method of contained items [#workaround]_.


Let's make some stub persistent reference objects. Also make some
objects that have same oid to simulate different transaction states.

    >>> from zc.queue.tests import StubPersistentReference
    >>> pr1 = StubPersistentReference(1)
    >>> pr2 = StubPersistentReference(2)
    >>> pr3 = StubPersistentReference(3)
    >>> pr_c1 = StubPersistentReference(1)
    >>> pr_c2 = StubPersistentReference(2)
    >>> pr_c3 = StubPersistentReference(3)

    >>> pr1 == pr_c1
    True
    >>> pr2 == pr_c2
    True
    >>> pr3 == pr_c3
    True
    >>> id(pr1) == id(pr_c1)
    False
    >>> id(pr2) == id(pr_c2)
    False
    >>> id(pr3) == id(pr_c3)
    False

    >>> set1 = set((pr1, pr2))
    >>> set1
    set([SPR (1), SPR (2)])
    >>> len(set1)
    2
    >>> set2 = set((pr_c1, pr_c3))
    >>> set2
    set([SPR (1), SPR (3)])
    >>> len(set2)
    2
    >>> set_c1 = set((pr_c1, pr_c2))
    >>> set_c1
    set([SPR (1), SPR (2)])
    >>> len(set_c1)
    2

`set` doesn't handle persistent reference objects properly. All
following set operations produce wrong results.

Deduplication (notice that for items longer than length two we're only
checking the length and contents, not the ordering of the
representation, because that varies among different versions of Python):

    >>> set((pr1, pr_c1))
    set([SPR (1), SPR (1)])
    >>> set((pr2, pr_c2))
    set([SPR (2), SPR (2)])
    >>> set4 = set((pr1, pr_c1, pr2))
    >>> len(set4)
    3
    >>> pr1 in set4 and pr_c1 in set4 and pr2 in set4
    True
    >>> set4 = set((pr1, pr2, pr3, pr_c1, pr_c2, pr_c3))
    >>> len(set4)
    6

Minus operation:

    >>> set3 = set1 - set2
    >>> len(set3)
    2
    >>> set3
    set([SPR (1), SPR (2)])

Contains:

    >>> pr3 in set2
    False

Intersection:

    >>> set1 & set2
    set([])

Compare:

    >>> set1 == set_c1
    False

So we made `PersistentReferenceProxy` wrapping `PersistentReference`
to work with sets.

    >>> from zc.queue._queue import PersistentReferenceProxy
    >>> prp1 = PersistentReferenceProxy(pr1)
    >>> prp2 = PersistentReferenceProxy(pr2)
    >>> prp3 = PersistentReferenceProxy(pr3)
    >>> prp_c1 = PersistentReferenceProxy(pr_c1)
    >>> prp_c2 = PersistentReferenceProxy(pr_c2)
    >>> prp_c3 = PersistentReferenceProxy(pr_c3)
    >>> prp1 == prp_c1
    True
    >>> prp2 == prp_c2
    True
    >>> prp3 == prp_c3
    True
    >>> id(prp1) == id(prp_c1)
    False
    >>> id(prp2) == id(prp_c2)
    False
    >>> id(prp3) == id(prp_c3)
    False

    >>> set1 = set((prp1, prp2))
    >>> set1
    set([SPR (1), SPR (2)])
    >>> len(set1)
    2
    >>> set2 = set((prp_c1, prp_c3))
    >>> set2
    set([SPR (1), SPR (3)])
    >>> len(set2)
    2
    >>> set_c1 = set((prp_c1, prp_c2))
    >>> set_c1
    set([SPR (1), SPR (2)])
    >>> len(set_c1)
    2

`set` handles persistent reference properly now. All following set
operations produce correct results.

Deduplication:

    >>> set4 = set((prp1, prp2, prp3, prp_c1, prp_c2, prp_c3))
    >>> len(set4)
    3
    >>> set((prp1, prp_c1))
    set([SPR (1)])
    >>> set((prp2, prp_c2))
    set([SPR (2)])
    >>> set((prp1, prp_c1, prp2))
    set([SPR (1), SPR (2)])

Minus operation:

    >>> set3 = set1 - set2
    >>> len(set3)
    1
    >>> set3
    set([SPR (2)])
    >>> set1 - set1
    set([])
    >>> set2 - set3
    set([SPR (1), SPR (3)])
    >>> set3 - set2
    set([SPR (2)])

Contains:

    >>> prp3 in set2
    True
    >>> prp1 in set2
    True
    >>> prp_c1 in set2
    True
    >>> prp2 not in set2
    True

Intersection:

    >>> set1 & set2
    set([SPR (1)])
    >>> set1 & set_c1
    set([SPR (1), SPR (2)])
    >>> set2 & set3
    set([])

Compare:

    >>> set1 == set_c1
    True
    >>> set1 == set2
    False
    >>> set1 == set4
    False


-----

.. [#why] The queue's `pull` method is actually the interesting part in why
    this constraint is used, and it becomes more so when you allow an
    arbitrary pull.  By asserting that you do not support having equal
    items in the queue at once, you can simply say that when you remove
    equal objects in the current state and the contemporary, conflicting
    state, it's a conflict error.  Ideally you don't enter another equal
    item in that queue again, or else in fact this is still an
    error-prone heuristic:

      - start queue == [X];
      - begin transactions A and B;
      - B removes X and commits;
      - transaction C adds X and Y and commits;
      - transaction A removes X and tries to commit, and conflict resolution
        code believes that it is ok to remove the new X from transaction C
        because it looks like it was just an addition of Y).  Commit succeeds,
        and should not.

    If you don't assert that you can use equality to examine conflicts,
    then you have to come up with another heuristic.  Given that the
    conflict resolution code only gets three states to resolve, I don't
    know of a reliable one.

    Therefore, zc.queue has a policy of assuming that it can use
    equality to distinguish items.  It's limiting, but the code can have
    a better confidence of doing the right thing.

    Also, FWIW, this is policy I want: for my use cases, it would be
    possible to put in two items in a queue that handle the same issue.
    With the right equality code, this can be avoided with the policy
    the queue has now.

.. [#caveats] Here are a few caveats about the state (as of this
    writing) of ZODB conflict resolution in general.

    The biggest is that, if you store persistent.Persistent subclass
    objects in a queue (or any other collection with conflict resolution
    code, such as a BTree), the collection will get a placeholder object
    (ZODB.ConflictResolution.PersistentReference), rather than the real
    contained object.  This object has __cmp__ method, but doesn't have
    __hash__ method, The same oid will get different placeholder in the
    different states because of different identity in memory (e.g. `id(obj)`)
    for conflict resolution, which is wrong behavior in a queue.

    Another is that, in ZEO, conflict resolution is currently done on
    the server, so the ZEO server must have a copy of the classes
    (software) necessary to instantiate any non-persistent object in the
    collection.

    A corollary to the above is that objects such as
    zope.app.keyreference.persistent, which are not persistent
    themselves but rely on a persistent object for their __cmp__, will
    fail during conflict resolution.  A reasonable solution in the case
    of zope.app.keyreference.persistent code is to have the object store
    the information it needs to do the comparison on itself, so the
    absence of the persistent object during conflict resolution is
    unimportant.

.. [#workaround] The reason why we defined
    `PersistentReferenceProxy` is that there would be a significant risk
    of unintended consequenses for some ZODB users if we add __hash__
    method to PersistentReference.
