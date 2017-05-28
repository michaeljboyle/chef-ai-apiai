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
import mock

from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext import testbed

from src.chat import chat
from src.common import eater, pantry
import src.chat.utils as utils
import src.chat.response_text as responses

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

    def test_utils_apiai_response(self):
        # test defaults
        r = utils.apiai_response({}, displayText='test')
        self.assertEqual('test', r['displayText'])
        self.assertEqual('test', r['speech'])
        self.assertEqual(None, r.get('data'))

        # Test setting
        r = utils.apiai_response({}, displayText='test', speech='test2',
                                 data={'a': 1})
        self.assertEqual(1, r.get('data').get('a'))

    def test_utils_get_source_id(self):
        # test defaults
        r = {
                'originalRequest': {
                    'source': 'facebook',
                    'data': {
                        'sender': {
                            'id': 123
                        }
                    }
                }
        }
        id_type, sender_id = utils.get_source_id(r)
        self.assertEqual('fb_id', id_type)
        self.assertEqual(123, sender_id)

    def test_utils_make_memcache_key(self):
        self.assertEqual('123.entities', utils._make_memcache_key('123'))

    @mock.patch('src.chat.utils._make_memcache_key')
    def test_utils_get_cached_entities(self, mock_memcache_key_maker):
        memcache.set('123.entities.account', 'abc')
        mock_memcache_key_maker.return_value = '123.entities'
        self.assertEqual('abc',
                         utils.get_cached_entities('123').get('account'))
        mock_memcache_key_maker.assert_called_with('123')

    @mock.patch('src.chat.utils._make_memcache_key')
    def test_utils_cache_entities(self, mock_memcache_key_maker):
        mock_memcache_key_maker.return_value = '123.entities'
        utils.cache_entities('123', account='a', eater='b', pantry='c')
        mock_memcache_key_maker.assert_called_with('123')
        account = memcache.get('123.entities.account')
        eater = memcache.get('123.entities.eater')
        pantry = memcache.get('123.entities.pantry')
        self.assertEqual('a', account)
        self.assertEqual('b', eater)
        self.assertEqual('c', pantry)

    @mock.patch('src.chat.utils.get_cached_entities')
    @mock.patch('src.chat.utils.get_source_id')
    def test_chat_get_eater_from_request(self, mock_get_source_id,
                                         mock_get_cached_entities):
        mock_get_cached_entities.return_value = {}
        mock_get_source_id.return_value = ('fb_id', '123')
        # Check queries for entity when none cached
        request = {'sessionId': None}
        e = eater.Eater(fb_id='123')
        e.put()
        queried1 = chat.get_eater_from_request(request)
        self.assertEqual('123', queried1.fb_id)

        # Now test value returned from memcache
        e.fb_id = '456'
        e.put()
        mock_get_cached_entities.return_value = {'eater': e}
        queried2 = chat.get_eater_from_request(request)
        self.assertEqual('456', queried2.fb_id)

    @mock.patch('src.chat.utils.get_cached_entities')
    @mock.patch('src.chat.chat.get_eater_from_request')
    def test_chat_get_pantry_from_request(self, get_eater,
                                          get_cached_entities):
        get_cached_entities.return_value = {}
        # Check queries for entity when none cached
        request = {'sessionId': None}
        p = pantry.Pantry(address='abc')
        k = p.put()
        e = eater.Eater(pantry=k)
        get_eater.return_value = e

        queried1 = chat.get_pantry_from_request(request)
        self.assertEqual('abc', queried1.address)

        # Now test value returned from memcache
        get_cached_entities.return_value = {
            'pantry': pantry.Pantry(address='def')
        }
        queried2 = chat.get_pantry_from_request(request)
        self.assertEqual('def', queried2.address)

    @mock.patch('src.chat.utils.cache_entities')
    @mock.patch('src.chat.chat.get_eater_from_request')
    @mock.patch('src.chat.utils.apiai_response')
    @mock.patch.object(eater.Eater, 'get_remaining_nutrition')
    def test_chat_get_remaining_nutrition(self, mock_get_remaining_nutrition,
                                          api_response, mock_get_eater,
                                          cache_entities):
        e = eater.Eater(fb_id='123')
        mock_get_eater.return_value = e
        api_response.return_value = 'apiai response'
        nut = {
            'cals': 1,
            'protein': 2,
            'fat': 3,
            'carb': 4,
            'fiber': 5,
            'sodium': 6
        }
        mock_get_remaining_nutrition.return_value = nut
        request = {'sessionId': 'abc123'}

        response = chat.get_remaining_nutrition(request)
        mock_get_eater.assert_called_with(request)
        mock_get_remaining_nutrition.assert_called()
        cache_entities.assert_called_with('abc123', eater=e)
        api_response.assert_called_with(
            request,
            displayText=responses.GET_REMAINING_NUTRITION_SUCCESS.format(
                n=nut))
        self.assertEqual('apiai response', response)

        # Check in actions
        self.assertTrue('get_remaining_nutrition' in chat.actions)

    @mock.patch('src.chat.utils.cache_entities')
    @mock.patch('src.chat.chat.get_pantry_from_request')
    @mock.patch('src.chat.utils.apiai_response')
    @mock.patch('src.common.chef.add_pantry_item')
    @mock.patch.object(eater.Eater, 'pantry')
    def test_chat_add_pantry_item(self, mock_pantry, chef_add_pantry_item,
                                  api_response, get_pantry,
                                  cache_entities):
        p = pantry.Pantry()
        get_pantry.return_value = p
        api_response.return_value = 'apiai response'
        item = {
            'name': 'apple',
            'quantity': '1',
            'expDays': '10'
        }
        chef_add_pantry_item.return_value = item
        request = {
            'sessionId': 'abc123',
            'result': {
                'resolvedQuery': 'Add 1 apple to my pantry',
                'parameters': {
                    'food': 'apple',
                    'number': '1',
                    'unit-weight': {
                        'amount': 2,
                        'unit': 'lb'
                    }
                }
            }
        }

        response = chat.add_pantry_item(request)
        get_pantry.assert_called_with(request)
        chef_add_pantry_item.assert_called_with(
            p, 'Add 1 apple to my pantry',
            food='apple', number=1,
            weight_amt=2, weight_unit='lb')
        cache_entities.assert_called_with('abc123', pantry=p)
        api_response.assert_called_with(
            request,
            displayText=responses.ADD_PANTRY_ITEM_SUCCESS.format(i=item))
        self.assertEqual('apiai response', response)

        # Check in actions
        self.assertTrue('add_pantry_item' in chat.actions)


# [START main]
if __name__ == '__main__':
    unittest.main()
# [END main]
