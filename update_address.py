import logging
import requests
import json
from copy import deepcopy
import sys

GEONAMES = {}
GEONAMES['USER'] = "roradmin"
GEONAMES['URL'] = 'http://api.geonames.org/getJSON'


def find_between(first, last, s):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ""


def ror_geonames_mapping():
    template = {
        "lat": "lat",
        "lng": "lng",
        "country_geonames_id": "countryId",
        "city": "name",
        "geonames_city": {
                "id": "geonameId",
            "city": "name",
                    "geonames_admin1": {
                        "name": "adminName1",
                        "ascii_name": "adminName1",
                        "id": "adminId1",
                        "code": ["countryCode", "adminCode1"]
                    },
                "geonames_admin2": {
                        "name": "adminName2",
                        "id": "adminId2",
                        "ascii_name": "adminName2",
                        "code": ["countryCode", "adminCode1", "adminCode2"]
                    }
        }
    }
    return template


def get_geonames_response(id):
    # queries geonames api with the city geonames id as a query parameter
    msg = None
    result = None
    query_params = {}
    query_params['geonameId'] = id
    query_params['username'] = GEONAMES['USER']
    url = GEONAMES['URL']
    try:
        response = requests.get(url, params=query_params)
        response.raise_for_status()
        result = json.loads(response.text)
    except requests.exceptions.RequestException as e:
        msg = "Connection Error"
    return result, msg


def map_type_float():
    return ["lat", "lng"]


def compare_ror_geoname(mapped_fields, ror_address, geonames_response, original_address):
    for key, value in mapped_fields.items():
        # If value is of dict type then print
        # all key-value pairs in the nested dictionary
        if isinstance(value, dict):
            if key in ror_address:
                compare_ror_geoname(
                    value, ror_address[key], geonames_response, original_address)
        else:
            ror_value = ror_address[key] if key in ror_address else original_address[key]
            geonames_value = None
            if (key == "code"):
                key_exists = True
                for x in value:
                    if not(x in geonames_response):
                        key_exists = False
                if key_exists:
                    geonames_value = ".".join(
                        [geonames_response[x] for x in value])
            elif (value in geonames_response) and (geonames_response[value] != ""):
                geonames_value = geonames_response[value]
            if str(ror_value) != str(geonames_value):
                if (key in map_type_float()):
                    ror_address[key] = float(geonames_value)
                else:
                    ror_address[key] = geonames_value
    return deepcopy(ror_address)


def get_record_address(record):
    # returns the address dictionary with the geonames city id
    address = record['addresses'][0]
    id = address['geonames_city']['id']
    return id, address


def update_geonames(record, alt_id=None):
    id, ror_address = get_record_address(record)
    if alt_id == None:
        geonames_response = get_geonames_response(id)[0]
    else:
        geonames_response = get_geonames_response(alt_id)[0]
    mapped_fields = ror_geonames_mapping()
    address = compare_ror_geoname(
        mapped_fields, ror_address, geonames_response, ror_address)
    record['addresses'][0] = address
    return record
