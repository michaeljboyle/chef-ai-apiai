import logging
import googlemaps

from google.appengine.ext import ndb

from src.common import eater, pantry, account
import src.chat.utils as utils
import response_text as responses

GOOG_API_KEY = 'AIzaSyBSocxmGzZUCgMMHB2gt53OVenv2TUwric'

LBS_KG = 0.454


def signup(request):
    logging.info('Action: signup')
    session_id = request['sessionId']
    id_type, src_id = utils.get_source_id(request)
    params = request['result']['parameters']
    first_name = params['first_name']
    last_name = params['last_name']
    email = params['email']
    raw_address = params['address']
    weight_amt = params['weight']['amount']
    weight_unit = params['weight']['amount']
    goal_weight_amt = params['goal_weight']['amount']
    goal_weight_unit = params['goal_weight']['unit']

    # Preprocess before creating objects
    first_name = first_name.capitalize()
    last_name = last_name.capitalize()

    # Get address
    gmaps = googlemaps.Client(key=GOOG_API_KEY)
    address_results = gmaps.geocode(raw_address)
    logging.info(address_results)
    geocode_result = address_results[0]
    address = geocode_result['formatted_address']
    coords = geocode_result['geometry']['location']
    timezone = gmaps.timezone((coords['lat'], coords['lng']))['timeZoneId']

    # Convert weights if necessary
    if weight_unit == 'lb':
        weight_amt = weight_amt * LBS_KG
    if goal_weight_unit == 'lb':
        goal_weight_amt = goal_weight_amt * LBS_KG

    acct = account.Account(first_name=first_name,
                           last_name=last_name, email=email)
    if id_type == 'fb_id':
        acct.fb_id = src_id
    logging.info('Account created')

    p = pantry.Pantry(parent=acct.key, address=address, timezone=timezone)
    logging.info('Pantry created')
    pantry_id = ndb.Model.allocate_ids(size=1, parent=acct.key)[0]
    pantry.key = ndb.Key(pantry.Pantry, pantry_id)

    e = eater.Eater(parent=acct.key,
                    pantry=pantry.key,
                    first_name=first_name, last_name=last_name,
                    goal_weight=goal_weight_amt, lift_days=[0, 2, 4])
    if id_type == 'fb_id':
        e.fb_id = src_id
    logging.info('Eater created')
    e.set_weight(weight_amt)
    e.set_default_goal()
    ndb.put_multi([acct, p, e])
    logging.info('Entities saved')

    # Cache session id : entity keys for easy lookup in subsequent requests
    utils.cache_entities(session_id, account=acct, eater=e, pantry=p)

    return utils.apiai_response(request, displayText=responses.SIGNUP_SUCCESS)


def add_dislikes(request):
    pass


def add_diet():
    pass


def add_meal(request):
    logging.info('Action: add_meal')
    session_id = request['sessionId']
    cached_entities = utils.get_cached_entities(session_id)
    e = cached_entities.get('eater')
    if e is None:
        id_type, src_id = utils.get_source_id(session_id)
        if id_type == 'fb_id':
            e = eater.Eater.query(eater.Eater.fb_id == src_id).fetch(1)[0]

    params = request['result']['parameters']
    protein = params.get('protein')
    if protein is None:
        protein = 0
    carb = params.get('carb')
    if carb is None:
        carb = 0
    fat = params.get('fat')
    if fat is None:
        fat = 0
    e.add_meal(protein=protein, carb=carb, fat=fat)

    utils.cache_entities(session_id, eater=e)

    return utils.apiai_response(request,
                                displayText=responses.ADD_MEAL_SUCCESS)

# def create_eater_dislikes(request):
#     logging.info('Wit action: create_eater_dislikes')
#     text, context, entities, session_id = parse_wit_msg(request)
#     data = get_memcache_data(session_id)

#     dislikes = get_list_entity_values(entities, 'product')
#     if not dislikes:
#         data['dislikes'] = []
#         context['dislikes_text'] = 'nothing'
#         return context

#     data['dislikes'] = dislikes
#     context['dislikes_text'] = ', '.join(dislikes)
#     set_memcache_data(session_id, data)
#     return context

# def create_eater_diet(request):
#     logging.info('Wit action: create_eater_diet')
#     text, context, entities, session_id = parse_wit_msg(request)
#     data = get_memcache_data(session_id)

#     diet = first_entity_value(entities, 'diet')
#     if not diet:
#         context['diet_text'] = 'standard'
#         data['diet'] = None
#         return context

#     data['diet'] = diet
#     context['diet_text'] = diet
#     set_memcache_data(session_id, data)
#     return context


def get_remaining_nutrition(request):
    logging.info('Action: get_remaining_nutrition')
    session_id = request['sessionId']
    cached_entities = utils.get_cached_entities(session_id)
    e = cached_entities.get('eater')
    if e is None:
        id_type, src_id = utils.get_source_id(request)
        if id_type == 'fb_id':
            e = eater.Eater.query(eater.Eater.fb_id == src_id).fetch(1)[0]

    nut = e.get_remaining_nutrition()
    response = responses.GET_REMAINING_NUTRITION_SUCCESS.format(n=nut)

    utils.cache_entities(session_id, eater=e)

    return utils.apiai_response(request, displayText=response)

actions = {
    # 'use_pantry_item': create_account,
    'add_meal': add_meal,
    # 'get_recipe_instructions': create_account,
    'get_remaining_nutrition': get_remaining_nutrition,
    # 'add_pantry_item': create_account,
    # 'get_recipe_options': create_account,
    # 'use_recipe_ingredients': create_account,
    # 'get_recipe': create_account,
    # 'create_account': create_account,
    # 'create_pantry': create_pantry,
    # 'create_eater_weight': create_eater_weight,
    # 'create_eater_goal_weight': create_eater_goal_weight,
    # 'create_eater_dislikes': create_eater_dislikes,
    # 'create_eater_diet': create_eater_diet,
    # 'create_eater': create_eater
    'signup': signup
}
