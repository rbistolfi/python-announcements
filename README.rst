#############
Announcements
#############

A python port of Announcements from Pharo Smalltalk


Overview
========

Announcements can be used to announce Events such as a button click or a state
change. It encodes events as classes (each event is represented by an
Announcement subclass.) Subscriptors to an announcement can be any callable.
Subscriptors can accept zero arguments (we call those "actions") one argument
(an instance of the Announcement is passed, you can use that instance to pass
relevant information to the subscriber), or two arguments (the Announcement
instance and the announcer are passed.)
A dummy example that subscribes a list append method to an event. Some data is
attached to the event instance:

    >>> class Event(Announcement):
    ...     pass
    >>> subscriber = []
    >>> announcer = Announcer()
    >>> announcer.subscribe(Event, send="append", to=subscriber)
    >>> newevent = Event()
    >>> newevent.usefullData = 42
    >>> announcer.announce(newevent)


TODO
====

* Thread safety - Subscriptions must be added, removed or executed in a thread
  safe manner.
* Error handling - St version handles errors in another process by passing the
  exception to the enclosing context after fork'ing.
* Convenience - Many methods in the ST version are not yet implemented. We
  just did enough for passing the Announcements-Core tests.


Note
====

This is a toy for now, you should probably use Blinker instead:
http://discorporate.us/projects/Blinker/.


