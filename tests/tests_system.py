import unittest
from callhub import CallHub
import random
import uuid

'''NOTE: Mocking not set up here. Testing with this file makes LIVE CHANGES to your CallHub account!!!!'''

class TestInit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.callhub = CallHub("https://api.callhub.io")

    def test_dnc_list_functionality(self):
        self.add_dnc_list()
        self.add_dnc_contacts()
        self.remove_dnc_contacts()
        self.remove_dnc_list()

    def add_dnc_list(self):
        self.dnc_name = "Test DNC List {}".format(uuid.uuid4())
        self.dnc_list_id = self.callhub.create_dnc_list(self.dnc_name)
        dnc_lists = self.callhub.get_dnc_lists()
        self.assertEqual(dnc_lists.get(self.dnc_list_id), self.dnc_name)

    def add_dnc_contacts(self):
        self.new_dnc_1 = "1555{}".format(random.randint(1000000, 4999999))
        self.new_dnc_2 = "1555{}".format(random.randint(5000000, 9999999))
        dnc_phones = self.callhub.get_dnc_phones()

        # Contacts not yet added, so they should not be in a dnc list
        self.assertEqual(dnc_phones.get(self.new_dnc_1), None)
        self.assertEqual(dnc_phones.get(self.new_dnc_2), None)

        self.callhub.add_dnc([self.new_dnc_1, self.new_dnc_2], self.dnc_list_id)
        dnc_phones = self.callhub.get_dnc_phones()

        # Contacts should each be added to a single dnc list
        self.assertEqual(len(dnc_phones.get(self.new_dnc_1, [])), 1)
        self.assertEqual(len(dnc_phones.get(self.new_dnc_2, [])), 1)

        # Contacts should be added to a dnc list with the correct list id and name
        self.assertEqual(dnc_phones.get(self.new_dnc_1, [{}])[0].get("list_id"), self.dnc_list_id)
        self.assertEqual(dnc_phones.get(self.new_dnc_1, [{}])[0].get("name"), self.dnc_name)
        self.assertEqual(dnc_phones.get(self.new_dnc_2, [{}])[0].get("list_id"), self.dnc_list_id)
        self.assertEqual(dnc_phones.get(self.new_dnc_2, [{}])[0].get("name"), self.dnc_name)

    def remove_dnc_contacts(self):
        self.callhub.remove_dnc([self.new_dnc_1, self.new_dnc_2], self.dnc_list_id)
        dnc_phones = self.callhub.get_dnc_phones()

        # Contacts should not be added to any DNC lists anymore
        self.assertEqual(dnc_phones.get(self.new_dnc_1), None)
        self.assertEqual(dnc_phones.get(self.new_dnc_2), None)

    def remove_dnc_list(self):
        self.callhub.remove_dnc_list(self.dnc_list_id)
        dnc_lists = self.callhub.get_dnc_lists()
        self.assertEqual(dnc_lists.get(self.dnc_list_id), None)

    @classmethod
    def tearDownClass(cls):
        cls.callhub.session.close()

if __name__ == '__main__':
    unittest.main()
