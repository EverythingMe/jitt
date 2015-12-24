import time
import datetime
import logging

from google.appengine.ext import ndb

class App(ndb.Model):
    name = ndb.StringProperty()
    apikey = ndb.StringProperty()
    secret = ndb.StringProperty()
    linktoken = ndb.StringProperty()
    owner = ndb.UserProperty()
    revision = ndb.IntegerProperty(default=0)
    collaborators = ndb.StringProperty(repeated=True)

    def __unicode__(self):
        return u"App:%s" % self.name

    def __str__(self):
        return self.__unicode__().encode('utf8')

class Suggestion(ndb.Model):

    STALE_PERIOD = 86400

    locale = ndb.StringProperty()
    text = ndb.StringProperty()
    score = ndb.FloatProperty()
    score_timestamp = ndb.DateTimeProperty(auto_now_add=True)
    created_at = ndb.DateTimeProperty(auto_now_add=True)
    flagged = ndb.IntegerProperty()
    uploaded = ndb.BooleanProperty(default=False)

    @staticmethod
    def stale(timestamp):
        if isinstance(timestamp,datetime.datetime):
            return (datetime.datetime.now() - timestamp).total_seconds() > Suggestion.STALE_PERIOD
        else:
            return (time.time() - timestamp) > Suggestion.STALE_PERIOD

class ResourceStat(ndb.Model):

    locale = ndb.StringProperty()
    weight = ndb.FloatProperty(default=0)
    skipped = ndb.IntegerProperty(default=0)
    unclear = ndb.IntegerProperty(default=0)
    last_suggestion_added = ndb.DateTimeProperty(auto_now_add=True)
    weight_timestamp = ndb.DateTimeProperty(auto_now_add=True)

class Resource(ndb.Model):

    app = ndb.KeyProperty(kind="App")
    revision = ndb.IntegerProperty(default=0)

    resource_id = ndb.StringProperty()
    filename = ndb.StringProperty()

    text = ndb.StringProperty()
    context = ndb.StringProperty()
    priority = ndb.IntegerProperty()

    suggestions = ndb.StructuredProperty(Suggestion, repeated=True)
    stats = ndb.StructuredProperty(ResourceStat)
    localeStats = ndb.StructuredProperty(ResourceStat, repeated=True)

    created_at = ndb.DateTimeProperty(auto_now_add=True)
    last_activity = ndb.DateTimeProperty(auto_now_add=True)

class Action(ndb.Model):

    app = ndb.KeyProperty(kind="App")
    resource = ndb.KeyProperty(kind="Resource")
    locale = ndb.StringProperty()
    owner = ndb.BooleanProperty()
    text = ndb.StringProperty()
    error = ndb.StringProperty()
    created_at = ndb.DateTimeProperty()

class TranslationsStats(ndb.Model):
    locale = ndb.StringProperty()
    served = ndb.IntegerProperty(default=0)
    received = ndb.IntegerProperty(default=0)
    translated = ndb.IntegerProperty(default=0)
    approved = ndb.FloatProperty(default=0)
    flagged = ndb.IntegerProperty(default=0)
    score_timestamp = ndb.DateTimeProperty(auto_now_add=True)

class User(ndb.Model):

    STALE_PERIOD = 86400

    userid = ndb.StringProperty()

    actions = ndb.StructuredProperty(Action,repeated=True)
    last_activity = ndb.DateTimeProperty(auto_now_add=True)
    stats = ndb.StructuredProperty(TranslationsStats)
    localeStats = ndb.StructuredProperty(TranslationsStats,repeated=True)
    created_at = ndb.DateTimeProperty(auto_now_add=True)

    def credibility(self,locale):
        stats = filter(lambda s:s.locale==locale,self.localeStats)
        if len(stats)>0:
            stats = stats[0]
        else:
            stats = self.stats
        if stats is not None:
            ret = float(stats.approved + 10) / (stats.received + 20)
        else:
            ret = 0.5
        logging.debug("credibility for %s is %f" % (self.userid,ret))
        return ret
