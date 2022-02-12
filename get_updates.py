import os
import csv
import json
import requests
import re


GITHUB = {}
GITHUB['USER'] = ''
GITHUB['TOKEN'] = ''


def find_between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        match = s[start:end]
        match = match.strip()
        return match
    except ValueError:
        return ''


def normalize_text(text):
    text = re.sub(' +', ' ', text)

    return text


def create_modify_records_metadata():
    pages = [1, 2, 3]
    issue_urls = []
    outfile = os.getcwd() + '/modify_records_metadata.csv'
    api_fields = ['issue_id', 'api_url', 'html_url']
    ror_fields = ['name', 'ror_id', 'update_field']
    issue_field_mappings = {
        'name': 'Name of organization:',
        'ror_id': 'ROR ID:',
        'update_field': 'Update:'}
    with open(outfile, 'w') as f_out:
        writer = csv.writer(f_out)
        header = api_fields + ror_fields
        writer.writerow(header)
    # approved column url
    url = 'https://api.github.com/projects/columns/13954326/cards'
    for page in pages:
        params = {'page': page, 'per_page': 100}
        cards = requests.get(url, auth=(
            GITHUB['USER'], GITHUB['TOKEN']), params=params).json()
        for card in cards:
            if 'content_url' in card:
                issue_urls.append(card['content_url'])
    for issue_url in issue_urls:
        issue_data = requests.get(issue_url, auth=(
            GITHUB['USER'], GITHUB['TOKEN'])).json()
        label_data = issue_data['labels']
        labels = []
        for label in label_data:
            labels.append(label['name'])
        record_type = 'update record'
        if record_type in labels:
            api_data = [issue_data[f] for f in api_fields]
            record_data = {}
            issue_text = issue_data['body']
            issue_text = normalize_text(issue_text)
            for key, value in issue_field_mappings.items():
                search_result = find_between(issue_text, value, '\n')
                record_data[key] = search_result
            with open(outfile, 'a') as f_out:
                record_entry = api_data + [record_data[k] for k in ror_fields]
                writer = csv.writer(f_out)
                writer.writerow(record_entry)


if __name__ == '__main__':
    create_modify_records_metadata()
