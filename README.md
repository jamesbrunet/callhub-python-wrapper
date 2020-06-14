# CallHub Python Wrapper

[![Build Status](https://travis-ci.org/jamesbrunet/callhub-python-wrapper.svg?branch=master)](https://travis-ci.org/jamesbrunet/callhub-python-wrapper) [![Coverage Status](https://coveralls.io/repos/github/jamesbrunet/callhub-python-wrapper/badge.svg?branch=master)](https://coveralls.io/github/jamesbrunet/callhub-python-wrapper?branch=master) ![PyPI - Downloads](https://img.shields.io/pypi/dm/callhub-python-wrapper?color=green&label=pypi%20downloads)

CallHub API Client Wrapper for Python

Creates a clean(er) python interface to several important functions of the CallHub API.

![project-logo](https://raw.githubusercontent.com/jamesbrunet/callhub-python-wrapper/master/docs/assets/logo-transparent-small.png)

### Installation

`pip install callhub-python-wrapper`

*Requires Python 3.5 or higher*

### Features

* Built-in (optional) ratelimiting that respects CallHub's varying rate limits for different functions
* Better error handling for uploading contacts with fields that don't exist in CallHub
* Abstracted away some tedious parts of using CallHub's API. When uploading contacts, CallHub wants you to map CSV columns to the ids of each field in CallHub, which is difficult and easy to mess up. This wrapper handles all of that by matching on field names.
* Automatically handles paging when doing bulk fetching
* Uses async requests to improve speed for repetitive calls (implemented in get_contacts)

### Currently implemented

* Bulk create contacts
* Get agent leaderboard
* Get all fields and IDs (including custom fields)
* Bulk get contacts and fields
* Create single contact

### Implemented but not in latest release

* Get all phone numbers on DNC list
* Get all DNC lists
* Add/remove numbers to/from DNC list(s)
* Create and delete DNC lists

### Currently on roadmap

* Create phonebook
* Create/get/delete webhook
* Create/get teams
* Add/delete agent to/from team
* Create/delete agent

# Usage
##### Initialization
    import callhub
    callhub = CallHub(api_key="123456789ABCDEF")
##### Contacts
    phonebook_id = 6545324
    contacts = [{'first name': 'Sumiya', 'phone number':'5555555555', 'mobile number': '5555555555'},
               {'first name': 'Joe', 'phone number':'5555555555', 'mobile number':'5555555555'}]
    country_iso = "CA"
    
    # Create multiple contacts
    callhub.bulk_create(phonebook_id, contacts, country_iso)
    
    # Create single contact
    callhub.create_contact(contacts[0])
    
    # Get all contacts (up to a user-specified limit)
    callhub.get_contacts(limit=1000000)
    
    # Get all contacts with no limit (this might take a while, see performance notes)
    callhub.get_contacts()
##### DNC Lists
    # Get names and ids of all do-not-contact lists
    callhub.get_dnc_lists()
    
    # Get all phone numbers marked do-not-contact and the do-not
    # contact list(s) that they are associated with
    callhub.get_dnc_phones()
    
    # Create a DNC list
    list_id = callhub.create_dnc_list("My DNC List Name")
    
    # Delete a DNC list
    callhub.remove_dnc_list(list_id)
    
    # Add phone number 555-555-5555 to DNC list id 123456789
    callhub.add_dnc(["5555555555"], "123456789")
    
    # Add multiple phone numbers to DNC list id 12345689
    callhub.add_dnc(["5555555555","5554443333"], "123456789")
    
    # Remove number(s) from all DNC lists
    callhub.remove_dnc(["5554443333"])
    
    # Remove number(s) from specific DNC list id
    callhub.remove_dnc(["5555555555"], "123456789")
    
# Performance Notes

##### Bulk creating contacts works differently from most other functions

This takes advantage of CallHub's built in bulk_create API endpoint, so expect equivalent speeds to uploading a spreadsheet of contacts as a normal admin user. Note that bulk_create can only be called once every 70 seconds to comply with a special CallHub ratelimit on this endpoint.

##### It's faster to call add_dnc/remove_dnc with ten numbers than to call add_dnc/remove_dnc with one number ten times

If you use this library to make looping calls on most functions (e.g. add_dnc), you can expect a performance of about 0.5-1 requests/second. This is because all functions wait until they receives a response from the server before exiting.

However, you can get much faster performance if you call these functions with a list of contacts (as opposed to ten times with one contact each time). This is because every function that does many similar repetitive API calls leverages async requests for repetitive calls (makes a large batch of requests and then waits for that pool of requests to finish.) Because of this, we can achieve real-world speeds of adding 5-10 numbers to a DNC list per second for large batches of numbers (CallHub's API limit is 20/s).

##### Fetching contacts with get_contacts can take a while

CallHub only gives us 10 contacts per api request when using get_contacts, so expect this library to fetch contacts at about 100 contacts/s. That's about 17 minutes to fetch 100K contacts!
