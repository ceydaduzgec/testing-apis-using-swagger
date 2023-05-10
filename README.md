# testing-apis-using-swagger
Testing APIs using Swagger




## How to run the script

Add the url of the json files that you want to test into the ```test_sites.txt```
and just run: ```source init.sh```

Or you can do all the steps manuelly by:

1- Install virual anv
```pip install virtualenv```

2- Create virtual env
```python3 -m venv venv```

3- Active virtual env
```source venv/bin/activate```

4- Install requirements
```pip install -r requirements.txt```

5- Add the url of the json files that you want to test into the ```test_sites.txt```

6- Run the script. ```python3 test_urls.py```


https://mainnet.staging.api.perawallet.app/v1/documentation/?format=openapi
