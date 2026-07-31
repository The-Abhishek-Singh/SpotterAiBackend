from django.urls import path
from .views import plan_trip_view

urlpatterns = [
    path('plan-trip/', plan_trip_view, name='plan_trip'),
]