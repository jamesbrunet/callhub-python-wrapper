import unittest
from unittest.mock import MagicMock
from callhub import CallHub
import time


class TestInit(unittest.TestCase):
    @classmethod
    def setUp(cls):
        TESTING_API_LIMIT = {
            "GENERAL": {"calls": 100, "period": 1},
            "BULK_CREATE": {"calls": 1, "period": 0.1},
        }

        cls.callhub = CallHub(rate_limit=TESTING_API_LIMIT)

        # Override all http methods with mocking so a poorly designed test can't mess with
        cls.callhub.session.get = MagicMock(returnvalue=None)
        cls.callhub.session.post = MagicMock(returnvalue=None)
        cls.callhub.session.put = MagicMock(returnvalue=None)
        cls.callhub.session.delete = MagicMock(returnvalue=None)
        cls.callhub.session.head = MagicMock(returnvalue=None)
        cls.callhub.session.options = MagicMock(returnvalue=None)

    def test_agent_leaderboard(self):
        self.callhub.agent_leaderboard("2019-12-30", "2020-12-30")

    def test_bulk_create_success(self):
        self.callhub.fields = MagicMock(return_value={"first name": 0, "phone number": 1})
        self.callhub.session.post = MagicMock()
        self.callhub.session.post.return_value.json.return_value = {
            "message": "'Import in progress. You will get an email when import is complete'"}
        result = self.callhub.bulk_create(
            2325931969109558581,
            [{"first name": "james", "phone number": "5555555555"}],
            "CA")
        self.assertEqual(result, True)

    def test_bulk_create_rate_limit(self):
        start = time.perf_counter()
        for i in range(11):
            self.test_bulk_create_success()
        stop = time.perf_counter()
        # 11 tests should run in almost exactly 1s, because there will be 10 exactly 0.1s delays between tests
        # This will only run longer than 1s if the time to execute each iteration is longer than 0.1s.
        # Time to execute one iteration Sandy Bridge i5: 0.0007s
        self.assertEqual(0.995 <= stop-start <= 1.005, True)

    def test_bulk_create_field_mismatch_failure(self):
        self.callhub.fields = MagicMock(return_value={"foo": 0, "bar": 1})
        self.assertRaises(LookupError,
                          self.callhub.bulk_create,
                          2325931969109558581,
                          [{"first name": "james", "phone number": "5555555555"}],
                          "CA"
                          )

    def test_fields(self):
        self.callhub.session.get = MagicMock()
        self.callhub.session.get.return_value.json.return_value = {'count': 4, 'results':
            [{'id': 0, 'name': 'phone number'}, {'id': 1, 'name': 'mobile number'},
             {'id': 2, 'name': 'last name'}, {'id': 3, 'name': 'first name'}]}
        self.assertEqual(self.callhub.fields(),
                        {'phone number': 0, 'mobile number': 1, 'last name': 2, 'first name': 3})

    def test_collect_fields(self):
        contacts = [{"first name": "James", "contact": 5555555555}, {"last name": "Brunet", "contact": 1234567890}]
        self.assertEqual(self.callhub._collect_fields(contacts), {"first name", "last name", "contact"})


if __name__ == '__main__':
    unittest.main()
