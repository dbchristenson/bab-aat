from django.http import HttpResponse
from django.shortcuts import render


# Create your views here.
def index(request):
    """
    Render the index page.
    """
    return HttpResponse("Welcome to the OCR API!")
