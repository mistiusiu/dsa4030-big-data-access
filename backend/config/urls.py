from django.conf import settings
from django.contrib import admin
from django.db import connection
from django.urls import path
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenVerifyView

from apps.accounts import views as auth
from apps.audit import views as audit
from apps.grid import views as grid
from apps.lake import views as lake
from apps.lake.catalog import DATASETS


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        connection.ensure_connection()
        missing = [d.slug for d in DATASETS if not (settings.LAKE_DIR / d.filename).exists()]
        return Response({"status": "ok" if not missing else "degraded", "database": "ok",
                         "lake_missing": missing})


class VerifyView(TokenVerifyView):
    authentication_classes = []


admin.site.site_header = "Mji Mpya · Super-admin console"
admin.site.site_title = "Mji Mpya super-admin"
admin.site.index_title = "Permission grid, identities and audit trail"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", HealthView.as_view()),
    path("api/auth/token/", auth.LoginView.as_view()),
    path("api/auth/token/refresh/", auth.RefreshView.as_view()),
    path("api/auth/token/verify/", VerifyView.as_view()),
    path("api/auth/logout/", auth.LogoutView.as_view()),
    path("api/auth/me/", auth.MeView.as_view()),
    path("api/auth/jwks/", auth.JWKSView.as_view()),
    path("api/auth/demo-accounts/", auth.DemoAccountsView.as_view()),
    path("api/grid/", grid.GridView.as_view()),
    path("api/grid/policies/<slug:role>/", grid.RolePolicyView.as_view()),
    path("api/lake/datasets/", lake.DatasetListView.as_view()),
    path("api/lake/datasets/<slug:slug>/", lake.DatasetDetailView.as_view()),
    path("api/lake/datasets/<slug:slug>/query/", lake.QueryView.as_view()),
    path("api/lake/datasets/<slug:slug>/aggregate/", lake.AggregateView.as_view()),
    path("api/lake/sql/tables/", lake.SQLTablesView.as_view()),
    path("api/lake/sql/", lake.SQLView.as_view()),
    path("api/audit/logs/", audit.LogListView.as_view()),
    path("api/audit/stats/", audit.StatsView.as_view()),
    path("api/audit/detections/", audit.DetectionsView.as_view()),
    path("api/audit/export/", audit.ExportView.as_view()),
]
