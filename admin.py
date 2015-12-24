#!/usr/bin/env python
import webapp2
import random
import json
import math
import urllib
import uuid
import datetime
import itertools

from google.appengine.ext import ndb
from google.appengine.api import taskqueue
from google.appengine.api import users
from models import *
from base import ApiHandler
from cached_queries import CachedQuery
from cached_query_manager import CachedQueryManager

def locale_contains(l1,l2):
    # Should l2 should be returned when l1 is requested
    return l1==l2 or l1.startswith(l2+"-r")

## Cached Queries
class AppUsers(CachedQuery):

    @classmethod
    def get_query(cls,args):
        appkey, = args
        appkey = ndb.Key(urlsafe=appkey)
        users = User.query(User.actions.app==appkey)
        print 'get_query', cls, appkey, users
        return users

    @classmethod
    def on_changed(cls,kind,keywords):
        # We refresh this cache whenever a resource is changed with a locale we haven't seen yet
        # If locale is None it means that we underwent a major resource update and we should refresh anyway
        if kind == 'User':
            appkey = keywords.get('appkey')
            if appkey is not None:
                cls.queue_refresh(appkey, src='on_changed')

class FileInfo(CachedQuery):

    @classmethod
    def get_data(cls,args):
        appkey, = args
        appkey = ndb.Key(urlsafe=appkey)
        app = appkey.get()
        resources = Resource.query(Resource.app==appkey,Resource.revision>=app.revision)
        filenames = {}
        locales = {}
        num = 0
        for r in resources:
            filenames.setdefault(r.filename,{'num':0, 'locales':{}})
            fileinfo = filenames[r.filename]
            fileinfo['num']+=1
            for l in set([s.locale for s in r.suggestions]):
                fileinfo['locales'].setdefault(l,0)
                fileinfo['locales'][l] += 1
                locales.setdefault(l,0)
                locales[l] += 1
            num +=1
        return {
            'files': filenames,
            'locales': locales,
            'num': num
        }

    @classmethod
    def on_refreshed(cls,data,args):
        logging.warn("refreshing file data for %r" % data['files'].keys())
        for filename,fileinfo in data['files'].iteritems():
            FileResources.queue_refresh(args[0],None,filename, src='FileInfo.on_refreshed')

    @classmethod
    def valid_for_time(cls,args):
        return 60 # 1 minute

    @classmethod
    def on_changed(cls,kind,keywords):
        # We refresh this cache whenever a resource is changed with a locale we haven't seen yet
        # If locale is None it means that we underwent a major resource update and we should refresh anyway
        if kind == 'Resource':
            locale = keywords.get('locale')
            appkey = keywords.get('appkey')
            if appkey is not None:
                current = cls.fetch(appkey)
                if locale is None or locale not in current.get('locales',[]):
                    logging.warn('FileInfo refreshing now!')
                    cls.queue_refresh(appkey, src='on_changed')

class FileResources(CachedQuery):

    @classmethod
    def get_data(cls,args):
        appkey,locale,path = args
        if locale is not None:
            resources = FileResources.fetch(appkey,None,path)
        else:
            appkey = ndb.Key(urlsafe=appkey)
            app = appkey.get()
            resources = [ r.to_dict() for r in Resource.query(Resource.app==appkey,Resource.filename==path,Resource.revision>=app.revision) ]
        if locale is not None:
            for r in resources:
                r['suggestions'] = sorted(filter(lambda s:locale_contains(locale,s['locale']),r['suggestions']),key=lambda s:s['score'],reverse=True)
                r['localeStats'] = filter(lambda s:locale==s['locale'],r.get('localeStats',[]))
                if len(r['localeStats'])>0:
                    r['weight'] = r['localeStats'][0].get('weight',0.1)
                else:
                    stats = r.get('stats')
                    r['weight'] = 0.1
                    if stats is not None:
                        r['weight'] = stats.get('weight',0.1)
        return resources

    @classmethod
    def valid_for_time(cls,args):
        appkey,locale,path = args
        if locale is None:
            return 60
        else:
            return CachedQuery.valid_for_time(args)

    @classmethod
    def on_refreshed(cls,data,args):
        app,locale,path = args
        if locale is None:
            logging.warn('FileResources refreshing every locale!')
            locales = set()
            for resource in data:
                for suggestion in resource['suggestions']:
                    locales.add(suggestion['locale'])
            for l in locales:
                FileResources.queue_refresh(app,l,path, src='FileResources.on_refreshed')

    @classmethod
    def on_changed(cls,kind,keywords):
        # We refresh this cache whenever a resource is changed
        if kind == 'Resource':
            locale = keywords.get('locale')
            filename = keywords.get('filename')
            appkey = keywords.get('appkey')
            if locale is not None and filename is not None and appkey is not None:
                cls.queue_refresh(appkey,locale,filename, src='on_changed')

class AppStats(CachedQuery):

    @classmethod
    def get_data(cls,args):
        appkey, hours = args
        appkey = ndb.Key(urlsafe=appkey)
        app = appkey.get()
        since = datetime.datetime.now() - datetime.timedelta(hours=hours)
        ret = {}
        num_resources = 0
        num_resources_since = 0
        num_suggestions = 0
        num_suggestions_since = 0
        num_users = 0
        num_users_since = 0
        num_active_users_since = 0
        num_actions = 0
        num_actions_since = 0
        for res in Resource.query(Resource.app==appkey,Resource.revision>=app.revision):
            num_resources += 1
            if res.created_at is not None and res.created_at>since: num_resources_since += 1
            for sugg in res.suggestions:
                if sugg.uploaded: continue
                num_suggestions += 1
                if sugg.created_at is not None and sugg.created_at>since: num_suggestions_since += 1
        for user in User.query(User.actions.app==appkey):
            num_users += 1
            if user.created_at is not None and user.created_at>since: num_users_since += 1
            last_actions = [a for a in user.actions if a.created_at is not None and a.created_at>since]
            if len(last_actions)>0:
                num_active_users_since += 1
            num_actions += len(user.actions)
            num_actions_since += len(last_actions)
        return {
            'num_resources': num_resources,
            'num_resources_since': num_resources_since,
            'num_suggestions': num_suggestions,
            'num_suggestions_since': num_suggestions_since,
            'num_actions': num_actions,
            'num_actions_since': num_actions_since,
            'num_users': num_users,
            'num_users_since': num_users_since,
            'num_active_users_since': num_active_users_since
        }

    @classmethod
    def on_changed(cls,kind,keywords):
        # We refresh this cache whenever a resource or user is changed
        if kind in ['Resource','User']:
            appkey = keywords.get('appkey')
            if appkey is not None:
                cls.queue_refresh(appkey,1, src='on_changed')
                cls.queue_refresh(appkey,6, src='on_changed')
                cls.queue_refresh(appkey,24, src='on_changed')
                cls.queue_refresh(appkey,24*7, src='on_changed')
                cls.queue_refresh(appkey,24*30, src='on_changed')

class TranslationStatus(CachedQuery):

    @classmethod
    def get_data(cls,args):
        urlsafe, = args
        appkey = ndb.Key(urlsafe=urlsafe)
        app = appkey.get()

        fileinfo = FileInfo.fetch(urlsafe)
        locales = set(fileinfo['locales'])

        locale_aliases = {}
        generic_reduction = itertools.groupby(sorted((l.split('-')[0],l) for l in locales if '-' in l),lambda l:l[0])
        for generic, specific in generic_reduction:
            specific = list(specific)
            if len(specific) == 1:
                specific = specific[0][1]
                locale_aliases[generic] = specific

        status = {}
        for res in Resource.query(Resource.app==appkey,Resource.revision>=app.revision):
            for locale in locales:
                locale_alias = locale_aliases.get(locale,locale)
                for priority in ["1","2","3","other"]:
                    status.setdefault(locale_alias,{}).setdefault(priority,{'total':0,'translated':0,'verified':0})
                priority = res.priority
                if priority>=1 and priority<=3:
                    priority = str(priority)
                else:
                    priority = "other"
                current = status[locale_alias][priority]
                current['total'] += 1
                translated = filter(lambda s:s.locale==locale,res.suggestions)
                if len(translated)>0:
                    current['translated'] += 1
                    verified = filter(lambda s:s.score>=5,translated)
                    if len(verified)>0:
                        current['verified'] += 1
        ret = []
        for locale, data in status.items():
            priorities = []
            for priority in ["1","2","3","other"]:
                priorities.append(data.get(priority))
            rec = { 'locale': locale, 'stats': priorities }
            ret.append(rec)

        return ret

    @classmethod
    def on_changed(cls,kind,keywords):
        # We refresh this cache whenever a resource is changed
        if kind=='Resource':
            appkey = keywords.get('appkey')
            if appkey is not None:
                cls.queue_refresh(appkey, src='on_changed')

class AppsResources(CachedQuery):
    @classmethod
    def get_data(self,args):
        appkey, locale = args
        appkey = ndb.Key(urlsafe=appkey)
        app = appkey.get()
        resources = Resource.query(Resource.app==appkey,Resource.revision>=app.revision)
        ret = []
        for res in resources:
            r = res.to_dict()
            r['key'] = res.key.urlsafe()
            if r['resource_id'] == 'activation_tools_tooltip':
                print 'filtering locale %r for %r' % (locale, r['suggestions'])
            r['suggestions'] = filter(lambda s:locale_contains(locale,s['locale']),r['suggestions'])
            if r['resource_id'] == 'activation_tools_tooltip':
                print 'after filtering locale %r for %r' % (locale, r['suggestions'])
            r['localeStats'] = filter(lambda s:locale==s['locale'],r['localeStats'])
            ret.append(r)
        return ret

    @classmethod
    def on_changed(cls,kind,keywords):
        # We refresh this cache whenever a resource is changed
        if kind == 'Resource':
            appkey = keywords.get('appkey')
            locale = keywords.get('locale')
            if appkey is not None:
                if locale is not None:
                    cls.queue_refresh(appkey, locale, src='on_changed')
                else:
                    # No prioriy and locale... this means that something big changed (e.g. upload)
                    # Let's refresh everything.
                    logging.warn('AppsResources refreshing every locale!')
                    file_info = FileInfo.fetch(appkey)
                    for locale in file_info.get('locales',[]):
                        cls.queue_refresh(appkey, locale, src='on_changed')

## Data Fetching Handlers
class AppUsersHandler(ApiHandler):

    def _get(self,key):
        app = self._get_app_for_current_user(key)
        return AppUsers.fetch(app.key.urlsafe())

class FileInfoHandler(ApiHandler):

    def _get(self,key):
        app = self._get_app_for_current_user(key)
        return FileInfo.fetch(app.key.urlsafe())

class FileResourcesHandler(ApiHandler):

    def _get(self,key,locale=None,path=None):
        app = self._get_app_for_current_user(key)
        if path is not None:
            path = urllib.unquote_plus(path)
        return FileResources.fetch(app.key.urlsafe(),locale,path)

class AppStatsHandler(ApiHandler):

    def _get(self,key,period):
        app = self._get_app_for_current_user(key)
        period = int(period)
        return AppStats.fetch(app.key.urlsafe(),period)

class TranslationStatusHandler(ApiHandler):

    def _get(self,key):
        app = self._get_app_for_current_user(key)
        return TranslationStatus.fetch(app.key.urlsafe())

## Real Handlers
class LoginHandler(ApiHandler):

    def _get(self):
        user = users.get_current_user()
        if user is None:
            return {
                'loggedin': False,
                'url': users.create_login_url(self.request.get('next','/'))
            }
        else:
            return {
                'loggedin': True,
                'nick': user.nickname(),
                'url': users.create_logout_url('/')
            }

class AppHandler(ApiHandler):

    def _get(self,key=None):
        if key is None:
            # Get all apps for user
            user = users.get_current_user()
            if user is None:
                self.abort(403)
            user_cond = ndb.OR(App.owner==user,App.collaborators==user.email())
            apps = App.query(user_cond)
            apps = [ a.to_dict() for a in apps ]
            return apps
        else:
            # Get single app info
            app = self._get_app_for_current_user(key)
            return app.to_dict()

    def _delete(self,key=None):
        if key is None:
            self.abort(400)
        app = self._get_app_for_current_user(key)
        app.key.delete()
        return {'OK':True}

    def _post(self,data,key=None):
        # Edit / create new app
        user = users.get_current_user()
        if user is None:
            self.abort(403)
        if key is None:
            app = App()
            app.owner = user
            random = uuid.uuid4().hex
            app.secret = random[:16]
            app.apikey = random[16:]
        else:
            app = App.query(App.apikey==key,App.owner==user).fetch(1)
            assert(len(app)==1)
            app = app[0]
        if app.linktoken is None:
            random = uuid.uuid4().hex
            app.linktoken = random[:8]

        if 'name' in data:
            app.name = data['name']
        if 'collaborators' in data:
            collaborators = data['collaborators']
            if type(collaborators) is not list:
                collaborators = [ x.strip() for x in collaborators.split(',') ]
            app.collaborators = collaborators
        app.put()
        return app.to_dict()

class ResourceHandler(ApiHandler):

    def _delete(self,key=None,resource_id=None,locale=None,suggestion=None):
        if key is None or resource_id is None:
            self.abort(400)
        app = self._get_app_for_current_user(key)
        resource = Resource.query(Resource.app==app.key, Resource.resource_id==resource_id).fetch(1)
        if len(resource)==1:
            resource = resource[0]
            if suggestion is None and locale is None:
                resource.revision -= 1
            elif suggestion is not None and locale is not None:
                print resource.suggestions
                print suggestion, locale
                suggestion = json.loads(suggestion)
                resource.suggestions = filter(lambda s:s.text!=suggestion or s.locale!=locale,resource.suggestions)
                print resource.suggestions
            else:
                self.abort(400)
            resource.put()
            CachedQueryManager.mark_changed('Resource',
                                            appkey=app.key.urlsafe())
            return {'OK':True}
        else:
            return {'OK':False}

app = webapp2.WSGIApplication([
    ('/api/admin/login', LoginHandler),
    ('/api/admin/app', AppHandler),
    ('/api/admin/app/(.*)', AppHandler),
    ('/api/admin/stats/(.+)/(.+)', AppStatsHandler),
    ('/api/admin/status/(.+)', TranslationStatusHandler),
    ('/api/admin/files/([^/]+)', FileInfoHandler),
    ('/api/admin/resource/([^/]+)/([^/]+)', ResourceHandler),
    ('/api/admin/resource/([^/]+)/([^/]+)/([^/]+)/(.*)', ResourceHandler),
    ('/api/admin/resources/([^/]+)/([^/]+)/(.*)', FileResourcesHandler),
    ('/api/admin/users/(.+)', AppUsersHandler),
], debug=True)
