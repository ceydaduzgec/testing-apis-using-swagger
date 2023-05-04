import json
import requests
from swagger_parser import SwaggerParser


def get_urls_from_txt():
    with open("test_sites.txt", "r") as file:
        urls = [line.strip() for line in file.readlines()]
    return urls


def get_swagger_data_for_each_url():
    url_results = {}
    urls = get_urls_from_txt()
    for url in urls:
        response = requests.get(url)
        if response.status_code == 200:
            url_results[url] = response.json()
    return url_results


def parse_json_content(data):
    return data


def test_urls():
    url_results = get_swagger_data_for_each_url()
    for url_name in url_results:
        print(f"Testing: {url_name}")
        parser = SwaggerParser(swagger_dict=url_results[url_name])
        spec = parser.specification
        print(spec['info']['version'])


test_urls()
