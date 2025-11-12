def request_zone(request):
    zone = request.headers.get('X-EP-REQUEST-ZONE', None)
    return zone


def request_model(request):
    name = request.headers.get('X-MODEL-NAME', None)
    if name:
        return name.strip()
    return None


def is_from_redzone(request):
    zone = request_zone(request)
    if zone and zone.lower() == 'redzone':
        return True
    return False
