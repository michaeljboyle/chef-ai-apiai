# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Google Cloud Endpoints sample application.

Demonstrates how to create a simple echo API as well as how to deal with
various authentication methods.
"""
"""
import base64
import json
import logging

from flask import Flask, jsonify, request
from flask_cors import cross_origin
from six.moves import http_client
"""
import endpoints
from protorpc import message_types
from protorpc import messages
from protorpc import remote
from endpoints_proto_datastore.ndb import EndpointsModel
from google.appengine.ext import ndb

"""
BEGIN IMPORTS FOR ACTIONS
"""

import chef
from account import Account
from pantry import Pantry
from eater import Eater

# Create the api collection
chef_api = endpoints.api(name='chef', version='v1')


@chef_api.api_class(resource_name='accounts')
class AccountApi(remote.Service):

    # Create account
    @Account.method(path='accounts', http_method='POST', name='account.insert')
    def AccountInsert(self, account):
        account.put()
        return account

    # Get a account by id
    @Account.method(request_fields=('id',), path='accounts/{id}',
                    http_method='GET', name='account.get')
    def AccountGet(self, account):
        if not account.from_datastore:
            raise endpoints.NotFoundException('Account not found.')
        else:
            return account

    # Delete account
    @Account.method(request_fields=('id',), path='accounts/{id}',
                    http_method='DELETE', name='account.delete')
    def AccountDelete(self, account):
        if not account.from_datastore:
            raise endpoints.NotFoundException('Account not found.')
        else:
            account.key.delete()
            return account


@chef_api.api_class(resource_name='pantries')
class PantryApi(remote.Service):

    # Create pantry
    @Pantry.method(path='pantries', http_method='POST', name='pantry.insert')
    def PantryInsert(self, pantry):
        pantry.put()
        #print pantry.id
        return pantry

    # Get a pantry by id
    @Pantry.method(request_fields=('id', 'parent',),
                   path='pantries/{parent}/{id}', http_method='GET',
                   name='pantry.get')
    def PantryGet(self, pantry):
        #print pantry.key
        pantry.UpdateFromKey(
            ndb.Key(Account, pantry.parent, Pantry, pantry.key.id()))
        if not pantry.from_datastore:
            raise endpoints.NotFoundException('Pantry not found.')
        else:
            return pantry

    # Delete a pantry
    @Pantry.method(request_fields=('id', 'parent',),
                   path='pantries/{parent}/{id}',
                   http_method='DELETE', name='pantry.delete')
    def PantryDelete(self, pantry):
        pantry.UpdateFromKey(
            ndb.Key(Account, pantry.parent, Pantry, pantry.key.id()))
        if not pantry.from_datastore:
            raise endpoints.NotFoundException('Pantry not found.')
        else:
            pantry.key.delete()
            return pantry


@chef_api.api_class(resource_name='eaters')
class EaterApi(remote.Service):

    # Create eater
    @Eater.method(
        request_fields=('parent', 'name', 'goal_weight', 'lift_days',
                        'dislikes', 'diet',),
        response_fields=('id', 'parent', 'name', 'goal_weight', 'lift_days',
                        'dislikes', 'diet',),
        path='eaters', http_method='POST', name='eater.insert')
    def EaterInsert(self, eater):
        #eater.UpdateFromKey(ndb.Key(Account, eater.parent, Eater, eater.key.id()))
        eater.put()
        print eater.key
        return eater

    # Get eater
    @Eater.method(request_fields=('id', 'parent',), path='eaters/{parent}/{id}',
                    http_method='GET', name='eater.get')
    def EaterGet(self, eater):
        print eater.key
        eater.UpdateFromKey(
            ndb.Key(Account, eater.parent, Eater, eater.key.id()))
        print eater.key
        if not eater.from_datastore:
            raise endpoints.NotFoundException('Eater not found.')
        else:
            return eater

    # Delete eater
    @Eater.method(request_fields=('id', 'parent',), path='eaters/{parent}/{id}',
                  http_method='DELETE', name='eater.delete')
    def EaterDelete(self, eater):
        eater.UpdateFromKey(
            ndb.Key(Account, eater.parent, Eater, eater.key.id()))
        if not eater.from_datastore:
            raise endpoints.NotFoundException('Eater not found.')
        else:
            eater.key.delete()
            return eater

# Begin chef message definitions
class RecipeRequest(messages.Message):
    meal_type = messages.StringField(1)
    cook_time = messages.StringField(2)


class RecipeSummaryResponse(messages.Message):
    """A proto Message that contains a simple string field."""
    recipes = messages.StringField(1)

class AddPantryItemRequest(messages.Message):
    product = messages.StringField(1)
    quantity = messages.FloatField(2)
    unit = messages.StringField(3)

class RecipeSummaryResponse(messages.Message):
    """A proto Message that contains a simple string field."""
    recipes = messages.StringField(1)


ECHO_RESOURCE = endpoints.ResourceContainer(
    EchoRequest,
    n=messages.IntegerField(2, default=1))
@chef_api.api_class(resource_name='chef', path='chef')
class AccountApi(remote.Service):


# Begin Chef API


#@chef_api.api_class(resource_name='chef', path='chef')
#class ChefApi(remote.Service):


# [END chef_api]


# [START api_server]
api = endpoints.api_server([chef_api])
# [END api_server]
