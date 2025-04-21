import pytest
import httpx
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the backend URL from environment variable
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL')

class TestLinkedInProfileAnalyzer:
    def test_root_endpoint(self):
        """Test the root endpoint"""
        response = httpx.get(f"{BACKEND_URL}/api/")
        assert response.status_code == 200
        assert response.json() == {"message": "LinkedIn Profile Analyzer API"}

    def test_valid_profile_url(self):
        """Test fetching profile with valid LinkedIn URL"""
        test_url = "https://www.linkedin.com/in/williamhgates"
        response = httpx.post(
            f"{BACKEND_URL}/api/fetch-profile",
            json={"linkedin_url": test_url}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "profile_data" in data
        assert "analysis_results" in data
        assert "content_suggestions" in data
        
        # Check profile data for Bill Gates
        profile_data = data["profile_data"]
        assert profile_data["full_name"] == "Bill Gates"
        assert "Co-chair" in profile_data["headline"]
        
        # Check analysis results structure
        analysis = data["analysis_results"]
        assert "overall_score" in analysis
        assert "sections" in analysis
        assert "overall_recommendations" in analysis
        
        # Check content suggestions
        assert isinstance(data["content_suggestions"], list)
        assert len(data["content_suggestions"]) > 0

    def test_invalid_profile_url(self):
        """Test fetching profile with invalid URL format"""
        test_url = "invalid-url"
        response = httpx.post(
            f"{BACKEND_URL}/api/fetch-profile",
            json={"linkedin_url": test_url}
        )
        assert response.status_code == 400
        assert "Invalid LinkedIn URL format" in response.json()["detail"]

    def test_different_profile(self):
        """Test fetching a different profile to ensure different results"""
        test_url = "https://www.linkedin.com/in/johndoe"
        response = httpx.post(
            f"{BACKEND_URL}/api/fetch-profile",
            json={"linkedin_url": test_url}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check if we get different data than Bill Gates
        profile_data = data["profile_data"]
        assert profile_data["full_name"] != "Bill Gates"
        assert "Software Developer" in profile_data["headline"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])