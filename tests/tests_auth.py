import os
import unittest
from unittest.mock import MagicMock
from requests_mock import Mocker
from callhub import CallHub


class TestInit(unittest.TestCase):
    def create_callhub(self, api_key=None):
        with Mocker() as mock:
            mock.get("https://api.callhub.io/v1/agents/",
                     status_code=200,
                     json={'count': 1,
                           'next': None,
                           'previous': None,
                           'results': [{'email': 'user@example.com',
                                        'id': 1111111111111111111,
                                        'owner': [{'url': 'https://api.callhub.io/v1/users/0/',
                                                   'username': 'admin@example.com'}],
                                        'teams': [],
                                        'username': 'defaultuser'}]
                           },
                     complete_qs=True,
                     )

            self.callhub = CallHub(api_key=api_key, rate_limit=False)
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
