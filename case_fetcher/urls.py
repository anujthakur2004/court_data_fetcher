from django.urls import path
from . import views

urlpatterns = [
    path('', views.fetch_case_view, name='fetch_case'),
]
