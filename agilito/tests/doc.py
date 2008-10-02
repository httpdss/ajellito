class TestGRS:
    """
    # a little set-up to make things less boring
    >>> from django import forms
    >>> from agilito.widgets import GroupedRadioSelect
    >>> from agilito.fields import GroupedChoiceField
    >>> def mkform(choices):
    ...    class AForm(forms.Form):
    ...        thing = GroupedChoiceField(widget=GroupedRadioSelect,
    ...                                   choices=choices)
    ...    return AForm
    ...


    First, see how GRS drops back to the usual behavior when working
    with "flat" data:

    >>> AForm = mkform([(1, "one"), (2, "two")])
    >>> print AForm().as_ul()
    <li><label for="id_thing_0">Thing:</label> <ul>
    <li><label for="id_thing_0"><input type="radio" id="id_thing_0" value="1" name="thing" /> one</label></li>
    <li><label for="id_thing_1"><input type="radio" id="id_thing_1" value="2" name="thing" /> two</label></li>
    </ul></li>

    Next, see how things start getting interesting when you nest 'em

    >>> AForm = mkform([([(1, "one"), (2, "two")], 'hi')])
    >>> print AForm().as_ul()
    <li><label for="id_thing_0">Thing:</label> <ul>
    <li><dl class="level0">
    <dt>hi</dt>
    <dd><ul>
    <li><label for="id_thing_0"><input type="radio" id="id_thing_0" value="1" name="thing" /> one</label></li>
    <li><label for="id_thing_1"><input type="radio" id="id_thing_1" value="2" name="thing" /> two</label></li>
    </ul></dd></dl></li>
    </ul></li>

    and the ids remain sane

    >>> AForm = mkform([(0, "nul"), ([(1, "one"), (2, "two")], 'hi')])
    >>> print AForm().as_ul()
    <li><label for="id_thing_0">Thing:</label> <ul>
    <li><label for="id_thing_0"><input type="radio" id="id_thing_0" value="0" name="thing" /> nul</label></li>
    <li><dl class="level0">
    <dt>hi</dt>
    <dd><ul>
    <li><label for="id_thing_1"><input type="radio" id="id_thing_1" value="1" name="thing" /> one</label></li>
    <li><label for="id_thing_2"><input type="radio" id="id_thing_2" value="2" name="thing" /> two</label></li>
    </ul></dd></dl></li>
    </ul></li>

    for ever

    >>> AForm = mkform([(0, "nul"), ([(1, "one"), (2, "two")], 'lo'), (3, "tri")])
    >>> print AForm().as_ul()
    <li><label for="id_thing_0">Thing:</label> <ul>
    <li><label for="id_thing_0"><input type="radio" id="id_thing_0" value="0" name="thing" /> nul</label></li>
    <li><dl class="level0">
    <dt>lo</dt>
    <dd><ul>
    <li><label for="id_thing_1"><input type="radio" id="id_thing_1" value="1" name="thing" /> one</label></li>
    <li><label for="id_thing_2"><input type="radio" id="id_thing_2" value="2" name="thing" /> two</label></li>
    </ul></dd></dl></li>
    <li><label for="id_thing_3"><input type="radio" id="id_thing_3" value="3" name="thing" /> tri</label></li>
    </ul></li>

    and ever

    >>> AForm = mkform([(0, "zero"), ([(1, "one"), ([(2, "two"), ([(3, "three")], "THREE")], "TWO")], "ONE")])
    >>> print AForm().as_ul()
    <li><label for="id_thing_0">Thing:</label> <ul>
    <li><label for="id_thing_0"><input type="radio" id="id_thing_0" value="0" name="thing" /> zero</label></li>
    <li><dl class="level0">
    <dt>ONE</dt>
    <dd><ul>
    <li><label for="id_thing_1"><input type="radio" id="id_thing_1" value="1" name="thing" /> one</label></li>
    <li><dl class="level1">
    <dt>TWO</dt>
    <dd><ul>
    <li><label for="id_thing_2"><input type="radio" id="id_thing_2" value="2" name="thing" /> two</label></li>
    <li><dl class="level2">
    <dt>THREE</dt>
    <dd><ul>
    <li><label for="id_thing_3"><input type="radio" id="id_thing_3" value="3" name="thing" /> three</label></li>
    </ul></dd></dl></li>
    </ul></dd></dl></li>
    </ul></dd></dl></li>
    </ul></li>
    

    """

class TestGRSValidates:
    """
    # a little set-up to make things less boring
    >>> from django import forms
    >>> from agilito.widgets import GroupedRadioSelect
    >>> from agilito.fields import GroupedChoiceField
    >>> def mkform(choices):
    ...    class AForm(forms.Form):
    ...        thing = GroupedChoiceField(widget=GroupedRadioSelect,
    ...                                   choices=choices)
    ...    return AForm
    ...

    
    >>> AForm = mkform([(1, "one"), (2, "two")])
    >>> f = AForm({'thing': 1})
    >>> f.is_valid()
    True


    >>> AForm = mkform([([(1, "one"), (2, "two")], 'hi')])
    >>> f = AForm({'thing': 1})
    >>> f.is_valid()
    True

    """

class TestUserStoryBacklog:
    """
    First, test that only shows unscheduled tasks

    >>> from agilito.models import UserStory, Project, Iteration
    >>> from datetime import datetime
    >>> p1 = Project()
    >>> p1.save()
    >>> i1 = Iteration(start_date=datetime.now(), end_date=datetime.now(), project=p1)
    >>> i1.save()
    >>> us_a = UserStory(rank= 3, name='User story A', planned=4, project=p1, iteration = i1)
    >>> us_b = UserStory(rank= 2, name='User story B', planned=8, project=p1)
    >>> us_c = UserStory(rank= 1, name='User story C', planned=1, project=p1)
    >>> us_a.save()
    >>> us_b.save()
    >>> us_c.save()
    >>> result = map(lambda x: x.name,UserStory.backlogged(p1.id))
    >>> u'User story C' in result
    True

    >>> u'User story B' in result
    True

    >>> u'User story A' in result
    False

    Second, test that short by rank

    >>> p2 = Project()
    >>> p2.save()
    >>> us_a= UserStory(rank= 3, name='User story A', planned=4, project=p2)
    >>> us_b= UserStory(rank= 2, name='User story B', planned=8, project=p2)
    >>> us_c= UserStory(rank= 1, name='User story C', planned=1, project=p2)
    >>> us_a.save()
    >>> us_b.save()
    >>> us_c.save()
    >>> map(lambda x: x.name,UserStory.backlogged(p2.id))
    [u'User story C', u'User story B', u'User story A']

    """



class TestUserStoryTestFailed:
    """
    >>> from agilito.models import UserStory, Project, Iteration, TestCase, TestResult, User
    >>> from datetime import datetime
    >>> p1 = Project(name='Test Project')
    >>> p1.save()
    >>> u = User.objects.create_user(username='test',password='test',email='test@test.com')
    >>> i1 = Iteration(start_date=datetime.now(), end_date=datetime.now(), project=p1)
    >>> i1.save()
    >>> us = UserStory(rank= 3, name='User story A', planned=4, project=p1, iteration = i1)
    >>> us.save()
    >>> us.test_failed
    0

    >>> tc = TestCase(user_story=us)
    >>> tc.save()
    >>> us.test_failed
    0

    >>> tr1 = TestResult(test_case=tc, result=1, date=datetime.now(), tester=u)
    >>> tr1.save()
    >>> us.test_failed
    0
    
    >>> tr2 = TestResult(test_case=tc, result=0, date=datetime.now(), tester=u)
    >>> tr2.save()
    >>> us.test_failed
    1

    >>> tr3 = TestResult(test_case=tc, result=2, date=datetime.now(), tester=u)
    >>> tr3.save()
    >>> us.test_failed
    1

    >>> tr4 = TestResult(test_case=tc, result=3, date=datetime.now(), tester=u)
    >>> tr4.save()
    >>> us.test_failed
    1

    >>> tc2 = TestCase(user_story=us)
    >>> tc2.save()
    >>> us.test_failed
    1

    >>> tr6 = TestResult(test_case=tc2, result=1, date=datetime.now(), tester=u)
    >>> tr6.save()
    >>> us.test_failed
    1

    >>> tr5 = TestResult(test_case=tc2, result=0, date=datetime.now(), tester=u)
    >>> tr5.save()
    >>> us.test_failed
    2

    >>> tr7 = TestResult(test_case=tc2, result=2, date=datetime.now(), tester=u)
    >>> tr7.save()
    >>> us.test_failed
    2

    >>> tr8 = TestResult(test_case=tc2, result=3, date=datetime.now(), tester=u)
    >>> tr8.save()
    >>> us.test_failed
    2

    >>> tr9 = TestResult(test_case=tc2, result=1, date=datetime.now(), tester=u)
    >>> tr9.save()
    >>> us.test_failed
    1

    >>> tr10 = TestResult(test_case=tc, result=1, date=datetime.now(), tester=u)
    >>> tr10.save()
    >>> us.test_failed
    0

    """
