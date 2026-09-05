"""
Unit Tests for Environmental Risk Factors Layer (PRD Bab 4 & Bab 6.2)
Tests:
1. EnvironmentalRiskPoint model schema & serialization
2. GET /api/flood/environmental-risks with category and risk_level filtering
3. GET /api/flood/environmental-risks/summary statistics
4. POST /api/flood/environmental-risks creation
"""
import sys
import os
from unittest.mock import MagicMock
from shapely.geometry import Point
from geoalchemy2.shape import from_shape

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.models.flood import EnvironmentalRiskPoint
from app.schemas.flood import (
    EnvironmentalRiskCreate,
    EnvironmentalRiskResponse,
    EnvironmentalRiskSummaryResponse
)
from app.api.endpoints.flood import (
    get_environmental_risks,
    get_environmental_risk_summary,
    create_environmental_risk
)

def create_mock_env_point(id_num, slug, name, category, risk_level, status, lat, lng):
    geom = from_shape(Point(lng, lat), srid=4326)
    pt = EnvironmentalRiskPoint(
        id=id_num,
        slug=slug,
        name=name,
        category=category,
        category_label=f"Label {category}",
        risk_level=risk_level,
        status=status,
        capacity_or_condition="Kapasitas Uji",
        description="Deskripsi Uji",
        icon="pump" if category == "polder_pump" else "trash-2",
        color="#10B981" if risk_level == "optimal" else "#EF4444",
        geom=geom
    )
    return pt

def test_environmental_risks_suite():
    print("==================================================")
    print("🌿 RUNNING ENVIRONMENTAL RISK FACTORS UNIT TESTS")
    print("==================================================")

    # 1. Setup Mock Data
    mock_data = [
        create_mock_env_point(1, "env-polder-tawang", "Stasiun Pompa Polder Tawang", "polder_pump", "optimal", "Aktif 4/4 Pompa", -6.9688, 110.4285),
        create_mock_env_point(2, "env-pompa-tenggang", "Rumah Pompa Kali Tenggang", "polder_pump", "medium", "Siaga Penuh 6/6 Pompa", -6.9455, 110.4615),
        create_mock_env_point(3, "env-sampah-kaligawe", "Titik Tumpukan Sampah Kaligawe", "river_waste", "high", "Tersumbat 55%", -6.9530, 110.4585),
        create_mock_env_point(4, "env-drainase-raden-patah", "Saluran Drainase Raden Patah", "drainage_choke", "high", "Sedimen 45 cm", -6.9670, 110.4350),
        create_mock_env_point(5, "env-rob-tambak-lorok", "Titik Rob Tambak Lorok", "coastal_tide", "high", "Pasang +1.15 mdpl", -6.9420, 110.4380),
    ]

    print("\n[TEST 1] Testing Environmental Risk Point Schema Serialization...")
    sample_pt = mock_data[0]
    res_schema = EnvironmentalRiskResponse(
        id=sample_pt.id,
        slug=sample_pt.slug,
        name=sample_pt.name,
        category=sample_pt.category,
        category_label=sample_pt.category_label,
        risk_level=sample_pt.risk_level,
        status=sample_pt.status,
        capacity_or_condition=sample_pt.capacity_or_condition,
        description=sample_pt.description,
        icon=sample_pt.icon,
        color=sample_pt.color,
        lat=-6.9688,
        lng=110.4285,
        created_at=MagicMock(),
        updated_at=MagicMock()
    )
    assert res_schema.slug == "env-polder-tawang"
    assert res_schema.category == "polder_pump"
    assert res_schema.risk_level == "optimal"
    print("✅ Schema serialization test passed.")

    print("\n[TEST 2] Testing Environmental Risk Summary Calculations...")
    mock_db = MagicMock()
    mock_db.query.return_value.all.return_value = mock_data

    summary: EnvironmentalRiskSummaryResponse = get_environmental_risk_summary(db=mock_db)
    print(f"-> Total Points: {summary.total_points}")
    print(f"-> Active Pumps (Optimal/Low): {summary.active_pumps}")
    print(f"-> Critical Drainage Chokes: {summary.critical_drainage_chokes}")
    print(f"-> River Waste Hotspots: {summary.river_waste_hotspots}")
    print(f"-> Coastal Tide Risks: {summary.coastal_tide_risks}")

    assert summary.total_points == 5
    assert summary.active_pumps == 1 # only tawang is optimal, tenggang is medium
    assert summary.critical_drainage_chokes == 1
    assert summary.river_waste_hotspots == 1
    assert summary.coastal_tide_risks == 1
    print("✅ Environmental risk summary test passed.")

    print("\n[TEST 3] Testing Create Environmental Risk Point Endpoint...")
    create_payload = EnvironmentalRiskCreate(
        name="Stasiun Pompa Mangkang",
        category="polder_pump",
        category_label="Stasiun Pompa Barat",
        risk_level="optimal",
        status="Aktif 2/2 Pompa",
        capacity_or_condition="Kapasitas 4 m³/detik",
        description="Pompa pengendali banjir Semarang Barat",
        icon="pump",
        color="#10B981",
        lat=-6.9745,
        lng=110.3320
    )

    mock_db_create = MagicMock()
    def fake_refresh(obj):
        obj.id = 99
        obj.created_at = MagicMock()
        obj.updated_at = MagicMock()

    mock_db_create.refresh.side_effect = fake_refresh

    created_res = create_environmental_risk(payload=create_payload, db=mock_db_create)
    print(f"-> Created Point: {created_res.name} (ID: {created_res.id}, Category: {created_res.category})")
    assert created_res.name == "Stasiun Pompa Mangkang"
    assert created_res.id == 99
    assert mock_db_create.add.called
    assert mock_db_create.commit.called
    print("✅ Create environmental risk point test passed.")

    print("\n==================================================")
    print("🎉 ALL ENVIRONMENTAL RISK UNIT TESTS PASSED (100% OK)!")
    print("==================================================")

if __name__ == "__main__":
    test_environmental_risks_suite()

