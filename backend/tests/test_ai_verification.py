import asyncio
import sys
import os
from unittest.mock import MagicMock, patch

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.models.report import FloodReport
from app.models.user import User
from app.models.flood import FloodPoint
from app.services.ai_service import (
    call_cv_classifier,
    call_report_verifier,
    process_ai_verification,
    confirm_report_by_peer
)
from app.schemas.user import UserProfile
from app.schemas.report import FloodReportResponse

def test_ai_verification():
    print("==================================================")
    print("🤖 RUNNING AI VERIFICATION & TRUST SCORE TESTS")
    print("==================================================")

    # 1. Test CV and Verifier fallback helpers
    print("\n[TEST 1] Testing CV & Spatial Verifier helpers...")
    cv_res = asyncio.run(call_cv_classifier(""))
    assert "confidence" in cv_res
    print("-> CV Response:", cv_res)

    verifier_res = asyncio.run(call_report_verifier(1, -6.9535, 110.4570, "Banjir Kaligawe"))
    assert "verification_status" in verifier_res
    print("-> Verifier Response:", verifier_res)
    print("✅ Sub-services helper test passed.")

    # 2. Test Verification Pipeline (Accurate Report -> Verified + Trust Score Reward)
    print("\n[TEST 2] Testing process_ai_verification for accurate citizen report...")
    mock_user = User(
        id=1,
        email="budi.semarang@gmail.com",
        trust_score=60,
        total_reports=2,
        verified_reports=1
    )

    mock_report = FloodReport(
        id=101,
        user_id=mock_user.id,
        location_name="Jl. Kaligawe Raya",
        depth_cm=50,
        condition="Tidak Dapat Dilalui",
        description="Air laut pasang rob meluap setinggi lutut",
        photo_url="/assets/cctv_kaligawe.jpg",
        is_verified=False,
        verification_status="pending",
        confirmations_count=1
    )

    mock_db = MagicMock()
    # Mock query returns for report, user, existing flood point
    def mock_query_side_effect(model_or_col):
        mock_q = MagicMock()
        if model_or_col is FloodReport:
            mock_q.filter.return_value.first.return_value = mock_report
        elif model_or_col is User:
            mock_q.filter.return_value.first.return_value = mock_user
        elif model_or_col is FloodPoint:
            mock_q.filter.return_value.first.return_value = None
        else:
            mock_q.filter.return_value.first.return_value = None
        return mock_q

    mock_db.query.side_effect = mock_query_side_effect

    asyncio.run(process_ai_verification(101, mock_db))

    print(f"-> Report status: {mock_report.verification_status}, is_verified: {mock_report.is_verified}")
    print(f"-> Report confidence: {mock_report.ai_confidence}%, Note: {mock_report.verification_note}")
    print(f"-> User Trust Score after reward: {mock_user.trust_score} (Verified count: {mock_user.verified_reports})")

    assert mock_report.is_verified == True
    assert mock_report.verification_status == "verified"
    assert mock_user.trust_score == 65 # 60 + 5
    assert mock_user.verified_reports == 2
    assert mock_user.total_reports == 3
    print("✅ Accurate report verification & user reward test passed.")

    # 3. Test Peer Confirmation (Warga mengonfirmasi laporan)
    print("\n[TEST 3] Testing Peer Confirmation (Warga sekitar mengonfirmasi)...")
    unverified_report = FloodReport(
        id=202,
        user_id=mock_user.id,
        location_name="Simpang Gayamsari",
        depth_cm=20,
        is_verified=False,
        verification_status="unverified",
        confirmations_count=1
    )

    def mock_query_test3(model_or_col):
        mock_q = MagicMock()
        if model_or_col is FloodReport:
            mock_q.filter.return_value.first.return_value = unverified_report
        elif model_or_col is User:
            mock_q.filter.return_value.first.return_value = mock_user
        elif model_or_col is FloodPoint:
            mock_q.filter.return_value.first.return_value = None
        else:
            mock_q.filter.return_value.first.return_value = None
        return mock_q

    mock_db.query.side_effect = mock_query_test3

    # Warga kedua mengonfirmasi (confirmations_count -> 2)
    conf_res = confirm_report_by_peer(202, mock_db)
    print("-> Peer confirmation result:", conf_res)
    assert conf_res["success"] == True
    assert conf_res["confirmations_count"] == 2
    assert conf_res["is_verified"] == True
    assert conf_res["verification_status"] == "verified"
    print("✅ Peer confirmation auto-promote test passed.")

    # 4. Test User Profile & Report Schema Serialization
    print("\n[TEST 4] Testing UserProfile & FloodReport schema serialization...")
    user_prof = UserProfile(
        id=1,
        email="budi.semarang@gmail.com",
        full_name="Budi Santoso",
        avatar_url=None,
        vehicle_type="Motor Bebek",
        vehicle_max_depth_cm=20,
        trust_score=65,
        total_reports=3,
        verified_reports=2,
        saved_locations=[],
        created_at=mock_user.created_at or "2026-09-05T00:00:00"
    )
    assert user_prof.trust_score == 65

    rep_resp = FloodReportResponse(
        id=101,
        user_id=1,
        location_name="Jl. Kaligawe Raya",
        address="Kaligawe",
        depth_category="40-70 cm",
        depth_cm=50,
        condition="Tidak Dapat Dilalui",
        description="Air pasang",
        photo_url="/assets/cctv_kaligawe.jpg",
        is_verified=True,
        verification_status="verified",
        verification_note="Diverifikasi AI",
        ai_confidence=92,
        confirmations_count=2,
        lat=-6.9535,
        lng=110.4570,
        created_at="2026-09-05T00:00:00"
    )
    assert rep_resp.verification_status == "verified"
    assert rep_resp.confirmations_count == 2
    print("✅ Schema serialization test passed.")

    print("\n==================================================")
    print("🎉 ALL AI VERIFICATION & TRUST SCORE TESTS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    test_ai_verification()
