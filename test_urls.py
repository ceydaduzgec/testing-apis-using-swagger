from cgi import test
import json
import requests
from swagger_parser import SwaggerParser


def get_json_urls_from_txt():
    with open("test_sites.txt", "r") as file:
        json_urls = [line.strip() for line in file.readlines()]
    return json_urls


def get_swagger_data_for_each_url():
    url_results = {}
    json_urls = get_json_urls_from_txt()
    for json_url in json_urls:
        response = requests.get(json_url)
        if response.status_code == 200:
            res_json = response.json()
            base_url = res_json["schemes"][0] + "://" + res_json["host"]
            # The second scheme is ignored, can be implemented later
            url_results[base_url] = res_json
        else:
            assert False, f"Failed to get swagger data for {json_url}"
    return url_results


def test_urls():
    url_results = get_swagger_data_for_each_url()
    for url_name in url_results:
        print(f"Parsing: {url_name}")
        parser = SwaggerParser(swagger_dict=url_results[url_name])

        for path in parser.paths:
            api = url_name + path
            print(f"Testing: {api}")
            for method in parser.paths[path]:
                print(f"Testing: {api} - {method}")
                parameters = parser.paths[path][method]["parameters"]
                parameter_values = {}
                for par in parameters:
                    if parameters[par]["required"] and parameters[par]["in"] == "path":
                        if parameters[par]["type"] == "string":
                            parameter_values[parameters[par]["name"]] = "test"
                        elif parameters[par]["type"] == "integer":
                            parameter_values[parameters[par]["name"]] = 123
                        elif parameters[par]["type"] == "boolean":
                            parameter_values[parameters[par]["name"]] = True

                response = requests.request(method=method, url=api)

                if response.status_code == 200:
                    print(f"PASSED - {api} - {method}")
                else:
                    print(f"FAILED - {api} - {method}")










test_urls()
