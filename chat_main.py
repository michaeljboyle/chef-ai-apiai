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

from wit import Wit

from src.chat import chat

from flask import Flask, request

# Wit.ai parameters
WIT_TOKEN = 'A5AQ6CLPTXEBFXAD7YMR3Y7QIVWORCWQ'


app = Flask(__name__)

# Facebook messenger GET webhook
@app.route('/webhook', methods=['GET'])
def messenger_get():
    """
    A webhook to return a challenge
    """
    logging.info('Messenger GET webhook')
    logging.info(request.form)
    verify_token = request.args.get('hub.verify_token', '')
    # check whether the verify tokens match
    if verify_token == FB_VERIFY_TOKEN:
        # respond with the challenge to confirm
        return request.args.get('hub.challenge', '')
    else:
        return 'Invalid Request or Verification Token'

# Facebook messenger POST webhook
@app.route('/webhook', methods=['POST'])
def messenger_post():
    """
    Handler for webhook (currently for postback and messages)
    """
    data = request.get_json()
    logging.info('Messenger POST webhook')
    logging.info(data)
    if data['object'] == 'page':
        for entry in data['entry']:
            # get all the messages
            messages = entry['messaging']
            if messages[0]:
                # Get the first message
                message = messages[0]
                # Yay! We got a new message!
                # We retrieve the Facebook user ID of the sender
                fb_id = message['sender']['id']
                timestamp = message['timestamp']
                # Check if there is an ongoing convo with this fb_id, or gen new
                sm = chat.session_manager
                session_id = sm.open_session(fb_id, timestamp)
                
                # Retrieve cached context
                memcache_key = '{}.context'.format(session_id)
                context = memcache.get(memcache_key)
                if context is None:
                    context = {}
                # We retrieve the message content
                text = message['message']['text']
                logging.info('Messenger message text: %s' % text)
                # Let's forward the message to the Wit.ai Bot Engine
                # We handle the response in the function send()
                context = client.run_actions(session_id=session_id,
                                             context=context, 
                                             message=text,
                                             max_steps=10)
                # Cache context for 5 minutes
                logging.info('Caching context')
                logging.info(context)
                set_ok = memcache.set(memcache_key, context, 60 * 5)
                if not set_ok:
                    logging.error('Memcache failed to set context')
    else:
        # Returned another event
        return 'Received Different Event'
    return ''

@app.errorhandler(500)
def server_error(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred.', 500
# [END app]

# Setup Wit Client
client = Wit(access_token=WIT_TOKEN, actions=chat.ACTIONS, logger=logging)
