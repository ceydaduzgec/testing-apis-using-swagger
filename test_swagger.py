#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from swagger_tester import swagger_test

import connexion
from multiprocessing import Process


class ConnexionProcess(Process):
    def run(self):
        self.conn = connexion.App(
            'tests',
            debug=True,
            specification_dir=os.path.dirname(__file__)
        )
        self.conn.add_api('swagger.yaml')
        self.conn.app.run(port=8080)

    def start(self):
        Process.start(self)

        import time
        time.sleep(3)

    def terminate(self):
        Process.terminate(self)
        Process.join(self)


swagger_yaml_path = os.path.join(os.path.dirname(__file__), 'swagger.yaml')
authorize_error = {
    'post': {
        '/v2/pet/{petId}': [200],
        '/v2/pet': [200]
    },
    'put': {
        '/v2/user/{username}': [200],
        '/v2/pet': [200]
    },
    'delete': {
        '/v2/pet/{petId}': [200],
        '/v2/store/order/{orderId}': [200],
        '/v2/user/{username}': [200]
    }
}
swagger_io_url = 'http://petstore.swagger.io/v2'


swagger_test(app_url=swagger_io_url, authorize_error=authorize_error, use_example=True) # dry_run=True)

