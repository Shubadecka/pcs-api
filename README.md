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
*GET /login*
- input: username, password, and device identifier
- logic: if the user is either not in the users table or is disabled, return that there is no such username. Otherwise, hashes the password, and compares it to the hashed password stored in the 'users' table. If it matches, returns that the combination is valid and the rest of the imformation. Otherwise, doesn't return anything but that the combination isn't valid. If the combination is valid, also sends out an email as listed in the 'users' table and stores the validation code in the 'validation_codes' table.
- returns: whether the username and password are valid, whether the user is an admin, and whether the device is remembered

*GET /two-factor-auth*
- input: a username and a string of numbers
- logic: compares the number sent in with the number stored in the 'validation_codes' table according to user_id. If they match and the code was submitted within 5 minutes of being generated, return True. Else return false. If it matches, delete the validation_code value in the table that was matched.
- returns: whether the user can log in

### File Browser
*GET /list-files*
- input: path
- logic: runs 'listdir' or a similar command to find all the files and directories in the given directory. Returns two lists, one for directories and one for files. Returns an error if the path is a file.
- output: list of files and list of directories and whether the user can share directories in this directory

*PUT /upload-file*
- input: directory, filename, and file
- logic: takes the file and uploads it to the directory with the filename
- output: whether the file was sucessfully uploaded

*PUT /create-directory*
- input: path to new directory and which other users it is shared with
- logic: creates the new directory and adds it to the list of shared directories in the 'root_directories' table and connects it to users in the 'root_directory_user_access' table.
- output: whether the directory was created

*GET /download-file*
- input: path
- logic: returns the file if it exists. If it doesn't exist or is a directory, returns an error message to that effect.
- output: file

*GET /download-directory*
- input: path
- logic: returns the directory as a zipped file. returns an error if it doesn't exist or is a file.
- output: zipped directory

*DELETE /file*
- input: path
- logic: moves the file to /media/tim/nautishub_cloud/palmer_server/storage_folder/deleted_files and returns whether the action was sucessful
- output: whether the file was sucessfully moved

*DELETE /directory*
- input: path
- logic: moves the directory to /media/tim/nautishub_cloud/palmer_server/storage_folder/deleted_files and returns whether the action was sucessful
- output: whether the directory was sucessfully moved

### LLM
*GET /response*
- input: user_id, user conversation so far, model to query
- logic: checks that the input conversation ends with a user message, then calls POST localhost:1440/v1/chat/completions with the entire conversation history, returns the result of that call. updates the user's row in the 'conversation_histories' table.
- output: LLM's next response

### Admin Tools
*GET /user*
- input: username of user performing action, username
- logic: checks that the user performing the action is an admin, if they are: returns the username given, that user's directories they have access to, whether they are an admin, and whether they are disabled

*POST /user*
- input: username of user performing action, username, password, extra directories to give access to, directories to remove access to, whether user is admin
- logic: checks that the user performing the action is an admin, if they are: adds/updates the row in the 'users' table given the username (removes disabled status if needed), adds a root directory with that user's username to the 'root_directories' table if needed, then updates the 'root_directories_user_access' table with the tables given, makes sure the user has access to the directory that shares their username
- output: directories user has access to, whether user is admin

*DELETE /user*
- input: username of user performing action, username
- logic: checks that the user performing the action is an admin, if they are: removes all directory access for that user, deletes their chat history row from the 'chat_histories' table, and marks them as disabled in the 'user' table
- output: whether user with username was disabled

## Database Structure
db_name: palmer_server
user: tim
password: in .env file as PG_PASSWORD
host: /var/run/postgresql
port: 5432

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

*root_directories*
- directory_id: int, PK, NOT NULL
- directory_path: varchar\[max], NOT NULL
- created_by_user_id: int, NULL
- row_created_datetime_utc: datetime\[64], NOT NULL
- row_modified_datetime_utc: datetime\[64], NULL

*user_root_directory_access*
- user_root_directory_access_id: int, PK, NOT NULL
- user_id: int, NOT NULL
- directory_id: int, NOT NULL
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
- was_validated: binary, NULL
- row_created_datetime_utc: datetime\[64], NOT NULL
- row_modified_datetime_utc: datetime\[64], NULL

*validation_codes*
- validation_codes_id: int, PK, NOT NULL
- user_id: int, FK, NOT NULL
- validation_code: int, NULL
- row_created_datetime_utc: datetime\[64], NOT NULL
- row_modified_datetime_utc: datetime\[64], NULL

*chat_histories*
- chat_history_id: int, PK, NOT NULL
- user_id: int, FK, NOT NULL
- chat_history: varchar\[max], NULL
- row_created_datetime_utc: datetime\[64], NOT NULL
- row_modified_datetime_utc: datetime\[64], NULL

-- Users Table
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE, -- Added UNIQUE constraint as usernames typically are
    email TEXT NOT NULL UNIQUE,    -- Added UNIQUE constraint for emails
    hashed_pass TEXT NOT NULL,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    row_created_datetime_utc TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    row_modified_datetime_utc TIMESTAMP WITH TIME ZONE
);

-- Devices Table
CREATE TABLE devices (
    device_id SERIAL PRIMARY KEY,
    incoming_device_id TEXT NOT NULL UNIQUE, -- Assuming this should be unique per device
    user_id INTEGER NULL REFERENCES users(user_id), -- Added potential FK to link device to a user
    device_last_connected_datetime_utc TIMESTAMP WITH TIME ZONE NOT NULL,
    device_remembered_datetime_utc TIMESTAMP WITH TIME ZONE,
    row_created_datetime_utc TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    row_modified_datetime_utc TIMESTAMP WITH TIME ZONE
);

-- Root Directories Table
CREATE TABLE root_directories (
    directory_id SERIAL PRIMARY KEY,
    directory_path TEXT NOT NULL UNIQUE, -- Directory paths should be unique
    created_by_user_id INTEGER NULL REFERENCES users(user_id) ON DELETE SET NULL, -- FK to users
    row_created_datetime_utc TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    row_modified_datetime_utc TIMESTAMP WITH TIME ZONE
);

-- User Root Directory Access Table
-- Junction table for many-to-many relationship between users and root_directories
CREATE TABLE user_root_directory_access (
    user_root_directory_access_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    directory_id INTEGER NOT NULL REFERENCES root_directories(directory_id) ON DELETE CASCADE,
    row_created_datetime_utc TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    row_modified_datetime_utc TIMESTAMP WITH TIME ZONE,
    UNIQUE (user_id, directory_id) -- Prevent duplicate access entries
);

-- Logins Table
CREATE TABLE logins (
    login_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    device_id INTEGER NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    was_validated BOOLEAN NULL, -- 'binary' interpreted as BOOLEAN
    row_created_datetime_utc TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    row_modified_datetime_utc TIMESTAMP WITH TIME ZONE
);

-- Validation Codes Table
CREATE TABLE validation_codes (
    validation_codes_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    validation_code INTEGER NULL, -- README says 'int', endpoint description says 'string of numbers'
                                 -- Sticking to INTEGER based on table schema type.
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, -- Added an expiry for codes
    row_created_datetime_utc TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    row_modified_datetime_utc TIMESTAMP WITH TIME ZONE
);

-- Chat Histories Table
CREATE TABLE chat_histories (
    chat_history_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    chat_history TEXT NULL,
    row_created_datetime_utc TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    row_modified_datetime_utc TIMESTAMP WITH TIME ZONE
);