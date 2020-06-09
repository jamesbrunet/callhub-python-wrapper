import unittest
from unittest.mock import MagicMock
from callhub import CallHub
import time


class TestInit(unittest.TestCase):
    @classmethod
    def setUp(cls):
        cls.TESTING_API_LIMIT = {
            "GENERAL": {"calls": 1, "period": 0.1},
            "BULK_CREATE": {"calls": 1, "period": 0.2},
        }
        # Create one callhub object stored in cls.callhub (for most test cases)
        # Create ten callhub objects stored in cls.callhubs (for bulk ratelimit testing)
        cls.callhubs = []

        for i in range(11):
            callhub = CallHub(rate_limit=cls.TESTING_API_LIMIT)

            # Override all http methods with mocking so a poorly designed test can't mess with
            callhub.session.get = MagicMock(returnvalue=None)
            callhub.session.post = MagicMock(returnvalue=None)
            callhub.session.put = MagicMock(returnvalue=None)
            callhub.session.delete = MagicMock(returnvalue=None)
            callhub.session.head = MagicMock(returnvalue=None)
            callhub.session.options = MagicMock(returnvalue=None)

            if i == 0:
                cls.callhub = callhub
            else:
                cls.callhubs.append(callhub)


    def test_agent_leaderboard(self):
        self.callhub.agent_leaderboard("2019-12-30", "2020-12-30")

    def test_bulk_create_success(self, test_specific_callhub_instance=None):
        if test_specific_callhub_instance:
            self.callhub = test_specific_callhub_instance

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
        num_iterations=11
        for i in range(num_iterations):
            self.test_bulk_create_success()
        stop = time.perf_counter()

        # Should run within 95% to 105% of ratelimit*num iterations -1
        lower_bound = 0.95 * self.TESTING_API_LIMIT["BULK_CREATE"]["period"] * (num_iterations - 1)
        upper_bound = 1.05 * self.TESTING_API_LIMIT["BULK_CREATE"]["period"] * (num_iterations - 1)
        self.assertEqual(lower_bound <= stop-start <= upper_bound, True)

    def test_bulk_create_many_objects_rate_limit(self):
        start = time.perf_counter()
        num_iterations = 11
        for i in range(num_iterations):
            for callhub in self.callhubs:
                self.test_bulk_create_success(test_specific_callhub_instance=callhub)
        stop = time.perf_counter()
        # num_iterations tests on n CallHub objects should run in almost exactly num_iterations*(ratelimit-1)
        # because the rate limiting should be on a per-object basis.
        lower_bound = 0.95 * self.TESTING_API_LIMIT["BULK_CREATE"]["period"] * (num_iterations - 1)
        upper_bound = 1.05 * self.TESTING_API_LIMIT["BULK_CREATE"]["period"] * (num_iterations - 1)
        self.assertEqual(lower_bound <= stop-start <= upper_bound, True)

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
