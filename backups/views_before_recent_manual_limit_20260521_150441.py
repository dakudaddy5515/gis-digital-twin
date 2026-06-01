import json

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.db import connection
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from .models import Service, Region


# =====================================================
# Basic Pages
# =====================================================
def home(request):
    if request.user.is_authenticated:
        return redirect("main_dashboard")
    return redirect("login")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("main_dashboard")

    error = ""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("main_dashboard")
        error = "Invalid username or password"

    return render(request, "services/login.html", {"error": error})


def logout_view(request):
    logout(request)
    return redirect("login")


def safe_count(table_name):
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            return cursor.fetchone()[0]
    except Exception:
        return 0


def manual_service_count():
    return Service.objects.filter(metadata__source="dashboard_manual").count()


def recent_manual_services():
    return Service.objects.filter(metadata__source="dashboard_manual").order_by("-id")[:6]


@login_required(login_url="login")
def main_dashboard(request):
    govt_hospitals = safe_count("final_api.govt_hospitals")
    private_hospitals = safe_count("final_api.private_hospitals")

    stats = {
        "roads": safe_count("final_api.roads"),
        "villages": safe_count("final_api.villages_demand"),
        "schools": safe_count("final_api.schools"),
        "colleges": safe_count("final_api.colleges"),
        "govt_hospitals": govt_hospitals,
        "private_hospitals": private_hospitals,
        "hospitals": govt_hospitals + private_hospitals,
        "petrol_pumps": safe_count("final_api.vw_petrol_pumps_chandigarh_4326"),
        "police_stations": safe_count("final_api.police_stations"),
        "railway_stations": safe_count("final_api.railway_stations"),
        "bus_stands": safe_count("final_api.bus_stands"),
        "manual_services": manual_service_count(),
        "covered_villages": 0,
        "uncovered_villages": 0,
    }

    try:
        with connection.cursor() as cursor:

            # Villages inside 2km hospital buffer = covered
            cursor.execute("""
                SELECT COUNT(DISTINCT v.village_id)
                FROM final_api.villages_demand v
                JOIN final_api.hospital_buffers_1km_2km b
                  ON ST_Intersects(v.geom_4326, b.geom_4326)
                WHERE b.buffer_km = 2;
            """)

            covered = cursor.fetchone()[0] or 0

            # Total villages
            cursor.execute("""
                SELECT COUNT(*)
                FROM final_api.villages_demand;
            """)

            total = cursor.fetchone()[0] or 0

            stats["covered_villages"] = covered
            stats["uncovered_villages"] = max(total - covered, 0)

    except Exception:
        pass

    return render(request, "services/dashboard.html", {
        "stats": stats,
        "recent_manual_services": recent_manual_services(),
    })


@login_required(login_url="login")
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


# Old name support
def services_api(request):
    return get_services(request)


# POST /api/services/add/
@csrf_exempt
def add_service(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        body = json.loads(request.body.decode("utf-8") or "{}")

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
        body = json.loads(request.body.decode("utf-8") or "{}")

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


# PATCH /api/services/<id>/
# DELETE /api/services/<id>/
@csrf_exempt
def service_detail_api(request, service_id):
    if request.method == "PATCH":
        return update_service(request, service_id)

    if request.method == "DELETE":
        return delete_service(request, service_id)

    return JsonResponse(
        {
            "error": "Only PATCH or DELETE allowed"
        },
        status=405,
    )


# =====================================================
# Region APIs
# =====================================================
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


# Old name support
def regions_api(request):
    return get_regions(request)


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
    "police_stations": {
        "schema": "final_api",
        "table": "police_stations",
        "geom": "geom_4326",
        "exclude": ["geom", "geom_4326"],
    },
    "railway_stations": {
        "schema": "final_api",
        "table": "railway_stations",
        "geom": "geom_4326",
        "exclude": ["geom", "geom_4326"],
    },
    "bus_stands": {
        "schema": "final_api",
        "table": "bus_stands",
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

    # Fast lightweight roads API:
    # Sends simplified road geometry + only useful road properties.
    # This improves Leaflet rendering speed.
    if layer_key == "roads":
        sql = f"""
            SELECT jsonb_build_object(
                'type', 'Feature',
                'geometry',
                    ST_AsGeoJSON(
                        ST_SimplifyPreserveTopology(
                            CASE
                                WHEN ST_SRID(t.{geom_col}) = 0
                                    THEN ST_SetSRID(t.{geom_col}, 4326)
                                WHEN ST_SRID(t.{geom_col}) = 4326
                                    THEN t.{geom_col}
                                ELSE
                                    ST_Transform(t.{geom_col}, 4326)
                            END,
                            0.00004
                        ),
                        5
                    )::jsonb,
                'properties',
                    jsonb_strip_nulls(jsonb_build_object(
                        'road_id', t.road_id,
                        'road_name', t.road_name,
                        'road_type', t.road_type,
                        'osm_highway', t.osm_highway,
                        'length_km', t.length_km
                    ))
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


def police_stations_api(request):
    return gis_layer_api(request, "police_stations")


def railway_stations_api(request):
    return gis_layer_api(request, "railway_stations")


def bus_stands_api(request):
    return gis_layer_api(request, "bus_stands")


def roads_api(request):
    return gis_layer_api(request, "roads")


def road_info_api(request):
    """
    GET /api/road-info/?lat=30.7333&lng=76.7794
    Returns nearest road information with assumed condition and width.
    """
    try:
        lat = float(request.GET.get("lat"))
        lng = float(request.GET.get("lng"))
    except (TypeError, ValueError):
        return JsonResponse({
            "success": False,
            "message": "lat and lng are required"
        }, status=400)

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                WITH click_point AS (
                    SELECT ST_Transform(
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                        32643
                    ) AS geom
                )
                SELECT
                    r.id,
                    COALESCE(NULLIF(r.name, ''), 'Unnamed Road') AS road_name,
                    COALESCE(NULLIF(r.osm_highway, ''), NULLIF(r.road_type, ''), 'Unknown') AS road_type,
                    COALESCE(NULLIF(r.assumed_condition, ''), NULLIF(r.condition, ''), 'Unknown') AS road_condition,
                    ROUND(r.assumed_width_m::numeric, 2) AS road_width_m,
                    ROUND(r.speed_kmh::numeric, 2) AS speed_kmh,
                    ROUND(r.length_m::numeric, 2) AS length_m,
                    r.passable,
                    ROUND(ST_Distance(r.geom, cp.geom)::numeric, 2) AS distance_from_click_m,
                    ST_AsGeoJSON(ST_Transform(r.geom, 4326))::json AS geojson
                FROM routing.roads_edges_routable r
                CROSS JOIN click_point cp
                WHERE r.geom IS NOT NULL
                  AND ST_DWithin(r.geom, cp.geom, 120)
                ORDER BY r.geom <-> cp.geom
                LIMIT 1;
            """, [lng, lat])

            row = cursor.fetchone()

        if not row:
            return JsonResponse({
                "success": False,
                "message": "No road found near clicked point"
            })

        return JsonResponse({
            "success": True,
            "road_id": row[0],
            "road_name": row[1],
            "road_type": row[2],
            "road_condition": row[3],
            "road_width_m": float(row[4]) if row[4] is not None else None,
            "speed_kmh": float(row[5]) if row[5] is not None else None,
            "length_m": float(row[6]) if row[6] is not None else None,
            "passable": row[7],
            "distance_from_click_m": float(row[8]) if row[8] is not None else None,
            "geojson": row[9],
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)


def villages_demand_api(request):
    return gis_layer_api(request, "villages_demand")


def uncovered_villages_api(request):
    """
    Returns villages outside 2km hospital buffer
    """

    try:
        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT json_build_object(
                    'type', 'FeatureCollection',
                    'features', COALESCE(json_agg(features.feature), '[]'::json)
                )
                FROM (
                    SELECT json_build_object(
                        'type', 'Feature',
                        'geometry', ST_AsGeoJSON(v.geom_4326)::json,
                        'properties', json_build_object(
                            'village_id', v.village_id,
                            'village_name', v.village_name,
                            'coverage_status', 'Uncovered'
                        )
                    ) AS feature
                    FROM final_api.villages_demand v
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM final_api.hospital_buffers_1km_2km b
                        WHERE b.buffer_km = 2
                          AND ST_Intersects(v.geom_4326, b.geom_4326)
                    )
                ) AS features;
            """)

            geojson = cursor.fetchone()[0]

        return JsonResponse(geojson, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def uncovered_villages_api(request):
    """
    Returns villages outside 2km hospital buffer
    """

    try:
        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT json_build_object(
                    'type', 'FeatureCollection',
                    'features', COALESCE(json_agg(features.feature), '[]'::json)
                )
                FROM (
                    SELECT json_build_object(
                        'type', 'Feature',
                        'geometry', ST_AsGeoJSON(v.geom_4326)::json,
                        'properties', json_build_object(
                            'village_id', v.village_id,
                            'village_name', v.village_name,
                            'coverage_status', 'Uncovered'
                        )
                    ) AS feature
                    FROM final_api.villages_demand v
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM final_api.hospital_buffers_1km_2km b
                        WHERE b.buffer_km = 2
                          AND ST_Intersects(v.geom_4326, b.geom_4326)
                    )
                ) AS features;
            """)

            geojson = cursor.fetchone()[0]

        return JsonResponse(geojson, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


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


# =====================================================
# Route Cache Helper
# Saves routing API output into routing.route_cache
# =====================================================

def save_route_cache(
    result,
    route_type="route",
    cost_by="distance",
    origin_service_id=None,
    destination_service_id=None,
    origin_lat=None,
    origin_lng=None,
    destination_lat=None,
    destination_lng=None,
):
    try:
        if not isinstance(result, dict):
            return result

        if not result.get("success"):
            return result

        geojson = result.get("geojson")
        if not geojson:
            return result

        geojson_text = json.dumps(geojson)

        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO routing.route_cache (
                    route_type,
                    cost_by,
                    origin_service_id,
                    destination_service_id,
                    origin_lat,
                    origin_lng,
                    destination_lat,
                    destination_lng,
                    origin_vertex,
                    destination_vertex,
                    origin_snap_m,
                    destination_snap_m,
                    distance_km,
                    time_min,
                    edge_count,
                    route_geojson,
                    geom
                )
                VALUES (
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s,
                    %s::jsonb,
                    ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)
                )
                RETURNING id;
            """, [
                route_type,
                cost_by,
                origin_service_id,
                destination_service_id,
                origin_lat,
                origin_lng,
                destination_lat,
                destination_lng,
                result.get("origin_vertex"),
                result.get("destination_vertex"),
                result.get("origin_snap_m"),
                result.get("destination_snap_m"),
                result.get("distance_km"),
                result.get("time_min"),
                result.get("edge_count"),
                geojson_text,
                geojson_text,
            ])

            cache_id = cursor.fetchone()[0]

        result["route_saved"] = True
        result["route_cache_id"] = cache_id
        return result

    except Exception as e:
        result["route_saved"] = False
        result["route_cache_error"] = str(e)
        return result

# =====================================================
# Phase 2 Routing API
# POST /api/routes/
# Service ID based routing
# =====================================================
@csrf_exempt
def route_api(request):
    if request.method != "POST":
        return JsonResponse(
            {
                "success": False,
                "message": "Only POST method is allowed",
            },
            status=405,
        )

    try:
        data = json.loads(request.body.decode("utf-8") or "{}")

        origin_service_id = data.get("origin_service_id")
        destination_service_id = data.get("destination_service_id")
        cost_by = data.get("cost_by", "distance")
        if cost_by not in ["distance", "time"]:
            cost_by = "distance"
        road_filter = "any"

        if not origin_service_id or not destination_service_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": "origin_service_id and destination_service_id are required",
                },
                status=400,
            )

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT routing.get_route_geojson(%s, %s, %s, %s);
                """,
                [origin_service_id, destination_service_id, cost_by, road_filter],
            )
            result = cursor.fetchone()[0]

        if isinstance(result, str):
            result = json.loads(result)

        if isinstance(result, dict) and result.get("success"):
            result = save_route_cache(
                result,
                route_type="service",
                cost_by=cost_by,
                origin_service_id=origin_service_id,
                destination_service_id=destination_service_id,
            )

        return JsonResponse(result, safe=False)

    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "message": str(e),
            },
            status=500,
        )
# =====================================================
# Petrol Pump APIs
# =====================================================

def petrol_pumps_api(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT jsonb_build_object(
                    'type', 'FeatureCollection',
                    'features', COALESCE(
                        jsonb_agg(
                            jsonb_build_object(
                                'type', 'Feature',
                                'geometry', ST_AsGeoJSON(geom)::jsonb,
                                'properties', to_jsonb(t) - 'geom'
                            )
                        ),
                        '[]'::jsonb
                    )
                )
                FROM (
                    SELECT
                        petrol_pump_id,
                        osm_id,
                        osm_type,
                        name,
                        amenity,
                        brand,
                        "operator",
                        opening_hours,
                        source,
                        geom
                    FROM final_api.vw_petrol_pumps_chandigarh_4326
                    ORDER BY petrol_pump_id
                ) t;
            """)
            result = cursor.fetchone()[0]

        if isinstance(result, str):
            result = json.loads(result)

        return JsonResponse(result, safe=False)

    except Exception as e:
        return JsonResponse({
            "type": "FeatureCollection",
            "features": [],
            "error": str(e)
        }, status=500)


def petrol_pump_buffers_api(request):
    try:
        buffer_km = request.GET.get("buffer_km")

        if buffer_km in ["1", "2"]:
            where_sql = "WHERE buffer_km = %s"
            params = [int(buffer_km)]
        else:
            where_sql = ""
            params = []

        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT jsonb_build_object(
                    'type', 'FeatureCollection',
                    'features', COALESCE(
                        jsonb_agg(
                            jsonb_build_object(
                                'type', 'Feature',
                                'geometry', ST_AsGeoJSON(geom)::jsonb,
                                'properties', to_jsonb(t) - 'geom'
                            )
                        ),
                        '[]'::jsonb
                    )
                )
                FROM (
                    SELECT
                        id,
                        petrol_pump_id,
                        name,
                        buffer_km,
                        geom
                    FROM final_api.vw_petrol_pump_buffers_1km_2km_4326
                    {where_sql}
                    ORDER BY buffer_km, petrol_pump_id
                ) t;
            """, params)

            result = cursor.fetchone()[0]

        if isinstance(result, str):
            result = json.loads(result)

        return JsonResponse(result, safe=False)

    except Exception as e:
        return JsonResponse({
            "type": "FeatureCollection",
            "features": [],
            "error": str(e)
        }, status=500)

# =====================================================
# Phase 2 Routing API
# POST /api/routes/coords/
# Coordinate based routing
# =====================================================
@csrf_exempt
def route_coords_api(request):
    if request.method != "POST":
        return JsonResponse(
            {
                "success": False,
                "message": "Only POST method is allowed",
            },
            status=405,
        )

    try:
        data = json.loads(request.body.decode("utf-8") or "{}")

        origin_lat = data.get("origin_lat")
        origin_lng = data.get("origin_lng")
        destination_lat = data.get("destination_lat")
        destination_lng = data.get("destination_lng")
        cost_by = data.get("cost_by", "distance")

        if (
            origin_lat is None
            or origin_lng is None
            or destination_lat is None
            or destination_lng is None
        ):
            return JsonResponse(
                {
                    "success": False,
                    "message": "origin_lat, origin_lng, destination_lat, destination_lng are required",
                },
                status=400,
            )

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT routing.get_route_geojson_by_coords(%s, %s, %s, %s, %s);
                """,
                [
                    float(origin_lat),
                    float(origin_lng),
                    float(destination_lat),
                    float(destination_lng),
                    cost_by,
                ],
            )
            result = cursor.fetchone()[0]

        if isinstance(result, str):
            result = json.loads(result)

        if isinstance(result, dict) and result.get("success"):
            result = save_route_cache(
                result,
                route_type="coords",
                cost_by=cost_by,
                origin_lat=float(origin_lat),
                origin_lng=float(origin_lng),
                destination_lat=float(destination_lat),
                destination_lng=float(destination_lng),
            )

        return JsonResponse(result, safe=False)

    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "message": str(e),
            },
            status=500,
        )

# =====================================================
# Fuel Gap Analysis APIs
# Sector/Village to Nearest Petrol Pump
# =====================================================

def sector_nearest_petrol_pump_api(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT jsonb_build_object(
                    'type', 'FeatureCollection',
                    'features', COALESCE(
                        jsonb_agg(
                            jsonb_build_object(
                                'type', 'Feature',
                                'geometry', ST_AsGeoJSON(geom)::jsonb,
                                'properties', to_jsonb(t) - 'geom'
                            )
                        ),
                        '[]'::jsonb
                    )
                )
                FROM (
                    SELECT
                        sector_id,
                        sector_name,
                        district,
                        petrol_pump_id,
                        petrol_pump_name,
                        nearest_petrol_pump_km,
                        fuel_coverage_status,
                        fuel_need_score,
                        geom
                    FROM final_api.vw_sector_nearest_petrol_pump_4326
                    ORDER BY fuel_need_score DESC, nearest_petrol_pump_km DESC
                ) t;
            """)
            result = cursor.fetchone()[0]

        if isinstance(result, str):
            result = json.loads(result)

        return JsonResponse(result, safe=False)

    except Exception as e:
        return JsonResponse({
            "type": "FeatureCollection",
            "features": [],
            "error": str(e)
        }, status=500)


def village_nearest_petrol_pump_api(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT jsonb_build_object(
                    'type', 'FeatureCollection',
                    'features', COALESCE(
                        jsonb_agg(
                            jsonb_build_object(
                                'type', 'Feature',
                                'geometry', ST_AsGeoJSON(geom)::jsonb,
                                'properties', to_jsonb(t) - 'geom'
                            )
                        ),
                        '[]'::jsonb
                    )
                )
                FROM (
                    SELECT
                        village_id,
                        village_name,
                        district,
                        petrol_pump_id,
                        petrol_pump_name,
                        nearest_petrol_pump_km,
                        fuel_coverage_status,
                        fuel_need_score,
                        geom
                    FROM final_api.vw_village_nearest_petrol_pump_4326
                    ORDER BY fuel_need_score DESC, nearest_petrol_pump_km DESC
                ) t;
            """)
            result = cursor.fetchone()[0]

        if isinstance(result, str):
            result = json.loads(result)

        return JsonResponse(result, safe=False)

    except Exception as e:
        return JsonResponse({
            "type": "FeatureCollection",
            "features": [],
            "error": str(e)
        }, status=500)
# =====================================================
# Route Cache / Route History API
# Returns saved routes from routing.route_cache
# =====================================================

def route_cache_api(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT jsonb_build_object(
                    'type', 'FeatureCollection',
                    'features', COALESCE(
                        jsonb_agg(
                            jsonb_build_object(
                                'type', 'Feature',
                                'geometry', ST_AsGeoJSON(geom)::jsonb,
                                'properties', to_jsonb(t) - 'geom'
                            )
                            ORDER BY id DESC
                        ),
                        '[]'::jsonb
                    )
                )
                FROM (
                    SELECT
                        id,
                        route_type,
                        cost_by,
                        origin_service_id,
                        destination_service_id,
                        origin_lat,
                        origin_lng,
                        destination_lat,
                        destination_lng,
                        origin_vertex,
                        destination_vertex,
                        origin_snap_m,
                        destination_snap_m,
                        distance_km,
                        time_min,
                        edge_count,
                        created_at,
                        geom
                    FROM routing.route_cache
                    ORDER BY id DESC
                    LIMIT 100
                ) t;
            """)
            result = cursor.fetchone()[0]

        if isinstance(result, str):
            result = json.loads(result)

        return JsonResponse(result, safe=False)

    except Exception as e:
        return JsonResponse({
            "type": "FeatureCollection",
            "features": [],
            "error": str(e)
        }, status=500)    
# =====================================================
# Phase 2 Road Block / Unblock API
# POST /api/roads/toggle-passable/
# Click nearest road and mark passable true/false
# =====================================================
@csrf_exempt
def toggle_road_passable_api(request):
    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "message": "Only POST method is allowed"
        }, status=405)

    try:
        data = json.loads(request.body.decode("utf-8") or "{}")

        lat = data.get("lat")
        lng = data.get("lng")
        passable_value = data.get("passable")
        max_distance_m = float(data.get("max_distance_m", 30))

        if lat is None or lng is None:
            return JsonResponse({
                "success": False,
                "message": "lat and lng are required"
            }, status=400)

        if isinstance(passable_value, str):
            passable_value = passable_value.lower() == "true"

        if not isinstance(passable_value, bool):
            return JsonResponse({
                "success": False,
                "message": "passable must be true or false"
            }, status=400)

        lat = float(lat)
        lng = float(lng)

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    e.id,
                    e.passable,
                    e.length_m,
                    ROUND(ST_Distance(e.geom, c.click_geom)::numeric, 2) AS distance_m,
                    ST_AsGeoJSON(ST_Transform(e.geom, 4326)) AS geojson
                FROM (
                    SELECT ST_Transform(
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                        32643
                    ) AS click_geom
                ) c
                JOIN LATERAL (
                    SELECT id, passable, length_m, geom
                    FROM routing.roads_edges_routable
                    WHERE geom IS NOT NULL
                    ORDER BY geom <-> c.click_geom
                    LIMIT 1
                ) e ON true;
            """, [lng, lat])

            row = cursor.fetchone()

            if not row:
                return JsonResponse({
                    "success": False,
                    "message": "No road found"
                }, status=404)

            edge_id, old_passable, length_m, distance_m, geojson_text = row

            if float(distance_m) > max_distance_m:
                return JsonResponse({
                    "success": False,
                    "message": "No road found near clicked point",
                    "nearest_edge_id": edge_id,
                    "nearest_distance_m": float(distance_m),
                    "max_distance_m": max_distance_m
                }, status=404)

            cursor.execute("""
                UPDATE routing.roads_edges_routable
                SET passable = %s
                WHERE id = %s
                RETURNING id, passable;
            """, [passable_value, edge_id])

            updated_id, new_passable = cursor.fetchone()

        return JsonResponse({
            "success": True,
            "message": "Road marked as passable" if new_passable else "Road marked as blocked",
            "edge_id": updated_id,
            "old_passable": old_passable,
            "new_passable": new_passable,
            "clicked_lat": lat,
            "clicked_lng": lng,
            "distance_m": float(distance_m),
            "length_m": float(length_m) if length_m is not None else None,
            "geojson": json.loads(geojson_text) if geojson_text else None
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)

# =====================================================
# Phase 2 Multi-stop Routing API
# POST /api/routes/multi/
# Example: {"service_ids":[11,12,13], "cost_by":"distance"}
# =====================================================
@csrf_exempt
def route_multi_api(request):
    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "message": "Only POST method is allowed"
        }, status=405)

    try:
        data = json.loads(request.body.decode("utf-8") or "{}")

        service_ids = data.get("service_ids")
        cost_by = data.get("cost_by", "distance")

        if not isinstance(service_ids, list) or len(service_ids) < 2:
            return JsonResponse({
                "success": False,
                "message": "service_ids must be a list with at least 2 service IDs"
            }, status=400)

        try:
            service_ids = [int(x) for x in service_ids]
        except Exception:
            return JsonResponse({
                "success": False,
                "message": "All service_ids must be integers"
            }, status=400)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT routing.get_multi_stop_route_geojson(%s::integer[], %s);
                """,
                [service_ids, cost_by],
            )
            result = cursor.fetchone()[0]

        if isinstance(result, str):
            result = json.loads(result)

        if isinstance(result, dict) and result.get("success"):
            result = save_route_cache(
                result,
                route_type="multi_stop",
                cost_by=cost_by,
                origin_service_id=service_ids[0],
                destination_service_id=service_ids[-1],
            )

        return JsonResponse(result, safe=False)

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)
