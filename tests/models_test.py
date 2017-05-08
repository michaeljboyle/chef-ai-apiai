# Copyright 2015 Google Inc
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

# [START imports]
import unittest

from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext import testbed

from src.common import eater

import datetime
# [END imports]


# [START eater_test]
class EaterTestCase(unittest.TestCase):

    def setUp(self):
        # First, create an instance of the Testbed class.
        self.testbed = testbed.Testbed()
        # Then activate the testbed, which prepares the service stubs for use.
        self.testbed.activate()
        # Next, declare which service stubs you want to use.
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        # Clear ndb's in-context cache between tests.
        # This prevents data from leaking between tests.
        # Alternatively, you could disable caching by
        # using ndb.get_context().set_cache_policy(False)
        ndb.get_context().clear_cache()

# [END eater_test]

    # [START eater_teardown]
    def tearDown(self):
        self.testbed.deactivate()
    # [END eater_teardown]

    def test_nutrition_plan_insert(self):
        p = eater.NutritionPlan()
        p.put()
        self.assertEqual(0, p.protein)
        self.assertEqual(25, p.fiber_min)
        self.assertEqual(2000, p.sodium_max)

        # Check sat fat calc
        p.fat = 100
        p.put()
        self.assertEqual(30, p.satfat_max)

    def test_nutrition_record_insert(self):
        p = eater.NutritionRecord(protein=10, fat=10, carb=20)
        p.put()
        self.assertEqual(10, p.protein)
        # Check cals calc
        self.assertEqual(210, p.cals)

    # [START eater_insert]
    def test_eater_insert(self):
        e = eater.Eater(parent=ndb.Key('Account', 1),
                        pantry=ndb.Key('Pantry', 2), first_name='first',
                        last_name='last',
                        goal_weight=10.0, lift_days=[0,1,2],
                        dislikes=['farts'], diet='paleo')
        e.put()
        self.assertEqual(1, len(eater.Eater.query().fetch(2)))
    # [END eater_insert]

    # [START eater_set_weight]
    def test_eater_set_weight(self):
        e = eater.Eater()
        e.put()
        # First test adding a weight for the first time
        date = datetime.datetime.now()
        e.set_weight(20.0, date)
        self.assertEqual(20.0, e.weight.weight)
        self.assertEqual(date, e.weight.date)

        # Now add new weight and confirm old weight became history
        date_2 = date + datetime.timedelta(days=1)
        e.set_weight(30.0, date_2)
        self.assertEqual(30.0, e.weight.weight)
        weights = eater.Weight.query(ancestor=e.key).fetch(2)
        self.assertEqual(1, len(weights))
        self.assertEqual(20.0, weights[0].weight)
    # [END eater_set_weight]

    def test_eater_get_weight_hx(self):
        e = eater.Eater()
        e.put()
        # Add two weights
        date = datetime.datetime.now()
        eater.Weight(parent=e.key, weight=20.0, date=date).put()
        date_2 = date + datetime.timedelta(days=1)
        eater.Weight(parent=e.key, weight=30.0, date=date_2).put()
        # Check there are two weights in hx and that later one is first result
        weights = e.get_weight_hx()
        self.assertEqual(2, len(weights))
        self.assertEqual(30.0, weights[0].weight)

    def test_eater_set_default_goal(self):
        e = eater.Eater(parent=ndb.Key('Account', 1),
                        pantry=ndb.Key('Pantry', 2), first_name='first',
                        last_name='last',
                        goal_weight=10.0, lift_days=[0],
                        dislikes=['farts'], diet='paleo')
        e.put()
        # Add weight > goal_weight
        e.weight = eater.Weight(weight=20.0)
        e.set_default_goal()
        self.assertEqual(7, len(e.nutrition_plans))
        self.assertEqual(242, e.nutrition_plans[0].cals)
        self.assertEqual(21, e.nutrition_plans[0].protein)
        self.assertEqual(21, e.nutrition_plans[0].carb)
        self.assertEqual(8, e.nutrition_plans[0].fat)

        # Now test with weight < goal_weight accounting for lift days
        e.weight.weight = 5.0
        e.set_default_goal()
        self.assertEqual(7, len(e.nutrition_plans))
        # Check lift day
        self.assertEqual(665, e.nutrition_plans[0].cals)
        self.assertEqual(22, e.nutrition_plans[0].protein)
        self.assertEqual(103, e.nutrition_plans[0].carb)
        self.assertEqual(18, e.nutrition_plans[0].fat)
        # Check rest day
        self.assertEqual(265, e.nutrition_plans[1].cals)
        self.assertEqual(22, e.nutrition_plans[1].protein)
        self.assertEqual(28, e.nutrition_plans[1].carb)
        self.assertEqual(7, e.nutrition_plans[1].fat)

        # Test protein when goal weight > 15 lbs above current wt
        # Protein should not exceed 1 g/lb bodyweight + 15
        e.goal_weight = 100.0
        e.set_default_goal()
        self.assertEqual(26, e.nutrition_plans[0].protein)

    def test_eater_get_nutrition_hx(self):
        e = eater.Eater()
        e.put()
        # create nut rec with date of today and protein 0
        rec = eater.NutritionRecord(parent=e.key)
        rec.put()
        # create another with yesterday date and protein 1
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        rec_2 = eater.NutritionRecord(parent=e.key, date=yesterday, protein=1)
        rec_2.put()

        # Test days arg in query works
        self.assertEqual(1, len(e.get_nutrition_hx(1)))

        # Test returns both and order correct
        hx = e.get_nutrition_hx(3)
        self.assertEqual(2, len(hx))
        self.assertEqual(1, hx[1].protein)

    def test_eater_get_nutrition_today(self):
        e = eater.Eater()
        e.put()

        # First check when no hx exists
        rec = e.get_nutrition_today()
        self.assertEqual(0, rec.protein)

        # Now try modifying nutrition rec and checking for it
        rec.protein = 1
        rec.put()
        hx_rec = e.get_nutrition_today()
        self.assertEqual(1, hx_rec.protein)

        # Now make this an old record from 1 day ago, should return a new rec
        rec.date = datetime.datetime.now().date() - datetime.timedelta(days=1)
        rec.put()
        hx_rec = e.get_nutrition_today()
        self.assertEqual(0, hx_rec.protein)

    def test_eater_get_nutrition_plan_today(self):
        e = eater.Eater()
        e.nutrition_plans = [eater.NutritionPlan(protein=i) for i in range(7)]
        e.put()
        today = datetime.datetime.now().weekday()
        self.assertEqual(today, e.get_nutrition_plan_today().protein)

    def test_eater_add_meal(self):
        e = eater.Eater()
        e.put()

        # Create nut record for today
        r = eater.NutritionRecord(parent=e.key, protein=10, carb=20, fat=30)
        r.put()

        e.add_meal(protein=1, carb=2, fat=3, sodium=4, fiber=5)
        self.assertEqual(11, r.protein)
        self.assertEqual(22, r.carb)
        self.assertEqual(33, r.fat)
        self.assertEqual(4, r.sodium)
        self.assertEqual(5, r.fiber)

    def test_eater_get_remaining_nutrition(self):
        e = eater.Eater()
        e.nutrition_plans = [eater.NutritionPlan(protein=2, carb=4, fat=6,
                                                 cals=78)] * 7
        e.put()
        rec = eater.NutritionRecord(parent=e.key, protein=0, carb=1, fat=2)
        rec.put()
        nut = e.get_remaining_nutrition()
        self.assertEqual(2, nut['protein'])
        self.assertEqual(3, nut['carb'])
        self.assertEqual(4, nut['fat'])
        self.assertEqual(56, nut['cals'])


# [START main]
if __name__ == '__main__':
    unittest.main()
# [END main]