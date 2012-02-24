# -*- coding: utf8 -*-


"""Tests for Python-Announcements

"""


import unittest
import gc
from .core import *


class AnnouncementMockA(Announcement):
    """This is a simple test mock.

    """
    pass


class AnnouncementMockB(Announcement):
    """This is a simple test mock.

    """
    pass


class AnnouncementMockC(AnnouncementMockB):
    """This is a simple test mock.

    """
    pass


class AnnouncementSetTest(unittest.TestCase):

    def testIncludeOnlyOnce(self):
        ann_set = AnnouncementMockA + AnnouncementMockB + AnnouncementMockA
        self.assertEqual(len(ann_set), 2)

    def testInstanceCreation(self):
        ann_set = AnnouncementMockA + AnnouncementMockB
        self.assertEqual(len(ann_set), 2)


class AnnouncerTest(unittest.TestCase):
    """test Announcer

    """
    @classmethod
    def shouldInheritSelectors(cls):
        return True

    def setUp(self):
        super(AnnouncerTest, self).setUp()
        self.announcer = self.newAnnouncer()

    def newAnnouncer(self):
        return Announcer()

    def testAnnounceClass(self):
        announce = self.announcer.announce(AnnouncementMockA)
        self.assertEqual(type(announce), AnnouncementMockA)

    def testAnnounceInstance(self):
        instance = AnnouncementMockA()
        announce = self.announcer.announce(instance)
        self.assertEqual(announce, instance)

    def testNoArgBlock(self):
        """We are supposed to accept zero-argument blocks as actions

        """
        counter = []

        def handler():
            counter.append(1)

        self.announcer.subscribe(AnnouncementMockA, do=handler)
        self.announcer.announce(AnnouncementMockA())
        self.assertEqual(counter[0], 1)

    def testSubscribeBlock(self):

        announcement = []

        def do(ann):
            announcement.append(ann)

        self.announcer.subscribe(AnnouncementMockA, do=do)
        instance = self.announcer.announce(AnnouncementMockA())
        self.assertEqual(announcement[0], instance)

        announcement.pop()
        instance = self.announcer.announce(AnnouncementMockB())
        self.assertEqual(len(announcement), 0)

    def testSubscribeSend(self):

        announcement = []

        class Receiver(object):
            def do(self, ann):
                announcement.append(ann)

        self.announcer.subscribe(AnnouncementMockA, send="do", to=Receiver())
        instance = self.announcer.announce(AnnouncementMockA())
        self.assertEqual(announcement[0], instance)

        announcement.pop()
        instance = self.announcer.announce(AnnouncementMockB())
        self.assertEqual(len(announcement), 0)

    def testSubscribeSet(self):

        announcement = []

        def do(ann):
            announcement.append(ann)

        self.announcer.subscribe(AnnouncementMockA + AnnouncementMockC, do=do)
        instance = self.announcer.announce(AnnouncementMockA())
        self.assertEqual(announcement[0], instance)

        announcement.pop()
        instance = self.announcer.announce(AnnouncementMockB())
        self.assertEqual(len(announcement), 0)

        instance = self.announcer.announce(AnnouncementMockC())
        self.assertEqual(announcement[0], instance)

    def testSubscribeSubclass(self):

        announcement = []

        def do(ann):
            announcement.append(ann)

        self.announcer.subscribe(AnnouncementMockB, do=do)
        instance = self.announcer.announce(AnnouncementMockA())
        self.assertEqual(len(announcement), 0)

        instance = self.announcer.announce(AnnouncementMockB())
        self.assertEqual(announcement[0], instance)

        announcement.pop()
        instance = self.announcer.announce(AnnouncementMockC())
        self.assertEqual(announcement[0], instance)

    def testTwoArgBlock(self):

        flag = [False]

        def do(ann, announcer2):
            flag[0] = announcer2 == self.announcer

        self.announcer.subscribe(AnnouncementMockA, do=do)
        self.announcer.announce(AnnouncementMockA())
        self.assertTrue(flag[0])

    def testUnsubscribeBlock(self):

        announcement = []

        def do(ann):
            announcement.append(ann)

        self.announcer.subscribe(AnnouncementMockA, do=do)
        self.announcer.unsubscribe(do)

        self.announcer.announce(AnnouncementMockA())
        self.assertEqual(len(announcement), 0)

    def testUnsubscribeSend(self):

        announcement = []

        class Receiver(object):
            def receive(ann):
                announcement.append(ann)
        receiver = Receiver()

        self.announcer.subscribe(AnnouncementMockA, send="receive",
                to=receiver)
        self.announcer.unsubscribe(receiver)
        self.announcer.announce(AnnouncementMockA())
        self.assertEqual(len(announcement), 0)

    def testUnsubscribeSet(self):

        announcement = []

        def do(ann):
            announcement.append(ann)

        self.announcer.subscribe(AnnouncementMockA + AnnouncementMockB, do=do)
        self.announcer.unsubscribe(do)
        self.announcer.announce(AnnouncementMockA())
        self.assertEqual(len(announcement), 0)
        self.announcer.announce(AnnouncementMockB())
        self.assertEqual(len(announcement), 0)


class WeakAnnouncerTest(AnnouncerTest):

    def setUp(self):
        super(WeakAnnouncerTest, self).setUp()
        self.counter = 0

    def newAnnouncer(self):
        return Announcer()

    def testWeakBlock(self):

        def do(ann):
            self.counter += 1

        self.announcer.subscribe(AnnouncementMockA, do=do).makeWeak()
        self.announcer.announce(AnnouncementMockA)
        self.assertEqual(self.counter, 1)
        del do
        gc.collect()
        self.announcer.announce(AnnouncementMockA)
        self.assertEqual(self.counter, 1)

    def testWeakObject(self):

        class Receiver(object):
            def do(self, announcement):
                announcement.value += 1

        receiver = Receiver()
        announcement = AnnouncementMockA()
        announcement.value = 0
        subscription = self.announcer.subscribe(AnnouncementMockA, send="do",
                to=receiver).makeWeak()
        self.announcer.announce(announcement)
        self.assertEqual(announcement.value, 1)
        del receiver
        gc.collect()
        self.announcer.announce(announcement)
        self.assertEqual(announcement.value, 1)

    def testWeakSubscription(self):

        class Receiver(object):
            def do(self, announcement):
                announcement.value += 1

        receiver = Receiver()
        subscription = self.announcer.subscribe(AnnouncementMockA, send="do",
                to=receiver).makeWeak()
        self.assertTrue(receiver is subscription.subscriber)
