import logging
import googlemaps

from google.appengine.ext import ndb
from google.appengine.api import memcache

import requests

from src.common import chef, eater, food, pantry, account
from src.chat.utils import SessionManager

# Messenger API parameters
FB_PAGE_TOKEN = 'EAAZARTX4JpZAsBAIUtyTwxirZBwB8iU5OqxKt37iSsvIyd6bieEXIAWDc847ym6uklRx3n5ZBKZAfFa3SdDxnXvGZCyr7Dewyj1cTuFistlVg7Qv0NTxpW9MhEi0f4BZAbLZAaNbsXiOZAYGIYi0GxDTpVVmfrwlnrLaCEQ3yHpzZA8QZDZD'
FB_APP_ID = '1778243129157019'
# A user secret to verify webhook get request.
FB_VERIFY_TOKEN = 'chef-ai-is-alive'
GOOG_API_KEY = 'AIzaSyBSocxmGzZUCgMMHB2gt53OVenv2TUwric'

session_manager = SessionManager()

def get_memcache_data(session_id):
    data = memcache.get('{}.data'.format(session_id))
    if data is None:
        return {}
    return data

def set_memcache_data(session_id, data, time=60 * 5):
    memcache.set('{}.data'.format(session_id), data, time)

def first_entity_value(entities, entity):
    """
    Returns first entity value
    """
    if entity not in entities:
        return None
    val = entities[entity][0]['value']
    if not val:
        return None
    return val['value'] if isinstance(val, dict) else val

def get_list_entity_values(entities, entity):
    """
    Returns list of entity values
    """
    if entity not in entities:
        return None
    vals = [item['value'] for item in entities[entity]]
    if not vals:
        return None
    if isinstance(vals[0], dict):
        return [val['value'] for val in vals]
    else:
        return vals

def parse_wit_msg(request):
    logging.info('Incoming request:')
    logging.info(request)
    text = request['text']
    context = request['context']
    entities = request['entities']
    session_id = request['session_id']
    return text, context, entities, session_id


def fb_message(sender_id, text):
    """
    Function for returning response to messenger
    """
    data = {
        'recipient': {'id': sender_id},
        'message': {'text': text}
    }
    # Setup the query string with your PAGE TOKEN
    qs = 'access_token=' + FB_PAGE_TOKEN
    # Send POST request to messenger
    resp = requests.post('https://graph.facebook.com/me/messages?' + qs,
                         json=data)
    return resp.content

def send(request, response):
    """
    Sender function
    """
    # We use the fb_id as equal to session_id
    logging.info('Wit action: send')
    text, context, entities, session_id = parse_wit_msg(request)
    
    # send message
    logging.info('Sending: ' + response['text'])
    logging.info(response)
    fb_message(session_manager.fb_id(), response['text'])

def create_account(request):
    logging.info('Wit action: create_account_update_name')
    text, context, entities, session_id = parse_wit_msg(request)
    data = get_memcache_data(session_id)

    name = first_entity_value(entities, 'contact')
    if not name:
        context['missing_name'] = True
        context.pop('name', None)
        return context
    acct = account.Account(name=name,
                           fb_id=session_manager.fb_id())
    acct_key = acct.put()
    context['name'] = name
    context.pop('missing_name', None)
    data['acct_key'] = acct_key.urlsafe()
    data['name'] = name
    set_memcache_data(session_id, data)
    return context

def create_pantry(request):
    logging.info('Wit action: create_pantry')
    text, context, entities, session_id = parse_wit_msg(request)
    data = get_memcache_data(session_id)

    gmaps = googlemaps.Client(key=GOOG_API_KEY)

    try:
        logging.info('text: ' + text)
        results = gmaps.geocode(text)
        logging.info(results)
        geocode_result = results[0]
    except:
        context['missing_address'] = True
        context.pop('address', None)
        return context

    address = geocode_result['formatted_address']
    coords = geocode_result['geometry']['location']
    timezone = gmaps.timezone((coords['lat'], coords['lng']))['timeZoneId']

    context['address'] = address
    acct_key = data['acct_key']
    p = pantry.Pantry(parent=ndb.Key(urlsafe=acct_key),
                      address=address, timezone=timezone)
    pantry_key = p.put()
    data['pantry_key'] = pantry_key.urlsafe()
    context.pop('missing_address', None)
    set_memcache_data(session_id, data)
    return context

def create_eater_weight(request):
    logging.info('Wit action: create_eater_weight')
    text, context, entities, session_id = parse_wit_msg(request)
    data = get_memcache_data(session_id)

    weight = first_entity_value(entities, 'number')
    if not weight:
        context['missing_weight'] = True
        context.pop('weight', None)
        return context

    context['weight'] = weight
    context.pop('missing_weight', None)
    data['weight'] = weight
    set_memcache_data(session_id, data)
    return context

def create_eater_goal_weight(request):
    logging.info('Wit action: create_eater_goal_weight')
    text, context, entities, session_id = parse_wit_msg(request)
    data = get_memcache_data(session_id)

    goal_weight = first_entity_value(entities, 'number')
    logging.info('goal wt is %s' % goal_weight)
    if not goal_weight:
        context['missing_goal_weight'] = True
        context.pop('goal_weight', None)
        return context

    context['goal_weight'] = goal_weight
    context.pop('missing_goal_weight', None)
    data['goal_weight'] = goal_weight
    set_memcache_data(session_id, data)
    return context

def create_eater_dislikes(request):
    logging.info('Wit action: create_eater_dislikes')
    text, context, entities, session_id = parse_wit_msg(request)
    data = get_memcache_data(session_id)

    dislikes = get_list_entity_values(entities, 'product')
    if not dislikes:
        data['dislikes'] = []
        context['dislikes_text'] = 'nothing'
        return context

    data['dislikes'] = dislikes
    context['dislikes_text'] = ', '.join(dislikes)
    set_memcache_data(session_id, data)
    return context

def create_eater_diet(request):
    logging.info('Wit action: create_eater_diet')
    text, context, entities, session_id = parse_wit_msg(request)
    data = get_memcache_data(session_id)

    diet = first_entity_value(entities, 'diet')
    if not diet:
        context['diet_text'] = 'standard'
        data['diet'] = None
        return context

    data['diet'] = diet
    context['diet_text'] = diet
    set_memcache_data(session_id, data)
    return context

def create_eater(request):
    logging.info('Wit action: create_eater')
    text, context, entities, session_id = parse_wit_msg(request)
    data = get_memcache_data(session_id)

    #try:
    e = eater.Eater(id=fb_id, fb_id=session_manager.fb_id(),
                    parent=ndb.Key(urlsafe=data['acct_key']),
                    pantry=ndb.Key(urlsafe=data['pantry_key']),
                    name=data['name'], goal_weight=data['goal_weight'],
                    lift_days=[0, 2, 4])

    e.set_weight(context['weight'])

    if 'diet' in data:
        e.diet = data['diet']
    if 'dislikes' in data:
        e.dislikes = data['dislikes']

    try:
        e.set_default_goal()
        e.put()
        session_manager.end_session()
        # nutrition = e.get_remaining_nutrition()
        # context['cals'] = nutrition['cals']
        # context['protein'] = nutrition['protein']
        # context['carb'] = nutrition['carb']
        # context['fat'] = nutrition['fat']
        context.pop('account_creation_failure', None)
    except:
        context['account_creation_failure'] = True

    set_memcache_data(session_id, data)
    return context

def get_remaining_nutrition(request):
    logging.info('Wit action: get_remaining_nutrition')
    text, context, entities, session_id = parse_wit_msg(request)

    fb_id = session_manager.fb_id()
    e = eater.Eater.query(eater.Eater.fb_id == fb_id).fetch(1)[0]
    nut = e.get_remaining_nutrition()
    context['cals'] = nut['cals']
    context['protein'] = nut['protein']
    context['carb'] = nut['carb']
    context['fat'] = nut['fat']
    context['fiber'] = nut['fiber']
    context['sodium'] = nut['sodium']
    session_manager.end_session()

    logging.info('outgoing context:')
    logging.info(context)
    return context

def clear_context(request):
    logging.info('Clearing context')
    session_manager.end_session()
    return {'context_cleared': True}

ACTIONS= {
    'send': send,
    # 'use_pantry_item': create_account,
    # 'add_meal': create_account,
    # 'get_recipe_instructions': create_account,
    'get_remaining_nutrition': get_remaining_nutrition,
    # 'add_pantry_item': create_account,
    # 'get_recipe_options': create_account,
    # 'use_recipe_ingredients': create_account,
    # 'get_recipe': create_account,
    'create_account': create_account,
    'create_pantry': create_pantry,
    'create_eater_weight': create_eater_weight,
    'create_eater_goal_weight': create_eater_goal_weight,
    'create_eater_dislikes': create_eater_dislikes,
    'create_eater_diet': create_eater_diet,
    'create_eater': create_eater,
    'clear_context': clear_context
}


