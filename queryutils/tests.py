from django.db.models.query import Q

import operator
import unittest
import queryutils

class ParseSearchQueryTestCase(unittest.TestCase):
    
    def setUp (self):
        ## stub
        keys = { 'company' : None,
                 'industry' : None,
                 'id' : None,
                 'including' : None,
                 'excluding' : None,
                 'rating_low__numeric' : None,
                 'rating_high__numeric' : None,
                 'community_high__numeric' : None,
                 'community_low__numeric' : None,
                 'governance_low__numeric' : None,
                 'governance_high__numeric' : None,
                 'employees_low__numeric' : None,
                 'employees_high__numeric' : None,
                 'environment_low__numeric' : None,
                 'environment_high__numeric' : None, }
        self.search_obj = queryutils.SearchQueryGenerator(keys,
                                                          'company',
                                                          ## Stub, here should go the 
                                                          ## model's class.
                                                          None)

    def testHasparse_search_query(self):
        self.assert_(hasattr(queryutils.SearchQueryGenerator, 'parse_search_query'))

    def testparse_search_query_0(self):
        query = " company:GM industry:341 "
        result = [(operator.and_, 'company', 'GM'),
                  (operator.and_, 'industry', '341')]
        self.assertEqual(self.search_obj.parse_search_query(query), result)

    def testparse_search_query_1(self):
        query = " GM industry:341 "
        result = [(operator.and_, 'company', 'GM'), (operator.and_, 'industry', '341')]
        self.assertEqual(self.search_obj.parse_search_query(query), result)

    def testparse_search_query_2(self):
        query = " garbage company:GM  &%$  industry:341 more"
        result = [(operator.and_, 'company', 'garbage'), (operator.and_, 'company', 'GM'),
                  (operator.and_, 'company', '&%$'), (operator.and_, 'industry', '341'),
                  (operator.and_, 'company', 'more')]
        self.assertEqual(self.search_obj.parse_search_query(query), result)

    def testparse_search_query_3(self):
        query = " garbage company:GM  &%$  industry:\"341 more garbage\""
        result = [(operator.and_, 'company', 'garbage'),
                  (operator.and_, 'company', 'GM'),
                  (operator.and_, 'company', '&%$'),
                  (operator.and_, 'industry', '341 more garbage')]
        self.assertEqual(self.search_obj.parse_search_query(query), result)

    def testparse_search_query_4(self):
        query = " company:GM  industry:\"341 more garbage"
        result = [(operator.and_, 'company','GM'),
                  (operator.and_, 'industry', '341 more garbage')]
        self.assertEqual(self.search_obj.parse_search_query(query), result)

    def testparse_search_query_5(self):
       query = "industry:\"341 more garbage company:GM"
       result = [(operator.and_, 'industry', '341 more garbage company:GM')]
       self.assertEqual(self.search_obj.parse_search_query(query), result)

    def testparse_search_query_6(self):
        query = " montoto:\"poroto\" industry:341"
        result = [(operator.and_, 'industry', '341')]
        self.assertEqual(self.search_obj.parse_search_query(query), result)

    def testparse_search_queryMultipleValues(self):
        query = " company:GM company:ATT"
        result = [(operator.and_, 'company', 'GM'), (operator.and_, 'company', 'ATT')]
        self.assertEqual(self.search_obj.parse_search_query(query), result)

    def testparse_search_queryRatingValues(self):
        query = " company:GM rating_low:0.578 rating_high:0.579"
        result = [(operator.and_, 'company', 'GM'),
                  (operator.and_, 'rating_low', float(0.57)),
                  (operator.and_, 'rating_high', float(0.57))]
        self.assertEqual(self.search_obj.parse_search_query(query), result)

    def testparse_search_queryCommunityRating(self):
        query = "community_low:0.3 community_high:1.0"
        result = [(operator.and_, 'community_low', float(0.3)),
                  (operator.and_, 'community_high', float(1.0))]
        self.assertEqual(self.search_obj.parse_search_query(query), result)

    def testparse_search_queryEmployeesRating(self):
        query = "employees_low:0.3 employees_high:1.0"
        result = [(operator.and_, 'employees_low', float(0.3)),
                  (operator.and_, 'employees_high', float(1.0))]
        self.assertEqual(self.search_obj.parse_search_query(query), result)

    def testparse_search_queryEnvironmentRating(self):
        query = "environment_low:0.3 environment_high:1.0"
        result = [(operator.and_, 'environment_low', float(0.3)),
                  (operator.and_, 'environment_high', float(1.0))]
        self.assertEqual(self.search_obj.parse_search_query(query), result)

    def testparse_search_queryGovernanceRating(self):
        query = "governance_low:0.3 governance_high:1.0"
        result = [(operator.and_, 'governance_low', float(0.3)),
                  (operator.and_, 'governance_high', float(1.0))]
        self.assertEqual(self.search_obj.parse_search_query(query), result)
