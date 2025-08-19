from django.urls import path
from .views import (
    HomeView,
    HistoryView,
    ClassificationDetailView,
    WasteAnalysisAPIView,
    WasteAnalysisView,
    ResultsView
)

urlpatterns = [
    # Web interface URLs (main site)
    path('', HomeView.as_view(), name='home'),
    path('analyze/', WasteAnalysisView.as_view(), name='analyze'),
    path('history/', HistoryView.as_view(), name='history'),
    path('results/<int:pk>/', ResultsView.as_view(), name='results'),
    path('detail/<int:pk>/', ClassificationDetailView.as_view(), name='detail'),
]

# API URLs (separate patterns)
api_urlpatterns = [
    path('analyze/', WasteAnalysisAPIView.as_view(), name='api_analyze'),
]
