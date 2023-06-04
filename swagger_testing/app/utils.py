import json
import requests
import logging
import six
import time
from django.contrib import messages

try:
    from urllib import urlencode
except ImportError:  # Python 3
    from urllib.parse import urlencode

from swagger_parser import SwaggerParser

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# The swagger path item object (as well as HTTP) allows for the following
# HTTP methods (http://swagger.io/specification/#pathItemObject):
_HTTP_METHODS = ['post', 'put', 'get', 'options', 'head', 'patch', 'delete']


def get_request_args(path, action, swagger_parser):
    """
    Get request args from an action and a path.

    Args:
        path: path of the action.
        action: action of the request(get, delete, post, put).
        swagger_parser: instance of SwaggerParser.

    Returns:
        A dict of args to transmit to bravado.
    """
    request_args = {}
    if path in swagger_parser.paths.keys() and action in swagger_parser.paths[path].keys():
        operation_spec = swagger_parser.paths[path][action]

        if 'parameters' in operation_spec.keys():
            for param_name, param_spec in operation_spec['parameters'].items():
                request_args[param_name] = swagger_parser.get_example_from_prop_spec(param_spec)

    return request_args


def get_url_body_from_request(action, path, request_args, swagger_parser):
    """Get the url and the body from an action, path, and request args.

    Args:
        action: HTTP action.
        path: path of the request.
        request_args: dict of args to send to the request.
        swagger_parser: instance of swagger parser.

    Returns:
        url, body, headers, files
    """

    url = path
    body = None
    query_params = {}
    files = {}
    headers = [('Content-Type', 'application/json')]

    if path in swagger_parser.paths.keys() and action in swagger_parser.paths[path].keys():
        operation_spec = swagger_parser.paths[path][action]

        # Get body and path
        for parameter_name, parameter_spec in operation_spec['parameters'].items():
            if parameter_spec['in'] == 'body':
                body = request_args[parameter_name]

            elif parameter_spec['in'] == 'path':
                url = url.replace(f"{{{parameter_name}}}", str(request_args[parameter_name]))

            elif parameter_spec['in'] == 'query':
                if isinstance(request_args[parameter_name], list):
                    query_params[parameter_name] = ','.join(request_args[parameter_name])
                else:
                    query_params[parameter_name] = str(request_args[parameter_name])

            elif parameter_spec['in'] == 'formData':
                if body is None:
                    body = {}

                if (isinstance(request_args[parameter_name], tuple) and
                        hasattr(request_args[parameter_name][0], 'read')):
                    files[parameter_name] = (request_args[parameter_name][1],
                                             request_args[parameter_name][0])
                else:
                    body[parameter_name] = request_args[parameter_name]

                # The first header is always content type, so just replace it so we don't squash custom headers
                headers[0] = ('Content-Type', 'multipart/form-data')

            elif parameter_spec['in'] == 'header':
                header_value = request_args.get(parameter_name)
                header_value = header_value or parameter_spec.get('default', '')
                headers += [(parameter_spec['name'], str(header_value))]

    if query_params:
        url = f"{url}?{urlencode(query_params)}"

    if ('Content-Type', 'multipart/form-data') not in headers:
        try:
            if body:
                body = json.dumps(body)
        except TypeError as exc:
            logger.warning(f"Cannot decode body: {repr(exc)}")
    else:
        headers.remove(('Content-Type', 'multipart/form-data'))

    return url, body, headers, files


def validate_definition(swagger_parser, valid_response, response):
    """
    Validate the definition of the response given the given specification and body.

    Args:
        swagger_parser: instance of swagger parser.
        body: valid body answer from spec.
        response: response of the request.
    """

    # if isinstance(response, dict) and response.get("code") in [200, 201]:
    #     return

    # additionalProperties do not match any definition because the keys
    # vary. we can only check the type of the values
    if 'any_prop1' in valid_response and 'any_prop2' in valid_response:
        # GET /v2/store/inventory
        assert swagger_parser.validate_additional_properties(valid_response, response)
        return

    # No answer
    if response is None or response == '':
        assert valid_response == '' or valid_response is None
        return

    if valid_response == '' or valid_response is None:
        assert response is None or response == ''
        return

    # Validate output definition
    if isinstance(valid_response, list):  # Return type is a list
        assert isinstance(response, list)
        if response:
            valid_response = valid_response[0]
            response = response[0]
        else:
            return

    # Not a dict and not a text
    if ((not isinstance(response, dict) or not isinstance(valid_response, dict)) and
        (not isinstance(response, (six.text_type, six.string_types)) or
            not isinstance(valid_response, (six.text_type, six.string_types)))):
        assert type(response) == type(valid_response)
    elif isinstance(response, dict) and isinstance(valid_response, dict):
        # Check if there is a definition that match body and response
        valid_definition = swagger_parser.get_dict_definition(valid_response, get_list=True)
        actual_definition = swagger_parser.get_dict_definition(response, get_list=True)
        assert len(set(valid_definition).intersection(actual_definition)) >= 1


def swagger_test_yield(app_url=None, wait_time_between_tests=0, extra_headers={},request=None):
    """Test the given swagger api Yield the action and operation done for each test.

    Args:
        app_url: URL of the swagger api.
        wait_time_between_tests: an number that will be used as waiting time between tests [in seconds].
        extra_headers: additional headers you may want to send for all operations

    Returns:
        Yield between each test: (action, operation)

    Raises:
        ValueError: In case you specify neither a swagger.yaml path or an app URL.
    """
    # Get swagger json response and parse it
    try:
        response = requests.get(app_url)
        remote_swagger_def = response.json()
    except:
        messages.error(request, f"You must specify a valid swagger.json path.: {app_url}")
        return

    try:
        swagger_parser = SwaggerParser(swagger_dict=remote_swagger_def, use_example=True)
    except ValueError as exc:
        error = str(exc).split(":")[0]
        messages.error(request, f"Invalid swagger: {error}")
        return

    try:
        app_url = swagger_parser.specification["schemes"][0] + "://" + swagger_parser.specification["host"] + swagger_parser.specification["basePath"]
    except KeyError:
        messages.error(request, f"JSON doesn't contain schemes, host or basePath")
        return

    print(f"Starting runing tests for {app_url} using examples.")
    logger.info(f"Starting runing tests for {app_url} using examples.")

    # Sort operation by action in order of _HTTP_METHODS
    operation_sorted = {}
    operations = swagger_parser.operation.copy()
    operations.update(swagger_parser.generated_operation)
    for operation, request in operations.items():
        path = request[0]
        operation_sorted[path] = operation_sorted.get(path, []) + [(operation, request)]

    # Sort operations for each endpoint based on _HTTP_METHODS
    for path, operations in operation_sorted.items():
        sorted_operations = sorted(operations, key=lambda x: _HTTP_METHODS.index(x[1][1]))
        for operation in sorted_operations:
            action = operation[1][1]
            request_args = get_request_args(path, action, swagger_parser)
            url, body, headers, files = get_url_body_from_request(action, path, request_args, swagger_parser)
            headers.extend([(key, value) for key, value in extra_headers.items()])

            if app_url.endswith(swagger_parser.base_path):
                base_url = app_url[:-len(swagger_parser.base_path)]
            else:
                base_url = app_url
            full_path = f"{base_url}{url}"

            if action not in _HTTP_METHODS:
                yield (f"Action '{action}' is not recognized; needs to be one of {str(_HTTP_METHODS)}")
                continue

            response = requests.__getattribute__(action)(full_path, headers=dict(headers), data=body, files=files)
            body_req = swagger_parser.get_send_request_correct_body(path, action)

            try:
                response_spec = swagger_parser.get_request_data(path, action, body_req)
            except (TypeError, ValueError) as exc:
                logger.warning(f"Error in the swagger file: {repr(exc)}")
                continue

            for expected_status_code, status_code_spec in response_spec.items():
                if str(expected_status_code) == str(response.status_code) or expected_status_code == 'default':
                    yield (f"Returned: {response.status_code} Expected: {expected_status_code} PASSED {action.upper()} {url}")
                    if wait_time_between_tests > 0:
                        time.sleep(wait_time_between_tests)
                else:
                    yield (f"Returned: {response.status_code} Expected: {expected_status_code} FAILED {action.upper()} {url}")


def swagger_test(app_url=None, wait_time_between_tests=0, extra_headers={}, request=None):
    """
    Args:
        app_url: URL of the swagger api.
        wait_time_between_tests: an number that will be used as waiting time between tests [in seconds].
        extra_headers: additional headers you may want to send for all operations

    Raises:
        ValueError: In case you specify neither a swagger.yaml path or an app URL.
    """
    tested_status_codes = {}  # Dictionary to track tested status codes for each endpoint

    for status in swagger_test_yield(app_url=app_url, wait_time_between_tests=wait_time_between_tests, extra_headers=extra_headers, request=request):
        # status_code, result = status.split(' ', 1)  # Split the status code and result message

        # endpoint = result.split(' ')[-1]  # Extract the endpoint from the result message

        # if endpoint not in tested_status_codes:
        #     tested_status_codes[endpoint] = set()  # Create a set to track status codes for the endpoint

        # if status_code in tested_status_codes[endpoint]:
        #     continue  # Skip testing for already tested status codes

        # tested_status_codes[endpoint].add(status_code)  # Add the tested status code to the set

        if 'PASSED' in status:
            messages.success(request, f"{status}")
        else:
            messages.error(request, f"{status}")
