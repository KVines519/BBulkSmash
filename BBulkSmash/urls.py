from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('xml/<str:xmlname>', views.serve_xml_file, name='xml-file'),
    path('download/<str:filename>', views.serve_pcap_csv, name='serve-pcap-csv'),
    path('download-log/<str:filename>', views.serve_log_file, name='serve-log'),
    path('edit-xml/', views.xml_editor, name='edit-xml'),
    path('sipp/<str:xml>/<int:pid>', views.sipp_screen, name='display_sipp_screen'),
    path('file-management/', views.file_mgmt_view, name='file-management'),
    path('create-scenario-xml/', views.create_scenario_xml_view, name='create_scenario_xml'),
]