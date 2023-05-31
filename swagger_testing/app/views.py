from django.contrib import messages
from django.shortcuts import render
from django.views import View
from app.forms import URLProcessingForm
from app.utils import swagger_test

class URLProcessingView(View):
    template_name = 'main.html'

    def get(self, request):
        form = URLProcessingForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = URLProcessingForm(request.POST)
        if form.is_valid():
            swagger_url = form.cleaned_data['swagger_url']
            results = swagger_test(app_url=swagger_url, request=request)
            return render(request, self.template_name, {'form': form, 'results': results})
        else:
            messages.error(request, f"Please enter a valid URL.")
            return render(request, self.template_name, {'form': form})
