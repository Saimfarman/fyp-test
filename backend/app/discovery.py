import csv
import io
import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from quart import Blueprint, current_app, g, jsonify, request
from sqlalchemy import and_, select

from .models import Lead, OptOutRequest, WorkspaceMember

bp = Blueprint("discovery", __name__, url_prefix="/api")

SOCIAL_HOSTS = {"facebook.com", "www.facebook.com", "instagram.com", "www.instagram.com", "wa.me", "linktr.ee"}
PRIVATE_NETWORKS = tuple(
    ipaddress.ip_network(network)
    for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8", "169.254.0.0/16", "::1/128", "fc00::/7")
)


@dataclass(frozen=True)
class ProviderPlace:
    provider_place_id: str
    name: str
    category: str | None
    address: str | None
    latitude: float
    longitude: float
    phone: str | None
    website_url: str | None
    rating: float | None
    review_count: int | None


class DiscoveryProvider:
    async def search(self, query: str, bbox: str | None = None) -> list[ProviderPlace]:
        raise NotImplementedError


class OverpassProvider(DiscoveryProvider):
    def __init__(self, endpoint: str = "https://overpass-api.de/api/interpreter") -> None:
        self.endpoint = endpoint

    async def search(self, query: str, bbox: str | None = None) -> list[ProviderPlace]:
        area = bbox or "24.70,66.90,24.98,67.25"
        tags = re.sub(r"[^a-zA-Z0-9_-]", "", query.strip().lower()) or "shop"
        category_query = {
            "restaurant": '["amenity"="restaurant"]',
            "cafe": '["amenity"="cafe"]',
            "clinic": '["amenity"="clinic"]',
            "salon": '["shop"="hairdresser"]',
            "retail": '["shop"]',
            "shop": '["shop"]',
        }.get(tags, f'["name"~"{tags}",i]')
        overpass_query = f'[out:json][timeout:25];nwr["name"]{category_query}({area});out center tags;'
        async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "LeadPitch/0.1 (local MVP)"}) as client:
            response = await client.post(self.endpoint, content=overpass_query)
            response.raise_for_status()
        places = []
        for item in response.json().get("elements", []):
            place = _place_from_osm(item)
            if place:
                places.append(place)
        return places


class NominatimProvider:
    endpoint = "https://nominatim.openstreetmap.org/search"

    async def geocode(self, query: str) -> tuple[float, float] | None:
        async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "LeadPitch/0.1 (local MVP)"}) as client:
            response = await client.get(self.endpoint, params={"q": query, "format": "jsonv2", "limit": 1})
            response.raise_for_status()
        rows = response.json()
        return (float(rows[0]["lat"]), float(rows[0]["lon"])) if rows else None


def _place_from_osm(item: dict) -> ProviderPlace | None:
    tags = item.get("tags", {})
    name = tags.get("name")
    center = item.get("center", item)
    if not name or "lat" not in center or "lon" not in center:
        return None
    return ProviderPlace(
        provider_place_id=f"osm:{item.get('type')}:{item.get('id')}",
        name=name,
        category=tags.get("amenity") or tags.get("shop") or tags.get("craft"),
        address=", ".join(filter(None, [tags.get("addr:housenumber"), tags.get("addr:street"), tags.get("addr:city")])),
        latitude=float(center["lat"]),
        longitude=float(center["lon"]),
        phone=tags.get("phone"),
        website_url=tags.get("website") or tags.get("contact:website"),
        rating=None,
        review_count=None,
    )


def normalize_url(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    parsed = urlparse(value if "://" in value else f"https://{value}")
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path or '/'}"


async def classify_website(url: str | None) -> str:
    normalized = normalize_url(url)
    if not normalized:
        return "NO_WEBSITE"
    hostname = (urlparse(normalized).hostname or "").lower()
    if hostname in SOCIAL_HOSTS or any(hostname.endswith(f".{host}") for host in SOCIAL_HOSTS):
        return "SOCIAL_ONLY"
    try:
        addresses = await _resolve_public_addresses(hostname)
        if not addresses:
            return "DEAD_SITE"
        async with httpx.AsyncClient(timeout=8, follow_redirects=True, max_redirects=5, headers={"User-Agent": "LeadPitch/0.1"}) as client:
            response = await client.get(normalized)
        if response.status_code >= 400 or _looks_parked(response.text):
            return "DEAD_SITE"
        return "HAS_WEBSITE"
    except (httpx.HTTPError, OSError, ValueError):
        return "DEAD_SITE"


async def _resolve_public_addresses(hostname: str) -> list[str]:
    loop = __import__("asyncio").get_running_loop()
    infos = await loop.run_in_executor(None, socket.getaddrinfo, hostname, 443, socket.AF_UNSPEC, socket.SOCK_STREAM)
    addresses = {info[4][0] for info in infos}
    if any(ipaddress.ip_address(address) in network for address in addresses for network in PRIVATE_NETWORKS):
        return []
    return list(addresses)


def _looks_parked(body: str) -> bool:
    text = re.sub(r"\s+", " ", body.lower())
    return any(marker in text for marker in ("domain is for sale", "parked free", "buy this domain", "coming soon"))


async def _workspace_id() -> object | None:
    if not g.user:
        return None
    workspace_header = request.headers.get("X-Workspace-ID")
    query = select(WorkspaceMember).where(WorkspaceMember.user_id == g.user.id)
    if workspace_header:
        query = query.where(WorkspaceMember.workspace_id == workspace_header)
    async with current_app.session_factory() as db:
        member = (await db.execute(query.order_by(WorkspaceMember.id))).scalars().first()
        return member.workspace_id if member else None


@bp.get("/leads")
async def list_leads():
    workspace_id = await _workspace_id()
    if not workspace_id:
        return jsonify({"error": {"code": "unauthenticated", "message": "Authentication required."}}), 401
    status = request.args.get("status")
    severity = request.args.get("severity")
    category = request.args.get("category")
    search = request.args.get("q")
    conditions = [Lead.workspace_id == workspace_id]
    if status:
        conditions.append(Lead.website_status == status.upper())
    if severity:
        conditions.append(Lead.severity == severity.upper())
    if category:
        conditions.append(Lead.category.ilike(f"%{category}%"))
    if search:
        conditions.append(Lead.name.ilike(f"%{search}%"))
    async with current_app.session_factory() as db:
        rows = (await db.execute(select(Lead).where(and_(*conditions)).order_by(Lead.created_at.desc()).limit(500))).scalars()
        return jsonify({"items": [_lead_json(lead) for lead in rows]})


@bp.get("/leads/map")
async def map_leads():
    workspace_id = await _workspace_id()
    if not workspace_id:
        return jsonify({"error": {"code": "unauthenticated", "message": "Authentication required."}}), 401
    try:
        min_lng, min_lat, max_lng, max_lat = [float(value) for value in request.args.get("bbox", "").split(",")]
    except (ValueError, TypeError):
        min_lng = min_lat = max_lng = max_lat = None
    conditions = [Lead.workspace_id == workspace_id]
    if min_lng is not None:
        conditions.extend([Lead.longitude >= min_lng, Lead.longitude <= max_lng, Lead.latitude >= min_lat, Lead.latitude <= max_lat])
    if request.args.get("severity"):
        conditions.append(Lead.severity == request.args["severity"].upper())
    async with current_app.session_factory() as db:
        rows = (await db.execute(select(Lead).where(and_(*conditions)).limit(5000))).scalars()
        return jsonify({"items": [_pin_json(lead) for lead in rows]})


@bp.get("/leads/<uuid:lead_id>")
async def get_lead(lead_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return jsonify({"error": {"code": "unauthenticated", "message": "Authentication required."}}), 401
    async with current_app.session_factory() as db:
        lead = (await db.execute(select(Lead).where(Lead.id == lead_id, Lead.workspace_id == workspace_id))).scalar_one_or_none()
        return jsonify(_lead_json(lead)) if lead else (jsonify({"error": {"code": "not_found", "message": "Lead not found."}}), 404)


@bp.post("/discovery/search")
async def search():
    workspace_id = await _workspace_id()
    if not workspace_id:
        return jsonify({"error": {"code": "unauthenticated", "message": "Authentication required."}}), 401
    payload = await request.get_json(silent=True) or {}
    query = str(payload.get("query", "shop")).strip()
    try:
        places = await OverpassProvider().search(query, payload.get("bbox"))
    except (httpx.HTTPError, ValueError) as error:
        return jsonify({"error": {"code": "provider_unavailable", "message": f"OpenStreetMap search failed: {error}"}}), 502
    created = await _persist_places(workspace_id, places)
    return jsonify({"status": "completed", "count": created}), 202


@bp.post("/discovery/scan-area")
async def scan_area():
    return await search()


@bp.post("/imports/csv")
async def import_csv():
    workspace_id = await _workspace_id()
    if not workspace_id:
        return jsonify({"error": {"code": "unauthenticated", "message": "Authentication required."}}), 401
    files = await request.files
    uploaded = files.get("file")
    if not uploaded:
        return jsonify({"error": {"code": "validation_error", "message": "A CSV file is required."}}), 400
    rows = csv.DictReader(io.StringIO((await uploaded.read()).decode("utf-8-sig")))
    places = []
    for index, row in enumerate(rows):
        try:
            places.append(ProviderPlace(f"csv:{index}:{row.get('name', '')}", row["name"], row.get("category"), row.get("address"), float(row["latitude"]), float(row["longitude"]), row.get("phone"), row.get("website"), float(row["rating"]) if row.get("rating") else None, int(row["review_count"]) if row.get("review_count") else None))
        except (KeyError, TypeError, ValueError):
            continue
    created = await _persist_places(workspace_id, places)
    return jsonify({"status": "completed", "count": created}), 202


async def _persist_places(workspace_id, places: list[ProviderPlace]) -> int:
    async with current_app.session_factory() as db:
        count = 0
        opt_outs = list((await db.execute(select(OptOutRequest).where(OptOutRequest.status != "REJECTED"))).scalars())
        for place in places:
            normalized_website = normalize_url(place.website_url)
            if any(
                (item.website_url and normalized_website and item.website_url.rstrip("/") == normalized_website.rstrip("/"))
                or item.business_name.casefold() == place.name.casefold()
                for item in opt_outs
            ):
                continue
            status = await classify_website(place.website_url)
            existing = (
                await db.execute(
                    select(Lead).where(
                        Lead.workspace_id == workspace_id,
                        Lead.provider_place_id == place.provider_place_id,
                    )
                )
            ).scalar_one_or_none()
            values = {
                "name": place.name,
                "category": place.category,
                "address": place.address,
                "latitude": place.latitude,
                "longitude": place.longitude,
                "phone": place.phone,
                "website_url": normalized_website,
                "website_status": status,
                "severity": _severity_for(status),
                "opportunity_score": 100 if status in {"NO_WEBSITE", "DEAD_SITE"} else 70 if status == "SOCIAL_ONLY" else 0,
                "lead_value_tier": "HIGH" if status in {"NO_WEBSITE", "DEAD_SITE"} else "LOW",
                "rating": place.rating,
                "review_count": place.review_count,
            }
            if existing:
                for key, value in values.items():
                    setattr(existing, key, value)
            else:
                db.add(Lead(workspace_id=workspace_id, provider_place_id=place.provider_place_id, **values))
            count += 1
        await db.commit()
        return count


def _lead_json(lead: Lead) -> dict:
    return {"id": str(lead.id), "name": lead.name, "category": lead.category, "address": lead.address, "phone": lead.phone, "latitude": lead.latitude, "longitude": lead.longitude, "websiteUrl": lead.website_url, "status": lead.website_status, "severity": lead.severity, "rating": lead.rating, "reviewCount": lead.review_count}


def _pin_json(lead: Lead) -> dict:
    return {"id": str(lead.id), "latitude": lead.latitude, "longitude": lead.longitude, "status": lead.website_status, "severity": lead.severity, "opportunityScore": lead.opportunity_score, "leadValueTier": lead.lead_value_tier}


def _severity_for(status: str) -> str:
    return {
        "NO_WEBSITE": "CRITICAL",
        "DEAD_SITE": "CRITICAL",
        "SOCIAL_ONLY": "HIGH",
        "HAS_WEBSITE": "UNSCANNED",
    }.get(status, "UNSCANNED")
