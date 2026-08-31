from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import EnquiryViewSet, ServiceRequestViewSet

router = DefaultRouter()
router.register("enquiries", EnquiryViewSet)
router.register("service-requests", ServiceRequestViewSet)

urlpatterns = [path("", include(router.urls))]
