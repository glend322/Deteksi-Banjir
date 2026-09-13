from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point, Polygon, mapping
from typing import List, Optional
import uuid

from app.core.database import get_db
from app.api.endpoints.auth import get_current_admin
from app.models.flood import FloodPoint, FloodZone, EnvironmentalRiskPoint
from app.schemas.flood import (
    FloodPointCreate,
    FloodPointUpdate,
    FloodPointResponse,
    FloodZoneCreate,
    FloodZoneUpdate,
    FloodZoneResponse,
    RiskSummaryResponse,
    RiskSummaryItem,
    EnvironmentalRiskCreate,
    EnvironmentalRiskResponse,
    EnvironmentalRiskSummaryResponse,
    EnvironmentalCategorySummary
)

router = APIRouter()


# ═══════════════════════════════════════════════════════
# FLOOD POINTS
# ═══════════════════════════════════════════════════════

def _build_flood_point_response(r) -> FloodPointResponse:
    return FloodPointResponse(
        id=r.id,
        slug=r.slug,
        name=r.name,
        area=r.area,
        status=r.status,
        status_label=r.status_label or r.status.capitalize(),
        depth_cm=r.depth_cm,
        confidence=r.confidence,
        source=r.source,
        image_url=r.image_url,
        recommendation=r.recommendation,
        cause=r.cause,
        vehicles_allowed=r.vehicles_allowed or [],
        lat=r.lat,
        lng=r.lng,
        created_at=r.created_at,
        updated_at=r.updated_at
    )

def _flood_point_query(db: Session):
    return db.query(
        FloodPoint.id,
        FloodPoint.slug,
        FloodPoint.name,
        FloodPoint.area,
        FloodPoint.status,
        FloodPoint.status_label,
        FloodPoint.depth_cm,
        FloodPoint.confidence,
        FloodPoint.source,
        FloodPoint.image_url,
        FloodPoint.recommendation,
        FloodPoint.cause,
        FloodPoint.vehicles_allowed,
        FloodPoint.created_at,
        FloodPoint.updated_at,
        func.ST_Y(FloodPoint.geom).label("lat"),
        func.ST_X(FloodPoint.geom).label("lng")
    )


@router.get("/points", response_model=List[FloodPointResponse])
def get_flood_points(
    status: str = Query("all", description="Filter status: all, safe, watch, flooded, impassable"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Daftar semua titik pantau banjir dengan pagination dan filter status."""
    query = _flood_point_query(db)
    if status != "all":
        query = query.filter(FloodPoint.status == status)
    results = query.offset(skip).limit(limit).all()
    return [_build_flood_point_response(r) for r in results]


@router.get("/points/nearby", response_model=List[FloodPointResponse])
def get_nearby_flood_points(
    lat: float = Query(..., ge=-90, le=90, description="Latitude posisi pengguna"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude posisi pengguna"),
    radius_km: float = Query(3.0, ge=0.1, le=50.0, description="Radius pencarian dalam km"),
    status: str = Query("all", description="Filter status: all, safe, watch, flooded, impassable"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Mengambil titik banjir dalam radius GPS tertentu menggunakan PostGIS ST_DWithin (PRD 6.2).
    Dipakai frontend untuk menampilkan titik relevan di sekitar posisi user.
    """
    user_geom = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
    radius_deg = radius_km / 111.0

    query = _flood_point_query(db).filter(
        func.ST_DWithin(FloodPoint.geom, user_geom, radius_deg)
    )
    if status != "all":
        query = query.filter(FloodPoint.status == status)

    results = query.limit(limit).all()
    return [_build_flood_point_response(r) for r in results]


@router.get("/points/{point_id}", response_model=FloodPointResponse)
def get_flood_point_by_id(point_id: int, db: Session = Depends(get_db)):
    result = _flood_point_query(db).filter(FloodPoint.id == point_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Titik pantau banjir tidak ditemukan")
    return _build_flood_point_response(result)


@router.get("/points/slug/{slug}", response_model=FloodPointResponse)
def get_flood_point_by_slug(slug: str, db: Session = Depends(get_db)):
    """Ambil titik pantau banjir berdasarkan slug unik (misal: 'loc-kaligawe')."""
    result = _flood_point_query(db).filter(FloodPoint.slug == slug).first()
    if not result:
        raise HTTPException(status_code=404, detail="Titik pantau banjir tidak ditemukan")
    return _build_flood_point_response(result)


@router.post("/points", response_model=FloodPointResponse, status_code=201)
def create_flood_point(
    payload: FloodPointCreate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin)
):
    """Tambah titik pantau banjir baru. Hanya admin."""
    geom = from_shape(Point(payload.lng, payload.lat), srid=4326)
    point = FloodPoint(
        slug=payload.slug or f"loc-{int(payload.lat*1000)}-{int(payload.lng*1000)}",
        name=payload.name,
        area=payload.area,
        status=payload.status,
        status_label=payload.status_label or payload.status.capitalize(),
        depth_cm=payload.depth_cm,
        confidence=payload.confidence,
        source=payload.source,
        image_url=payload.image_url,
        recommendation=payload.recommendation,
        cause=payload.cause,
        vehicles_allowed=payload.vehicles_allowed,
        geom=geom
    )
    db.add(point)
    db.commit()
    db.refresh(point)

    return FloodPointResponse(
        id=point.id,
        slug=point.slug,
        name=point.name,
        area=point.area,
        status=point.status,
        status_label=point.status_label,
        depth_cm=point.depth_cm,
        confidence=point.confidence,
        source=point.source,
        image_url=point.image_url,
        recommendation=point.recommendation,
        cause=point.cause,
        vehicles_allowed=point.vehicles_allowed or [],
        lat=payload.lat,
        lng=payload.lng,
        created_at=point.created_at,
        updated_at=point.updated_at
    )


@router.put("/points/{point_id}", response_model=FloodPointResponse)
def update_flood_point(
    point_id: int,
    payload: FloodPointUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin)
):
    """
    Update sebagian atau seluruh data titik pantau banjir (admin only).
    Berguna untuk update status saat banjir berubah atau reda.
    """
    point = db.query(FloodPoint).filter(FloodPoint.id == point_id).first()
    if not point:
        raise HTTPException(status_code=404, detail="Titik pantau banjir tidak ditemukan")

    # Hanya update field yang dikirim
    update_data = payload.model_dump(exclude_unset=True)
    new_lat = update_data.pop("lat", None)
    new_lng = update_data.pop("lng", None)

    for field, value in update_data.items():
        setattr(point, field, value)

    if new_lat is not None and new_lng is not None:
        point.geom = from_shape(Point(new_lng, new_lat), srid=4326)

    db.commit()
    db.refresh(point)

    # Ambil koordinat dari geom untuk response
    shape = to_shape(point.geom)
    return FloodPointResponse(
        id=point.id,
        slug=point.slug,
        name=point.name,
        area=point.area,
        status=point.status,
        status_label=point.status_label or point.status.capitalize(),
        depth_cm=point.depth_cm,
        confidence=point.confidence,
        source=point.source,
        image_url=point.image_url,
        recommendation=point.recommendation,
        cause=point.cause,
        vehicles_allowed=point.vehicles_allowed or [],
        lat=shape.y,
        lng=shape.x,
        created_at=point.created_at,
        updated_at=point.updated_at
    )


@router.delete("/points/{point_id}", status_code=status.HTTP_200_OK)
def delete_flood_point(
    point_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin)
):
    """Hapus titik pantau banjir (admin only)."""
    point = db.query(FloodPoint).filter(FloodPoint.id == point_id).first()
    if not point:
        raise HTTPException(status_code=404, detail="Titik pantau banjir tidak ditemukan")
    db.delete(point)
    db.commit()
    return {"message": "Titik pantau banjir berhasil dihapus", "id": point_id}


@router.get("/summary", response_model=RiskSummaryResponse)
def get_risk_summary(db: Session = Depends(get_db)):
    safe_cnt = db.query(FloodPoint).filter(FloodPoint.status == "safe").count()
    watch_cnt = db.query(FloodPoint).filter(FloodPoint.status == "watch").count()
    flooded_cnt = db.query(FloodPoint).filter(FloodPoint.status == "flooded").count()
    impassable_cnt = db.query(FloodPoint).filter(FloodPoint.status == "impassable").count()

    return RiskSummaryResponse(
        safe=RiskSummaryItem(count=safe_cnt, label="Aman", color="#10B981", desc="Kondisi jalan normal lancar"),
        watch=RiskSummaryItem(count=watch_cnt, label="Waspada", color="#F59E0B", desc="Genangan 10-20 cm, licin"),
        flooded=RiskSummaryItem(count=flooded_cnt, label="Tergenang", color="#F97316", desc="Genangan 20-40 cm, motor rawan mogok"),
        impassable=RiskSummaryItem(count=impassable_cnt, label="Tidak Dapat Dilalui", color="#EF4444", desc="Genangan >40 cm, ditutup total")
    )


# ═══════════════════════════════════════════════════════
# FLOOD ZONES (Polygon)
# ═══════════════════════════════════════════════════════

@router.get("/polygons", response_model=List[FloodZoneResponse])
def get_flood_polygons(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    zones = db.query(FloodZone).offset(skip).limit(limit).all()
    results = []
    for z in zones:
        shape = to_shape(z.geom)
        coords = [[pt[1], pt[0]] for pt in shape.exterior.coords]
        results.append(
            FloodZoneResponse(
                id=z.id,
                slug=z.slug,
                name=z.name,
                status=z.status,
                fill_color=z.fill_color,
                fill_opacity=float(z.fill_opacity),
                border_color=z.border_color,
                border_weight=z.border_weight,
                coordinates=coords
            )
        )
    return results


@router.post("/polygons", response_model=FloodZoneResponse, status_code=status.HTTP_201_CREATED)
def create_flood_zone(
    payload: FloodZoneCreate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin)
):
    """Buat zona poligon banjir baru (admin only)."""
    pts = [(coord[1], coord[0]) for coord in payload.coordinates]
    if pts[0] != pts[-1]:
        pts.append(pts[0])

    poly_shape = Polygon(pts)
    geom = from_shape(poly_shape, srid=4326)

    slug = payload.slug or f"poly-{uuid.uuid4().hex[:8]}"
    zone = FloodZone(
        slug=slug,
        name=payload.name,
        status=payload.status,
        fill_color=payload.fill_color or "#3B82F6",
        fill_opacity=str(payload.fill_opacity or 0.45),
        border_color=payload.border_color or "#EF4444",
        border_weight=payload.border_weight or 3,
        geom=geom
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)

    shape = to_shape(zone.geom)
    coords = [[pt[1], pt[0]] for pt in shape.exterior.coords]
    return FloodZoneResponse(
        id=zone.id,
        slug=zone.slug,
        name=zone.name,
        status=zone.status,
        fill_color=zone.fill_color,
        fill_opacity=float(zone.fill_opacity),
        border_color=zone.border_color,
        border_weight=zone.border_weight,
        coordinates=coords
    )


@router.put("/polygons/{zone_id}", response_model=FloodZoneResponse)
def update_flood_zone(
    zone_id: int,
    payload: FloodZoneUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin)
):
    """Update zona poligon banjir (admin only)."""
    zone = db.query(FloodZone).filter(FloodZone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zona banjir tidak ditemukan")

    update_data = payload.model_dump(exclude_unset=True)
    new_coords = update_data.pop("coordinates", None)

    for field, value in update_data.items():
        if field == "fill_opacity" and value is not None:
            setattr(zone, field, str(value))
        else:
            setattr(zone, field, value)

    if new_coords and len(new_coords) >= 3:
        pts = [(coord[1], coord[0]) for coord in new_coords]
        if pts[0] != pts[-1]:
            pts.append(pts[0])
        poly_shape = Polygon(pts)
        zone.geom = from_shape(poly_shape, srid=4326)

    db.commit()
    db.refresh(zone)

    shape = to_shape(zone.geom)
    coords = [[pt[1], pt[0]] for pt in shape.exterior.coords]
    return FloodZoneResponse(
        id=zone.id,
        slug=zone.slug,
        name=zone.name,
        status=zone.status,
        fill_color=zone.fill_color,
        fill_opacity=float(zone.fill_opacity),
        border_color=zone.border_color,
        border_weight=zone.border_weight,
        coordinates=coords
    )


@router.delete("/polygons/{zone_id}", status_code=status.HTTP_200_OK)
def delete_flood_zone(
    zone_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin)
):
    """Hapus zona poligon banjir (admin only)."""
    zone = db.query(FloodZone).filter(FloodZone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zona banjir tidak ditemukan")
    db.delete(zone)
    db.commit()
    return {"message": "Zona banjir berhasil dihapus", "id": zone_id}


# ═══════════════════════════════════════════════════════
# ENVIRONMENTAL RISKS
# ═══════════════════════════════════════════════════════

@router.get("/environmental-risks", response_model=List[EnvironmentalRiskResponse], summary="Daftar Titik Risiko Lingkungan & Infrastruktur Drainase")
def get_environmental_risks(
    category: str = Query("all", description="Filter kategori: all, polder_pump, river_waste, drainage_choke, coastal_tide"),
    risk_level: str = Query("all", description="Filter risiko: all, optimal, low, medium, high"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    query = db.query(
        EnvironmentalRiskPoint.id,
        EnvironmentalRiskPoint.slug,
        EnvironmentalRiskPoint.name,
        EnvironmentalRiskPoint.category,
        EnvironmentalRiskPoint.category_label,
        EnvironmentalRiskPoint.risk_level,
        EnvironmentalRiskPoint.status,
        EnvironmentalRiskPoint.capacity_or_condition,
        EnvironmentalRiskPoint.description,
        EnvironmentalRiskPoint.icon,
        EnvironmentalRiskPoint.color,
        EnvironmentalRiskPoint.created_at,
        EnvironmentalRiskPoint.updated_at,
        func.ST_Y(EnvironmentalRiskPoint.geom).label("lat"),
        func.ST_X(EnvironmentalRiskPoint.geom).label("lng")
    )

    if category != "all":
        query = query.filter(EnvironmentalRiskPoint.category == category)
    if risk_level != "all":
        query = query.filter(EnvironmentalRiskPoint.risk_level == risk_level)

    results = query.offset(skip).limit(limit).all()
    return [
        EnvironmentalRiskResponse(
            id=r.id,
            slug=r.slug,
            name=r.name,
            category=r.category,
            category_label=r.category_label,
            risk_level=r.risk_level,
            status=r.status,
            capacity_or_condition=r.capacity_or_condition,
            description=r.description,
            icon=r.icon,
            color=r.color,
            lat=r.lat,
            lng=r.lng,
            created_at=r.created_at,
            updated_at=r.updated_at
        )
        for r in results
    ]


@router.get("/environmental-risks/summary", response_model=EnvironmentalRiskSummaryResponse, summary="Ringkasan Statistik Infrastruktur Lingkungan")
def get_environmental_risk_summary(db: Session = Depends(get_db)):
    all_points = db.query(EnvironmentalRiskPoint).all()
    total_points = len(all_points)

    active_pumps = sum(1 for p in all_points if p.category == "polder_pump" and p.risk_level in ["optimal", "low"])
    critical_drainage = sum(1 for p in all_points if p.category == "drainage_choke" and p.risk_level in ["medium", "high"])
    river_waste = sum(1 for p in all_points if p.category == "river_waste" and p.risk_level in ["medium", "high"])
    coastal_tide = sum(1 for p in all_points if p.category == "coastal_tide")

    categories_meta = {
        "polder_pump": "Stasiun Pompa Polder",
        "river_waste": "Titik Sampah Sungai",
        "drainage_choke": "Saluran Drainase Kritis",
        "coastal_tide": "Titik Pasang Rob"
    }

    cat_summaries = []
    for cat_key, cat_name in categories_meta.items():
        cat_pts = [p for p in all_points if p.category == cat_key]
        cat_summaries.append(
            EnvironmentalCategorySummary(
                category=cat_key,
                label=cat_name,
                total_count=len(cat_pts),
                critical_count=sum(1 for p in cat_pts if p.risk_level in ["medium", "high"]),
                optimal_count=sum(1 for p in cat_pts if p.risk_level in ["optimal", "low"])
            )
        )

    return EnvironmentalRiskSummaryResponse(
        total_points=total_points,
        active_pumps=active_pumps,
        critical_drainage_chokes=critical_drainage,
        river_waste_hotspots=river_waste,
        coastal_tide_risks=coastal_tide,
        categories=cat_summaries
    )


@router.post("/environmental-risks", response_model=EnvironmentalRiskResponse, status_code=201, summary="Tambah Titik Faktor Risiko Lingkungan")
def create_environmental_risk(
    payload: EnvironmentalRiskCreate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin)
):
    """Tambah titik risiko lingkungan baru (admin only)."""
    geom = from_shape(Point(payload.lng, payload.lat), srid=4326)
    point = EnvironmentalRiskPoint(
        slug=payload.slug or f"env-{int(payload.lat*1000)}-{int(payload.lng*1000)}",
        name=payload.name,
        category=payload.category,
        category_label=payload.category_label,
        risk_level=payload.risk_level,
        status=payload.status,
        capacity_or_condition=payload.capacity_or_condition,
        description=payload.description,
        icon=payload.icon,
        color=payload.color,
        geom=geom
    )
    db.add(point)
    db.commit()
    db.refresh(point)

    return EnvironmentalRiskResponse(
        id=point.id,
        slug=point.slug,
        name=point.name,
        category=point.category,
        category_label=point.category_label,
        risk_level=point.risk_level,
        status=point.status,
        capacity_or_condition=point.capacity_or_condition,
        description=point.description,
        icon=point.icon,
        color=point.color,
        lat=payload.lat,
        lng=payload.lng,
        created_at=point.created_at,
        updated_at=point.updated_at
    )
