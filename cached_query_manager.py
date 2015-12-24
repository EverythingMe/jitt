#!/usr/bin/env python
import webapp2
import json
import logging

from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import *

class CachedQueryManager(webapp2.RequestHandler):

    initialized = False

    @classmethod
    def init(cls):
        if cls.initialized:
            return
        # Used to avoid cyclic import loops
        from admin import FileInfo, FileResources, AppUsers, AppStats, AppsResources, TranslationStatus
        from upload import DownloadPack
        cls.cqs = dict((x.__name__,x) for x in [ FileInfo, FileResources, AppsResources, DownloadPack, AppUsers, AppStats, TranslationStatus ])

    def post(self):
        self.init()
        cls = self.request.get('cls')
        cls = self.cqs[cls]
        args = self.request.get('args')
        args = cls.deserialize_args(args)
        logging.info('Refreshing %s, args=%r' % (cls,args))
        cls.task_handler(*args)

    @classmethod
    def mark_changed(cls,kind,**kw):
        cls.init()
        for cq in cls.cqs.values():
            cq.on_changed(kind,kw)

app = webapp2.WSGIApplication([
    ('/api/tasks/refresh', CachedQueryManager),
], debug=True)
