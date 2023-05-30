from django.shortcuts import render
from django.views import View

from app.utils import swagger_test

class URLProcessingView(View):
    template_name = 'input.html'  # Replace with the name of your template file

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        swagger_url = request.POST.get('swagger_url')  # Assuming the URL is submitted via a form field named 'url'
        swagger_url = 'http://petstore.swagger.io/v2/swagger.json'
        results = swagger_test(app_url=swagger_url)
        return render(request, self.template_name, {'results': results})
