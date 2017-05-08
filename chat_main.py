# Copyright 2016 Google Inc.
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

# [START app]
import logging
from datetime import datetime

from google.appengine.api import memcache

from src.chat import chat
from src.chat.utils import apiai_response

from flask import Flask, request, jsonify

app = Flask(__name__)

# API AI POST webhook
@app.route('/apiai-webhook', methods=['POST'])
def apiai_post():
    """
    Handler for webhook (currently for postback and messages)
    """
    data = request.get_json()
    logging.info('APIAI POST webhook')
    logging.info(data)
    if 'result' in data:
        result = data['result']
        
        # We retrieve the message content
        text = result['resolvedQuery']
        logging.info('Message text: %s' % text)
        # Let's forward the message to the action handler
        if 'action' in result and not result.get('actionIncomplete'):
            action = result['action']
            logging.info('Action is: %s' % action)
            if action in chat.actions:
                response = chat.actions[action](data)
                logging.info('Action response:')
                logging.info(response)
                return jsonify(response)
            else:
                logging.error('Action %s not in actions' % action)


@app.errorhandler(500)
def server_error(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred.', 500
# [END app]
