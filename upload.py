#!/usr/bin/env python
import webapp2
import random
import json
import math
import urllib

from google.appengine.ext import ndb
from google.appengine.api import taskqueue

from models import *

from base import ApiHandler
from admin import FileInfo, FileResources

from cached_queries import CachedQuery
from cached_query_manager import CachedQueryManager

class DownloadPack(CachedQuery):

    @classmethod
    def get_data(cls,args):
        appkey, = args
        fileinfo = FileInfo.fetch(appkey)
        ret = {}
        for filename in fileinfo['files']:
            for locale in fileinfo['locales']:
                resources = FileResources.fetch(appkey,locale,filename)
                for res in resources:
                    suggestions = filter(lambda s:not s['uploaded'],res['suggestions'])
                    if len(suggestions)==0:
                        continue
                    suggestion = suggestions[0]
                    res_id = res['resource_id']
                    if res_id not in ret:
                        ret[res_id] = {
                            'name':res_id,
                            'priority':res['priority'],
                            'context':res['context'],
                            'original':res['text'],
                            'locales':{},
                            'filename': res['filename'],
                            'locales': {}
                        }
                    ret[res_id]['locales'][locale] = [suggestion['text'],suggestion['score']]
        return list(ret.values())

    @classmethod
    def on_changed(cls,kind,keywords):
        # We refresh this cache whenever a resource is changed
        if kind == 'Resource':
            appkey = keywords.get('appkey')
            if appkey is not None:
                cls.queue_refresh(appkey,src='on_changed')


class UploadHandler(ApiHandler):
    def _post(self,recs):
        app = self._authenticate_secret()
        locales = set()
        for rec in recs:
            locales = locales.union(set(rec['locales'].keys()))
        revision = app.revision + 1
        total = len(recs)
        while len(recs)>0:
            params = {'app': app.key.urlsafe(),
                      'recs': json.dumps(recs[:25]),
                      'locales':json.dumps(list(locales)),
                      'revision':revision}
            taskqueue.add(url='/api/tasks/upload-resources', params=params,queue_name="upload")
            recs = recs[25:]
        taskqueue.add(url='/api/tasks/upload-resources',
                      params={'app': app.key.urlsafe(),
                      'recs': json.dumps([]),
                      'locales':json.dumps(list(locales)),
                      'revision':revision},queue_name="upload")
        return { 'success': True, 'processed': total }

class DownloadHandler(ApiHandler):
    def _get(self):
        app = self._authenticate_secret()
        threshold = self.request.get('threshold','5')
        threshold = float(threshold)
        pack = DownloadPack.fetch(app.key.urlsafe())
        ret = []
        for rec in pack:
            locales = {}
            for locale,suggestion in rec['locales'].items():
                if suggestion[1] >= threshold:
                    locales[locale] = suggestion[0]
            if len(locales)>0:
                rec['locales'] = locales
                ret.append(rec)
        return ret

### Tasks
class TaskUploadResources(webapp2.RequestHandler):

    def post(self): # should run at most 1/s due to entity group limit
        appkey = self.request.get('app')
        revision = self.request.get('revision')
        recs = json.loads(self.request.get('recs'))
        locales = self.request.get('locales')
        logging.info("Got %d recs to update" % len(recs))
        for rec in recs:
            taskqueue.add(url='/api/tasks/upload-resource',
                          params={'app': appkey, 'data': json.dumps(rec),'locales':locales,'revision':revision},
                          queue_name="upload")
        if len(recs) == 0:
            taskqueue.add(url='/api/tasks/upload-resource',
                          params={'app': appkey, 'data': json.dumps(None),'locales':locales,'revision':revision},
                          queue_name="upload")

class TaskUploadResource(webapp2.RequestHandler):

    def post(self): # should run at most 1/s due to entity group limit
        appkey = self.request.get('app')
        app = ndb.Key(urlsafe=appkey).get()
        data = json.loads(self.request.get('data'))
        locales = json.loads(self.request.get('locales'))
        revision = int(self.request.get('revision'))
        if data is None:
            app.revision = revision
            app.put()
            CachedQueryManager.mark_changed('Resource',appkey=appkey)
            return

        resource = Resource.query(Resource.app==app.key, Resource.resource_id==data['name']).fetch(1)
        if len(resource)>0:
            resource = resource[0]
        else:
            resource = Resource(app=app.key)
        resource.resource_id = data['name']
        resource.filename = data['filename']
        resource.context = data.get('context')
        resource.priority = int(data['priority'])
        resource.revision = revision
        resource.text = data['original']

        for locale,text in data['locales'].iteritems():
            suggestion = filter(lambda x:x.locale==locale and x.text==text,resource.suggestions)
            if len(suggestion)==0:
                resource.suggestions.append(Suggestion(locale=locale,text=text,score=0,uploaded=True))

        resource.put()

app = webapp2.WSGIApplication([
    ('/api/upload', UploadHandler),
    ('/api/download', DownloadHandler),
    ('/api/tasks/upload-resource', TaskUploadResource),
    ('/api/tasks/upload-resources', TaskUploadResources),
], debug=True)
