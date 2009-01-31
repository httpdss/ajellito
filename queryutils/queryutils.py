"""
This module is used to implement a very simple query/search language bound to
some model for a webapp. The idea is to have a simple way in which users of a 
webapp can specify a search/query in some written form (a textbox). 

The syntax of a query language is:
    
    keyword1:value1 keyword2:value2 keyword3:value3
        
        where values can be string, numbers or expresions of the form 'bl*h'
        (some 'glob' expresions) 
    
For example, we have the model Author which has the fields: firstname, surname, 
etc. The user would type something like this in a textbox: 'surname:*smith*'.

What we would like to do is map a keyword with a field of some model and make a
query related to the field. Parse the input string and generate a query 
for the Author model. Something of the form:
    
    Author.objects.filter(surname__iregex='.*smith.*')
    
Of course we could map both firstname a surname into one keyword, so the users
can type 'name:*smith*' and the resulting query would be:

    Author.objects.filter(surname__iregex='.*smith.*',
                          firstname__iregex='.*smith.*')


So summing up, we have a string which is of the form:

    keyword1:value1 keyword2:value2 keyword3:value3

and the keywords map to some model attributes'

    keyword1 -> Author.firstname, keyword1 -> Author.surname

and for those attributes we construct a query (using Q objects)
 
    qset = Q(firstname__OP=value1)
    
and then:
    
    Author.objects.filter(qset)

The OP also depends on your keyword, for example for the keyword 'name' 
we mapped it to a iregex. (So you can conclude that we map a keyword to
a field name and type of query)

How do I use it then?

First you have to define a 'grammar', by specifing a dict which contains as
keys the keywords of the your syntax and object which specifies the field and
type of query you need


keys = { ## We map the 'keyword' company to the field name and the op will be
         ## __iregex. When we call SearchGlobOp('name').generate_query(value1)
         ## we get an object Q of the form Q(name__iregex=value1)
         'company' : SearchGlobOp('name'),
         
         ## SearchEqualOp(...).generate_query(value) returns the following:
         ## Q(id=value) & Q(duns=value) & Q(cusip=int_value)
         ## where int_value is int(value) or 0 in case int(value)
         ## raises ValueError 
         'id' : SearchEqualOp('id', 'duns', ('cusip',int,0)),
         
         ## Same as above but we are making a reference to a field in another
         ## model. So now we get: Q(foreignkey__foreignkeyfield__icontains=value)
         ## when calling generate_query method 
         'including' : SearchEqualOp('foreignkey__foreignkeyfield__icontains'),
         
         ## You can also wrap sql queries...
         'rating_low__numeric' : SearchExtraSQL(sql, *args), 
        }


define an ordering:

_ORDERING = [
    'name', ## your models fieldnames
    'sic',
]
    
create query generator:

sg = SearchQueryGenerator(keys,      ## Grammar

                         'company',  ## This is the 'blank keyword'
                                     ## so instead of typing company:value1
                                     ## the user can just type value1 and
                                     ## the parser will parse this as
                                     ## company:value1 
                         
                         Company)    ## model   

this actually does everything, parses, creates Q objects, and returs
a queryset, the last three arguments are optional, wheres is a list
of sql statements that go after filter(...).where(wheres),
ordering is the ordering of the results, and startingqset is
the queryset to which we apply filter(...), by default is model.objects.all()
but if you can override it with this argument.

sg.make_query(search_query, wheres, ordering, startingqset)


Comments: There are some parse test included but no test for the model querying
as the models where part of proprietary software
    
ToDo: Support more operations
      Tests
"""


# -*- coding: utf-8 -*-

import re
import math
import operator


from django.db.models.query import Q

## Pattern used to parse the query string given as input by the user
_pat = re.compile(r'(?:(?P<header>\w+):)?(?P<value>(?:(?:"(?:[^"]+"|[^"]+$))|\S+))')

class SearchOp (object):
    def is_query_generator (self):
        return (hasattr(self, 'generate_query'))

    def is_sql_generator (self):
        return (hasattr(self, 'generate_sql'))

class SearchGlobOp(SearchOp):
    
    def __init__ (self, *fields):
        self.fields = fields
        self._op_suffix = '__iregex'

    def generate_query (self, value):
        v = self._glob2regexp(value)
        qset = Q()
        for field in self.fields:
            if field.startswith("^"):
                k = field.lstrip("^")+self._op_suffix
                qset = qset | ~Q(**{k:v})

            else: 
                k = field+self._op_suffix
                qset = qset | Q(**{k:v})
        return qset

    def _glob2regexp (self, glob):
        regexp = ['^']
        for char in glob:
            if char == '*':
                regexp.append('.*')
            elif char == '?':
                regexp.append('.')
            elif char in '([.\])':
                regexp.append('\\' + char)
            else:
                regexp.append(char)
        return ''.join(regexp)

class SearchEqualOp(SearchOp):
    
    def __init__ (self, *fields):
        self.fields = fields

    def generate_query (self, value):
        qset = Q()
        for field in self.fields:
            k = field
            if isinstance(field, tuple):
                if len(field) == 3:
                    k, func, default = field
                    try:
                        value = func (value)
                    except ValueError:
                        value = default
                else:
                    raise ValueError, 'The tuple should have a length of 3:' + \
                                      ' (<field name>,<func>,<default value>)'
            if k.startswith("^"):
                k = field.lstrip("^")
                qset = qset | ~Q(**{k:value})

            else: 
                qset = qset | Q(**{k:value})
        return qset

class SearchExtraSQL(SearchOp):
    
    def __init__ (self, sql_string, *values):
        self.sql_string = sql_string
        self.args = values
    
    def generate_sql (self, value):
        return (self.sql_string %(self.args)) %(value)

class SearchQueryGenerator:

    def __init__(self, search_keywords, blank_key, klass):
        self.search_keywords = {}
        self.num_key_list = []
        for k in search_keywords.iterkeys():
            value = search_keywords.get(k)
            if not k.endswith('__numeric'):
                self.search_keywords[k] = value
            else:
                new_key = k[:-9]
                self.search_keywords[new_key] = value
                self.num_key_list.append(new_key)
        self.blank_key = blank_key
        self.klass = klass
        self.search_ops = {'AND': operator.and_, 'OR': operator.or_}


    def parse_search_query(self, query_string):
        iterator = _pat.finditer(query_string)
        search_env = []
        default_op = next_op = self.search_ops['AND']
        for match in iterator:
            key, value = (match.group('header'), match.group('value'))
            value = value.strip(r'" ')
            if self.search_keywords.has_key(key):
                #Convert string to a two digit float truncating at the second digit.
                if key in self.num_key_list:
                    try:
                        value = math.floor(float(value)*100)/100
                    except ValueError:
                        value = 0
                search_env.append((next_op, key, value))
                next_op = default_op
            elif key == '' or key == None:
                if value in self.search_ops:
                    next_op = self.search_ops[value]
                else:
                    search_env.append((next_op, self.blank_key, value))
                    next_op = default_op
        return search_env


    def make_query(self, search_query, wheres=[],
                   ordering=tuple(), init_q_set=None):
        qset = Q()
        for op, k, v in self.parse_search_query(search_query):
         
            q_object = None
            search_op =  self.search_keywords.get(k)
         
            if search_op != None:
                if search_op.is_query_generator():
                    q_object = search_op.generate_query(v) 
                elif search_op.is_sql_generator():
                    wheres.append(search_op.generate_sql(v))
         
            if q_object is not None:
                qset = op(qset, q_object)
        
        if init_q_set != None:
            q = init_q_set
        else:
            q = self.klass.objects.all()
            
        q = q.filter(qset).extra(where=wheres)
        return q.distinct()   