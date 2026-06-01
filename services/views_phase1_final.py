import json

from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .models import Service, Region


# =====================================================
# Basic Pages
# =====================================================
def home(request):
    return HttpResponse("GIS Digital Twin Running 🚀")


def map_view(request):
    return render(request, "services/map.html")


# =====================================================
# Service CRUD API
# =====================================================
def service_to_dict(service):
    return {
        "id": service.id,
        "name": service.name,
        "type": service.type,
        "region": service.region,
        "country": service.country,
        "latitude": service.latitude,
        "longitude": service.longitude,
        "metadata": service.metadata,
        "created_at": service.created_at.isoformat() if service.created_at else None,
        "updated_at": service.updated_at.isoformat() if service.updated_at else None,
    }


def update_service_geom(service_id, longitude, latitude):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE public.services_service
            SET geom = ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            WHERE id = %s;
            """,
            [longitude, latitude, service_id],
        )


# GET /api/services/
# Optional filters:
# /api/services/?region=Punjab&type=hospital&country=India
def get_services(request):
    services = Service.objects.all().order_by("-id")

    region = request.GET.get("region")
    service_type = request.GET.get("type")
    country = request.GET.get("country")

    if region:
        services = services.filter(region__iexact=region)

    if service_type:
        services = services.filter(type__iexact=service_type)

    if country:
        services = services.filter(country__iexact=country)

    data = [service_to_dict(service) for service in services]

    return JsonResponse(data, safe=False)


# POST /api/services/add/
@csrf_exempt
def add_service(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        body = json.loads(request.body or "{}")

        name = body.get("name")
        service_type = body.get("type")
        latitude = body.get("latitude")
        longitude = body.get("longitude")

        if not name or not service_type or latitude is None or longitude is None:
            return JsonResponse(
                {
                    "error": "name, type, latitude, longitude are required"
                },
                status=400,
            )

        service = Service.objects.create(
            name=name,
            type=service_type,
            region=body.get("region"),
            country=body.get("country", "India"),
            latitude=float(latitude),
            longitude=float(longitude),
            metadata=body.get("metadata", {}),
        )

        update_service_geom(service.id, service.longitude, service.latitude)

        return JsonResponse(
            {
                "message": "Service added",
                "service": service_to_dict(service),
            },
            status=201,
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# PATCH /api/services/<id>/
@csrf_exempt
def update_service(request, service_id):
    if request.method != "PATCH":
        return JsonResponse({"error": "Only PATCH allowed"}, status=405)

    try:
        service = Service.objects.get(id=service_id)
        body = json.loads(request.body or "{}")

        if "name" in body:
            service.name = body["name"]

        if "type" in body:
            service.type = body["type"]

        if "region" in body:
            service.region = body["region"]

        if "country" in body:
            service.country = body["country"]

        if "latitude" in body:
            service.latitude = float(body["latitude"])

        if "longitude" in body:
            service.longitude = float(body["longitude"])

        if "metadata" in body:
            service.metadata = body["metadata"] or {}

        service.save()

        update_service_geom(service.id, service.longitude, service.latitude)

        return JsonResponse(
            {
                "message": "Service updated",
                "service": service_to_dict(service),
            }
        )

    except Service.DoesNotExist:
        return JsonResponse({"error": "Service not found"}, status=404)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# DELETE /api/services/<id>/
@csrf_exempt
def delete_service(request, service_id):
    if request.method != "DELETE":
        return JsonResponse({"error": "Only DELETE allowed"}, status=405)

    try:
        service = Service.objects.get(id=service_id)
        service.delete()

        return JsonResponse(
            {
                "message": "Service deleted",
                "id": service_id,
            }
        )

    except Service.DoesNotExist:
        return JsonResponse({"error": "Service not found"}, status=404)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
    # =========================================================
# Region APIs
# =========================================================
def region_to_dict(region):
    return {
        "id": region.id,
        "name": region.name,
        "country": region.country,
        "level": region.level,
        "metadata": region.metadata,
        "created_at": region.created_at.isoformat() if region.created_at else None,
        "updated_at": region.updated_at.isoformat() if region.updated_at else None,
    }


# GET /api/regions/
# Optional filters:
# /api/regions/?country=India&level=city
def get_regions(request):
    regions = Region.objects.all().order_by("country", "level", "name")

    country = request.GET.get("country")
    level = request.GET.get("level")

    if country:
        regions = regions.filter(country__iexact=country)

    if level:
        regions = regions.filter(level__iexact=level)

    data = [region_to_dict(region) for region in regions]

    return JsonResponse(data, safe=False)


# =====================================================
# GIS Dashboard API Config
# final_utm = UTM storage
# final_api = Leaflet/API 4326 views
# =====================================================
GIS_LAYERS = {
    "govt_hospitals": {
        "schema": "final_api",
        "table": "govt_hospitals",
        "geom": "geom_4326",
        "exclude": ["geom", "geom_4326"],
    },
    "private_hospitals": {
        "schema": "final_api",
        "table": "private_hospitals",
        "geom": "geom_4326",
        "exclude": ["geom", "geom_4326"],
    },
    "schools": {
        "schema": "final_api",
        "table": "schools",
        "geom": "geom_4326",
        "exclude": ["geom", "geom_4326"],
    },
    "colleges": {
        "schema": "final_api",
        "table": "colleges",
        "geom": "geom_4326",
        "exclude": ["geom", "geom_4326"],
    },
    "roads": {
        "schema": "final_api",
        "table": "roads",
        "geom": "geom_4326",
        "exclude": ["geom", "geom_4326"],
    },
    "villages_demand": {
        "schema": "final_api",
        "table": "villages_demand",
        "geom": "geom_4326",
        "exclude": ["geom", "geom_4326"],
    },
    "sectors_demand": {
        "schema": "final_api",
        "table": "sectors_demand",
        "geom": "geom_4326",
        "exclude": ["geom", "geom_4326"],
    },
    "chandigarh_boundary": {
        "schema": "final_api",
        "table": "chandigarh_boundary",
        "geom": "geom_4326",
        "exclude": ["geom", "geom_4326"],
    },
    "sector_boundary": {
        "schema": "final_api",
        "table": "sector_boundaries",
        "geom": "geom_4326",
        "exclude": ["geom", "geom_4326"],
    },
    "hospital_buffers": {
        "schema": "final_api",
        "table": "hospital_buffers_1km_2km",
        "geom": "geom_4326",
        "exclude": ["geom", "geom_4326"],
    },
    "village_nearest_hospital": {
        "schema": "final_api",
        "table": "village_nearest_hospital_line",
        "geom": "geom_4326",
        "exclude": ["geom", "geom_4326"],
    },
    "village_nearest_school": {
        "schema": "final_api",
        "table": "village_nearest_school_line",
        "geom": "geom_4326",
        "exclude": ["geom", "geom_4326"],
    },
    "village_nearest_college": {
        "schema": "final_api",
        "table": "village_nearest_college_line",
        "geom": "geom_4326",
        "exclude": ["geom", "geom_4326"],
    },
    "sector_nearest_hospital": {
        "schema": "final_api",
        "table": "sector_nearest_hospital_line",
        "geom": "geom_4326",
        "exclude": ["geom", "geom_4326"],
    },
    "sector_nearest_school": {
        "schema": "final_api",
        "table": "sector_nearest_school_line",
        "geom": "geom_4326",
        "exclude": ["geom", "geom_4326"],
    },
    "sector_nearest_college": {
        "schema": "final_api",
        "table": "sector_nearest_college_line",
        "geom": "geom_4326",
        "exclude": ["geom", "geom_4326"],
    },

    # Old API support
    "facilities": {
        "schema": "final_api",
        "table": "govt_hospitals",
        "geom": "geom_4326",
        "exclude": ["geom", "geom_4326"],
    },
}


def quote_ident(name):
    return '"' + name.replace('"', '""') + '"'


def table_to_geojson(layer_key, request):
    if layer_key not in GIS_LAYERS:
        raise Exception("Invalid GIS layer key")

    layer = GIS_LAYERS[layer_key]

    schema = quote_ident(layer["schema"])
    table = quote_ident(layer["table"])
    geom_col = quote_ident(layer["geom"])

    exclude_sql = ""
    for col in layer.get("exclude", []):
        exclude_sql += f" - '{col}'"

    try:
        limit = int(request.GET.get("limit", 50000))
    except ValueError:
        limit = 50000

    limit = min(limit, 50000)

    where_sql = f"WHERE t.{geom_col} IS NOT NULL"
    params = []

    # Buffer filter:
    # /api/hospital-buffers/?buffer_km=1
    # /api/hospital-buffers/?buffer_km=2
    if layer_key == "hospital_buffers":
        buffer_km = request.GET.get("buffer_km")
        if buffer_km in ["1", "2"]:
            where_sql += " AND t.buffer_km = %s"
            params.append(int(buffer_km))

    sql = f"""
        SELECT jsonb_build_object(
            'type', 'Feature',
            'geometry',
                CASE
                    WHEN ST_SRID(t.{geom_col}) = 0
                        THEN ST_AsGeoJSON(ST_SetSRID(t.{geom_col}, 4326))::jsonb
                    WHEN ST_SRID(t.{geom_col}) = 4326
                        THEN ST_AsGeoJSON(t.{geom_col})::jsonb
                    ELSE
                        ST_AsGeoJSON(ST_Transform(t.{geom_col}, 4326))::jsonb
                END,
            'properties',
                to_jsonb(t) {exclude_sql}
        ) AS feature
        FROM {schema}.{table} AS t
        {where_sql}
        LIMIT %s;
    """

    features = []

    with connection.cursor() as cursor:
        cursor.execute(sql, params + [limit])
        rows = cursor.fetchall()

        for row in rows:
            feature = row[0]

            if isinstance(feature, str):
                feature = json.loads(feature)

            features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def gis_layer_api(request, layer_key):
    try:
        geojson = table_to_geojson(layer_key, request)
        return JsonResponse(geojson, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# =====================================================
# GIS API Endpoints
# =====================================================
def govt_hospitals_api(request):
    return gis_layer_api(request, "govt_hospitals")


def private_hospitals_api(request):
    return gis_layer_api(request, "private_hospitals")


def schools_api(request):
    return gis_layer_api(request, "schools")


def colleges_api(request):
    return gis_layer_api(request, "colleges")


def roads_api(request):
    return gis_layer_api(request, "roads")


def villages_demand_api(request):
    return gis_layer_api(request, "villages_demand")


def sectors_demand_api(request):
    return gis_layer_api(request, "sectors_demand")


def hospital_buffers_api(request):
    return gis_layer_api(request, "hospital_buffers")


def village_nearest_hospital_api(request):
    return gis_layer_api(request, "village_nearest_hospital")


def village_nearest_school_api(request):
    return gis_layer_api(request, "village_nearest_school")


def village_nearest_college_api(request):
    return gis_layer_api(request, "village_nearest_college")


def sector_nearest_hospital_api(request):
    return gis_layer_api(request, "sector_nearest_hospital")


def sector_nearest_school_api(request):
    return gis_layer_api(request, "sector_nearest_school")


def sector_nearest_college_api(request):
    return gis_layer_api(request, "sector_nearest_college")


def chandigarh_boundary_api(request):
    return gis_layer_api(request, "chandigarh_boundary")


def sector_boundary_api(request):
    return gis_layer_api(request, "sector_boundary")


# =====================================================
# Old API Function Names Support
# =====================================================
def facilities_api(request):
    return gis_layer_api(request, "facilities")


def villages_api(request):
    return gis_layer_api(request, "villages_demand")


def sectors_api(request):
    return gis_layer_api(request, "sectors_demand")


def sector_boundaries_api(request):
    return gis_layer_api(request, "sector_boundary")