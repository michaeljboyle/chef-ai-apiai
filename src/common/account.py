from google.appengine.ext import ndb
from endpoints_proto_datastore.ndb import EndpointsModel

class Account(EndpointsModel):
  """A model for representing an a account"""
  # Special part to specific protorpc fields
  _message_fields_schema = ('id', 'name', 'email', 'fb_id')

  date_created = ndb.DateTimeProperty(auto_now_add=True)
  name = ndb.StringProperty()
  email = ndb.StringProperty()
  fb_id = ndb.StringProperty()