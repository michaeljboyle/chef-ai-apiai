import logging
import json

from google.appengine.ext import ndb
import urllib
from google.appengine.api import urlfetch

from pantry import PantryItem, Food
from account import Account
from eater import Eater


MASHAPE_KEY = 'GoKMxAXMPfmshJjg608MY2zAsyGRp1baUNxjsnAC2DVxSi4P5P'
SPOONACULAR_API_URL = ('https://spoonacular-recipe-food-nutrition-v1.'
                       'p.mashape.com/')


def convert_amount(q, u):
    if u.lower() in ['g', 'grams', 'gs']:
        return (q, 'g')
    if u.lower() in ['pounds', 'pound', 'lbs', 'lb']:
        return (454 * q, 'g')
    if u.lower() in ['ounces', 'ounce', 'oz', 'ozs']:
        return (28.3 * q, 'g')


def create_account(name, email):
    acc = Account(name, email)
    return acc.put().urlsafe()


# Pantry mgmt
def add_pantry_item(pantry, text, food=None, number=None,
                    weight_amt=None, weight_unit=None):
    # send to spoonacular to parse ingredients
    url = SPOONACULAR_API_URL + 'recipes/parseIngredients'
    headers = {
        "X-Mashape-Key": MASHAPE_KEY,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    params = {
        "ingredientList": text,
        "servings": 1
    }
    response = urlfetch.fetch(
        url,
        payload=urllib.urlencode(params),
        method=urlfetch.POST,
        headers=headers,
        deadline=60)
    logging.info('Response from spoonacular: %s' % response.content)
    data = json.loads(response.content)[0]
    if not data.get('unitShort'):
        weight_unit = None
        amount = data.get('amount')
    else:
        amount, weight_unit = convert_amount(data.get('amount'),
                                             data.get('unitShort'))

    # Create a pantry item
    pi = PantryItem(
        food=Food(
            name=data.get('name'),
            spoonacular_id=data.get('id'),
            lasts_days=7),
        initial_quantity=amount,
        initial_quantity_unit=weight_unit,
        percent_remaining=100)

    pi.put()
    pi.set_expiration_date()

    # Add the item to the pantry
    pi.put()

    # Return item object
    o = {'name': pi.food.name, 'expDays': pi.food.lasts_days}
    if pi.initial_quantity_unit:
        o['quantity'] = '{} {}'.format(pi.initial_quantity,
                                       pi.initial_quantity_unit)
    else:
        o['quantity'] = pi.initial_quantity
    return o


# Meals and tracking
def add_meal(eater_urlkey):
    pass


# Getting setting goals
def get_remaining_goals(eater_id):
    eater = ndb.Key(Eater, eater_id).get()
    return eater.get_remaining_nutrition()


# Recipes
def get_makeable_recipes(eater_urlkey, query, meal_type='main course',
                         cuisine=''):
    eater = ndb.Key(urlsafe=eater_urlkey).get()
    pantry = eater.pantry.get()
    item_list = ','.join([item.food.name for item in pantry.items])
    nutrition = eater.get_remaining_nutrition()
    # Set protein requirement if main course
    if meal_type is 'main course':
        min_protein = min(nutrition.protein, eater.protein_goal_g / 2)
    headers = {
        'X-Mashape-Key': MASHAPE_KEY,
        'Accept': 'application/json'
    }
    params = {
        'addRecipeInformation': False,
        'type': meal_type,
        'cuisine': cuisine,
        'diet': eater.diet,
        'includeIngredients': item_list,
        'intolerances': ','.join(eater.dislikes),
        'maxCalories': nutrition.cals,
        'maxCarbs': nutrition.carb,
        'maxFat': nutrition.fat,
        'minProtein': min_protein,
        'ranking': 1,
        'query': query,
        'number': 5,
        'offset': 0,
        'limitLicense': False
    }
    r = requests.get(
        ('https://spoonacular-recipe-food-nutrition-v1.p.mashape.com/recipes'
         '/searchComplex'), params=param, headers=headers)
    return r.json()


def rate_recipe():
    pass
