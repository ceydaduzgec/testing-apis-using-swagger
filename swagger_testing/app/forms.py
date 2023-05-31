from django import forms

class URLProcessingForm(forms.Form):
    swagger_url = forms.URLField(label='Enter a URL', help_text='e.g. https://petstore.swagger.io/v2/swagger.json')
