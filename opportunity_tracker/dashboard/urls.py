from django.urls import path
from dashboard.views import DashboardDataView, get_total_opportunity_count, get_total_submitted_amount, get_total_won_amount, get_won_to_lost_rfp

app_name = 'dashboard'

urlpatterns = [
    path("chart/data/",
         DashboardDataView.as_view(), name="dashboard_data"),
    path("total_opportunity_count/",
         get_total_opportunity_count, name="total_opportunity_count"),
    path("total_submitted_amount/",
         get_total_submitted_amount, name="total_submitted_amount"),
    path("total_won_amount/",
         get_total_won_amount, name="total_won_amount"),
    path("won_to_lost_rfp/", get_won_to_lost_rfp, name="won_to_lost_rfp")
]
