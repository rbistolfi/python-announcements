# -*- coding: utf8 -*-


"""A python port of Announcements from Pharo Smalltalk


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

"""


__all__ = [ "Announcement", "Announcer" ]
__author__ = "rbistolfi"
__date__ = 2012


import types
import inspect
import threading
import weakref


class AnnouncementMeta(type):
    """A metaclass giving support for addition to its classes

    """
    def __add__(cls, announcementClass):
        return AnnouncementSet(cls, announcementClass)


class Announcement(object):
    """This class is the superclass for events that someone might want to
    announce, such as a button click or an attribute change. Typically you
    create subclasses for your own events you want to announce.

    """
    __metaclass__ = AnnouncementMeta

    def __eq__(self, other):
        #XXX Since any event is encoded as a *class* (actually a subclass of
        #    Announcement, or an Announcement like object), the type is what
        #    really matters here. Two events are equivalent if they are of
        #    the same type.
        return type(self) == type(other)

    @staticmethod
    def asAnnouncement(obj):
        #XXX This method will be called sometimes from the class side and
        #    sometimes from the instance side. I guess it should be static.
        #    We cant make a class and an instance method with the same name,
        #    bummer. Use this like: obj.asAnnouncement(obj)
        if inspect.isclass(obj):
            return obj()
        else:
            return obj

    @classmethod
    def handles(cls, announcementClass):
        return announcementClass is cls or issubclass(announcementClass, cls)


class AnnouncementSet(object):
    """This is a set for Announcements. An instance is created when
    Announcements are added with the "+" operator. It knows what kind of events
    its elements can handle.

    """
    def __init__(self, *announcements):
        """Create a set from the arguments tuple

        """
        super(AnnouncementSet, self).__init__()
        self.announcements = set(announcements)

    def __add__(self, announcementClass):
        """Add announcementClass to the announcements set

        """
        self.add(announcementClass)
        return self

    def __repr__(self):
        return "<%s(%s)>" % (type(self).__name__,
                repr(self.announcements)[4:-1])

    def __len__(self):
        return len(self.announcements)

    def __getattr__(self, name):
        return getattr(self.announcements, name)

    def handles(self, announcementClass):
        """We can handle an announcement if any of the elements in the
        announcements set can handle it

        """
        return any(i.handles(announcementClass) for i in self.announcements)


class Announcer(object):
    """The code is based on the announcements as described by Vassili Bykov in
    http://www.cincomsmalltalk.com/userblogs/vbykov/.
    The implementation uses a threadsafe subscription registry, in the sense
    that registering, unregistering, and announcing from an announcer at the
    same time in different threads should never cause failures.
    This Python version is based in the Pharo Smalltalk implementation.
    Btw, thread-safety is in the TODO

    """
    def __init__(self):
        super(Announcer, self).__init__()
        self.registry = SubscriptionRegistry()

    def announce(self, announcement):
        announcement = announcement.asAnnouncement(announcement)
        if self.registry:
            self.registry.deliver(announcement)
        return announcement

    def subscribe(self, announcementClass, do=None, send=None, to=None):
        """Declare that when announcementClass is raised, do is
        executed. The do and send/to keyword arguments are mutually exclusive,
        you can't provide both do and send.
        Python detail: we cant overlap message names like in st, as in
        subscribe:do: and subscribe:send:to:. I choosed to implement all of them
        as kwargs, the other option was to do subscribeDo and subscribeSendTo.
        My taste picked the first one.

        """
        assert not (do and (send or to)), "The keywords do and send/to are "\
                "mutually exclusive, you can not provide both"

        if send:
            do = getattr(to, send)

        subscription = AnnouncementSubscription()
        subscription.announcer = self
        subscription.announcementClass = announcementClass
        #XXX Original uses #valuable instead #action and #subscriber
        subscription.action = do
        subscription.subscriber = to or do
        return self.registry.add(subscription)

    def on(self, announcementClass, do=None):
        """Declare that when announcementClass is raised, do is
        executed

        """
        return self.subscribe(announcementClass, do=do)

    def replace(self, subscription, newOne):
        return self.registry.replace(subscription, newOne)

    def removeSubscription(self, subscription):
        return self.registry.remove(subscription)

    def unsubscribe(self, subscriber):
        return self.registry.removeSubscriber(subscriber)


class AnnouncementSubscription(object):
    """The subscription is a single entry in a SubscriptionRegistry.
    Several subscriptions by the same object is possible.

    """
    def __init__(self):
        super(AnnouncementSubscription, self).__init__()
        self.announcer = None
        self.announcementClass = None
        self.subscriber = None
        self.action = None

    @property
    def valuable(self):
        return self.action

    @valuable.setter
    def valuable(self, valuable):
        """This can be used when the subscriber needs to be extracted from the
        action (for example, when the action is an instance method, then the
        subscriber is the instance owning that method.)

        """
        self.action = valuable
        if self.isMethod():
            self.subscriber = valuable.im_self
        else:
            self.subscriber = valuable

    def deliver(self, announcement):
        """Deliver an announcement to receiver. In case of failure, it will be
        handled in separate process

        """
        if self.handles(type(announcement)):
            argumentsCount = self.getArgumentsCount()
            if argumentsCount == 0:
                self.action()
            elif argumentsCount == 1:
                self.action(announcement)
            elif argumentsCount == 2:
                self.action(announcement, self.announcer)
            else:
                raise TypeError("Incompatible signature")

    def makeStrong(self):
        """I am already strong, do nothing

        """
        return self

    def makeWeak(self):
        """Create a weak subscription equivalent to self and return it

        """
        #XXX Use http://code.activestate.com/recipes/81253/
        subscription = WeakAnnouncementSubscription()
        subscription.announcer = self.announcer
        subscription.announcementClass = self.announcementClass
        subscription.subscriber = self.subscriber
        subscription.action = self.action
        subscription.subscriber.__announcementsIm = self.action
        self.announcer.replace(self, subscription)
        return subscription

    def handles(self, announcementClass):
        """Return true if self.announcementClass can handle it

        """
        return self.announcementClass.handles(announcementClass)

    #XXX Python specific methods

    def getArgumentsCount(self):
        """Returns the number of arguments a function takes

        """
        count = len(inspect.getargspec(self.action).args)
        if self.isMethod():
            return count - 1 # self is passed automatically
        else:
            return count

    def isMethod(self):
        """Returns True if self.action is a method

        """
        return isinstance(self.action, (types.MethodType,
            types.BuiltinMethodType))


class WeakAnnouncementSubscription(AnnouncementSubscription):
    """A WeakAnnouncementSubscription is a subscription which is removed
    automatically when the subscriber is unreferenced.
    To switch between subscription types, use makeStrong/makeWeak on the
    subscription returned when initially registering with announcer.

    """
    def __init__(self):
        #super(WeakAnnouncementSubscription, self).__init__()
        self.weaksubscription = None
        self.weakaction = None

    @property
    def subscriber(self):
        return self.weaksubscription()

    @subscriber.setter
    def subscriber(self, subscription):
        self.weaksubscription = weakref.ref(subscription, self.finalize)

    @property
    def action(self):
        return self.weakaction()

    @action.setter
    def action(self, valuable):
        self.weakaction = weakref.ref(valuable, self.finalize)

    def finalize(self, wr):
        print "Finalizing", wr
        self.announcer.removeSubscription(self)

    def makeStrong(self):
        """Create a strong subscription equivalent to self and return it

        """
        subscription = AnnouncementSubscription()
        subscription.announcer = self.announcer
        subscription.announcementClass = self.announcementClass
        subscription.subscriber = self.subscriber
        subscription.action = self.action
        self.announcer.replace(self, subscription)
        return subscription

    def makeWeak(self):
        """We are already weak, do nothing

        """
        return self


class SubscriptionRegistry(object):
    """The subscription registry is a threadsafe storage for the subscriptions
    to an Announcer.

    """
    def __init__(self, lock=None):
        super(SubscriptionRegistry, self).__init__()
        self.subscriptions = set()
        self.lock = lock or threading.Lock()

    def __len__(self):
        return len(self.subscriptions)

    def numberOfSubscriptions(self):
        return len(self)

    def reset(self):
        self.subscriptions = set()

    def add(self, subscription):
        with self.protected():
            self.subscriptions.add(subscription)
        return subscription

    def remove(self, subscription):
        with self.protected():
            if subscription in self.subscriptions:
                self.subscriptions.remove(subscription)

    def removeSubscriber(self, subscriber):
        with self.protected():
            subscriptions = list(self.subscriptions)
            for subscription in subscriptions:
                if subscription.subscriber == subscriber:
                    self.subscriptions.remove(subscription)

    def replace(self, subscription, newOne):
        """Note that it will signal an error if subscription is not there

        """
        with self.protected():
            self.subscriptions.remove(subscription)
            self.subscriptions.add(newOne)
        return newOne

    def deliver(self, announcement):
        with self.protected():
            subscriptions = list(self.subscriptions)
        self.deliverTo(announcement, subscriptions)

    def deliverTo(self, announcement, subscriptions):
        """Ensure all the subscriptions are delivered even if some fail. If an
        exception is raised, catch it, continue delivering messages and only when
        all the messages are delivered re-raise with the original context.

        """
        #XXX there is no tco
        for index, subscription in enumerate(subscriptions):
            try:
                subscription.deliver(announcement)
            except:
                self.deliverTo(announcement, subscriptions[index+1:])
                raise

    def subscriptionsOf(self, subscriber, do):
        with self.protected():
            subscriptions = self.subscriptions
        for subscription in subscriptions:
            if subscription.subscriber == subscriber:
                do(subscription)

    def protected(self):
        """Context manager providing thread safe block execution

        """
        #XXX
        return self.lock
