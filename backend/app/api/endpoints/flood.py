from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point, mapping
from typing import List, Optional

from app.core.database import get_db
from app.models.flood import FloodPoint, FloodZone, EnvironmentalRiskPoint
from app.schemas.flood import (
    FloodPointCreate,
    FloodPointResponse,
    FloodZoneResponse,
    RiskSummaryResponse,
    RiskSummaryItem,
    EnvironmentalRiskCreate,
    EnvironmentalRiskResponse,
    EnvironmentalRiskSummaryResponse,
    EnvironmentalCategorySummary
)

router = APIRouter()

@router.get("/points", response_model=List[FloodPointResponse])
def get_flood_points(
    status: str = Query("all", description="Filter status: all, safe, watch, flooded, impassable"),
    db: Session = Depends(get_db)
):
    query = db.query(
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

    if status != "all":
        query = query.filter(FloodPoint.status == status)

    results = query.all()
    return [
        FloodPointResponse(
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
        for r in results
    ]

@router.get("/points/{point_id}", response_model=FloodPointResponse)
def get_flood_point_by_id(point_id: int, db: Session = Depends(get_db)):
    result = db.query(
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
    ).filter(FloodPoint.id == point_id).first()

    if not result:
        raise HTTPException(status_code=404, detail="Titik pantau banjir tidak ditemukan")

    return FloodPointResponse(
        id=result.id,
        slug=result.slug,
        name=result.name,
        area=result.area,
        status=result.status,
        status_label=result.status_label or result.status.capitalize(),
        depth_cm=result.depth_cm,
        confidence=result.confidence,
        source=result.source,
        image_url=result.image_url,
        recommendation=result.recommendation,
        cause=result.cause,
        vehicles_allowed=result.vehicles_allowed or [],
        lat=result.lat,
        lng=result.lng,
        created_at=result.created_at,
        updated_at=result.updated_at
    )

@router.post("/points", response_model=FloodPointResponse, status_code=201)
def create_flood_point(payload: FloodPointCreate, db: Session = Depends(get_db)):
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

@router.get("/polygons", response_model=List[FloodZoneResponse])
def get_flood_polygons(db: Session = Depends(get_db)):
    zones = db.query(FloodZone).all()
    results = []
    for z in zones:
        shape = to_shape(z.geom)
        # Convert Shapely Polygon coordinates to [[lat, lng], ...]
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


# -------------------------------------------------------------
# PRD Bab 4 & 6.2: Faktor Risiko Lingkungan & Infrastruktur Kota
# -------------------------------------------------------------

@router.get("/environmental-risks", response_model=List[EnvironmentalRiskResponse], summary="Daftar Titik Risiko Lingkungan & Infrastruktur Drainase")
def get_environmental_risks(
    category: str = Query("all", description="Filter kategori: all, polder_pump, river_waste, drainage_choke, coastal_tide"),
    risk_level: str = Query("all", description="Filter risiko: all, optimal, low, medium, high"),
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

    results = query.all()
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

    # Group by category
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
def create_environmental_risk(payload: EnvironmentalRiskCreate, db: Session = Depends(get_db)):
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


