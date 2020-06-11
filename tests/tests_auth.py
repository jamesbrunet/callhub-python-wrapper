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

            return CallHub(api_key=api_key, rate_limit=False)

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

    def test_api_key_good(self):
        with Mocker() as mock:
            mock.get("https://api.callhub.io/v1/agents/",
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
            self.assertEqual(CallHub(api_key="G00D4P1K3Y").validate_api_key(), "admin@example.com")

    def test_api_key_bad(self):
        with Mocker() as mock:
            mock.get("https://api.callhub.io/v1/agents/", json={'detail': 'Invalid token.'})
            self.assertRaises(ValueError, CallHub, api_key="B4D4P1K3Y")

            mock.get("https://api.callhub.io/v1/agents/", json={'detail': 'User inactive or deleted.'})
            self.assertRaises(ValueError, CallHub, api_key="B4D4P1K3Y",)

    def test_api_key_good_but_callhub_misbehaving(self):
        with Mocker() as mock:
            mock.get("https://api.callhub.io/v1/agents/", json={'garbagedata': 'callhub api misbehaving'})
            self.assertRaises(RuntimeError, CallHub, api_key="G00D4P1K3YBUTC4LLHUB1S4CT1NGUP")

    def test_auth_env(self):
        self.assertIsInstance(self.create_callhub(), CallHub)

    def test_auth_kwarg(self):
        del os.environ['CALLHUB_API_KEY']
        self.assertIsInstance(self.create_callhub(api_key="123456789ABCDEF"), CallHub)

if __name__ == '__main__':
    unittest.main()
