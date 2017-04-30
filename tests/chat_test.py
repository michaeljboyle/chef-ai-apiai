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

from src.chat import chat
from src.common import eater
from src.chat.utils import SessionManager

import datetime
# [END imports]


# [START eater_test]
class ChatTestCase(unittest.TestCase):

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

    def test_utils_session_manager(self):
        fb_id = 'abc'
        t1 = '123'
        t2 = '456'

        sm = SessionManager()
        sid = sm.open_session(fb_id, t1)
        self.assertEqual('abc.123', sid)
        self.assertEqual('abc', sm.fb_id())
        self.assertEqual('123', sm.timestamp())
        self.assertEqual('abc.123', sm.session_id())
        # Check caching works
        sid = sm.open_session(fb_id, t2)
        self.assertEqual('abc.123', sid)
        self.assertEqual('123', sm.timestamp())
        # Test end_session uncaches
        sm.end_session()
        sid = sm.open_session(fb_id, t2)
        self.assertEqual('abc.456', sid)

    def test_chat_get_remaining_nutrition(self):
        request = {
            'session_id': 'abc.123',
            'text': '',
            'context': {},
            'entities': {}
        }
        e = eater.Eater(parent=ndb.Key('Account', 9), id='abc', fb_id='abc')
        e.nutrition_plans = [eater.NutritionPlan(protein=2, carb=4, fat=6,
                                                 cals=78)] * 7
        def get_remaining_nutrition_patch():
            return {
                'cals': 0,
                'protein': 0,
                'carb': 0,
                'fat': 0,
                'fiber': 0,
                'sodium': 0
            }
        e.get_remaining_nutrition = get_remaining_nutrition_patch
        e.put()
        context = chat.get_remaining_nutrition(request)
        self.assertEqual(0, context['cals'])
        self.assertTrue(context['complete'])

        # rec = eater.NutritionRecord(parent=e.key, protein=0, carb=1, fat=2)
        # rec.put()
        # nut = e.get_remaining_nutrition()
        # self.assertEqual(2, nut['protein'])
        # self.assertEqual(3, nut['carb'])
        # self.assertEqual(4, nut['fat'])
        # self.assertEqual(56, nut['cals'])



# [START main]
if __name__ == '__main__':
    unittest.main()
# [END main]