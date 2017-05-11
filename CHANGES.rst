=======
CHANGES
=======

2.0.0 (2017-05-11)
==================

- Dropped support for Python 2.6 and 3.3.

- Added support for Python 3.4, 3.5, 3.6 and PyPy.

- Fix using complex slices (e.g., negative strides) in
  ``CompositeQueue``. The cost is higher memory usage.


2.0.0a1 (2013-03-01)
====================

- Added support for Python 3.3.

- Replaced deprecated ``zope.interface.implements`` usage with equivalent
  ``zope.interface.implementer`` decorator.

- Dropped support for Python 2.4 and 2.5.

- Fixed an issue where slicing a composite queue would fail due to a
  programming error.
  [malthe]


1.3 (2012-01-11)
================

- Fixed a conflict resolution bug that didn't handle
  `ZODB.ConflictResolution.PersistentReference` correctly.
  Note that due to syntax we require Python 2.5 or higher now.


1.2.1 (2011-12-17)
==================

- Fixed ImportError in setup.py.
  [maurits]


1.2 (2011-12-17)
================

- Fixed undefined ZODB.POSException.StorageTransactionError in tests.

- Let tests pass with ZODB 3.8 and ZODB 3.9.

- Added test extra to declare test dependency on ``zope.testing``.

- Using Python's ``doctest`` module instead of deprecated
  ``zope.testing.doctest``.

- Clean up the generation of reST docs.


1.1
===

- Fixed a conflict resolution bug in CompositeQueue

- Renamed PersistentQueue to Queue, CompositePersistentQueue to
  CompositeQueue. The old names are nominally deprecated, although no
  warnings are generated and there are no current plans to eliminate
  them.  The PersistentQueue class has more conservative conflict
  resolution than it used to.  (The Queue class has the same conflict
  resolution as the PersistentQueue used to have.)

1.0.1
=====

- Minor buildout changes

- Initial release to PyPI

1.0
===

- Initial release to zope.org
