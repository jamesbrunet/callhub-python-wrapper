import unittest
from callhub import CallHub
import os

class TestInit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.callhub = CallHub()

    def test_agent_stats(self):
        self.callhub.agent_stats("2019-12-30", "2020-12-30")

if __name__ == '__main__':
    unittest.main()
