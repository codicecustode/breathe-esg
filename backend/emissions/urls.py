from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AuditEventViewSet,
    DataSourceViewSet,
    ImportJobViewSet,
    NormalizedEmissionRecordViewSet,
    RawRecordViewSet,
    TenantViewSet,
)

router = DefaultRouter()
router.register('tenants', TenantViewSet)
router.register('data-sources', DataSourceViewSet)
router.register('import-jobs', ImportJobViewSet)
router.register('raw-records', RawRecordViewSet)
router.register('emissions', NormalizedEmissionRecordViewSet)
router.register('audit-events', AuditEventViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
