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
    for base_url in url_results:
        print(f"-------- Parsing: {base_url} -------")
        parser = SwaggerParser(swagger_dict=url_results[base_url])

        for path in parser.paths:
            api = base_url + path
            for method in parser.paths[path]:
                parameter_values = {}
                data = None
                headers = None
                #print(f"Testing: {api} - {method}")
                parameters = parser.paths[path][method]["parameters"]

                for par in parameters:
                    if parameters[par]["in"] == "path" and parameters[par]["required"]:
                        if parameters[par]["type"] == "string":
                            parameter_values[parameters[par]["name"]] = "test"
                        elif parameters[par]["type"] == "integer":
                            parameter_values[parameters[par]["name"]] = "9222968140491042141"
                        elif parameters[par]["type"] == "boolean":
                            parameter_values[parameters[par]["name"]] = "True"

                        for api_parameter in parameter_values:
                            if api.find("{") != -1:
                                api = api.split("{")[0] + parameter_values[api_parameter] + api.split("}")[1]

                    elif parameters[par]["in"] == "body" and parameters[par]["required"]:
                        model = parameters[par]["schema"]["$ref"].split("/")[2]
                        data = json.dumps(parser.definitions_example[model])
                        headers = {"Content-Type": parser.paths[path][method]["consumes"][0]}

                response = requests.request(method=method, url=api, data=data, headers=headers)

                if response.status_code == 200:
                    print(f"PASSED: {api} - {method}")
                else:
                    print(f"FAILED: {api} - {method}")










test_urls()
