# DOI tester

This is a one purpose project but contains several interesting code snippets that might be useful for others.


## Core Installation
* redis (http://redis.io/)
* redis-py (sudo pip install redis)
* TOR (https://www.torproject.org/) with authentication via cookie enabled (check control_auth_cookie)

## Reporting
* get a google developer account (email like) and your .p12
* google spreadsheet must be shared with your google developer account
* google spreadsheet must have at least the "progress" sheet with
"UPDATED","OK", "size", "IMPORTED", "ERRORS", "IN PROGRESS", "TOTAL" header column names
* google spreadsheet *cannot* be shared using Share->Shareable link
* see status/requirements.txt


## How to start
1. start tor
2. copy control_auth_token to this directory (e.g., copy.tor.cookie.bat)
3. start redis (e.g., start.redis.bat when redis is inside ./redis directory)
4. copy settings.py.dist settings.py and update it
5. start.import.bat
6. start.checking.bat
7. optional start.status.bat (start.status.erors.bat)
8. ...
9. kill.checkers.bat

## Hints for Windows
* https://github.com/MSOpenTech/redis/releases
* use redis desktop monitor for inspection redis db
* including *.bat files for cleaner picture
