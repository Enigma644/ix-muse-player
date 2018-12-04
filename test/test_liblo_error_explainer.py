import unittest

import liblo
import liblo_error_explainer


class LibloErrorExplainerTest(unittest.TestCase):
    def fakeError(self, num=1234, msg='Fake message', where='fake-loc:1234'):
        return liblo.ServerError(num, msg, where)

    def ee(self, *args, **kwargs):
        return liblo_error_explainer.LibloErrorExplainer(*args, **kwargs)

    def test_noport_explanation_mentions_bind(self):
        err = self.fakeError(num=9904)
        ee = self.ee(err)
        exp = ee.explanation()
        self.assertTrue(exp)
        self.assertRegexpMatches(exp, 'bind')

    def test_random_error_has_no_explanation(self):
        ee = self.ee(self.fakeError())
        self.assertFalse(ee.explanation())
