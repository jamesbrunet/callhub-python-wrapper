import requests
from .auth import CallHubAuth
from ratelimit import limits, sleep_and_retry
from .bulk_upload_tools import csv_and_mapping_create
from requests.structures import CaseInsensitiveDict
import types
import math
from requests_futures.sessions import FuturesSession
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import traceback

class CallHub:
    API_LIMIT = {
        "GENERAL": {"calls": 15, "period": 1},
        "BULK_CREATE": {"calls": 1, "period": 70},
    }

    def __init__(self, api_domain, api_key=None, rate_limit=API_LIMIT):
        """
        Instantiates a new CallHub instance
        >>> callhub = CallHub("https://api-na1.callhub.io")
        With built-in rate limiting disabled:
        >>> callhub = CallHub(rate_limit=False)
        Args:
            api_domain (``str``): Domain to access API (eg: api.callhub.io, api-na1.callhub.io), this varies by account
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
        self.session = FuturesSession(max_workers=43)

        # Truncate final '/' off of API domain if it was provided
        if api_domain[-1] == "/":
            self.api_domain = api_domain[:-1]
        else:
            self.api_domain = api_domain

        if rate_limit:
            # Apply general rate limit to self.session.get
            rate_limited_get = sleep_and_retry(limits(**rate_limit["GENERAL"])(FuturesSession.get))
            self.session.get = types.MethodType(rate_limited_get, self.session)
            
            # Apply general rate limit to self.session.post
            rate_limited_post = sleep_and_retry(limits(**rate_limit["GENERAL"])(FuturesSession.post))
            self.session.post = types.MethodType(rate_limited_post, self.session)
            
            # Apply bulk rate limit to self.bulk_create
            self.bulk_create = sleep_and_retry(limits(**rate_limit["BULK_CREATE"])(self.bulk_create))

        self.session.auth = CallHubAuth(api_key=api_key)

        # validate_api_key returns administrator email on success
        self.admin_email = self.validate_api_key()

        # cache for do-not-contact number/list to id mapping
        self.dnc_cache = {}

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
        response = self.session.get("{}/v1/agents/".format(self.api_domain)).result()
        if response.json().get("detail") in ['User inactive or deleted.', 'Invalid token.']:
            raise ValueError("Bad API Key")
        elif "count" in response.json():
            if response.json()["count"]:
                return response.json()["results"][0]["owner"][0]["username"]
            else:
                return "Cannot deduce admin account. No agent accounts (not even the default account) exist."
        else:
            raise RuntimeError("CallHub API is not returning expected values, but your api_key is fine. Their API "
                               "specifies that https://callhub-api-domain/v1/agents returns a 'count' field, but this was "
                               "not returned. Please file an issue on GitHub for this project, if an issue for this not "
                               "already exist.")

    def agent_leaderboard(self, start, end):
        params = {"start_date": start, "end_date": end}
        response = self.session.get("{}/v1/analytics/agent-leaderboard/".format(self.api_domain), params=params).result()
        return response.json().get("plot_data")

    def fields(self):
        """
        Returns a list of fields configured in the CallHub account and their ids
        Returns:
            fields (``dict``): dictionary of fields and ids
            >>> {"first name": 0, "last name": 1}
        """
        response = self.session.get('{}/v1/contacts/fields/'.format(self.api_domain)).result()
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

            response = self.session.post('{}/v1/contacts/bulk_create/'.format(self.api_domain), data=data,
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
            url = "{}/v1/contacts/".format(self.api_domain)
            responses, errors = self._handle_requests([{
                "func": self.session.post,
                "func_params": {"url": url, "data": {"name": contact}},
                "expected_status": 201
            }])
            if errors:
                raise RuntimeError(errors)
            return responses[0].json().get("id")

    def get_contacts(self, limit):
        """
        Gets all contacts.
        Args:
            limit (``int``): Limit of number of contacts to get. If limit not provided, will
                return first 100 contacts.
        Returns:
            contact_list (``list``): List of contacts, where each contact is a dict of key value pairs.
        """
        contacts_url = "{}/v1/contacts/".format(self.api_domain)
        return self._get_paged_data(contacts_url, limit)

    def _get_paged_data(self, url, limit=float(math.inf)):
        """
        Internal function. Leverages _bulk_requests to aggregate paged data and return it quickly.
        Args:
            url (``str``): API endpoint to get paged data from.
        Keyword Args:
            limit (``float or int``): Limit of paged data to get. Default is infinity.
        Returns:
            paged_data (``list``) All of the paged data as a signle list of dicts, where each dict contains key value
                pairs that represent each individual item in a page.
        """
        first_page = self.session.get(url).result()
        if first_page.status_code != 200:
            raise RuntimeError("Status code {} when making request to: "
                                "{}, expected 200. Details: {})".format(first_page.status_code,
                                                                        url,
                                                                        first_page.text))
        first_page = first_page.json()

        # Handle either limit of 0 or no results
        if first_page["count"] == 0 or limit == 0:
            return []

        # Set limit to the smallest of either the count or the limit
        limit = min(first_page["count"], limit)

        # Calculate number of pages
        page_size = len(first_page["results"])
        num_pages = math.ceil(limit/page_size)

        requests = []
        for i in range(1, num_pages+1):
            requests.append({"func": self.session.get,
                             "func_params": {"url": url, "params": {"page": i}},
                             "expected_status": 200})
        responses_list, errors = self._handle_requests(requests)
        if errors:
            raise RuntimeError(errors)

        # Turn list of responses into aggregated data from all pages
        paged_data = []
        for response in responses_list:
            paged_data += response.json()["results"]
        paged_data = paged_data[:limit]
        return paged_data

    def _handle_requests(self, requests_list, aggregate_json_value=None, retry=False, current_retry_count=0):
        """
        Internal function. Executes a list of requests in batches, asynchronously. Allows fast execution of many reqs.
        >>> requests_list = [{"func": session.get,
        >>>                   "func_params": {"url":"https://callhub-api-domain/v1/contacts/", "params":{"page":"1"}}}
        >>>                   "expected_status": 200]
        >>> _bulk_request(requests_list)
        Args:
            requests_list (``list``): List of dicts that each include a request function, its parameters, and an
                optional expected status. These will be executed in batches.
        """
        # Send bulk requests in batches of at most 500
        batch_size = 500
        requests_awaiting_response = []
        responses = []
        errors = []
        for i, request in enumerate(requests_list):
            # Execute request asynchronously
            requests_awaiting_response.append(request["func"](**request["func_params"]))
            # Every time we execute batch_size requests OR we have made our last request, wait for all requests
            # to have received responses before continuing. This batching prevents us from having tens or hundreds of
            # thousands of pending requests with CallHub
            if i % batch_size == 0 or i == (len(requests_list)-1):
                for req_awaiting_response in requests_awaiting_response:
                    response = req_awaiting_response.result()
                    try:
                        if requests_list[i]["expected_status"] and response.status_code != int(requests_list[i]["expected_status"]):
                            raise RuntimeError("Status code {} when making request to: "
                                               "{}, expected {}. Details: {})".format(response.status_code,
                                                                         requests_list[i]["func_params"]["url"],
                                                                         requests_list[i]["expected_status"],
                                                                         response.text))
                        responses.append(response)

                    except RuntimeError as api_except:
                        errors.append((requests_list[i], api_except))

                requests_awaiting_response = []

        if errors and retry and current_retry_count < 1:
            failed_requests = [error[0] for error in errors]
            new_responses, errors = self._handle_requests(failed_requests, retry=True, current_retry_count=current_retry_count+1)
            responses = responses + new_responses

        return responses, errors

    def get_dnc_lists(self):
        """
        Returns ids and names of all do-not-contact lists
        Returns:
            dnc_lists (``dict``): Dictionary of dnc lists where the key is the id and the value is the name
        """
        dnc_lists = self._get_paged_data("{}/v1/dnc_lists/".format(self.api_domain))
        return {dnc_list['url'].split("/")[-2]: dnc_list["name"] for dnc_list in dnc_lists}

    def pretty_format_dnc_data(self, dnc_contacts):
        dnc_lists = self.get_dnc_lists()
        dnc_phones = defaultdict(list)
        for dnc_contact in dnc_contacts:
            phone = dnc_contact["phone_number"]
            dnc_list_id = dnc_contact["dnc"].split("/")[-2]
            dnc_contact_id = dnc_contact["url"].split("/")[-2]
            dnc_list = {"list_id": dnc_list_id, "name": dnc_lists[dnc_list_id], "dnc_contact_id": dnc_contact_id}
            dnc_phones[phone].append(dnc_list)
        return dict(dnc_phones)

    def get_dnc_phones(self):
        """
        Returns all phone numbers in all DNC lists
        Returns:
            dnc_phones (``dict``): Dictionary of all phone numbers in all dnc lists. A phone number may be associated
                with multiple dnc lists. Note that each phone number on each dnc list has a unique dnc_contact_id that
                has NOTHING to do with the contact_id of the actual contacts related to those phone numbers. Schema:
                >>> dnc_contacts = {"16135554432": [
                >>>                                    {"list_id": 5543, "name": "Default DNC List", "dnc_contact_id": 1234}
                >>>                                    {"list_id": 8794, "name": "SMS Campaign", "dnc_contact_id": 4567}
                >>>                                 ]}}
        """
        dnc_contacts = self._get_paged_data("{}/v1/dnc_contacts/".format(self.api_domain))
        return self.pretty_format_dnc_data(dnc_contacts)


    def add_dnc(self, phone_numbers, dnc_list_id):
        """
        Adds phone numbers to a DNC list of choice
        Args:
            phone_numbers (``list``): Phone numbers to add to DNC
            dnc_list (``str``): DNC list id to add contact(s) to
        Returns:
            results (``dict``): Dict of phone numbers and DNC lists added to
            errors (``list``): List of errors and failures
        """
        if not isinstance(phone_numbers, list):
            raise TypeError("add_dnc expects a list of phone numbers. If you intend to only add one number to the "
                            "do-not-contact list, add a list of length 1")

        url = "{}/v1/dnc_contacts/".format(self.api_domain)
        requests = []
        for number in phone_numbers:
            data = {"dnc": "{}/v1/dnc_lists/{}/".format(self.api_domain, dnc_list_id), 'phone_number': number}
            requests.append({"func": self.session.post,
                             "func_params": {"url": url, "data":data},
                             "expected_status": 201})

        responses, errors = self._handle_requests(requests, retry=True)
        dnc_records = [request.json() for request in responses]
        results = self.pretty_format_dnc_data(dnc_records)
        return results, errors


    def remove_dnc(self, numbers, dnc_list=None):
        """
        Removes phone numbers from do-not-contact list. CallHub's api does not support this, instead it only supports
        removing phone numbers by their internal do not contact ID. I want to abstract away from that, but it requires
        building a table of phone numbers mapping to their dnc ids, which can slow this function down especially when
        using an account with many numbers already marked do-not-contact. This function takes advantage of caching to
        get around this, and a CallHub instance will have a cache of numbers and dnc lists -> dnc_contact ids available
        for use. This cache is refreshed if a number is requested to be removed from the DNC list that does not appear
        in the cache.
        Args:
            phone_numbers (``list``): Phone numbers to remove from DNC
        Keyword Args:
            dnc_list (``str``, optional): DNC list id to remove numbers from. If not specified, will remove number from
                all dnc lists.
        Returns:
            errors (``list``): List of errors
        """
        # Check if we need to refresh DNC phone numbers cache
        if not set(numbers).issubset(set(self.dnc_cache.keys())):
            self.dnc_cache = self.get_dnc_phones()

        dnc_ids_to_purge = []
        for number in numbers:
            for dnc_entry in self.dnc_cache[number]:
                if dnc_list and (dnc_entry["list_id"] == dnc_list):
                    dnc_ids_to_purge.append(dnc_entry["dnc_contact_id"])
                elif not dnc_list:
                    dnc_ids_to_purge.append(dnc_entry["dnc_contact_id"])

        url = "{}/v1/dnc_contacts/{}/"
        requests = []
        for dnc_id in dnc_ids_to_purge:
            requests.append({"func": self.session.delete,
                             "func_params": {"url": url.format(self.api_domain, dnc_id)},
                             "expected_status": 204})
        responses, errors = self._handle_requests(requests)
        return errors

    def create_dnc_list(self, name):
        """
        Creates a new DNC list
        Args:
            name (``str``): Name to assign to DNC list
        Returns:
            id (``str``): ID of created dnc list
        """
        url = "{}/v1/dnc_lists/".format(self.api_domain)
        responses, errors = self._handle_requests([{
            "func": self.session.post,
            "func_params": {"url": url, "data": {"name": name}},
            "expected_status": 201
        }])
        if errors:
            raise RuntimeError(errors)
        return responses[0].json()["url"].split("/")[-2]

    def remove_dnc_list(self, id):
        """
        Deletes an existing DNC list
        Args:
            id (``str``): ID of DNC list to delete
        """
        url = "{}/v1/dnc_lists/{}/"
        responses, errors = self._handle_requests([{
            "func": self.session.delete,
            "func_params": {"url": url.format(self.api_domain, id)},
            "expected_status": 204
        }])
        if errors:
            raise RuntimeError(errors)


    def get_campaigns(self):
        """
        Get call campaigns
        Returns:
            campaigns (``dict``): list of campaigns
        """
        url = "{}/v1/callcenter_campaigns/".format(self.api_domain)
        campaigns = self._get_paged_data(url)
        return campaigns

    def create_phonebook(self, name, description=""):
        """
        Create a phonebook
        Args:
            name (``str``): Name of phonebook
        Keyword Args:
            description (``str``, optional): Description of phonebook
        Returns:
            id (``str``): id of phonebook
        """
        url = "{}/v1/phonebooks/".format(self.api_domain)
        responses, errors = self._handle_requests([{
            "func": self.session.post,
            "func_params": {"url": url, "data": {"name": name, "description": description}},
            "expected_status": 201
        }])
        if errors:
            raise RuntimeError(errors)
        id = responses[0].json()["url"].split("/")[-2]
        return id

    def create_webhook(self, target, event="cc.notes"):
        """
        Creates a webhook on a particular target
        Args:
            target (``str``): URL for CallHub to send webhook to
        Keyword Args:
            event (``str``, optional): Event which triggers webhook. Default: When an agent completes a call (cc.notes)
        Returns:
            id (``str``): id of created webhook
        """
        url = "{}/v1/webhooks/".format(self.api_domain)
        responses, errors = self._handle_requests([{
            "func": self.session.post,
            "func_params": {"url": url, "data": {"target": target, "event": event}},
            "expected_status": 201
        }])
        if errors:
            raise RuntimeError(errors)
        return responses[0].json()["id"]

    def get_webhooks(self):
        """
        Fetches webhooks created by a CallHub account
        Returns:
            webhooks (``dict``): list of webhooks
        """
        url = "{}/v1/webhooks/".format(self.api_domain)
        webhooks = self._get_paged_data(url)
        return webhooks

    def remove_webhook(self, id):
        """
        Deletes a webhook with a given id
        Args:
            id (``str``): id of webhook to delete
        """
        url = "{}/v1/webhooks/{}/".format(self.api_domain, id)
        responses, errors = self._handle_requests([{
            "func": self.session.delete,
            "func_params": {"url": url},
            "expected_status": 204
        }])
        if errors:
            raise RuntimeError(errors)
