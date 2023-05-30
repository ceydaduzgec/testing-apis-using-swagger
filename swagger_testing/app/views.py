from django.shortcuts import render
from django.views import View

from app.utils import swagger_test

class URLProcessingView(View):
    template_name = 'input.html'  # Replace with the name of your template file

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        url = request.POST.get('url')  # Assuming the URL is submitted via a form field named 'url'
        results = swagger_test(app_url=url)
        return render(request, self.template_name, {'results': results})

