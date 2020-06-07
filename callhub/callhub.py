import requests
from .auth import CallHubAuth
from ratelimit import limits, sleep_and_retry
from .bulk_upload_tools import csv_and_mapping_create
from requests.structures import CaseInsensitiveDict


class CallHub:
    def __init__(self, api_key=None, rate_limit=True):
        """
        Instantiates a new CallHub instance
        >>> callhub = CallHub()
        With built-in rate limiting disabled:
        >>> callhub = CallHub(rate_limit=False)
        Keyword Args:
            api_key (``str``, optional): Optional API key. If not provided,
                it will attempt to use ``os.environ['CALLHUB_API_KEY']``
            timeout (``bool``, optional): Optional ratelimiting. Tested in single thread mode only.
                - Limits bulk_create to 1 per 70 seconds (CallHub states their limit is every 60s but in practice
                  a delay of 60s exactly can trip their rate limiter anyways)
                - Limits all other API requests to 2 per second
        """
        if rate_limit:
            # Apply general rate limit to requests.session.get
            requests.Session.get = sleep_and_retry(limits(calls=2, period=1)(requests.Session.get))
            # Apply bulk rate limit to self.bulk_create
            self.bulk_create = sleep_and_retry(limits(calls=1, period=70)(self.bulk_create))

        session = requests.Session()
        session.auth = CallHubAuth(api_key=api_key)
        self.session = session

    def _collect_fields(self, contacts):
        """ Internal Function to get all fields used in a list of contacts """
        fields = set()
        for contact in contacts:
            for key in contact:
                fields.add(key)
        return fields

    def agent_leaderboard(self, start, end):
        params = {"start_date": start, "end_date": end}
        response = self.session.get("https://api.callhub.io/v1/analytics/agent-leaderboard", params=params)
        return response.json().get("plot_data")

    def fields(self):
        """
        Returns a list of fields configured in the CallHub account and their ids
        Returns:
            fields (``dict``): dictionary of fields and ids
            >>> {"first name": 0, "last name": 1}
        """
        response = self.session.get('https://api.callhub.io/v1/contacts/fields/')
        return {field['name']: field["id"] for field in response.json()["results"]}

    def bulk_create(self, phonebook_id, contacts, country_iso):
        """
        Leverages CallHub's bulk-upload feature to create many contacts. Supports custom fields.
        >>> contacts = [{'first name': 'Sumiya', 'phone number':'5555555555', 'mobile number': '5555555555'},
        >>>             {'first name': 'Joe', 'phone number':'5555555555', 'mobile number':'5555555555'}]
        >>> callhub.bulk_create(885473, contacts, 'CA')
        Args:
            phonebook_id(``int``): ID of phonebank to insert contacts into.
            contacts(``list``): Contacts to insert
            country_iso(``str``): ISO 3166 two-char country code,
                see https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2
        """
        # Step 1. Get all fields from callhub account
        # Step 2. Check if fields match contacts
        # Step 3. Bulk upload

        # Note: CallHub fields are implemented funkily. They can contain capitalization but "CUSTOM_FIELD"
        # and "custom_field" cannot exist together in the same account. For that reason, for the purposes of API work,
        # fields are treated as case insensitive despite capitalization being allowed. Attempting to upload a contact
        # with "CUSTOM_FIELD" will match to "custom_field" in a CallHub account.
        contacts = [CaseInsensitiveDict(contact) for contact in contacts]
        account_fields = self.fields()
        account_fields_names = set([field.lower() for field in account_fields.keys()])
        upload_fields_names = set([field.lower() for field in self._collect_fields(contacts)])

        if upload_fields_names.issubset(account_fields_names):
            # Create CSV file in memory in a way that pleases CallHub and generate column mapping
            csv_file, mapping = csv_and_mapping_create(contacts, account_fields)

            # Upload CSV
            data = {
                'phonebook_id': phonebook_id,
                'country_choice': 'custom',
                'country_ISO': country_iso,
                'mapping': mapping
            }

            r = self.session.post('https://api.callhub.io/v1/contacts/bulk_create/', data=data,
                                  files={'contacts_csv': csv_file})

            if r.json().get("message") == "'Import in progress. You will get an email when import is complete'":
                return True
            elif 'Request was throttled.' in r.json().get("detail"):
                raise RuntimeError("Bulk_create request was throttled because rate limit was exceeded.", r.json())
            else:
                raise RuntimeError("CallHub did not report that import was successful: ", r.json())

        else:
            raise LookupError("Attempted to upload contacts that contain fields that haven't been "
                              "created in CallHub. Fields present in upload: {} Fields present in "
                              "account: {}".format(upload_fields_names, account_fields_names))
