# pcs-api
Backend api for the palmer cloud storage

## File Structure
### /router
- Holds the endpoints and fastapi logic
- files are broken down corresponding to the section of utility in the app they provide

### /src
- holds the python logic that make the fastapi endpoints work
- holds connection information to the postgres db
- handles authentication logic and security checks

## Needed Endpoints
### Login Flow
*GET Login*
- input: username, password, and device identifier
- returns: whether the username and password are valid, whether the user is an admin, and whether the device is remembered

*GET 2FA*
- input: a string of numbers
- returns: whether they equal the string sent out

### File Browser
*GET List Files*
- input: path
- output: list of files and list of folders and whether the user can share folders in this directory

*PUT Upload File*
- input: file
- output: whether the file was sucessfully uploaded

*PUT Create Directory*
- input: path to new directory and which other users it is shared with
- output: whether the directory was created

*GET Download File*
- input: path
- output: file

*GET Download Directory*
- input: path
- output: zipped directory

*DELETE File*
- input: path
- output: whether the file was deleted

*DELETE Directory*
- input: path
- output: whether the directory was deleted

### LLM
*GET Response*
- input: user conversation so far, model to query  
- output: LLM's next response

### Admin Tools
*PUT User*
- input: username of user performing action, username, password, extra folders to have access to, whether user is admin
- output: whether the user was sucessfully added

*POST User*
- input: username of user performing action, username, password, extra folders to give access to, folders to remove access to, whether user is admin
- output: folders user has access to, whether user is admin

*DELETE User*
- input: username of user performing action, username
- output: whether user with username was disabled

## Database Structure
### palmer_server
*users*
- user_id: int, PK
- username: varchar\[max], NOT NULL
- email: varchar\[max], NOT NULL
- hashed_pass: varchar\[max], NOT NULL
- is_admin: bit, NOT NULL
- is_active: bit, NOT NULL
- row_created_datetime_utc: datetime\[64], NOT NULL
- row_modified_datetime_utc: datetime\[64], NULL

*root_folders*
- folder_id: int, PK, NOT NULL
- folder_path: varchar\[max], NOT NULL
- created_by_user_id: int, NULL
- row_created_datetime_utc: datetime\[64], NOT NULL
- row_modified_datetime_utc: datetime\[64], NULL

*user_root_folder_access*
- user_root_folder_access_id: int, PK, NOT NULL
- user_id: int, NOT NULL
- folder_id: int, NOT NULL
- row_created_datetime_utc: datetime\[64], NOT NULL
- row_modified_datetime_utc: datetime\[64], NULL

*devices*
- device_id: int, PK, NOT NULL
- incoming_device_id: varchar\[max], NOT NULL
- device_last_connected_datetime_utc: datetime\[64], NOT NULL
- device_remembered_datetime_utc: datetime\[64], NULL
- row_created_datetime_utc: datetime\[64], NOT NULL
- row_modified_datetime_utc: datetime\[64], NULL

*logins*
- login_id: int, PK, NOT NULL
- user_id: int, FK, NOT NULL
- device_id: int, FK, NOT NULL
- row_created_datetime_utc: datetime\[64], NOT NULL
- row_modified_datetime_utc: datetime\[64], NULL