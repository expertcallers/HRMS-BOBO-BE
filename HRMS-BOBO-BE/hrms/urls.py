"""hrms URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from hrms import settings

urlpatterns = [
    path('mapping/', include('mapping.urls')),
    path('interview/', include('interview.urls')),
    path('ams/', include('ams.urls')),
    path("payroll/", include('payroll.urls')),
    path("int_test/", include('interview_test.urls')),
    path("faq/", include("faq.urls")),
    path('onboard/', include('onboarding.urls')),
    path('tax/', include('tax.urls')),
    # path("emma/", include("ask_emma.urls"))
]
if not settings.IS_PUBLIC_SERVER:
    urlpatterns += [
        path('ecpl1/', admin.site.urls),
        path('onboard/', include('onboarding.urls')),
        path("report/", include("report.urls")),
        path("erf/", include('erf.urls')),
        path("team/", include('team.urls')),
        path("ijp/", include('ijp.urls')),
        path("training_room/", include('training_room.urls')),
        path("exit/", include('exit.urls')),
        path("tkt/", include('ticketing.urls')),
        path("asset/", include('asset.urls')),
        path("po/", include('po.urls')),
        path("hc/", include('headcount.urls')),
        path("pbi/", include('powerbi.urls')),
        path("it/", include("it.urls")),
        path("appraisal/", include("appraisal.urls")),
        path("article/", include("article.urls")),
        path("transport/", include('transport.urls'))
        # path("emma/", include("ask_emma.urls"))
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
