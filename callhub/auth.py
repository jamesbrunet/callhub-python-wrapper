"""
The class can handle authentication automatically
if the environment variable `CALLHUB_API_KEY` is set with your api key.
>>> callhub = CallHub()
Alternatively, you can pass the key explicitly:
>>> callhub = CallHub(api_key='yourapikey')
Many thanks to Gui Talarico who provided this with their airtable-python-wrapper package
"""  #
import os
import requests


class CallHubAuth(requests.auth.AuthBase):
    def __init__(self, api_key=None):
        """
        Authentication used by CallHub Class
        Args:
            api_key (``str``): CallHub API Key. Optional.
                If not set, it will look for
                enviroment variable ``CALLHUB_API_KEY``
        """
        try:
            self.api_key = api_key or os.environ["CALLHUB_API_KEY"]
        except KeyError:
            raise KeyError(
                "Api Key not found. Pass api_key as a kwarg \
                            or set an env var CALLHUB_API_KEY with your key"
            )

    def __call__(self, request):
        auth_token = {"Authorization": "Token {}".format(self.api_key)}
        request.headers.update(auth_token)
        return request
