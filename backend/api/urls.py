from django.urls import path

from .views import agent2_chat, assess_formula, assess_safety, health


urlpatterns = [
    path("health", health, name="health"),
    path("assess-formula", assess_formula, name="assess_formula"),
    path("assess-safety", assess_safety, name="assess_safety"),
    path("agent2-chat", agent2_chat, name="agent2_chat"),
]
