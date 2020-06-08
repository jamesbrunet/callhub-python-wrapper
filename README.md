# CallHub Python Wrapper
CallHub API Client Wrapper for Python

Creates a clean(er) python interface to several important functions of the CallHub API.

### Features
* Built-in (optional) ratelimiting that respects CallHub's varying rate limits for different functions
* Better error handling for uploading contacts with fields that don't exist in CallHub
* Abstracted away some tedious parts of using CallHub's API. When uploading contacts, CallHub wants you to map CSV columns to the ids of each field in CallHub, which is difficult and easy to mess up. This wrapper handles all of that by matching on field names.

### Currently implemented
* Bulk create contacts
* Get agent leaderboard
* Get all fields and IDs (including custom fields)

### Currently on roadmap
* Create phonebook
* Create single contact
* Add/delete/get contacts to/from DNC list
* Create/get/delete webhook
* Create/get teams
* Add/delete agent to/from team
* Create/delete agent

# Usage
    callhub = CallHub(api_key="123456789ABCDEF")
    contacts = [{'first name': 'Sumiya', 'phone number':'5555555555', 'mobile number': '5555555555'},
               {'first name': 'Joe', 'phone number':'5555555555', 'mobile number':'5555555555'}],
    callhub.bulk_create(6545324, contacts, "CA")
