import unittest
from callhub import CallHub
import os

'''NOTE: Mocking not set up here. Testing with this file makes LIVE CHANGES to your CallHub account.
RUN THESE TESTS AT YOUR OWN RISK!!!!'''

class TestInit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.callhub = CallHub()

    def test_agent_leaderboard(self):
        print(self.callhub.agent_leaderboard("2019-12-30", "2020-12-30"))

    def test_bulk_create(self):
        # Tests ratelimit
        self.callhub.bulk_create(
            2325931969109558581,
            [{"first name": "james", "phone number": "3333333333"}],
            "CA")

    def test_fields(self):
        print(self.callhub.fields())

    def test_collect_fields(self):
        contacts = [{"first name": "James", "contact": 5555555555}, {"last name": "Brunet", "contact": 1234567890}]
        self.assertEqual(self.callhub._collect_fields(contacts), {"first name", "last name", "contact"})

    @classmethod
    def tearDownClass(cls):
        cls.callhub.session.close()

if __name__ == '__main__':
    unittest.main()
