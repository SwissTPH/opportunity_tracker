from django.urls import path
from .views import get_rational, reports, get_opportunities, get_financial

app_name = "reports"
urlpatterns = [
    path("", reports, name="home"),
    path("opportunities/", get_opportunities, name="opportunities_report"),
    path("financial/", get_financial, name="financial_report"),
    path("rational/", get_rational, name="rational_report"),
]
