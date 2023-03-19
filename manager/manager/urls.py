from django.urls import path

from manager import views

urlpatterns = [
    path('report/', views.report_stream_session, name='report'),
    path('get/icon/<str:name>', views.get_icon, name='get_icon'), # download icon (str is base64 encoded url of the icon)
    path('get/epg/<str:name>', views.get_epg, name='get_epg'), # download epg
    path('get/playlist/<str:name>', views.get_downstream_playlist, name='get_playlist'), # download playlist
]
