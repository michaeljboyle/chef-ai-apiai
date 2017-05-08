from google.appengine.api import memcache

def apiai_response(request, displayText='', speech=None, data=None,
                   contextOut=None, followupEvent=None,
                   source='chef-ai-apiai-webhook'):
    if speech is None:
        speech = displayText

    j = {
        'displayText': displayText,
        'speech': speech,
        'source': source
    }
    if data:
        j['data'] = data
    if contextOut:
        j['contextOut'] = contextOut
    if followupEvent:
        j['followupEvent'] = followupEvent

    # if request.get('originalRequest').get('source') == 'facebook':
    #     msg = request.get('originalRequest')
    #     sender_id = msg['data']['sender']['id']
    #     fb_response = {
    #         'recipient': {'id': sender_id},
    #         'message': {'text': displayText}
    #     }
    #     j['data']['facebook'] = fb_response

    return j


def get_source_id(request):
    src = request.get('originalRequest').get('source')
    if src == 'facebook':
        id_type = 'fb_id'
        sender_id = request.get(
            'originalRequest').get('data').get('sender').get('id')
    return id_type, sender_id

def _make_memcache_key(session_id):
    return '{}.{}'.format(session_id, 'entities')

def get_cached_entities(session_id):
    key_root = _make_memcache_key(session_id)
    account = memcache.get('{}.{}'.format(key_root, 'account'))
    eater = memcache.get('{}.{}'.format(key_root, 'eater'))
    pantry = memcache.get('{}.{}'.format(key_root, 'pantry'))
    return {'account': account, 'eater': eater, 'pantry': pantry}

def cache_entities(session_id, account=None, eater=None, pantry=None):
    key_root = _make_memcache_key(session_id)
    if account:
        memcache.set('{}.{}'.format(key_root, 'account'), account, time=3600)
    if eater:
        memcache.set('{}.{}'.format(key_root, 'eater'), eater, time=3600)
    if pantry:
        memcache.set('{}.{}'.format(key_root, 'pantry'), pantry, time=3600)


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