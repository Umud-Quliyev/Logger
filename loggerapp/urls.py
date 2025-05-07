from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AttendanceViewSet, PersonViewSet

router = DefaultRouter()
router.register(r'attendance', AttendanceViewSet, basename='attendance')
router.register(r'person', PersonViewSet, basename='person')

urlpatterns = [
    path('api/', include(router.urls)),
]
