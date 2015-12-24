#!/usr/bin/env python
import webapp2
import json
import logging

from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import *
from base import MyEncoder
import time

class CachedQuery(object):

    @classmethod
    def cache_key(cls,args):
        return cls.__name__+"::"+":".join(str(a).replace(':',';') for a in args)

    @classmethod
    def specialized_key(cls,ns,args):
        serialized_args = cls.serialize_args(args)
        cls_name = cls.__name__
        key = "%s:%s:%s" % (ns,cls_name,serialized_args)
        return key, serialized_args, cls_name

    @classmethod
    def pending_refresh_key(cls,args):
        return cls.specialized_key("pending-refresh",args)

    @classmethod
    def next_run_key(cls,args):
        return cls.specialized_key("next-run",args)

    @classmethod
    def serialize_args(cls,args):
        return json.dumps(args,sort_keys=True)

    @classmethod
    def deserialize_args(cls,args):
        return json.loads(args)

    @classmethod
    def get_query(cls,args):
        return None

    @classmethod
    def on_refreshed(cls,data,args):
        pass

    @classmethod
    def valid_for_time(cls,args):
        return 60*60 # 1 hour

    @classmethod
    def fetch(cls,*args,**kw):
        force_refresh = kw.get('force_refresh',False)
        cache_key = cls.cache_key(args)
        data = None
        if not force_refresh:
            serialized = memcache.get(cache_key)
            if serialized is not None:
                idx = int(serialized[:4],16)
                tot = int(serialized[4:8],16)
                serialized = serialized[8:]
                for i in range(1,tot):
                    part = memcache.get(cache_key+("::%d" % i))
                    if part is None:
                        break
                    serialized += part
                data = json.loads(serialized)
        else:
            logging.info("force_refresh-ing %s" % cls.__name__)
        if data is None:
            query = cls.get_query(args)
            if query is None:
                data = cls.get_data(args)
            else:
                data = [ r.to_dict() for r in query ]
            serialized = json.dumps(data,cls=MyEncoder)

            CHUNK = 512*1024
            tot = ((len(serialized)-1)/CHUNK)+1
            idx = 0
            part = ("%04x%04x" % (idx,tot)) + serialized[:CHUNK]
            serialized = serialized[CHUNK:]
            memcache.set(cache_key,part)
            logging.debug("%s <-- %s..." % (cache_key,part[:16]))
            while len(serialized)>0:
                idx += 1
                part = serialized[:CHUNK]
                serialized = serialized[CHUNK:]
                part_cache_key = cache_key+"::%d"
                memcache.set(part_cache_key % idx,part)
                logging.debug("%s <-- %s..." % (part_cache_key,part[:16]))

            next_run_key, _, _ = cls.next_run_key(args)
            valid_for = cls.valid_for_time(args)
            next_run_time = time.time()+valid_for
            memcache.set(next_run_key,next_run_time)
            logging.info('setting %s to run in %d seconds at %.1f' % (next_run_key,valid_for,next_run_time))

            cls.on_refreshed(data,args)

        return data

    @classmethod
    def task_handler(cls,*args):
        key, _, _ = cls.pending_refresh_key(args)
        client = memcache.Client()
        client.set(key, False)
        cls.fetch(*args,force_refresh=True)

    @classmethod
    def get_next_run(cls,args):
        key, _, _ = cls.next_run_key(args)
        val = memcache.get(key)
        if val is None:
            return key,0
        else:
            return key,val

    @classmethod
    def queue_refresh(cls,*args,**kw):
        key, next_run = cls.get_next_run(args)
        countdown = 0
        if next_run > 0:
            diff = next_run - time.time()
            logging.info("task %s is only allowed to run in %.1f seconds" % (key,diff))
            if diff > 0:
                countdown = int(diff)
        else:
            logging.info("task %s is not scheduled" % key)

        key, serialized_args, cls_name = cls.pending_refresh_key(args)
        client = memcache.Client()
        value = client.get(key)
        if value is None:
            client.set(key,False)
        value = client.gets(key)
        if not value:
            ok = client.cas(key, True, time=countdown+60)
            if ok:
                countdown = max(countdown,kw.get('wait',3))
                logging.info("requesting refresh of task %s in %s seconds" % (key,countdown))
                taskqueue.add(url='/api/tasks/refresh',
                              params={'cls':cls_name, 'args': serialized_args},
                              countdown=countdown,
                              queue_name="refresh",
                              name="%s_%s_%s_%08x" % (cls_name,"_".join(str(x).replace('/','_') for x in args),kw.get('src','?'),int(time.time())))
                return
        else:
            logging.info("task %s already pending" % key)
