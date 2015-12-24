#!/usr/bin/env python
import webapp2
import random
import json
import math
import urllib
import logging
import datetime
import time

from google.appengine.ext import ndb
from google.appengine.api import taskqueue

from models import *
from plurals_config import PLURALS

from base import ApiHandler
from cached_queries import CachedQuery
from cached_query_manager import CachedQueryManager
from admin import FileResources, FileInfo, AppsResources

def filterLocale(locale,elems):
    filtered = filter(lambda s:s.locale==locale,elems)
    if len(filtered)>0:
        return filtered[0]
    return None

def weighted_choice(choices):
   while len(choices)>0:
       total = sum(w for c, w in choices)
       r = random.uniform(0, total)
       upto = 0
       for i,e in enumerate(choices):
           c, w = e
           if upto + w >= r:
               yield c
               del choices[i]
               break
           upto += w

class TranslateHandler(ApiHandler):

    @staticmethod
    def refresh_resource(key,locale,wait,resource_id):
        taskqueue.add(url='/tasks/rescore/resource', params={'key': key, 'locale':locale},countdown=wait,queue_name="rescore",name='%s_%s_%08x' % (resource_id,locale,int(time.time())))

    @staticmethod
    def refresh_user(key,appkey,locale,wait,user_id):
        taskqueue.add(url='/tasks/rescore/user', params={'key': key, 'appkey':appkey, 'locale':locale},countdown=wait,queue_name="rescore",name='%s_%s_%08x' % (user_id,locale,int(time.time())))

    def update_stats(self,user,locale,func):
        localeStats = filterLocale(locale,user.localeStats)
        if localeStats is None:
            localeStats = TranslationsStats(locale=locale)
            user.localeStats.append(localeStats)
        globalStats = user.stats
        if globalStats is None:
            globalStats = TranslationsStats(locale=None)
            user.stats = globalStats
        stats = [localeStats, globalStats]
        for stat in stats:
            func(stat)

    def _get(self):
        app = self._authenticate_link()
        amount = int(self.request.get('amount'))
        _locale = self.request.get('locale')
        userid = self.request.get('userid')
        locale = self._resolve_locale(_locale)
        logging.info("%s, %s->%s, %s" % (userid, _locale, locale, amount))

        # Get all actions for this user and locale
        user = User.query(User.userid==userid).fetch(1)
        new_user = False
        if len(user) == 0:
            user = User(userid=userid)
            new_user = True
        else:
            user = user[0]
        if user.stats is None:
            user.stats = TranslationsStats()

        actions = filter(lambda a:a.locale==locale,user.actions)
        # Compile a list of all resources the user already voted on
        already_voted = dict(map(lambda a:(a.resource.urlsafe(),a.created_at),actions))

        selected = []
        _amount = amount+1

        # Get all unresolved resources for this app & locale, sorted by weight
        potential_resources = AppsResources.fetch(app.key.urlsafe(),locale)

        def get_weight(resource):
            stats = filter(lambda s:s['locale']==locale,resource['localeStats'])
            weight = None
            if len(stats)>0:
                weight = stats[0]['weight']
            else:
                stats = resource['stats']
                if stats is not None:
                    weight = stats['weight']
            if weight is None or weight == 0:
                weight = 0.1
            pri = resource['priority']
            if pri >= 1 and pri<=3:
                weight = weight * 5**(3-pri)
            return weight

        choices = [(res,get_weight(res)) for res in potential_resources]
        # Sort potential_resources (TODO: randomly) (TODO: weighted by priority + score of highest string)
        # sum_weight = sum(r.weight for r in potential_resources)
        # assert(sum_weight>0)
        # TODO
        choices = weighted_choice(choices)

        # Iterate on all resources
        for resource in choices:

            # if we're done, break out
            if len(selected) == _amount:
                break

            # Last Activity
            lastActivity = None
            stats = filter(lambda s:s['locale']==locale,resource['localeStats'])
            if len(stats)>0:
                stats = stats[0]
                lastActivity = stats['last_suggestion_added']
                if type(lastActivity)==float:
                    lastActivity = datetime.datetime.fromtimestamp(lastActivity)

            # Check: did the user already vote on this resource?
            key = resource['key']
            if key in already_voted:
                # Was a new suggestion added since then
                action_time = already_voted[key]
                if lastActivity is None or action_time is None or action_time >= lastActivity:
                    # If not, skip this resource (it may be equal if the current user made the last suggestion)
                    continue

            # Check: Is this a plural? If so, is this plural relevant for this language?
            if "::P::" in resource['resource_id']:
                quantity = resource['resource_id'].split('::P::')[1]
                allowed_quantities = PLURALS.get(locale,[])
                if quantity not in allowed_quantities:
                    continue

            # Get suggestions by locale
            suggestions = sorted(resource['suggestions'],key=lambda r:r['score'],reverse=True)

            # Check: does any of the suggestions need to be re-scored?
            if any(map(lambda s:Suggestion.stale(s['score_timestamp']),suggestions)):
                # If so, skip this resource and queue for re-scoring
                TranslateHandler.refresh_resource(resource['key'],locale,1,resource['resource_id'])

            # Select top 3 suggestions + random 2 from the rest
            extra_suggestions = suggestions[3:]
            suggestions = suggestions[:3] + random.sample(extra_suggestions,min(2,len(extra_suggestions)))
            random.shuffle(suggestions)
            selected.append({
                'id': resource['resource_id'],
                'original': resource['text'],
                'context': resource['context'],
                'suggestions': map(lambda s:s['text'],suggestions)
            })

            logging.debug("selected %s (p:%s w:%s)" % (resource['text'].encode('utf-8'),get_weight(resource),resource['priority']))


        has_more = len(selected)>amount
        selected = selected[:amount]

        # Update the user's stats and save
        def update_served(s):
            s.served+=len(selected)
        self.update_stats(user,locale,update_served)
        user.put()

        # Return the result to the user
        return {'resources':selected,'more':has_more,'new_user':new_user}

    def _post(self,payload):
        # Retrieve user object
        app = self._authenticate_link()
        _locale = self.request.get('locale')
        userid = self.request.get('userid')
        locale = self._resolve_locale(_locale)
        logging.debug("%s, %s->%s" % (userid, _locale, locale))

        user = User.query(User.userid==userid).fetch(1)
        if len(user) == 0:
            self.abort(403)
        user = user[0]

        now = datetime.datetime.now()

        # Stuff that will be saved later
        to_put = [user]
        user.last_activity = now

        # Get all votes from the user
        votes = json.loads(self.request.get('votes'))

        # For every vote:
        for vote in votes:
            # Get the relevant resource
            resource = Resource.query(Resource.app==app.key, Resource.resource_id==vote['resource_id']).fetch(1)[0]
            text = vote['text']
            if text is not None:
                text = text.strip()
            error = vote['error']
            skipped = False
            unclear = False
            added = False
            # If there's already an action for this resource and locale -
            actions = filter(lambda a:a.resource==resource.key and a.locale==locale,user.actions)
            if len(actions) > 0:
                # Check the existing action
                action = actions[0]
                action.text = text
                action.error = error
                action.created_at = now
            else:
                # create a new action and add it to the list of the user's actions
                action = Action(app=app.key,resource=resource.key,locale=locale,owner=True,text=text,error=error,created_at=now)
                user.actions.append(action)

            if text is not None:
                suggestions = filter(lambda s:s.locale==locale and s.text==text,resource.suggestions)
                if len(suggestions)==0:
                    resource.suggestions.append(Suggestion(locale=locale,text=text))
                    added = True
            elif error=='skipped':
                skipped = True
            elif error=='unclear':
                unclear = True
            else:
                continue

            action.owner = added

            resource.last_activity = now
            to_put.append(resource)

            # Update resource stats
            stats = filterLocale(locale,resource.localeStats)
            if stats is None:
                stats = ResourceStat(locale=locale)
                resource.localeStats.append(stats)
            if skipped:
                stats.skipped += 1
            if unclear:
                stats.unclear += 1
            if added:
                stats.last_suggestion_added = now

        # Update user stats
        def update_received(s):
            s.received+=len(votes)
            s.translated+=len([v for v in votes if v['text'] is not None])
        self.update_stats(user,locale,update_received)

        # Save the user
        ndb.put_multi(to_put)
        TranslateHandler.refresh_user(user.key.urlsafe(),app.key.urlsafe(),locale,6,user.userid)
        for res in to_put[1:]:
            TranslateHandler.refresh_resource(res.key.urlsafe(),locale,3,res.resource_id)

        return True

class VerificationHandler(ApiHandler):
    def _get(self):
        app = self._authenticate_link()
        return { 'success':True, 'name':app.name }

### Tasks
class RescoreResource(webapp2.RequestHandler):
    def post(self):
        urlsafe_key = self.request.get('key')
        key = ndb.Key(urlsafe=urlsafe_key)
        logging.debug("RescoreResource: %s" % key)
        resource = key.get()

        locales = self.request.get('locale').split(",")
        now = datetime.datetime.now()

        for locale in locales:

            if all(s.locale!=locale for s in resource.suggestions):
                return

            users = User.query(User.actions.resource==key,User.actions.locale==locale)

            suggestions = {}
            for s in resource.suggestions:
                if s.locale == locale:
                    suggestions[s.text.strip()] = s
                    s.score = 0.0
                    s.score_timestamp = now

            OTHER = ' __other__ '
            suggestions[OTHER] = Suggestion(score=0.0,text=OTHER)

            for user in users:
                cred = user.credibility(locale)
                print user.userid, cred

                for action in user.actions:
                    if action.resource == key and action.locale == locale and action.text is not None:
                        action_text = action.text.strip()
                        if suggestions.has_key(action_text):
                            for k, v in suggestions.items():
                                if action_text == k:
                                    v.score += math.log(1-cred)
                                else:
                                    v.score += math.log(cred)

                print suggestions

            # normalize scores so that they sum to 1
            values = suggestions.values()
            scores = [ s.score for s in values ]
            minscore = min(scores)
            for s in values:
                s.score -= minscore
                s.score = math.exp(s.score)
            scores = [ s.score for s in values ]
            sumscores = sum( scores )
            if sumscores > 0:
                weight = 1 - (max(scores)*0.9 / sumscores)
                for s in values:
                    s.score /= sumscores
                    s.score = -math.log(s.score)
            else:
                weight = 0.1
            scores = [ s.score for s in values ]

            stats = filterLocale(locale,resource.localeStats)
            if stats is None:
                stats = ResourceStat(locale=locale)
                resource.localeStats.append(stats)

            stats.weight = weight
            stats.weight_timestamp = now

            logging.info("RescoreResource %s / %s - weight: %.2f" % (resource.resource_id, locale, stats.weight))
            for s in values:
                logging.info("- %s: %.2f" % (s.text, s.score))

        resource.stats = ResourceStat()
        for stat in resource.localeStats:
            resource.stats.skipped += stat.skipped
            resource.stats.unclear += stat.unclear
            if stat.weight is not None:
                resource.stats.weight += stat.weight
        if len(resource.localeStats)>0:
            resource.stats.weight /= len(resource.localeStats)
            resource.stats.weight_timestamp = now

        resource.put()
        logging.info("saved %r" % resource.to_dict())
        logging.info("locales %r" % locales)

        for locale in locales:
            CachedQueryManager.mark_changed('Resource',
                                            key=urlsafe_key,
                                            locale=locale,
                                            filename=resource.filename,
                                            priority=resource.priority,
                                            appkey=resource.app.urlsafe())

class RescoreUser(webapp2.RequestHandler):
    def post(self):
        urlsafe_key = self.request.get('key')
        urlsafe_appkey = self.request.get('appkey')
        key = ndb.Key(urlsafe=urlsafe_key)
        user = key.get()

        locale = self.request.get('locale')

        now = datetime.datetime.now()

        approved = 0.0
        for action in user.actions:
            resource = action.resource.get()
            suggestions = filter(lambda s:s.locale==locale,resource.suggestions)
            suggestions = sorted(suggestions,key=lambda s:s.score,reverse=True)
            if len(suggestions)>0:
                if action.text==suggestions[0].text:
                    score1 = suggestions[0].score
                    score2 = min(0,score1)
                    if len(suggestions)>1:
                        score2 = suggestions[1].score
                    suggestion_score = 1 - math.exp(score2-score1)
                    approved += suggestion_score

        stats = filter(lambda s:s.locale==locale,user.localeStats)
        if len(stats)==0:
            stats = TranslationsStats()
            user.stats.append(stats)
        else:
            stats = stats[0]
        stats.approved = approved
        if stats.approved > stats.received:
            stats.approved = stats.received
        stats.score_timestamp = now
        gstats = user.stats
        gstats.approved = sum(s.approved for s in user.localeStats)
        if gstats.approved > gstats.received:
            gstats.approved = gstats.received
        gstats.score_timestamp = now

        logging.info("RescoreUser %s / %s" % (user.userid, locale))
        logging.info("Local Stats %s" % stats)
        logging.info("Global Stats %s" % stats)

        user.put()

        CachedQueryManager.mark_changed('User',key=urlsafe_key,appkey=urlsafe_appkey)

## Periodic Tasks
class PeriodicResourceRefresh(webapp2.RequestHandler):
    def get(self):
        now = datetime.datetime.now()
        score_older_than = now - datetime.timedelta(days=1)
        active_after = now - datetime.timedelta(days=7)
        refreshable = Resource.query()#Resource.last_activity>active_after)
        allowed_amount = 100
        for resource in refreshable:
            if allowed_amount == 0:
                break
            if resource.last_activity is not None and resource.last_activity < active_after:
                continue
            stale_suggestions = filter(lambda s:s.score_timestamp<score_older_than,resource.suggestions)
            sugg_locales = set(s.locale for s in stale_suggestions)
            stale_weights = filter(lambda s:s.weight_timestamp is None or s.weight_timestamp<score_older_than,resource.localeStats)
            weight_locales = set(s.locale for s in stale_weights)
            locales = sugg_locales.union(weight_locales)
            if len(locales)>0:
                allowed_amount -= 1
                locales = ",".join(list(locales))
                TranslateHandler.refresh_resource(resource.key.urlsafe(),locales,0,resource.resource_id)

class PeriodicUserRefresh(webapp2.RequestHandler):
    def get(self):
        now = datetime.datetime.now()
        score_older_than = now - datetime.timedelta(days=1)
        active_after = now - datetime.timedelta(days=7)
        refreshable = User.query(User.last_activity>active_after)
        allowed_amount = 100
        for user in refreshable:
            if allowed_amount == 0:
                break
            apps = set(a.app.urlsafe() for a in user.actions)
            stale_stats = filter(lambda s:s.score_timestamp<score_older_than,user.localeStats)
            if len(stale_stats)>0:
                allowed_amount -= 1
                locales = set(s.locale for s in stale_stats)
                for app in apps:
                    for locale in locales:
                        TranslateHandler.refresh_user(user.key.urlsafe(),app,locale,0,user.userid)

app = webapp2.WSGIApplication([
    ('/api/verification', VerificationHandler),
    ('/api/translate', TranslateHandler),
    ('/tasks/rescore/resource', RescoreResource),
    ('/tasks/rescore/user', RescoreUser),
    ('/tasks/rescore/resource-periodic', PeriodicResourceRefresh),
    ('/tasks/rescore/user-periodic', PeriodicUserRefresh),
], debug=True)
