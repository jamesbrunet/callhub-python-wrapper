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
* Add number to DNC list

### Currently on roadmap

* Create phonebook
* Delete contact(s) from DNC list
* Create/get/delete webhook
* Create/get teams
* Add/delete agent to/from team
* Create/delete agent

# Usage

    import callhub
    callhub = CallHub(api_key="123456789ABCDEF")
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
    
    # Get names and ids of all do-not-contact lists
    callhub.get_dnc_lists()
    
    # Get all phone numbers marked do-not-contact and the do-not
    # contact list(s) that they are associated with
    callhub.get_dnc_phones()
    
    # Add phone number 555-555-5555 to DNC list 123456789
    callhub.add_dnc("5555555555", "123456789")
