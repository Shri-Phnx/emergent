import pytest
import httpx
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the backend URL from environment variable
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'http://localhost:8001')

async def test_root_endpoint():
    """Test the root endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BACKEND_URL}/api/")
        assert response.status_code == 200
        assert response.json() == {"message": "LinkedIn Profile Analyzer API"}

async def test_fetch_profile_valid_url():
    """Test fetching profile with valid LinkedIn URL"""
    async with httpx.AsyncClient() as client:
        data = {
            "linkedin_url": "https://www.linkedin.com/in/williamhgates"
        }
        response = await client.post(f"{BACKEND_URL}/api/fetch-profile", json=data)
        
        # Check response status
        assert response.status_code == 200
        
        # Check response structure
        response_data = response.json()
        assert "profile_id" in response_data
        assert "profile_data" in response_data
        assert "analysis_results" in response_data
        assert "content_suggestions" in response_data
        
        # Check analysis results structure
        analysis = response_data["analysis_results"]
        assert "overall_score" in analysis
        assert "sections" in analysis
        assert isinstance(analysis["sections"], dict)
        
        # Check content suggestions
        assert isinstance(response_data["content_suggestions"], list)
        assert len(response_data["content_suggestions"]) > 0

async def test_fetch_profile_invalid_url():
    """Test fetching profile with invalid LinkedIn URL"""
    async with httpx.AsyncClient() as client:
        data = {
            "linkedin_url": "https://invalid-url.com/profile"
        }
        response = await client.post(f"{BACKEND_URL}/api/fetch-profile", json=data)
        assert response.status_code == 400
        assert "Invalid LinkedIn URL format" in response.json()["detail"]

if __name__ == "__main__":
    import asyncio
    
    async def run_tests():
        print("\n🔍 Running LinkedIn Profile Analyzer API Tests...")
        
        try:
            print("\n1️⃣ Testing root endpoint...")
            await test_root_endpoint()
            print("✅ Root endpoint test passed")
            
            print("\n2️⃣ Testing profile fetch with valid URL...")
            await test_fetch_profile_valid_url()
            print("✅ Profile fetch test with valid URL passed")
            
            print("\n3️⃣ Testing profile fetch with invalid URL...")
            await test_fetch_profile_invalid_url()
            print("✅ Profile fetch test with invalid URL passed")
            
            print("\n✨ All tests passed successfully!")
            
        except Exception as e:
            print(f"\n❌ Test failed: {str(e)}")
            raise e

    asyncio.run(run_tests())