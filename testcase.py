import unittest
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


class TestURLs(unittest.TestCase):
    def test_urls(self):
        url_results = get_swagger_data_for_each_url()
        for base_url in url_results:
            passed = 0
            failed = 0
            print(f"-------- Parsing: {base_url} -------")
            parser = SwaggerParser(swagger_dict=url_results[base_url])
            def_examples = parser.definitions_example

            for path in parser.specification["paths"]:
                api = base_url + parser.base_path + path
                for method in parser.specification["paths"][path]:
                    parameter_values = {}
                    data = None
                    headers = None
                    # print(f"Testing: {api} - {method}")
                    parameters = parser.specification["paths"][path][method]["parameters"]
                    tag = parser.specification["paths"][path][method]["tags"][0]

                    for parameter in parameters:
                        if parameter["in"] == "path" and parameter["required"]:
                            if parameter["type"] == "string":
                                parameter_values[parameter["name"]] = "string"
                            elif parameter["type"] == "integer":
                                parser.specification["paths"][path][method]
                                parameter_values[parameter["name"]] = "42"
                            elif parameter["type"] == "boolean":
                                parameter_values[parameter["name"]] = "True"

                            for api_parameter in parameter_values:
                                if api.find("{") != -1:
                                    api = api.split(
                                        "{")[0] + parameter_values[api_parameter] + api.split("}")[1]

                        elif parameter["in"] == "body" and parameter["required"]:
                            if parameter["schema"].get("$ref"):
                                model = parameter["schema"]["$ref"].split(
                                    "/")[2]
                                data = def_examples[model]
                            elif parameter["schema"].get("items"):
                                model = parameter["schema"]["items"]["$ref"].split(
                                    "/")[2]
                                if parameter["schema"].get("type") == "array":
                                    data = [def_examples[model]]

                            data = json.dumps(data)

                            # The second consumes is ignored, can be implemented later
                            headers = {
                                "Content-Type": parser.paths[path][method]["consumes"][0]}

                    response = requests.request(
                        method=method, url=api, data=data, headers=headers)

                    if response.status_code == 200:
                        # print(f"PASSED: {api} - {method}")
                        passed += 1
                    else:
                        print(f"FAILED: {api} - {method}")
                        failed += 1

            print(f"Passed: {passed} - Failed: {failed}")


if __name__ == "__main__":
    unittest.main()
