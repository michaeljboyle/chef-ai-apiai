import datetime
import time
from google.appengine.ext import ndb
from pantry import Pantry
from account import Account

import endpoints
from endpoints_proto_datastore.ndb import EndpointsModel
from endpoints_proto_datastore.ndb import EndpointsAliasProperty

from protorpc import messages

class Weight(ndb.Model):
    weight = ndb.FloatProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)


class NutritionPlan(ndb.Model):
    # P, F, C, Fiber in grams. Sodium in mg.
    protein = ndb.IntegerProperty(default=0)
    fat = ndb.IntegerProperty(default=0)
    carb = ndb.IntegerProperty(default=0) 
    cals = ndb.IntegerProperty(default=0)
    satfat_max = ndb.ComputedProperty(lambda self: int(self.fat * 0.3))
    fiber_min = ndb.IntegerProperty(default=25)
    sodium_max = ndb.IntegerProperty(default=2000)


class NutritionRecord(ndb.Model):
    # P, F, C, Fiber in grams. Sodium in mg.
    date = ndb.DateProperty(auto_now_add=True)
    protein = ndb.IntegerProperty(default=0)
    fat = ndb.IntegerProperty(default=0)
    satfat = ndb.IntegerProperty(default=0)
    carb = ndb.IntegerProperty(default=0)
    fiber = ndb.IntegerProperty(default=0)
    sodium = ndb.IntegerProperty(default=0)
    cals = ndb.ComputedProperty(
        lambda self: self.protein * 4 + self.carb * 4 + self.fat * 9)


class RecipeRating(ndb.Model):
    recipe_ident = ndb.StringProperty()
    rating = ndb.IntegerProperty(choices=(1, 2, 3, 4))


class RecipeRecord(ndb.Model):
    ident = ndb.StringProperty()
    date_used = ndb.DateProperty()


class Eater(EndpointsModel):
    """A model for representing an eater with dietary preferences and hx"""
    # Include special properties for setting parent in RPC
    # See: http://endpoints-proto-datastore.appspot.com/examples/keys_with_ancestors.html
    _parent = None

    # Special part to specific protorpc fields
    
    _message_fields_schema = ('id', 'parent', 'name', 'goal_weight',
                              'lift_days', 'dislikes', 'diet') 
    
    date_created = ndb.DateTimeProperty(auto_now_add=True)
    fb_id = ndb.StringProperty()
    pantry = ndb.KeyProperty(kind=Pantry)
    name = ndb.StringProperty()
    weight = ndb.StructuredProperty(Weight)
    goal_weight = ndb.FloatProperty()
    lift_days = ndb.IntegerProperty(repeated=True, choices=range(7))
    nutrition_plans = ndb.StructuredProperty(NutritionPlan, repeated=True)
    dislikes = ndb.StringProperty(repeated=True)
    #protein_goal_g = ndb.IntegerProperty()
    #fat_goal_g = ndb.IntegerProperty()
    #carb_goal_g = ndb.IntegerProperty() 
    #cal_goal = ndb.IntegerProperty()
    #satfat_max = ndb.IntegerProperty()
    #fiber_min = ndb.IntegerProperty(default=25)
    #sodium_max = ndb.IntegerProperty(default=2000)
    diet = ndb.StringProperty(choices=(
        'pescetarian', 'lacto vegetarian', 'ovo vegetarian', 'vegan', 'paleo',
        'primal', 'vegetarian'))

    def parent_set(self, value):
        if not isinstance(value, int):
            raise TypeError('Parent id must be an int.')
        self._parent = value
        if ndb.Key(Account, value).get() is None:
            raise endpoints.NotFoundException(
                    'Parent %s does not exist.' % value)
        self.key = ndb.Key(Account, self._parent, Eater, None)
        self._endpoints_query_info.ancestor = ndb.Key(Account, value)

    @EndpointsAliasProperty(setter=parent_set,
                            property_type=messages.IntegerField, required=True)
    def parent(self):
        if self._parent is None and self.key is not None:
            self._parent = self.key.parent().id()
        return self._parent

    def get_nutrition_today(self):
        most_recent = self.get_nutrition_hx(1)
        # # Must offset UTC date to local
        offset = datetime.timedelta(seconds=-time.timezone)
        if len(most_recent) > 0:
            raise ValueError('record date was {}. system date is {}'.format(most_recent[0].date, datetime.datetime.now()))
        if (most_recent and 
            most_recent[0].date + offset == datetime.datetime.now().date()):
            return most_recent[0]
        else:
            rec = NutritionRecord(parent=self.key)
            rec.put()
            #raise ValueError('record date was {}. system date is {}'.format(rec.date, datetime.datetime.now()))
            return rec

    def get_nutrition_plan_today(self):
        # where 0 is monday
        day_of_week = datetime.datetime.today().weekday()
        return self.nutrition_plans[day_of_week]

    def get_remaining_nutrition(self):
        nut = self.get_nutrition_today()
        plan = self.get_nutrition_plan_today()
        return {
            'cals': plan.cals - nut.cals,
            'protein': plan.protein - nut.protein,
            'carb': plan.carb - nut.carb,
            'fat': plan.fat - nut.fat,
            'fiber': plan.fiber_min - nut.fiber,
            'sodium': plan.sodium_max - nut.sodium
        }

    def get_nutrition_hx(self, days):
        return NutritionRecord.query(
            ancestor=self.key).order(-NutritionRecord.date).fetch(days)

    def get_weight_hx(self):
        return Weight.query(ancestor=self.key).order(-Weight.date).fetch()

    def get_recipe_hx(self):
        return RecipeRecord.query(ancestor=self.key).order(
            -RecipeRecord.date_used).fetch()

    def get_rating_hx(self):
        return RecipeRating.query(ancestor=self.key).fetch()

    def set_weight(self, wt, date=datetime.datetime.now()):
        if self.weight:
            wt_record = Weight(parent=self.key, weight=self.weight.weight,
                               date=self.weight.date)
            wt_record.put()
        self.weight = Weight(weight=wt, date=date)

    def set_default_goal(self):
        wt = self.weight.weight
        # Apply AFL wt loss guideline if deficit
        if wt > self.goal_weight:
            cal_goal = int(11 * self.goal_weight * 2.2)
            protein_goal_g = int(cal_goal * 0.35 / 4)
            carb_goal_g = protein_goal_g
            fat_goal_g = int((cal_goal - 4 *
                (carb_goal_g + protein_goal_g)) / 9)
            nut_plan = NutritionPlan(cals=cal_goal, protein=protein_goal_g,
                                     fat=fat_goal_g, carb=carb_goal_g)
            # set up plan by day
            self.nutrition_plans = [nut_plan] * 7
        else:
            # Apply Greek God guidelines
            maint = int(15 * wt * 2.2)
            protein = int(
                min(self.goal_weight * 2.2, wt * 2.2 + 15))
            # Set up plan by day
            plans = []
            for day in range(7):
                if day in self.lift_days:
                    cal_goal = maint + 500
                else:
                    cal_goal = maint + 100
                fat = int(cal_goal * 0.25 / 9)
                carb = int((cal_goal - protein * 4 - fat * 9) / 4)
                plans.append(NutritionPlan(cals=cal_goal, protein=protein,
                                           fat=fat, carb=carb))
                self.nutrition_plans = plans

    def set_goal_by_grams(self, p, c, f):
        nut_plan = NutritionPlan(cals = 4 * (c + p) + 9 * f, protein = p,
                                 fat = f, carb = c)

    def set_goal_by_composition_and_total(self, p, c, f, total=2000):
        nut_plan = NutritionPlan(cals = total, protein = int(total * p / 4),
                                 fat = int(total * f / 9),
                                 carb = int(total * c / 4))

    def add_meal(self, protein=0, carb=0, fat=0, sodium=0, fiber=0,
                 date=None):
        nut_today = self.get_nutrition_today()
        nut_today.protein += protein
        nut_today.carb += carb
        nut_today.fat += fat
        nut_today.sodium += sodium
        nut_today.fiber += fiber
        nut_today.put()

    def rate_recipe(self, recipe_ident, rating, date):
        pass


