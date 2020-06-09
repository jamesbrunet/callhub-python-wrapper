import os

import unittest
from unittest.mock import MagicMock
from callhub import CallHub


class TestInit(unittest.TestCase):
    def create_callhub(self, api_key=None):
        callhub = CallHub(api_key=api_key, rate_limit=False)
        # Override all http methods with mocking so a poorly designed test can't mess with
        callhub.session.get = MagicMock(returnvalue=None)
        callhub.session.post = MagicMock(returnvalue=None)
        callhub.session.put = MagicMock(returnvalue=None)
        callhub.session.delete = MagicMock(returnvalue=None)
        callhub.session.head = MagicMock(returnvalue=None)
        callhub.session.options = MagicMock(returnvalue=None)
        return True

    def setUp(self):
        os.environ["CALLHUB_API_KEY"] = "123456789ABCDEF"

    def tearDown(self):
        try:
            del os.environ['CALLHUB_API_KEY']
        except:
            pass

    def test_auth_failure(self):
        del os.environ['CALLHUB_API_KEY']
        self.assertRaises(KeyError, self.create_callhub)

    def test_auth_env(self):
        self.assertEqual(self.create_callhub(), True)

    def test_auth_kwarg(self):
        del os.environ['CALLHUB_API_KEY']
        self.assertEqual(self.create_callhub(api_key="123456789ABCDEF"), True)

if __name__ == '__main__':
    unittest.main()
