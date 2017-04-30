from google.appengine.ext import ndb

class Food(ndb.Model):
  """A model for representing a food item"""
  name = ndb.StringProperty()
  spoonacular_id = ndb.StringProperty()
  upc = ndb.StringProperty()
  lasts_days = ndb.IntegerProperty()
  # unit = ndb.StringProperty(choices=[''])