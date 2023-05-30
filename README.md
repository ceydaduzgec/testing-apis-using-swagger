# Testing APIs using Swagger

## How to run the script

You can just run: ```source init.sh```

Or you can do all the steps manuelly by:

1- Install virual anv
```pip install virtualenv```

2- Create virtual env
```python3 -m venv venv```

3- Active virtual env
```source venv/bin/activate```

4- Install requirements
```pip install -r requirements.txt```

5- Run the script. ```python3 test_urls.py```

In order to change the url of the swagger file, you can change the variable ```swagger_url``` in the file ```test_swagger.py```
