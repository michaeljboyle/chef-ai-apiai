from google.appengine.api import memcache

# class SessionId(object):
    
#     def __init__(self, fb_id=None, t=None):
#         self._fb_id = fb_id
#         self._timestamp = t

#     def fb_id(self):
#         return self._fb_id

#     def timestamp(self):
#         return self._timestamp

#     def get(self):
#         return '{}.{}'.format(self._fb_id, self._timestamp)

#     def key(self):
#         return '{}.session_id'.format(self._fb_id)

    # def from_string(self, s):
    #     [f, t] = s.split('.')
    #     self._fb_id = f
    #     self._timestamp = t
    #     return self

class SessionManager(object):

    def __init__(self):
        self._fb_id = None
        self._timestamp = None

    def _make_memcache_key(self, fb_id):
        return '{}.session_id'.format(fb_id)

    def _make_session_id(self, fb_id, timestamp):
        return '{}.{}'.format(fb_id, timestamp)

    def _parse_sid(self, s):
        [f, t] = s.split('.')
        self._fb_id = f
        self._timestamp = t

    def open_session(self, fb_id, timestamp):
        key = self._make_memcache_key(fb_id)
        session_id = memcache.get(key)
        if session_id is None:
            self._fb_id = fb_id
            self._timestamp = timestamp
            session_id = self.session_id()
            memcache.set(key, session_id, 60 * 5)
            return session_id
        else:
            self._parse_sid(session_id)
            return session_id

    # def key(self):
    #     if self._fb_id is None:
    #         return None
    #     else return self._make_memcache_key(self._fb_id)

    def fb_id(self):
        return self._fb_id

    def timestamp(self):
        return self._timestamp

    def session_id(self):
        if self._fb_id is None or self._timestamp is None:
            return None
        return self._make_session_id(self._fb_id, self._timestamp)

    def end_session(self):
        memcache.delete(self._make_memcache_key(self._fb_id))
        self._fb_id = None
        self._timestamp = None