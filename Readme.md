### Setup

- Dependent libraries installed by running 'python -m pip install -r requirements.txt'
- A file named bdsp_config.json need to be filled before running
- Create the required tables by running the SQL scripts in tables folder on the database being used

### bsp_config file

- "bs_term": org unit number of the term in the Brightspace
- "bspace_url": Brightspace URL
- "client_id": From OAuth 2.0 application registration
- "client_secret": From OAuth 2.0 application registration
- "csv_path": path to database folder in MySql. This due to MySql requires csv uploads from secure folder. Can be changed to any folder, but requires MySql ini file to be changed
- "current_term": Sakai current term
- "current_term_eid": Sakai current term eid
- "dbhost": Hostname for MySqL
- "dbname": Name of the database
- "dbpassword": Password of the user accessing the database
- "dbuser": Username for accessing the database
- "password": Sakai user password
- "refresh_token": From OAuth 2.0 application registration
- "sakai_url": Sakai URL
- "username": Sakai username

### Run

'''
python main.py --help
python main.py # full data sets
python main.py --differential
'''

run main.py with full data sets initially, then schedule differentials
