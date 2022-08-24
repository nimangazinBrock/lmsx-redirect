import argparse
import collections
import json
import io
import zipfile
import sakai
import csv
import logging
import sys

import requests
from requests.auth import HTTPBasicAuth
import mysql.connector

DataSetMetadata = collections.namedtuple('DataSetMetadata', ['plugin', 'table'])

API_VERSION = '1.36'
AUTH_SERVICE = 'https://auth.brightspace.com/'
CONFIG_LOCATION = 'bsp_config.json'


# Set up root logger, and add a file handler to root logger
logging.basicConfig(filename = 'logging.log',
                    level = logging.WARNING,
                    format = '%(asctime)s:%(levelname)s:%(name)s:%(message)s')
 
# Create logger, set level, and add stream handler
parent_logger = logging.getLogger("parent")
parent_logger.setLevel(logging.INFO)
parent_shandler = logging.StreamHandler()
parent_logger.addHandler(parent_shandler)
 
logging.disable('DEBUG')

FULL_DATA_SET_METADATA = [
    DataSetMetadata(
        plugin='07a9e561-e22f-4e82-8dd6-7bfb14c91776',
        table='org_units'
    ),
    DataSetMetadata(
        plugin='1d6d722e-b572-456f-97c1-d526570daa6b',
        table='users'
    ),
    DataSetMetadata(
        plugin='88cfcc22-ce8b-4dab-8d42-2b9da92f29cf',
        table='enroll_withdrawals'
    ),
    DataSetMetadata(
        plugin='2e20f325-6fef-4065-9b5d-1400304611db',
        table='org_units_descendants'
    )

]

DIFF_DATA_SET_METADATA = [
    DataSetMetadata(
        plugin='867fb940-2b80-49da-9c8b-277c99686fc3',
        table='org_units'
    ),
    DataSetMetadata(
        plugin='e8339b7a-2d32-414e-9136-2adf3215a09c',
        table='users'
    ),
    DataSetMetadata(
        plugin='b6660b04-aabe-4603-b415-c9520d7931fe',
        table='enroll_withdrawals'
    ),
    DataSetMetadata(
        plugin='56d9e64a-0076-4fe7-8fd8-2f68feeb6161',
        table='org_units_descendants'
    )
]


def get_config():
    with open(CONFIG_LOCATION, 'r') as f:
        return json.load(f)


def put_config(config):
    with open(CONFIG_LOCATION, 'w') as f:
        json.dump(config, f, sort_keys=True, indent=4)


def trade_in_refresh_token(config):
    response = requests.post(
        '{}/core/connect/token'.format(AUTH_SERVICE),
        # Content-Type 'application/x-www-form-urlencoded'
        data={
            'grant_type': 'refresh_token',
            'refresh_token': config['refresh_token'],
            'scope': 'datahub:*:*'
        },
        auth=HTTPBasicAuth(config['client_id'], config['client_secret'])
    )

    if response.status_code != 200:
        logging.error('Status code: %s; content: %s; message: %s', response.status_code, response.text,
                     "Was not able to obtain access/refresh token")
    response.raise_for_status()

    config['refresh_token'] = response.json()['refresh_token']
    put_config(config)
    return response.json()


def get_with_auth(endpoint, access_token):
    headers = {'Authorization': 'Bearer {}'.format(token_response['access_token'])}
    response = requests.get(endpoint, headers=headers)

    if response.status_code != 200:
        logging.error('Status code: %s; content: %s', response.status_code, response.text)
        response.raise_for_status()

    return response


def get_plugin_link_mapping(config, access_token):
    data_sets = []
    next_page_url = '{bspace_url}/d2l/api/lp/{lp_version}/dataExport/bds'.format(
        bspace_url=config['bspace_url'],
        lp_version=API_VERSION
    )

    while next_page_url is not None:
        list_response = get_with_auth(next_page_url, access_token)
        list_json = list_response.json()

        data_sets += list_json['BrightspaceDataSets']
        next_page_url = list_json['NextPageUrl']

    return {d['PluginId']: d['DownloadLink'] for d in data_sets}


def unzip_and_update_db(response_content, db_conn_params, table):

    with io.BytesIO(response_content) as response_stream:
        with zipfile.ZipFile(response_stream) as zipped_data_set:
            zipped_data_set.extractall(config["csv_path"])
            files = zipped_data_set.namelist()
            assert len(files) == 1
            csv_name = files[0]
            update_db(db_conn_params, table, csv_name)


def date_formatting(db_conn_params, table, csv_file):
    table_column = []
    set_values = []
    with mysql.connector.connect(**db_conn_params) as conn:
        with conn.cursor(buffered=True) as cur:
            cur.execute(
                "SELECT * FROM {table} LIMIT 0;".format(table=table)
            )
            for desc in cur.description:
                if desc[1] == 12:
                    table_column.append("@"+desc[0])
                    tmp_field = desc[0]+"=" + f"""date_format(SUBSTRING(NULLIF({'@'+desc[0]}, ''), 1, 26), "%Y-%m-%d %h:%m:%s")"""
                    set_values.append(tmp_field)
                else:
                    table_column.append("@"+desc[0])
                    set_values.append(f"{desc[0]}=@{desc[0]}")
    with open(config["csv_path"] + csv_file, "r", encoding='utf-8-sig') as data_file:
        header = next(csv.reader(data_file))
    for i in range(len(header)-len(table_column)):
        table_column.append("@dummy")

    return ",".join(table_column), ",".join(set_values)


def update_db(db_conn_params, table, csv_file):
    table_fields, set_variables = date_formatting(db_conn_params, table, csv_file)
    with mysql.connector.connect(**db_conn_params) as conn:
        with conn.cursor(buffered=True) as cur:
            tmp_table_id = 'tmp_' + table
            cur.execute(
                f"""CREATE TABLE IF NOT EXISTS {tmp_table_id} 
                    LIKE {table};"""
            )
            cur.execute(
                f"""LOAD DATA INFILE '{csv_file}'
                  REPLACE INTO TABLE {tmp_table_id}
                  CHARACTER SET utf8mb4
                  FIELDS TERMINATED BY ','
                  ENCLOSED BY '"'
                  LINES TERMINATED BY '\\r\\n'  
                  IGNORE 1 LINES
                  ({table_fields})
                  set {set_variables};"""
            )
            cur.execute(
                f"replace into {table} select * from {tmp_table_id};"
            )
        conn.commit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Script for downloading data sets.')
    parser.add_argument(
        '--differential',
        action='store_true',
        help='Use differential data sets instead of full data sets'
    )
    args = parser.parse_args()

config = get_config()
token_response = trade_in_refresh_token(config)

config['refresh_token'] = token_response['refresh_token']
put_config(config)

data_set_metadata = DIFF_DATA_SET_METADATA if args.differential else FULL_DATA_SET_METADATA
plugin_to_link = get_plugin_link_mapping(config, token_response['access_token'])

db_conn_params = {
    'host': config['dbhost'],
    'database': config['dbname'],
    'user':config['dbuser'],
    'password':config['dbpassword']
}

parent_logger.info("Start running Brightspace jobs")


#Download required csv's from Brightspace and create a tables
for plugin, table in data_set_metadata:
    response = get_with_auth(
        endpoint=plugin_to_link[plugin],
        access_token=token_response['access_token']
    )
    unzip_and_update_db(response.content, db_conn_params, table)
    parent_logger.info(f"{table} created/updated")
    


parent_logger.info("Brightspace jobs ended")

parent_logger.info("Start running Sakai jobs")

# Run sakai jobs
sakai.sakai_run(db_conn_params, config)

parent_logger.info("Sakai jobs ended")

#sakai.delete_all_sites_for_user(config, "nimangazin", '2022-FW')
