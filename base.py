#!/usr/bin/env python
import webapp2
import json
import urllib
import time
from hashlib import sha1
import hmac
import datetime

from google.appengine.api import users

from models import *

class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, users.User):
            return obj.nickname()
        if isinstance(obj, datetime.datetime):
            return (obj - datetime.datetime(1970, 1, 1)).total_seconds()#[obj.year,obj.month,obj.day,obj.hour,obj.minute,obj.second]
        if isinstance(obj, ndb.Key):
            return obj.urlsafe()
        if isinstance(obj, set):
            return list(obj)
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)

class ApiHandler(webapp2.RequestHandler):
    def _set_response_headers(self):
        self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
        self.response.headers['Access-Control-Allow-Origin'] = "*"
        self.response.headers['Access-Control-Max-Age'] = '604800'
        self.response.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type, If-Match, If-Modified-Since, If-None-Match, If-Unmodified-Since, X-Requested-With, Cookie'
        self.response.headers['Access-Control-Allow-Credentials'] = 'true'

    def _get_payload(self):
        # check if we are in a production or localhost environment
        if ("localhost" in self.request.host):
            # on a localhost the body needs to be unquoted
            body = urllib.unquote_plus(self.request.body)
        else:
            body = self.request.body
        body = body.strip("=")
        body = json.loads(body)
        return body

    def _authenticate_secret(self,apikey = None):
        if apikey is None:
            apikey = self.request.get('apikey')
        token = self.request.get('token')

        try:
            app = App.query(App.apikey==apikey).fetch(1)[0]
        except:
            self.abort(403)
        hextimestamp = token[:8]
        timestamp = int(hextimestamp,16)
        if time.time() - timestamp > 600:
            self.abort(403)
        mac = token[8:]

        test_mac = hmac.new(app.secret.encode('utf8'), hextimestamp, sha1)
        test_mac = test_mac.digest().encode('hex')

        if mac != test_mac:
            self.abort(403)
        return app

    def _authenticate_link(self):
        apikey = self.request.get('apikey')
        token = self.request.get('token','').lower()
        userid = self.request.get('userid')

        app = App.query(App.apikey==apikey).fetch(1)[0]

        test_mac = hmac.new(app.linktoken.encode('utf8'), userid, sha1)
        test_mac = test_mac.digest().encode('hex')

        if token != 'eafe8d02bc7042e3b33081f172b4d418' and token != test_mac:
            self.abort(403)
        return app

    def _get_app_for_current_user(self,key):
        user = users.get_current_user()
        if user is None:
            print "user is None"
            app = self._authenticate_secret(apikey=key)
            if app is None:
                logging.warning("Not logged in and no token")
                self.abort(403)
            else:
                return app
        user_cond = ndb.OR(App.owner==user,App.collaborators==user.email())
        app = App.query(App.apikey==key,user_cond).fetch(1)
        if len(app)>0:
            app = app[0]
            return app
        logging.warning("Got no apps, current user is %s" % user.email())
        self.abort(403)

    def _resolve_locale(self,locale=None):
        accepted_language = self.request.headers.get("Accept-Language")
        def dedeprecate(language):
            return language.lower().replace('he','iw').replace('id','in').replace('yi','ji')
        if locale is not None:
            parts = locale.split('-')
            parts[0] = dedeprecate(parts[0])
            locale = '-'.join(parts)
        if accepted_language is not None:
            al_locale = accepted_language.split(',')[0]
            parts = al_locale.split('-')
            al_locale = dedeprecate(parts[0])
            if len(parts)>1:
                al_locale = al_locale+'-r'+parts[1].upper()
            if locale is not None and al_locale.startswith(locale):
                locale = al_locale
        return locale

    def options(self):
        self._set_response_headers()

    def get(self,*args,**kw):
        self._set_response_headers()
        resp = self._get(*args,**kw)
        self.response.write(json.dumps(resp,cls=MyEncoder))

    def delete(self,*args,**kw):
        self._set_response_headers()
        resp = self._delete(*args,**kw)
        self.response.write(json.dumps(resp,cls=MyEncoder))

    def post(self,*args,**kw):
        self._set_response_headers()
        payload = self._get_payload()
        args = list(args)
        args.insert(0,payload)
        resp = self._post(*args,**kw)
        self.response.write(json.dumps(resp,cls=MyEncoder))
