"""iptvmanager URL Configuration

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
from manager import views
from django.urls import path, include
from django.contrib import admin

urlpatterns = [
    path('manager/', include('manager.urls')),
    # TODO: Check if pattern is ok
    path('admin/manager/iptvicon/purge', views.purge_icons, name='purge_icons'),  # delete all icons
    path('admin/manager/iptvchannel/purge', views.purge_channels, name='purge_channels'),  # delete all channels
    path('admin/manager/iptvgroup/purge', views.purge_groups, name='purge_groups'),  # delete all groups
    path('admin/manager/iptvgroup/get', views.get_groups, name='get_groups'), # get a convenient list of groups for filter fields
    path('admin/', admin.site.urls),
]
