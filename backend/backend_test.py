import unittest
import requests
import os
from datetime import datetime

BACKEND_URL = "https://cca0c709-874c-4030-875e-1c7b0cb97979.preview.emergentagent.com"

class LinkedInProfileAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.base_url = BACKEND_URL
        self.test_profile_url = "https://www.linkedin.com/in/williamhgates"
        self.test_profile_id = None

    def test_01_root_endpoint(self):
        """Test root endpoint"""
        response = requests.get(f"{self.base_url}/api/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "LinkedIn Profile Analyzer API"})

    def test_02_fetch_profile(self):
        """Test profile fetching"""
        data = {"linkedin_url": self.test_profile_url}
        response = requests.post(f"{self.base_url}/api/fetch-profile", json=data)
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        
        # Store profile_id for resume upload test
        self.test_profile_id = response_data["profile_id"]
        
        # Check response structure
        self.assertIn("profile_data", response_data)
        self.assertIn("analysis_results", response_data)
        self.assertIn("content_suggestions", response_data)
        
        # Check profile data
        profile_data = response_data["profile_data"]
        self.assertIn("headline", profile_data)
        self.assertIn("summary", profile_data)
        self.assertIn("experience", profile_data)
        self.assertIn("skills", profile_data)
        
        # Check analysis results
        analysis = response_data["analysis_results"]
        self.assertIn("overall_score", analysis)
        self.assertIn("score_categories", analysis)
        self.assertIn("sections", analysis)
        
        # Check content suggestions
        suggestions = response_data["content_suggestions"]
        self.assertTrue(isinstance(suggestions, list))
        self.assertTrue(len(suggestions) > 0)

    def test_03_upload_resume(self):
        """Test resume upload and analysis"""
        if not self.test_profile_id:
            self.skipTest("Profile ID not available - profile fetch test must pass first")
            
        # Create a sample resume file
        resume_content = """
        PROFESSIONAL SUMMARY
        Experienced technology leader with a passion for innovation and philanthropy.
        
        EXPERIENCE
        Co-chair, Bill & Melinda Gates Foundation
        - Led global health initiatives
        - Managed multi-billion dollar programs
        - Developed strategic partnerships
        
        CEO, Microsoft Corporation
        - Founded and grew company to industry leader
        - Developed Windows operating system
        - Led product innovation and strategy
        
        SKILLS
        Leadership, Strategic Planning, Technology Innovation, Public Speaking,
        Philanthropy, Business Strategy, Global Health Initiatives
        """
        
        # Create temporary resume file
        with open("test_resume.txt", "w") as f:
            f.write(resume_content)
            
        # Upload resume
        files = {"file": open("test_resume.txt", "rb")}
        data = {"profile_id": self.test_profile_id}
        
        response = requests.post(
            f"{self.base_url}/api/upload-resume",
            data=data,
            files=files
        )
        
        # Clean up
        os.remove("test_resume.txt")
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        
        # Check response structure
        self.assertIn("optimized_sections", response_data)
        self.assertIn("branding_plan", response_data)
        
        # Check optimized sections
        optimized = response_data["optimized_sections"]
        self.assertIn("headline", optimized)
        self.assertIn("summary", optimized)
        self.assertIn("experience", optimized)
        self.assertIn("skills", optimized)
        
        # Check branding plan
        branding = response_data["branding_plan"]
        self.assertIn("weekly_plan", branding)
        self.assertIn("banner_suggestion", branding)
        self.assertIn("posting_schedule", branding)

if __name__ == "__main__":
    unittest.main()