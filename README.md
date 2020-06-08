# CallHub Python Wrapper
CallHub API Client Wrapper for Python

Creates a clean(er) python interface to several important functions of the CallHub API.

Features:
* Built-in (optional) ratelimiting that respects CallHub's varying rate limits for different functions
* Better error handling for uploading contacts with fields that don't exist in CallHub
* Abstracted away some tedious parts of using CallHub's API. When uploading contacts, CallHub wants you to map CSV columns to the ids of each field in CallHub, which is difficult and easy to mess up. This wrapper handles all of that for you.

Currently implemented:
* Bulk create contacts
* Get agent leaderboard
* Get all fields and IDs (including custom fields)

Currently on roadmap:
* Create phonebook
* Create single contact
* Add/delete/get contacts to/from DNC list
* Create/get/delete webhook
* Create/get teams
* Add/delete agent to/from team
* Create/delete agent
