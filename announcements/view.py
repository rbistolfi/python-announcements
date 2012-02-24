# -*- coding: utf8 -*-

"""This module implements AnnouncementSpy, a class logging every announcement
published by an announcer.

"""

import core
import logging


class AnnouncementSpy(object):
    """A class logging every announcement

    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("AnnouncementSpy")

    def __init__(self, announcer):

        self._announcer = None
        self.announcer = announcer
        self.announcements = []
        self.index = 0

    def __repr__(self):
        return "<AnnouncementSpy announcer=%s>" % self.announcer

    def clear(self):
        self.announcements = []

    def announce(self, announcement):
        self.announcements.append(announcement)
        self.index = len(self.announcements)
        self.logger.info("%s: IncommingEvent=%s", self.announcer, announcement)

    @property
    def announcer(self):
        return self._announcer

    @announcer.setter
    def announcer(self, announcer):
        if self._announcer:
            self._announcer.unsubscribe(self)
        self._announcer = announcer
        self._announcer.subscribe(core.Announcement, send="announce",
                to=self).makeWeak()

