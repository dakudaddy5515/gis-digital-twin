from django.urls import path
from . import views

urlpatterns = [
    # Map page
    path("map/", views.map_view, name="map"),

    # Service CRUD APIs
    path("api/services/", views.get_services, name="api_services"),
    path("api/services/add/", views.add_service, name="api_services_add"),
    path("api/regions/", views.get_regions, name="api_regions"),
    path("api/services/<int:service_id>/", views.update_service, name="api_service_update"),
    path("api/services/<int:service_id>/delete/", views.delete_service, name="api_service_delete"),

    # Main GIS data APIs
    path("api/govt-hospitals/", views.govt_hospitals_api, name="api_govt_hospitals"),
    path("api/private-hospitals/", views.private_hospitals_api, name="api_private_hospitals"),
    path("api/schools/", views.schools_api, name="api_schools"),
    path("api/colleges/", views.colleges_api, name="api_colleges"),
    path("api/roads/", views.roads_api, name="api_roads"),

    # Demand APIs
    path("api/villages-demand/", views.villages_demand_api, name="api_villages_demand"),
    path("api/sectors-demand/", views.sectors_demand_api, name="api_sectors_demand"),

    # Buffer API
    path("api/hospital-buffers/", views.hospital_buffers_api, name="api_hospital_buffers"),

    # Nearest village line APIs
    path("api/village-nearest-hospital/", views.village_nearest_hospital_api, name="api_village_nearest_hospital"),
    path("api/village-nearest-school/", views.village_nearest_school_api, name="api_village_nearest_school"),
    path("api/village-nearest-college/", views.village_nearest_college_api, name="api_village_nearest_college"),

    # Nearest sector line APIs
    path("api/sector-nearest-hospital/", views.sector_nearest_hospital_api, name="api_sector_nearest_hospital"),
    path("api/sector-nearest-school/", views.sector_nearest_school_api, name="api_sector_nearest_school"),
    path("api/sector-nearest-college/", views.sector_nearest_college_api, name="api_sector_nearest_college"),

    # Boundary APIs
    path("api/chandigarh-boundary/", views.chandigarh_boundary_api, name="api_chandigarh_boundary"),
    path("api/sector-boundary/", views.sector_boundary_api, name="api_sector_boundary"),

    # Old API names support
    path("api/facilities/", views.facilities_api, name="api_facilities"),
    path("api/villages/", views.villages_api, name="api_villages"),
    path("api/sectors/", views.sectors_api, name="api_sectors"),
    path("api/sector-boundaries/", views.sector_boundaries_api, name="api_sector_boundaries"),
]