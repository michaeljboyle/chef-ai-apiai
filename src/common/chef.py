from google.appengine.ext import ndb
# from pantry import Pantry
import requests
from account import Account
from eater import Eater

MASHAPE_KEY = 'GoKMxAXMPfmshJjg608MY2zAsyGRp1baUNxjsnAC2DVxSi4P5P'

def create_account(name, email):
    acc = Account(name, email)
    return acc.put().urlsafe()


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



