import requests
from .auth import CallHubAuth
from ratelimit import limits, sleep_and_retry
from .bulk_upload_tools import csv_and_mapping_create
from requests.structures import CaseInsensitiveDict
import types
import math
from requests_futures.sessions import FuturesSession

class CallHub:
    API_LIMIT = {
        "GENERAL": {"calls": 18, "period": 1},
        "BULK_CREATE": {"calls": 1, "period": 70},
    }

    def __init__(self, api_key=None, rate_limit=API_LIMIT):
        """
        Instantiates a new CallHub instance
        >>> callhub = CallHub()
        With built-in rate limiting disabled:
        >>> callhub = CallHub(rate_limit=False)
        Keyword Args:
            api_key (``str``, optional): Optional API key. If not provided,
                it will attempt to use ``os.environ['CALLHUB_API_KEY']``
            rate_limit (``dict``, optional): Enabled by default with settings that respect callhub's API limits.
                Setting this to false disables ratelimiting, or you can set your own limits by following the example
                below. Please don't abuse! :)
                >>> callhub = CallHub(rate_limit={"GENERAL": {"calls": 18, "period": 1},
                >>>                               "BULK_CREATE": {"calls": 1, "period": 70}})
                - Default limits bulk_create to 1 per 70 seconds (CallHub states their limit is every 60s but in
                  practice a delay of 60s exactly can trip their rate limiter anyways)
                - Default limits all other API requests to 18 per second (CallHub support states their limit is 20/s but
                  this plays it on the safe side, because other rate limiters seem a little sensitive)
        """
        self.session = FuturesSession()

        if rate_limit:
            # Apply general rate limit to self.session.get
            rate_limited_get = sleep_and_retry(limits(**rate_limit["GENERAL"])(FuturesSession.get))
            self.session.get = types.MethodType(rate_limited_get, self.session)
            # Apply bulk rate limit to self.bulk_create
            self.bulk_create = sleep_and_retry(limits(**rate_limit["BULK_CREATE"])(self.bulk_create))

        self.session.auth = CallHubAuth(api_key=api_key)

        # validate_api_key returns administrator email on success
        self.admin_email = self.validate_api_key()




    def __repr__(self):
        return "<CallHub admin: {}>".format(self.admin_email)

    def _collect_fields(self, contacts):
        """ Internal Function to get all fields used in a list of contacts """
        fields = set()
        for contact in contacts:
            for key in contact:
                fields.add(key)
        return fields

    def _assert_fields_exist(self, contacts):
        """
        Internal function to check if fields in a list of contacts exist in CallHub account
        If fields do not exist, raises LookupError.
        """
        # Note: CallHub fields are implemented funkily. They can contain capitalization but "CUSTOM_FIELD"
        # and "custom_field" cannot exist together in the same account. For that reason, for the purposes of API work,
        # fields are treated as case insensitive despite capitalization being allowed. Attempting to upload a contact
        # with "CUSTOM_FIELD" will match to "custom_field" in a CallHub account.
        fields_in_contacts = self._collect_fields(contacts)
        fields_in_callhub = self.fields()

        # Ensure case insensitivity and convert to set
        fields_in_contact = set([field.lower() for field in fields_in_contacts])
        fields_in_callhub = set([field.lower() for field in fields_in_callhub.keys()])

        if fields_in_contact.issubset(fields_in_callhub):
            return True
        else:
            raise LookupError("Attempted to upload contact (s) that contain fields that haven't been "
                              "created in CallHub. Fields present in upload: {} Fields present in "
                              "account: {}".format(fields_in_contact, fields_in_callhub))

    def validate_api_key(self):
        """
        Returns admin email address if API key is valid. In rare cases, may be unable to find admin email address, and
        returns a warning in that case. If API key invalid, raises ValueError. If the CallHub API returns unexpected
        information, raises RunTimeError.
        Returns:
            username (``str``): Email of administrator account
        """
        response = self.session.get("https://api.callhub.io/v1/agents/").result()
        if response.json().get("detail") in ['User inactive or deleted.', 'Invalid token.']:
            raise ValueError("Bad API Key")
        elif "count" in response.json():
            if response.json()["count"]:
                return response.json()["results"][0]["owner"][0]["username"]
            else:
                return "Cannot deduce admin account. No agent accounts (not even the default account) exist."
        else:
            raise RuntimeError("CallHub API is not returning expected values, but your api_key is fine. Their API "
                               "specifies that https://api.callhub.io/v1/agents returns a 'count' field, but this was "
                               "not returned. Please file an issue on GitHub for this project, if an issue for this not "
                               "already exist.")

    def agent_leaderboard(self, start, end):
        params = {"start_date": start, "end_date": end}
        response = self.session.get("https://api.callhub.io/v1/analytics/agent-leaderboard/", params=params).result()
        return response.json().get("plot_data")

    def fields(self):
        """
        Returns a list of fields configured in the CallHub account and their ids
        Returns:
            fields (``dict``): dictionary of fields and ids
            >>> {"first name": 0, "last name": 1}
        """
        response = self.session.get('https://api.callhub.io/v1/contacts/fields/').result()
        return {field['name']: field["id"] for field in response.json()["results"]}

    def bulk_create(self, phonebook_id, contacts, country_iso):
        """
        Leverages CallHub's bulk-upload feature to create many contacts. Supports custom fields.
        >>> contacts = [{'first name': 'Sumiya', 'phone number':'5555555555', 'mobile number': '5555555555'},
        >>>             {'first name': 'Joe', 'phone number':'5555555555', 'mobile number':'5555555555'}]
        >>> callhub.bulk_create(885473, contacts, 'CA')
        Args:
            phonebook_id(``int``): ID of phonebank to insert contacts into.
            contacts(``list``): Contacts to insert (phone number is a MANDATORY field in all contacts)
            country_iso(``str``): ISO 3166 two-char country code,
                see https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2
        """
        # Step 1. Get all fields from CallHub account
        # Step 2. Check if all fields provided for contacts exist in CallHub account
        # Step 3. Turn list of dictionaries into a CSV file and create a column mapping for the file
        # Step 4. Upload the CSV and column mapping to CallHub

        contacts = [CaseInsensitiveDict(contact) for contact in contacts]

        if self._assert_fields_exist(contacts):
            # Create CSV file in memory in a way that pleases CallHub and generate column mapping
            csv_file, mapping = csv_and_mapping_create(contacts, self.fields())

            # Upload CSV
            data = {
                'phonebook_id': phonebook_id,
                'country_choice': 'custom',
                'country_ISO': country_iso,
                'mapping': mapping
            }

            response = self.session.post('https://api.callhub.io/v1/contacts/bulk_create/', data=data,
                                         files={'contacts_csv': csv_file}).result()
            if "Import in progress" in response.json().get("message", ""):
                return True
            elif 'Request was throttled' in response.json().get("detail", ""):
                raise RuntimeError("Bulk_create request was throttled because rate limit was exceeded.",
                                   response.json())
            else:
                raise RuntimeError("CallHub did not report that import was successful: ", response.json())

    def create_contact(self, contact):
        """
        Creates single contact. Supports custom fields.
        >>> contact = {'first name': 'Sumiya', 'phone number':'5555555555', 'mobile number': '5555555555'}
        >>> callhub.create_contact(contact)
        Args:
            contacts(``dict``): Contacts to insert
            Note that country_code and phone_number are MANDATORY
        Returns:
            (``str``): ID of created contact or None if contact not created
        """
        if self._assert_fields_exist([contact]):
            response = self.session.post('https://api.callhub.io/v1/contacts/', data=contact).result()
            return response.json().get("id")

    def get_contacts(self, limit):
        """
        Gets all contacts.
        Args:
            limit (``int``): Limit of number of contacts to get. If limit not provided, will
                return first 100 contacts.
        """
        fetched = 0
        contacts_url = "https://api.callhub.io/v1/contacts/"
        contact_list = []
        first_page = self.session.get(contacts_url).result().json()

        # Handle either limit of 0 or no contacts
        if first_page["count"] == 0 or limit == 0:
            return []

        # Calculate number of pages
        page_size = len(first_page["results"])
        num_pages = min(math.ceil(first_page["count"]/page_size), math.ceil(limit/page_size))
        requests = []
        fetched = 0
        for i in range(1, num_pages+1):
            fetched += page_size
            requests.append(self.session.get(contacts_url, params={"page": i}))

        for i, request in enumerate(requests):
            request = request.result()
            contacts = request.json()
            contact_list += contacts["results"]

            if request.status_code != 200:
                raise RuntimeError("Request {} status code {}".format(request.text, request.status_code))

        contact_list = contact_list[:limit]
        return contact_list
