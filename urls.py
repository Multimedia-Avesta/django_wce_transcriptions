from django.conf.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^$', views.home, name='home'),
    re_path(r'manage/?', views.manage, name='manage'),
    re_path(r'validate/?', views.validate, name="validate"),
    re_path(r'delete/?', views.delete, name="delete"),
    re_path(r'collationunits/?', views.collation_units, name="collationunits"),
    re_path(r'schema/?', views.schema_download, name="schemadownload"),
    re_path(r'index/?', views.index, name="index")  # this is for indexing transcriptions

]
