from django.urls import path
from . import views

urlpatterns = [
    # Basic pages
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.main_dashboard, name="main_dashboard"),
    path("map/", views.map_view, name="map"),
    

    # Service CRUD APIs
    path("api/services/", views.get_services, name="get_services"),
    path("api/services/add/", views.add_service, name="add_service"),
    path("api/services/<int:service_id>/", views.service_detail_api, name="service_detail_api"),

    # Region API
    path("api/regions/", views.get_regions, name="get_regions"),

    # Phase 2 Routing API
    path("api/routes/", views.route_api, name="route_api"),

    # GIS Dashboard Layer APIs
    path("api/govt-hospitals/", views.govt_hospitals_api, name="govt_hospitals_api"),
    path("api/private-hospitals/", views.private_hospitals_api, name="private_hospitals_api"),
    path("api/schools/", views.schools_api, name="schools_api"),
    path("api/colleges/", views.colleges_api, name="colleges_api"),
    path("api/police-stations/", views.police_stations_api, name="police_stations_api"),
    path("api/railway-stations/", views.railway_stations_api, name="railway_stations_api"),
    path("api/bus-stands/", views.bus_stands_api, name="bus_stands_api"),
    path("api/roads/", views.roads_api, name="roads_api"),
    path("api/road-info/", views.road_info_api, name="road_info_api"),

    path("api/villages-demand/", views.villages_demand_api, name="villages_demand_api"),
    path("api/uncovered-villages/", views.uncovered_villages_api, name="uncovered_villages_api"),
    path("api/sectors-demand/", views.sectors_demand_api, name="sectors_demand_api"),

    path("api/hospital-buffers/", views.hospital_buffers_api, name="hospital_buffers_api"),

    path("api/village-nearest-hospital/", views.village_nearest_hospital_api, name="village_nearest_hospital_api"),
    path("api/village-nearest-school/", views.village_nearest_school_api, name="village_nearest_school_api"),
    path("api/village-nearest-college/", views.village_nearest_college_api, name="village_nearest_college_api"),

    path("api/sector-nearest-hospital/", views.sector_nearest_hospital_api, name="sector_nearest_hospital_api"),
    path("api/sector-nearest-school/", views.sector_nearest_school_api, name="sector_nearest_school_api"),
    path("api/sector-nearest-college/", views.sector_nearest_college_api, name="sector_nearest_college_api"),

    path("api/village-nearest-police-station/", views.village_nearest_police_station_api, name="village_nearest_police_station_api"),
    path("api/village-nearest-railway-station/", views.village_nearest_railway_station_api, name="village_nearest_railway_station_api"),
    path("api/village-nearest-bus-stand/", views.village_nearest_bus_stand_api, name="village_nearest_bus_stand_api"),

    path("api/sector-nearest-police-station/", views.sector_nearest_police_station_api, name="sector_nearest_police_station_api"),
    path("api/sector-nearest-railway-station/", views.sector_nearest_railway_station_api, name="sector_nearest_railway_station_api"),
    path("api/sector-nearest-bus-stand/", views.sector_nearest_bus_stand_api, name="sector_nearest_bus_stand_api"),

    path("api/chandigarh-boundary/", views.chandigarh_boundary_api, name="chandigarh_boundary_api"),
    path("api/sector-boundary/", views.sector_boundary_api, name="sector_boundary_api"),

    # Old API support
    path("api/facilities/", views.facilities_api, name="facilities_api"),
    path("api/villages/", views.villages_api, name="villages_api"),
    path("api/sectors/", views.sectors_api, name="sectors_api"),
    path("api/sector-boundaries/", views.sector_boundaries_api, name="sector_boundaries_api"),
    path("api/routes/coords/", views.route_coords_api, name="route_coords_api"),
    path("api/routes/multi/", views.route_multi_api, name="route_multi_api"),
    path("api/petrol-pumps/", views.petrol_pumps_api, name="petrol_pumps_api"),
    path("api/petrol-pump-buffers/", views.petrol_pump_buffers_api, name="petrol_pump_buffers_api"),
    path("api/sector-nearest-petrol-pump/", views.sector_nearest_petrol_pump_api, name="sector_nearest_petrol_pump_api"),
    path("api/village-nearest-petrol-pump/", views.village_nearest_petrol_pump_api, name="village_nearest_petrol_pump_api"),
    path("api/route-cache/", views.route_cache_api, name="route_cache_api"),
    path("api/roads/toggle-passable/", views.toggle_road_passable_api, name="toggle_road_passable_api"),
    path("api/login-live-stats/", views.login_live_stats_api, name="login_live_stats_api"),
]