import pytest
import requests
import json
from urllib.parse import urljoin
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the backend URL from environment variable
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'http://localhost:8001')

class TestLinkedInAnalyzer:
    def setup_method(self):
        """Setup test class"""
        self.base_url = BACKEND_URL
        self.headers = {'Content-Type': 'application/json'}

    def test_root_endpoint(self):
        """Test the root endpoint"""
        response = requests.get(urljoin(self.base_url, '/api/'))
        assert response.status_code == 200
        assert response.json()['message'] == 'LinkedIn Profile Analyzer API'

    def test_valid_profile_analysis(self):
        """Test profile analysis with valid LinkedIn URL"""
        url = urljoin(self.base_url, '/api/fetch-profile')
        data = {
            'linkedin_url': 'https://www.linkedin.com/in/williamhgates'
        }
        
        response = requests.post(url, json=data, headers=self.headers)
        assert response.status_code == 200
        
        result = response.json()
        assert 'profile_id' in result
        assert 'analysis_results' in result
        assert 'content_suggestions' in result
        
        # Verify analysis results structure
        analysis = result['analysis_results']
        assert 'overall_score' in analysis
        assert 'sections' in analysis
        assert isinstance(analysis['sections'], dict)
        
        # Verify content suggestions
        assert isinstance(result['content_suggestions'], list)
        assert len(result['content_suggestions']) > 0

    def test_invalid_url_format(self):
        """Test profile analysis with invalid URL format"""
        url = urljoin(self.base_url, '/api/fetch-profile')
        data = {
            'linkedin_url': 'invalid-url'
        }
        
        response = requests.post(url, json=data, headers=self.headers)
        assert response.status_code == 400
        assert 'Invalid LinkedIn URL format' in response.json()['detail']

    def test_different_profile(self):
        """Test profile analysis with a different profile"""
        url = urljoin(self.base_url, '/api/fetch-profile')
        data = {
            'linkedin_url': 'https://www.linkedin.com/in/johndoe'
        }
        
        response = requests.post(url, json=data, headers=self.headers)
        assert response.status_code == 200
        
        result = response.json()
        # Verify we get different results for different profiles
        assert result['profile_data']['full_name'] == 'John Doe'

if __name__ == '__main__':
    pytest.main([__file__])