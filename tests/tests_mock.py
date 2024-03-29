import unittest
from unittest.mock import MagicMock
from callhub import CallHub
import time
import math
from requests_mock import Mocker
import requests_mock


class TestInit(unittest.TestCase):
    @classmethod
    def setUp(cls):
        cls.TESTING_API_LIMIT = {
            "GENERAL": {"calls": 1, "period": 0.1},
            "BULK_CREATE": {"calls": 1, "period": 0.2},
        }
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
                     )
            # Create one callhub object stored in cls.callhub (for most test cases)
            # Create ten callhub objects stored in cls.callhubs (for bulk testing)
            cls.callhubs = []
            for i in range(11):
                callhub = CallHub("https://api.callhub.io", api_key="123456789ABCDEF", rate_limit=cls.TESTING_API_LIMIT)
                # Override all http methods with mocking so a poorly designed test can't mess with
                if i == 0:
                    cls.callhub = callhub
                else:
                    cls.callhubs.append(callhub)

    def test_repr(self):
        self.assertEqual("<CallHub admin: admin@example.com>", self.callhub.__repr__())

    def test_agent_leaderboard(self):
        with Mocker() as mock:
            mock.get("https://api.callhub.io/v1/analytics/agent-leaderboard/",
                     status_code=200,
                     json={
                         "plot_data": [
                             {
                                 'connecttime': 3300,
                                 'teams': ['Fundraising'],
                                 'calls': 5,
                                 'agent': 'jimmybru',
                                 'talktime': 120
                             }
                         ]
                     })
            leaderboard = self.callhub.agent_leaderboard("2019-12-30", "2020-12-30")
            expected_leaderboard = [
                {
                    'connecttime': 3300,
                    'teams': ['Fundraising'],
                    'calls': 5,
                    'agent': 'jimmybru',
                    'talktime': 120
                }
            ]
            self.assertEqual(leaderboard, expected_leaderboard)

    def test_bulk_create_success(self, test_specific_callhub_instance=None):
        with Mocker() as mock:
            mock.post("https://api.callhub.io/v1/contacts/bulk_create/",
                      status_code=200,
                      json={"message": "'Import in progress. You will get an email when import is complete'"})
            if test_specific_callhub_instance:
                self.callhub = test_specific_callhub_instance
            self.callhub.fields = MagicMock(return_value={"first name": 0, "phone number": 1})
            result = self.callhub.bulk_create(
                2325931969109558581,
                [{"first name": "james", "phone number": "5555555555"}],
                "CA")
            self.assertEqual(result, True)

    def test_bulk_create_field_mismatch_failure(self):
        self.callhub.fields = MagicMock(return_value={"foo": 0, "bar": 1})
        self.assertRaises(LookupError,
                          self.callhub.bulk_create,
                          2325931969109558581,
                          [{"first name": "james", "phone number": "5555555555"}],
                          "CA"
                          )

    def test_bulk_create_api_exceeded_or_other_failure(self):
        with Mocker() as mock:
            mock.post("https://api.callhub.io/v1/contacts/bulk_create/",
                      json={"detail": "Request was throttled."})
            self.callhub.fields = MagicMock(return_value={"first name": 0, "phone number": 1})
            self.assertRaises(RuntimeError,
                              self.callhub.bulk_create,
                              2325931969109558581,
                              [{"first name": "james", "phone number": "5555555555"}],
                              "CA"
                              )
            mock.post("https://api.callhub.io/v1/contacts/bulk_create/",
                      json={"NON STANDARD KEY": "YOU MESSED UP FOR SOME REASON"})
            self.assertRaises(RuntimeError,
                              self.callhub.bulk_create,
                              2325931969109558581,
                              [{"first name": "james", "phone number": "5555555555"}],
                              "CA"
                              )

    def test_bulk_create_rate_limit(self):
        start = time.perf_counter()
        num_iterations = 11
        for i in range(num_iterations):
            self.test_bulk_create_success()
        stop = time.perf_counter()

        # Should run within 95% to 105% of ratelimit*num iterations -1
        lower_bound = 0.95 * self.TESTING_API_LIMIT["BULK_CREATE"]["period"] * (num_iterations - 1)
        upper_bound = 1.05 * self.TESTING_API_LIMIT["BULK_CREATE"]["period"] * (num_iterations - 1)
        self.assertEqual(lower_bound <= stop - start <= upper_bound, True)

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
        self.assertEqual(lower_bound <= stop - start <= upper_bound, True)

    def test_fields(self):
        with Mocker() as mock:
            mock.get('https://api.callhub.io/v1/contacts/fields/',
                     json={'count': 4, 'results':
                         [{'id': 0, 'name': 'phone number'}, {'id': 1, 'name': 'mobile number'},
                          {'id': 2, 'name': 'last name'}, {'id': 3, 'name': 'first name'}]})
            self.assertEqual(self.callhub.fields(),
                             {'phone number': 0, 'mobile number': 1, 'last name': 2, 'first name': 3})

    def test_collect_fields(self):
        contacts = [{"first name": "James", "contact": 5555555555}, {"last name": "Brunet", "contact": 1234567890}]
        self.assertEqual(self.callhub._collect_fields(contacts), {"first name", "last name", "contact"})

    def test_create_contact(self):
        expected_id = 123456
        with Mocker() as mock:
            mock.post('https://api.callhub.io/v1/contacts/', json={"id": expected_id}, status_code=201)

            # Test if contact creation successful
            self.callhub.fields = MagicMock(return_value={"first name": 0, "phone number": 1})
            contact_id = self.callhub.create_contact({"first name": "Jimmy", "phone number": "5555555555"})
            self.assertEqual(contact_id, expected_id)

            # Ensure contact creation fails on field mismatch
            self.callhub.fields = MagicMock(return_value={"foo": 0, "bar": 1})
            self.assertRaises(LookupError,
                              self.callhub.create_contact,
                              {"first name": "james", "phone number": "5555555555"},
                              )

    def get_all_contacts(self, limit, count, status=200):
        page_json = {
            "count": count,
            "results": [
                {"first name": "james"},
                {"first name": "sumiya"}
            ]
        }
        expected_result = page_json["results"].copy()
        # We expect get_contacts to fetch either the limit/page_size pages or the total/page_size pages, depending
        # on which is smaller
        expected_result *= min(math.ceil(limit / len(page_json["results"])),
                               math.ceil(count / len(page_json["results"])))
        # We then expect get_contacts to trim the result to exactly the limit (because we fetch in batches equal to the
        # page size but the limit is for the exact number of contacts)
        expected_result = expected_result[:limit]
        with Mocker() as mock:
            mock.get('https://api.callhub.io/v1/contacts/', status_code=status, json=page_json)
            # Test number of contacts matches size given
            self.assertEqual(len(self.callhub.get_contacts(limit)), min(limit, count))
            # Test that the results of get_contacts match the expected results
            self.assertEqual(self.callhub.get_contacts(limit), expected_result)

    def test_get_all_contacts(self):
        # Test different variations of get_all_contacts with different numbers of contacts and different limits
        # Test when no contacts exist
        self.get_all_contacts(limit=50, count=0)
        # Test when limit is zero
        self.get_all_contacts(limit=0, count=50)
        # Test when limit > contacts
        self.get_all_contacts(limit=50, count=40)
        # Test with odd number limit
        self.get_all_contacts(limit=49, count=55)
        # Test with even number limit
        self.get_all_contacts(limit=50, count=55)
        # Test with 500 error
        self.assertRaises(RuntimeError, self.get_all_contacts, limit=50, count=50, status=500)

    def test_get_dnc_lists(self):
        expected_result = {
            "5543": "Default DNC List",
            "8794": "SMS Campaign 2020-01-1",
        }
        callhub_api_json = {
            "count": 2,
            "next": None,
            "previous": None,
            "results": [
                {
                    "url": "https://api.callhub.io/v1/dnc_lists/5543/",
                    "owner": "does not matter",
                    "name": "Default DNC List"
                },
                {
                    "url": "https://api.callhub.io/v1/dnc_lists/8794/",
                    "owner": "does not matter",
                    "name": "SMS Campaign 2020-01-1"
                },
            ]
        }
        with Mocker() as mock:
            mock.get('https://api.callhub.io/v1/dnc_lists/', status_code=200, json=callhub_api_json)
            self.assertEqual(self.callhub.get_dnc_lists(), expected_result)

    def test_get_dnc_phones(self):
        expected_result = {"16135554432": [
            {"list_id": "5543", "name": "Default DNC List", "dnc_contact_id": "9964"},
            {"list_id": "8794", "name": "SMS Campaign 2020-01-1", "dnc_contact_id": "8894"}
        ]}
        callhub_api_json = {
            "count": 2,
            "next": None,
            "previous": None,
            "results": [
                {
                    "url": "https://api.callhub.io/v1/dnc_contacts/9964/",
                    "dnc": "https://api.callhub.io/v1/dnc_lists/5543/",
                    "phone_number": "16135554432"
                },
                {
                    "url": "https://api.callhub.io/v1/dnc_contacts/8894/",
                    "dnc": "https://api.callhub.io/v1/dnc_lists/8794/",
                    "phone_number": "16135554432"
                },
            ]
        }
        get_dnc_lists_json = {
            "5543": "Default DNC List",
            "8794": "SMS Campaign 2020-01-1",
        }
        self.callhub.get_dnc_lists = MagicMock(return_value=get_dnc_lists_json)
        with Mocker() as mock:
            mock.get("https://api.callhub.io/v1/dnc_contacts/", status_code=200, json=callhub_api_json)
            self.assertEqual(self.callhub.get_dnc_phones(), expected_result)

    def test_add_dnc(self):
        successful_dnc_create_json = {
          "url": "https://api.callhub.io/v1/dnc_contacts/12345678/",
          "dnc": "https://api.callhub.io/v1/dnc_lists/8794/",
          "phone_number": "15555555555"
        }
        expected_result = {
            "15555555555": [{
                "list_id": "8794",
                "name": "SMS Campaign 2020-01-1",
                "dnc_contact_id": "12345678"
            }]
        }
        get_dnc_lists_json = {
            "5543": "Default DNC List",
            "8794": "SMS Campaign 2020-01-1",
        }
        self.callhub.get_dnc_lists = MagicMock(return_value=get_dnc_lists_json)
        with Mocker() as mock:
            mock.post("https://api.callhub.io/v1/dnc_contacts/", status_code=201, json=successful_dnc_create_json)
            self.assertEqual(self.callhub.add_dnc(["15555555555"], "8794")[0], expected_result)
            self.assertRaises(TypeError, self.callhub.add_dnc, "15555555555", "8794")
            mock.post("https://api.callhub.io/v1/dnc_contacts/", status_code=400, json="error message")
            self.assertEqual(len(self.callhub.add_dnc(["15555555555"], "8794")[1]), 1)

    def test_remove_dnc(self):
        dnc_cache = {"15555555555": [
            {"list_id": "5543", "name": "Default DNC List", "dnc_contact_id": "9964"},
            {"list_id": "8794", "name": "SMS Campaign 2020-01-1", "dnc_contact_id": "8894"}
        ]}
        self.callhub.get_dnc_phones = MagicMock(return_value=dnc_cache)
        with Mocker() as mock:
            mock.delete("https://api.callhub.io/v1/dnc_contacts/{}/".format("9964"), status_code=204)
            # Test removing single contact from particular dnc lists
            self.assertEqual(self.callhub.remove_dnc(["15555555555"], "5543"), [])
            # Ensure that removing a single contact from no particular dnc list makes a request to delete phone number
            # from multiple dnc lists (tries to delete multiple dnc contacts). We've only mocked ONE dnc contact, so we
            # should get a requests_mock.exceptions.NoMockAddress when we try to remove any other dnc contact
            self.assertRaises(requests_mock.exceptions.NoMockAddress, self.callhub.remove_dnc, ["15555555555"])

    def test_remove_dnc_list(self):
        list_id = "9964"
        with Mocker() as mock:
            mock.delete("https://api.callhub.io/v1/dnc_lists/{}/".format(list_id), status_code=204)
            self.assertEqual(self.callhub.remove_dnc_list(list_id), None)
            mock.delete("https://api.callhub.io/v1/dnc_lists/{}/".format(list_id), status_code=400)
            self.assertRaises(RuntimeError, self.callhub.remove_dnc_list, list_id)

    def test_add_dnc_list(self):
        list_id = "9964"
        list_name = "This is a do not call list!"
        callhub_api_json = {
            "url": "https://api.callhub.io/v1/dnc_lists/{}/".format(list_id),
            "owner": "jamesbrunet",
            "name": list_name
        }
        with Mocker() as mock:
            mock.post("https://api.callhub.io/v1/dnc_lists/", status_code=201, json=callhub_api_json)
            self.assertEqual(self.callhub.create_dnc_list(list_name), list_id)
            mock.post("https://api.callhub.io/v1/dnc_lists/", status_code=400)
            self.assertRaises(RuntimeError, self.callhub.create_dnc_list, list_name)

    def test_create_phonebook(self):
        phonebook_id = "123456789"
        callhub_api_json = {
            "url": "https://api.callhub.io/v1/phonebooks/{}/".format(phonebook_id),
            "owner": "doesnotmatter",
            "name": "my phonebook name",
            "description": "doesnotmatter"
        }
        with Mocker() as mock:
            mock.post("https://api.callhub.io/v1/phonebooks/", status_code=201, json=callhub_api_json)
            self.assertEqual(self.callhub.create_phonebook("my phonebook name"), phonebook_id)
            mock.post("https://api.callhub.io/v1/phonebooks/", status_code=400)
            self.assertRaises(RuntimeError, self.callhub.create_phonebook, "my phonebook name")

    def test_get_campaigns(self):
        campaign_id = 123456789
        callhub_api_json = {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [
                {
                    "url": "https://api.callhub.io/v1/callcenter_campaigns/{}/".format(campaign_id),
                    "owner": "readme",
                    "name": "Second Campaign",
                    "status": 4,
                    "phonebook": ["https://api.callhub.io/v1/phonebooks/1332/"],
                    "id": str(campaign_id)
                },
            ]
        }
        expected_result = callhub_api_json["results"].copy()
        with Mocker() as mock:
            mock.get("https://api.callhub.io/v1/callcenter_campaigns/", status_code=200, json=callhub_api_json)
            self.assertEqual(self.callhub.get_campaigns(), expected_result)
            mock.get("https://api.callhub.io/v1/callcenter_campaigns/", status_code=400)
            self.assertRaises(RuntimeError, self.callhub.get_campaigns)

    def test_create_webhook(self):
        target = "https://example.com/webhook"
        webhook_id = "12345"
        callhub_api_json = {
            "id": webhook_id,
            # There's other stuff that callhub returns, but we only care about the ID
        }
        with Mocker() as mock:
            mock.post("https://api.callhub.io/v1/webhooks/", status_code=201, json=callhub_api_json)
            self.assertEqual(self.callhub.create_webhook(target), webhook_id)
            mock.post("https://api.callhub.io/v1/webhooks/", status_code=400)
            self.assertRaises(RuntimeError, self.callhub.create_webhook, target)

    def test_get_webhooks(self):
        callhub_api_json = {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [
                {
                    "id":"1234"
                },
            ]
        }
        expected_result = callhub_api_json["results"].copy()
        with Mocker() as mock:
            mock.get("https://api.callhub.io/v1/webhooks/", status_code=200, json=callhub_api_json)
            self.assertEqual(self.callhub.get_webhooks(), expected_result)
            mock.get("https://api.callhub.io/v1/webhooks/", status_code=400)
            self.assertRaises(RuntimeError, self.callhub.get_webhooks)

    def test_remove_webhook(self):
        webhook_id = "1234"
        with Mocker() as mock:
            mock.delete("https://api.callhub.io/v1/webhooks/{}/".format(webhook_id), status_code=204)
            self.assertEqual(self.callhub.remove_webhook(webhook_id), None)
            mock.delete("https://api.callhub.io/v1/webhooks/{}/".format(webhook_id), status_code=400)
            self.assertRaises(RuntimeError, self.callhub.remove_webhook, webhook_id)

    def test_export_campaign(self):
        get_polling_url_json = {
            'polling_url':'https://api.callhub.io/polling_url_example'
        }
        polling_result_timeout_json = {
            'state': 'TIMEOUT'
        }
        polling_result_weird_json = {
            'state': 'SUCCESS',
            'data': {
                'url':'https://example-download.location',
                'code': 500
            },
        }
        polling_result_success_json = {
            'state': 'SUCCESS',
            'data': {
                'url':'https://example-download.location',
                'code': 200
            }
        }
        campaign_id = 1234
        with Mocker() as mock:
            mock.post("https://api.callhub.io/v1/power_campaign/{}/export/".format(campaign_id),
                      status_code=202, json=get_polling_url_json)
            mock.get(get_polling_url_json['polling_url'], status_code=200, json=polling_result_timeout_json)
            self.assertRaises(RuntimeError, self.callhub.export_campaign, campaign_id)
            mock.get(get_polling_url_json['polling_url'], status_code=500, json=polling_result_weird_json)
            self.assertRaises(RuntimeError, self.callhub.export_campaign, campaign_id)
            mock.get(get_polling_url_json['polling_url'], status_code=200, json=polling_result_success_json)
            self.assertEqual(self.callhub.export_campaign(campaign_id), polling_result_success_json['data']['url'])


if __name__ == '__main__':
    unittest.main()
