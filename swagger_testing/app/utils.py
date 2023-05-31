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

    if app_url is not None:
        app_client = requests
        try:
            response = app_client.get(app_url)
        except:
            messages.error(request, f"Invalid URL: {app_url}")
            return
        remote_swagger_def = response.json()
        try:
            swagger_parser = SwaggerParser(swagger_dict=remote_swagger_def, use_example=True)
        except ValueError as exc:
            error = str(exc).split(":")[0]
            messages.error(request, f"Invalid swagger: {error}")
            return

    else:
        raise ValueError('You must either specify a swagger.yaml path or an app url')

    try:
        app_url = swagger_parser.specification["schemes"][0] + "://" + swagger_parser.specification["host"] + swagger_parser.specification["basePath"]
    except KeyError:
        messages.error(request, f"JSON doesn't contain schemes, host or basePath")
        return
    print(f"Starting runing tests for {app_url} using examples.")
    logger.info(f"Starting runing tests for {app_url} using examples.")
    operation_sorted = {method: [] for method in _HTTP_METHODS}

    # Sort operation by action in order of _HTTP_METHODS
    operations = swagger_parser.operation.copy()
    operations.update(swagger_parser.generated_operation)
    for operation, request in operations.items():
        operation_sorted[request[1]].append((operation, request))

    # For every action make request
    for action in _HTTP_METHODS:
        for operation in operation_sorted[action]:
            # path is relative to the base path
            path = operation[1][0]
            request_args = get_request_args(path, action, swagger_parser)
            url, body, headers, files = get_url_body_from_request(action, path, request_args, swagger_parser)
            # Add any extra headers specified by the user
            headers.extend([(key, value)for key, value in extra_headers.items()])

            if app_url.endswith(swagger_parser.base_path):
                base_url = app_url[:-len(swagger_parser.base_path)]
            else:
                base_url = app_url
            full_path = f"{base_url}{url}"

            try:
                assert action in _HTTP_METHODS, f"Action '{action}' is not recognized; needs to be one of {str(_HTTP_METHODS)}"
            except:
                yield ("FAILED", operation)
                continue
            response = requests.__getattribute__(action)(full_path, headers=dict(headers), data=body, files=files)

            if response.status_code == 404:
                yield (f"{response.status_code} FAILED", operation)
                continue

            # Get valid request and response body
            body_req = swagger_parser.get_send_request_correct_body(path, action)

            try:
                response_spec = swagger_parser.get_request_data(path, action, body_req)
            except (TypeError, ValueError) as exc:
                logger.warning(f"Error in the swagger file: {repr(exc)}")
                continue

            # Get response data
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = response.data

            # Convert to str
            if hasattr(response_text, 'decode'):
                response_text = response_text.decode('utf-8')

            # Get json
            try:
                response_json = json.loads(response_text)
            except ValueError:
                response_json = response_text

            try:
                if response.status_code in [200, 201]:
                    print(f"PASSED status code {response.status_code} {action.upper()} {url}")
                elif response.status_code in response_spec.keys():
                    validate_definition(swagger_parser, response_spec[response.status_code], response_json)
                    print(f"PASSED status code {response.status_code} {action.upper()} {url}")
                elif 'default' in response_spec.keys():
                    validate_definition(swagger_parser, response_spec['default'], response_json)
                    print(f"PASSED status code {response.status_code} {action.upper()} {url}")
                else:
                    print(f"FAILED status code {response.status_code} {action.upper()} {url} Expected: {list(response_spec.keys())}")
            except AssertionError as exc:
                yield (f"{response.status_code} FAILED", operation)
                continue

            if wait_time_between_tests > 0:
                time.sleep(wait_time_between_tests)

            yield (f"{response.status_code} PASSED", operation)



def swagger_test(app_url=None, wait_time_between_tests=0, extra_headers={}, request=None):
    """
    Args:
        app_url: URL of the swagger api.
        wait_time_between_tests: an number that will be used as waiting time between tests [in seconds].
        extra_headers: additional headers you may want to send for all operations

    Raises:
        ValueError: In case you specify neither a swagger.yaml path or an app URL.
    """
    for status, operation in swagger_test_yield(app_url=app_url,
                                              wait_time_between_tests=wait_time_between_tests,
                                              extra_headers=extra_headers,
                                              request=request):
        if 'PASSED' in status:
            messages.success(request, f"{status} {operation[1][1]} {operation[1][0]}")
        else:
            messages.error(request, f"{status} {operation[1][1]} {operation[1][0]}")