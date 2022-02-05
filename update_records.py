import os
import re
import sys
import csv
import json
import logging
import pkg_resources
import requests
from update_address import update_geonames
from collections import defaultdict


def generate_file_path(ror_id):
	json_dir = os.getcwd() + '/'
	json_file_path = json_dir + ror_id + '.json'
	return json_file_path


def download_record(ror_id):
	api_url = 'https://api.ror.org/organizations/' + ror_id
	ror_data = requests.get(api_url).json()
	ror_data = update_geonames(ror_data)
	json_file_path = generate_file_path(ror_id)
	with open(json_file_path, 'w') as f_out:
		json.dump(ror_data, f_out)


def export_json(json_data, json_file):
	json_file.seek(0)
	json.dump(json_data, json_file)
	json_file.truncate()


def change_nonrepeating_field(json_file, field, value):
	with open(json_file, 'r+') as json_in:
		json_data = json.load(json_in)
		json_data[field] = value
		export_json(json_data, json_in)


def add_repeating_field(json_file, field, value):
	with open(json_file, 'r+') as json_in:
		json_data = json.load(json_in)
		json_data[field].append(value)
		export_json(json_data, json_in)


def delete_repeating_field(json_file, field, value):
	with open(json_file, 'r+') as json_in:
		json_data = json.load(json_in)
		value_index = json_data[field].index(value)
		del json_data[field][value_index]
		export_json(json_data, json_in)


def load_iso_codes():
	iso639_file = pkg_resources.resource_filename(
		__name__, 'iso_data/iso639_mappings.csv')
	iso639_codes = {}
	with open(iso639_file) as f_in:
		reader = csv.reader(f_in)
		for row in reader:
			lang_code, lang = row[0], row[1]
			iso639_codes[lang] = lang_code
	return iso639_codes


def add_label(json_file, value):
	with open(json_file, 'r+') as json_in:
		json_data = json.load(json_in)
		# Update text string uses the convention "label*language" to denote the two parts
		value = value.split('*')
		label_text, label_lang = value[0], value[1]
		iso639_codes = load_iso_codes()
		try:
			lang_iso_code = iso639_codes[label_lang]
			json_data['labels'].append(
				{'label': label_text, 'iso639': lang_iso_code})
			export_json(json_data, json_in)
		except KeyError:
			logging.error('Error:', label_lang,
						  'not found in iso639 standard.')
			sys.exit()


def delete_label(json_file, value):
	with open(json_file, 'r+') as json_in:
		json_data = json.load(json_in)
		del_index = ''
		for index, label in enumerate(json_data['labels']):
			if label['label'] == value:
				del_index = index
		if del_index == '':
			logging.error('Error:', value, 'not found in labels.')
			sys.exit()
		else:
			del json_data['labels'][del_index]
			export_json(json_data, json_in)


def add_external_id(json_file, field, value):
	with open(json_file, 'r+') as json_in:
		json_data = json.load(json_in)
		if field in json_data['external_ids'].keys():
			json_data['external_ids'][field]['preferred'] = value
			json_data['external_ids'][field]['all'].append(value)
		else:
			json_data['external_ids'][field] = {
				'preferred': value, 'all': [value]}
		export_json(json_data, json_in)


def delete_external_id(json_file, field, value):
	with open(json_file, 'r+') as json_in:
		json_data = json.load(json_in)
		if value == json_data['external_ids'][field]['preferred'] and len(json_data['external_ids'][field]['all']) > 1:
			del_index = json_data['external_ids'][field]['all'].index(value)
			del json_data['external_ids'][field]['all'][del_index]
			json_data['external_ids'][field]['preferred'] = json_data['external_ids'][field]['all'][0]
		else:
			del json_data['external_ids'][field]
		export_json(json_data, json_in)


def parse_record_updates_file(f):
	# See test data for update string examples related to this parsing.
	record_updates = defaultdict(list)
	with open(f) as f_in:
		reader = csv.DictReader(f_in)
		for row in reader:
			ror_id = re.sub('https://ror.org/', '', row['ror_id'])
			update_field = row['update_field']
			updates = update_field.split(';')
			updates = [u for u in updates if u.strip() != '']
			for update in updates:
				change_type = update.split('.')[0].strip()
				change_field = re.search(
					r'(?<=\.)(.*)(?=\=\=)', update).group(1)
				change_value = update.split('==')[1].strip()
				record_updates[ror_id].append(
					{'change_type': change_type, 'change_field': change_field, 'change_value': change_value})
	return record_updates


def update_records(record_updates):
	non_repeating_fields = ['name', 'established', 'wikipedia_url']
	repeating_fields = ['links', 'types', 'aliases', 'acronyms']
	external_ids = ['Wikidata', 'ISNI', 'FundRef']
	for ror_id, record_changes in record_updates.items():
		download_record(ror_id)
		json_file_path = generate_file_path(ror_id)
		for record_change in record_changes:
			if record_change['change_field'] in non_repeating_fields:
				change_nonrepeating_field(
					json_file_path, record_change['change_field'], record_change['change_value'])
			if record_change['change_field'] in repeating_fields:
				if record_change['change_type'] == 'add':
					add_repeating_field(
						json_file_path, record_change['change_field'], record_change['change_value'])
				elif record_change['change_type'] == 'delete':
					delete_repeating_field(
						json_file_path, record_change['change_field'], record_change['change_value'])
			if record_change['change_field'] == 'labels':
				if record_change['change_type'] == 'add':
					add_label(json_file_path,
							  record_change['change_value'])
				if record_change['change_type'] == 'delete':
					delete_label(json_file_path,
								 record_change['change_value'])
			if record_change['change_field'] in external_ids:
				if record_change['change_type'] == 'add':
					add_external_id(
						json_file_path, record_change['change_field'], record_change['change_value'])
				if record_change['change_type'] == 'delete':
					delete_external_id(
						json_file_path, record_change['change_field'], record_change['change_value'])


if __name__ == '__main__':
	record_updates = parse_record_updates_file(sys.argv[1])
	update_records(record_updates)
