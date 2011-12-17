from persistent.interfaces import IPersistent


class IQueue(IPersistent):
    def put(item):
        """Put an item on the end of the queue.

        Item must be persistable (picklable)."""

    def pull(index=0):
        """Remove and return an item, by default from the front of the queue.

        Raise IndexError if index does not exist.
        """

    def __len__():
        """Return len of queue"""

    def __iter__():
        """Iterate over contents of queue"""

    def __getitem__(index):
        """return item at index, or slice"""

    def __nonzero__():
        """return True if the queue contains more than zero items, else False.
        """
