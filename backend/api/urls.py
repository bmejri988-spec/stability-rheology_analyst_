from django.urls import path

from .views import assess_formula, health


urlpatterns = [
    path("health", health, name="health"),
    path("assess-formula", assess_formula, name="assess_formula"),
]
