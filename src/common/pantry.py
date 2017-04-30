from google.appengine.ext import ndb
import endpoints
from endpoints_proto_datastore.ndb import EndpointsModel
from endpoints_proto_datastore.ndb import EndpointsAliasProperty

from protorpc import messages

from account import Account

class Food(ndb.Model):
    """A model for representing a food item"""
    name = ndb.StringProperty()
    spoonacular_id = ndb.StringProperty()
    upc = ndb.StringProperty()
    lasts_days = ndb.IntegerProperty()


def percent_validator(prop, value):
    if value > 100:
        return 100
    if value < 0:
        return 0


class PantryItem(ndb.Model):
    """A model for representing a food item"""
    """
    _parent = None
    # Special part to specific protorpc fields
    _message_fields_schema = ('id', 'parent', 'food', 'initial_quantity',
                              'initial_quantity_unit', 'percent_remaining',
                              'start_date', 'expiration_date')
    """
    food = ndb.StructuredProperty(Food)
    initial_quantity = ndb.IntegerProperty()
    initial_quantity_unit = ndb.StringProperty(choices=('g', 'ml'))
    percent_remaining = ndb.IntegerProperty(validator=percent_validator)
    start_date = ndb.DateProperty()
    expiration_date = ndb.DateProperty()

    def set_expiration_date(self, date):
        if not date:
            self.expiration_date = self.start_date + self.food.lasts_days
        else:
            self.expiration_date = date


class ShoppingListItem(ndb.Model):
    name = ndb.StringProperty()
    amount = ndb.StringProperty()


class Pantry(EndpointsModel):
    """A model for representing all food storage in a kitchen""" 
    _parent = None
    # Special part to specific protorpc fields
    _message_fields_schema = ('id', 'parent', 'address', 'timezone') 

    date_created = ndb.DateTimeProperty(auto_now_add=True)
    address = ndb.StringProperty()
    timezone = ndb.StringProperty()

    def parent_set(self, value):
        if not isinstance(value, int):
            raise TypeError('Parent id must be an int.')
        self._parent = value
        if ndb.Key(Account, value).get() is None:
            raise endpoints.NotFoundException(
                    'Parent %s does not exist.' % value)
        self.key = ndb.Key(Account, self._parent, Pantry, None)
        self._endpoints_query_info.ancestor = ndb.Key(Account, value)

    @EndpointsAliasProperty(setter=parent_set,
                            property_type=messages.IntegerField, required=True)
    def parent(self):
        if self._parent is None and self.key is not None:
            self._parent = self.key.parent().id()
        return self._parent
  
    @property
    def items(self):
        return PantryItem.query(ancestor=self.key)

    @property
    def shopping_list(self):
        return ShoppingListItem.query(ancestor=self.key)