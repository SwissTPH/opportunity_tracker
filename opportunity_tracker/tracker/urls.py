from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import DownloadFolderView, FileDeleteView, OpportunityListView, OpportunityViewSet, OpportunityUpdateView, OpportunityCreateView, OpportunitySubmitView, OpportunityStatusUpdateView, OpportunityDetailView, OpportunityDetailAnonymousView, IndexView, NewFundingAgencyView, NewClientView, TransferOpportunityView, OpportunityBudgetView

router = DefaultRouter()
router.register(r"Opportunity", OpportunityViewSet)

urlpatterns = [
    path("api/", include(router.urls)),
    path("", IndexView.as_view(), name="home"),
    path("opportunities/", OpportunityListView.as_view(), name="opportunities"),
    path("opportunity/new/", OpportunityCreateView.as_view(), name="new_opportunity"),
    path("opportunity/<uuid:pk>/",
         OpportunityDetailView.as_view(), name="opportunity"),
    path("opportunity/<uuid:pk>/anon/",
         OpportunityDetailAnonymousView.as_view(), name="opportunity_anonymous"),
    path("opportunity/<uuid:pk>/update",
         OpportunityUpdateView.as_view(), name="update_opportunity"),
    path("opportunity/<uuid:pk>/submit",
         OpportunitySubmitView.as_view(), name="submit_proposal"),
    path("opportunity/<uuid:pk>/status",
         OpportunityStatusUpdateView.as_view(), name="udpate_status"),
    path("delete_attachment/<int:pk>/",
         FileDeleteView.as_view(), name="delete_attachment"),
    path("opportunity/download/<uuid:pk>/",
         DownloadFolderView.as_view(), name="download_folder"),
    path("opportunity/new_funding_agency/",
         NewFundingAgencyView.as_view(), name="new_funding_agency"),    path("opportunity/new_client/",
                                                                             NewClientView.as_view(), name="new_client"),
    path("opportunity/<uuid:pk>/transfer",
         TransferOpportunityView.as_view(), name="transfer_opportunity"),

    path("opportunity/budget", OpportunityBudgetView.as_view(),
         name="opportunity_budget")
]
