import pytest
import httpx
import os
from fastapi.testclient import TestClient
from server import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/api/")
    assert response.status_code == 200
    assert response.json() == {"message": "LinkedIn Profile Analyzer API"}

def test_fetch_profile_valid_url():
    test_url = "https://www.linkedin.com/in/williamhgates"
    response = client.post(
        "/api/fetch-profile",
        json={"linkedin_url": test_url}
    )
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields in response
    assert "profile_id" in data
    assert "profile_data" in data
    assert "analysis_results" in data
    assert "content_suggestions" in data
    
    # Check profile data structure
    profile_data = data["profile_data"]
    assert "full_name" in profile_data
    assert "headline" in profile_data
    assert isinstance(profile_data.get("experience", []), list)
    assert isinstance(profile_data.get("skills", []), list)

    # Check analysis results structure
    analysis = data["analysis_results"]
    assert "overall_score" in analysis
    assert "score_categories" in analysis
    assert "sections" in analysis
    
    # Check content suggestions
    assert isinstance(data["content_suggestions"], list)

def test_fetch_profile_invalid_url():
    response = client.post(
        "/api/fetch-profile",
        json={"linkedin_url": "invalid-url"}
    )
    assert response.status_code == 400
    assert "Invalid LinkedIn URL format" in response.json()["detail"]

def test_upload_resume_without_profile():
    # Test uploading resume without analyzing profile first
    with open("test_resume.pdf", "wb") as f:
        f.write(b"Test resume content")
    
    with open("test_resume.pdf", "rb") as f:
        response = client.post(
            "/api/upload-resume",
            files={"file": ("test_resume.pdf", f, "application/pdf")},
            data={"profile_id": "invalid-id"}
        )
    
    assert response.status_code == 404
    assert "Profile not found" in response.json()["detail"]
    
    # Cleanup
    os.remove("test_resume.pdf")

def test_upload_resume_with_profile():
    # First analyze a profile
    profile_response = client.post(
        "/api/fetch-profile",
        json={"linkedin_url": "https://www.linkedin.com/in/williamhgates"}
    )
    assert profile_response.status_code == 200
    profile_id = profile_response.json()["profile_id"]
    
    # Create and upload test resume
    with open("test_resume.pdf", "wb") as f:
        f.write(b"Test resume content with skills and experience")
    
    with open("test_resume.pdf", "rb") as f:
        response = client.post(
            "/api/upload-resume",
            files={"file": ("test_resume.pdf", f, "application/pdf")},
            data={"profile_id": profile_id}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "profile_id" in data
    assert "optimized_sections" in data
    assert "branding_plan" in data
    
    # Check optimized sections
    sections = data["optimized_sections"]
    assert "headline" in sections
    assert "summary" in sections
    assert "skills" in sections
    
    # Check branding plan
    plan = data["branding_plan"]
    assert "weekly_plan" in plan
    assert "banner_suggestion" in plan
    assert "posting_schedule" in plan
    
    # Cleanup
    os.remove("test_resume.pdf")

if __name__ == "__main__":
    pytest.main([__file__])