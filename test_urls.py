import requests
from test_swagger import swagger_test


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
            base_url = res_json["schemes"][0] + "://" + res_json["host"] + res_json["basePath"]
            # The first scheme is ignored, can be implemented later
            url_results[base_url] = res_json
        else:
            assert False, f"Failed to get swagger data for {json_url}"
    return url_results


def use_swagger_tester():
    url_results = get_swagger_data_for_each_url()
    for base_url in url_results:
        swagger_io_url = 'http://petstore.swagger.io/v2'
        swagger_test(app_url=swagger_io_url, use_example=True)
        #swagger_test(app_url=base_url, use_example=True)


if __name__ == "__main__":
    use_swagger_tester()
