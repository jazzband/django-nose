"""
Tests for FastFixtureTestCase.

These tests primarily verify that the TestCases load and tests run rather than
specifically verifying how the TestCase handles the fixtures themselves.
"""

from datetime import datetime

from django_nose.testcases import FastFixtureTestCase
from testapp.models import Question


class HasFixturesTestCase(FastFixtureTestCase):
    """Tests that use a test fixture."""

    fixtures = ["testdata.json"]

    def test_fixture_loaded(self):
        """Test that a FAST fixture was loaded."""
        question = Question.objects.get()
        self.assertEqual(
            'What is your favorite color?', question.question_text)
        self.assertEqual(datetime(1975, 4, 9), question.pub_date)
        choice = question.choice_set.get()
        self.assertEqual("Blue.", choice.choice_text)
        self.assertEqual(3, choice.votes)


class MissingFixturesTestCase(FastFixtureTestCase):
    """No fixtures defined."""

    def test_anything(self):
        """Run any test to ensure Testcase is loaded without fixtures."""
        assert True
