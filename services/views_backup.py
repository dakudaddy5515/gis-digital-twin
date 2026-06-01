from django.http import HttpResponse

def home(request):
    return HttpResponse("GIS Digital Twin Running 🚀")


from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.http import JsonResponse
from .models import Service
import json


# GET → saare services laane ke liye
def get_services(request):
    services = Service.objects.all()

    data = []
    for s in services:
        data.append({
            "id": s.id,
            "name": s.name,
            "type": s.type,
            "region": s.region,
            "country": s.country,
            "latitude": s.latitude,
            "longitude": s.longitude,
        })

    return JsonResponse(data, safe=False)


# POST → naya service add karne ke liye
def add_service(request):
    if request.method == "POST":
        body = json.loads(request.body)

        service = Service.objects.create(
            name=body.get("name"),
            type=body.get("type"),
            region=body.get("region"),
            country=body.get("country"),
            latitude=body.get("latitude"),
            longitude=body.get("longitude"),
        )

        return JsonResponse({"message": "Service added", "id": service.id})

    return JsonResponse({"error": "Only POST allowed"})

def map_view(request):
    return render(request, 'services/map.html')


# Frontend (map) se direct data database me save karna
@csrf_exempt
def add_service(request):
    if request.method == "POST":
        body = json.loads(request.body)

        service = Service.objects.create(
            name=body.get("name"),
            type=body.get("type"),
            region=body.get("region"),
            country=body.get("country"),
            latitude=body.get("latitude"),
            longitude=body.get("longitude"),
        )

        return JsonResponse({
            "message": "Service added",
            "id": service.id
        })

    return JsonResponse({"error": "Only POST allowed"})