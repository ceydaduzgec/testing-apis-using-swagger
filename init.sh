#!/bin/bash
pip install virtualenv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 test_urls.py