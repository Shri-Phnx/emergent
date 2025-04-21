from fastapi import FastAPI, HTTPException, Body, File, UploadFile
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import uvicorn
import os
import logging
from pathlib import Path
import httpx
import json
from pydantic import BaseModel
import uuid
import io
import PyPDF2
import re
from typing import Optional

# /backend 
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client.get_database(os.environ.get('DB_NAME', 'linkedin_analyzer'))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# LinkedIn API Configuration
LINKEDIN_API_HOST = "linkedin-data-api.p.rapidapi.com"
LINKEDIN_API_KEY = "e44d54a7damshf20519bc6b0ebffp14daaajsn8adfb44c57d1"
LINKEDIN_API_URL = f"https://{LINKEDIN_API_HOST}"

# Models
class ProfileRequest(BaseModel):
    linkedin_url: str

class ResumeUploadRequest(BaseModel):
    profile_id: str

class ProfileAnalysis(BaseModel):
    profile_id: str
    linkedin_url: str
    analysis_results: dict
    content_suggestions: list
    created_at: str
    
class ResumeAnalysis(BaseModel):
    profile_id: str
    resume_text: str
    optimized_sections: dict
    branding_plan: dict
    created_at: str

@app.get("/api/")
async def root():
    return {"message": "LinkedIn Profile Analyzer API"}

@app.post("/api/fetch-profile")
async def fetch_profile(request: ProfileRequest):
    # Extract username from LinkedIn URL
    if "linkedin.com/in/" in request.linkedin_url:
        username = request.linkedin_url.split("linkedin.com/in/")[1].split("/")[0].split("?")[0]
        logger.info(f"Extracted username: {username} from URL: {request.linkedin_url}")
    else:
        logger.warning(f"Invalid LinkedIn URL format: {request.linkedin_url}")
        raise HTTPException(status_code=400, detail="Invalid LinkedIn URL format")
        
    try:
        # Attempt to fetch profile data from LinkedIn API
        headers = {
            "x-rapidapi-host": LINKEDIN_API_HOST,
            "x-rapidapi-key": LINKEDIN_API_KEY
        }
        
        async with httpx.AsyncClient() as client:
            # Try to fetch using profile-details endpoint
            try:
                logger.info(f"Attempting to fetch LinkedIn profile data for: {username}")
                api_url = f"{LINKEDIN_API_URL}/profile-details?linkedin_id={username}"
                logger.info(f"API URL: {api_url}")
                
                response = await client.get(api_url, headers=headers)
                
                if response.status_code == 200:
                    logger.info("Successfully fetched profile data from LinkedIn API")
                    api_profile_data = response.json()
                    
                    # Map API response to our profile data structure
                    profile_data = map_api_response_to_profile_data(api_profile_data, username)
                else:
                    logger.warning(f"LinkedIn API returned status code: {response.status_code}")
                    logger.warning(f"API Response: {response.text}")
                    logger.warning("Falling back to mock data")
                    profile_data = generate_mock_profile_data(username)
                    
            except Exception as api_error:
                logger.error(f"Error fetching from LinkedIn API: {str(api_error)}")
                logger.warning("Falling back to mock data")
                profile_data = generate_mock_profile_data(username)
        
        # Analyze the profile
        analysis_results = analyze_profile(profile_data)
        
        # Generate content suggestions
        content_suggestions = generate_content_suggestions(profile_data, analysis_results)
        
        # Store results in database
        profile_analysis = {
            "profile_id": str(uuid.uuid4()),
            "linkedin_url": request.linkedin_url,
            "profile_data": profile_data,
            "analysis_results": analysis_results,
            "content_suggestions": content_suggestions,
            "created_at": str(datetime.now())
        }
        
        await db.profile_analyses.insert_one(profile_analysis)
        
        return {
            "profile_id": profile_analysis["profile_id"],
            "profile_data": profile_data,
            "analysis_results": analysis_results,
            "content_suggestions": content_suggestions
        }
            
    except Exception as e:
        logger.error(f"Error processing LinkedIn profile: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing LinkedIn profile: {str(e)}")

def analyze_profile(profile_data):
    """
    Analyze LinkedIn profile data and provide comprehensive feedback
    """
    analysis = {
        "overall_score": 0,
        "score_categories": {
            "completeness": 0,
            "relevance": 0,
            "impact": 0,
            "keywords": 0
        },
        "sections": {}
    }
    
    # Analyze headline
    if "headline" in profile_data:
        headline_score, headline_feedback, headline_category_scores = analyze_headline(profile_data["headline"])
        analysis["sections"]["headline"] = {
            "score": headline_score,
            "feedback": headline_feedback,
            "category_scores": headline_category_scores
        }
    
    # Analyze about section (in some APIs it's called "summary")
    about_text = profile_data.get("about", profile_data.get("summary", ""))
    if about_text:
        about_score, about_feedback, about_category_scores = analyze_about(about_text)
        analysis["sections"]["about"] = {
            "score": about_score,
            "feedback": about_feedback,
            "category_scores": about_category_scores
        }
    
    # Analyze experience
    if "experience" in profile_data:
        exp_score, exp_feedback, exp_category_scores = analyze_experience(profile_data["experience"])
        analysis["sections"]["experience"] = {
            "score": exp_score,
            "feedback": exp_feedback,
            "category_scores": exp_category_scores
        }
    
    # Analyze education
    if "education" in profile_data:
        edu_score, edu_feedback, edu_category_scores = analyze_education(profile_data["education"])
        analysis["sections"]["education"] = {
            "score": edu_score,
            "feedback": edu_feedback,
            "category_scores": edu_category_scores
        }
    
    # Analyze skills
    if "skills" in profile_data:
        skills_score, skills_feedback, skills_category_scores = analyze_skills(profile_data["skills"])
        analysis["sections"]["skills"] = {
            "score": skills_score,
            "feedback": skills_feedback,
            "category_scores": skills_category_scores
        }
    
    # Analyze certifications
    certifications = profile_data.get("certifications", [])
    cert_score, cert_feedback, cert_category_scores = analyze_certifications(certifications)
    analysis["sections"]["certifications"] = {
        "score": cert_score,
        "feedback": cert_feedback,
        "category_scores": cert_category_scores
    }
    
    # Analyze recommendations
    recommendations = profile_data.get("recommendations", [])
    rec_score, rec_feedback, rec_category_scores = analyze_recommendations(recommendations)
    analysis["sections"]["recommendations"] = {
        "score": rec_score,
        "feedback": rec_feedback,
        "category_scores": rec_category_scores
    }
    
    # Analyze visuals (profile picture and banner)
    visuals = {
        "has_profile_image": profile_data.get("has_profile_image", False),
        "has_banner": profile_data.get("has_banner", False)
    }
    visuals_score, visuals_feedback, visuals_category_scores = analyze_visuals(visuals)
    analysis["sections"]["visuals"] = {
        "score": visuals_score,
        "feedback": visuals_feedback,
        "category_scores": visuals_category_scores
    }
    
    # Analyze featured section
    featured = profile_data.get("featured", [])
    featured_score, featured_feedback, featured_category_scores = analyze_featured(featured)
    analysis["sections"]["featured"] = {
        "score": featured_score,
        "feedback": featured_feedback,
        "category_scores": featured_category_scores
    }
    
    # Analyze activity
    activity = profile_data.get("activity", [])
    activity_score, activity_feedback, activity_category_scores = analyze_activity(activity)
    analysis["sections"]["activity"] = {
        "score": activity_score,
        "feedback": activity_feedback,
        "category_scores": activity_category_scores
    }
    
    # Calculate category scores by averaging across all sections
    for category in ["completeness", "relevance", "impact", "keywords"]:
        category_scores = [
            section["category_scores"][category] 
            for section in analysis["sections"].values() 
            if "category_scores" in section and category in section["category_scores"]
        ]
        analysis["score_categories"][category] = sum(category_scores) / len(category_scores) if category_scores else 0
    
    # Calculate overall score (sum of category scores)
    analysis["overall_score"] = sum(analysis["score_categories"].values())
    
    # Provide overall recommendations
    analysis["overall_recommendations"] = generate_overall_recommendations(analysis)
    
    return analysis

def analyze_headline(headline):
    """Analyze the headline section"""
    score = 0
    feedback = []
    category_scores = {
        "completeness": 0,
        "relevance": 0,
        "impact": 0,
        "keywords": 0
    }
    
    # Assess completeness (25 points)
    if headline and len(headline) > 10:
        category_scores["completeness"] = 15
        if len(headline) > 30:
            category_scores["completeness"] = 25
    else:
        feedback.append("Your headline is too short. Add more relevant information.")
    
    # Assess keywords (25 points)
    keyword_count = 0
    keywords = ["leader", "expert", "specialist", "manager", "developer", 
                "engineer", "professional", "consultant", "strategist"]
    
    for keyword in keywords:
        if headline and keyword.lower() in headline.lower():
            keyword_count += 1
    
    if keyword_count > 0:
        category_scores["keywords"] = min(25, keyword_count * 8)
    else:
        feedback.append("Consider adding industry-relevant keywords to your headline.")
    
    # Assess impact (25 points)
    if headline and any(char in headline for char in "|•★✓✔"):
        category_scores["impact"] = 25
        feedback.append("Good use of special characters to make your headline stand out.")
    else:
        category_scores["impact"] = 10
        feedback.append("Consider using separators (|, •) to structure your headline and make it more scannable.")
    
    # Assess relevance (25 points) - placeholder for now
    category_scores["relevance"] = min(25, (category_scores["keywords"] / 25) * 25)
    
    # Calculate overall score
    score = sum(category_scores.values())
    
    # Final assessment
    if score < 25:
        feedback.append("Your headline needs significant improvement to attract attention.")
    elif score < 50:
        feedback.append("Your headline is basic and could be more compelling.")
    elif score < 75:
        feedback.append("Your headline is good but has room for improvement.")
    else:
        feedback.append("Your headline is excellent and likely to catch attention.")
    
    return min(100, score), feedback, category_scores

def analyze_about(about):
    """Analyze the about section"""
    score = 0
    feedback = []
    category_scores = {
        "completeness": 0,
        "relevance": 0,
        "impact": 0,
        "keywords": 0
    }
    
    # Assess completeness (25 points) - check length
    if about:
        if len(about) < 50:
            category_scores["completeness"] = 5
            feedback.append("Your about section is too short. Aim for at least 200-300 characters.")
        elif len(about) < 200:
            category_scores["completeness"] = 10
            feedback.append("Your about section is on the shorter side. Consider expanding it.")
        elif len(about) < 1000:
            category_scores["completeness"] = 20
            feedback.append("Your about section has a good length.")
        else:
            category_scores["completeness"] = 25
            feedback.append("Your about section is comprehensive, but ensure it remains focused and relevant.")
    else:
        feedback.append("You don't have an about section. This is a crucial part of your profile.")
    
    # Assess impact (25 points) - check for storytelling elements
    storytelling_indicators = ["journey", "passion", "learned", "discovered", "built", 
                               "created", "led", "achieved", "mission", "vision"]
    
    storytelling_score = 0
    if about:
        for indicator in storytelling_indicators:
            if indicator.lower() in about.lower():
                storytelling_score += 3
    
    category_scores["impact"] = min(25, storytelling_score)
    
    if storytelling_score < 15:
        feedback.append("Your about section could benefit from more storytelling elements to engage readers.")
    else:
        feedback.append("Good use of storytelling in your about section.")
    
    # Assess keywords (25 points) - Check for industry-relevant terms and professional vocabulary
    # This is a placeholder - in a real implementation, we would check against industry-specific terms
    if about:
        keyword_density = min(25, len(about.split()) / 20)  # Simple placeholder calculation
        category_scores["keywords"] = keyword_density
    
    # Assess relevance (25 points) - Check for personal brand alignment and first-person narrative
    if about and ("I am" in about or "I have" in about or "I " in about):
        category_scores["relevance"] = 20
        feedback.append("Good use of first-person narrative in your about section.")
    else:
        category_scores["relevance"] = 5
        feedback.append("Consider using first-person narrative for a more personal touch.")
    
    # Calculate overall score
    score = sum(category_scores.values())
    
    # Final assessment
    if score < 25:
        feedback.append("Your about section needs significant improvement.")
    elif score < 50:
        feedback.append("Your about section is basic and could be more compelling.")
    elif score < 75:
        feedback.append("Your about section is good but has room for improvement.")
    else:
        feedback.append("Your about section is excellent and likely to engage readers.")
    
    return min(100, score), feedback, category_scores

def analyze_experience(experience):
    """Analyze the experience section"""
    score = 0
    feedback = []
    category_scores = {
        "completeness": 0,
        "relevance": 0,
        "impact": 0,
        "keywords": 0
    }
    
    if not experience or len(experience) == 0:
        feedback.append("Your experience section is empty. This is a crucial part of your profile.")
        return 0, feedback, category_scores
    
    # Assess completeness (25 points)
    num_experiences = len(experience)
    if num_experiences < 2:
        category_scores["completeness"] = 5
        feedback.append("Consider adding more professional experiences to showcase your career progression.")
    elif num_experiences < 4:
        category_scores["completeness"] = 15
        feedback.append("You have a good number of experiences listed.")
    else:
        category_scores["completeness"] = 25
        feedback.append("You have a comprehensive list of experiences. Ensure they're all relevant.")
    
    # Check description quality for keyword and impact scoring
    descriptions_with_bullets = 0
    descriptions_with_achievements = 0
    
    achievement_indicators = ["achieved", "increased", "reduced", "improved", "led", 
                             "managed", "created", "developed", "implemented", "launched"]
    
    for exp in experience:
        description = exp.get("description", "")
        
        if description and ("•" in description or "-" in description or "*" in description):
            descriptions_with_bullets += 1
        
        for indicator in achievement_indicators:
            if description and indicator.lower() in description.lower():
                descriptions_with_achievements += 1
                break
    
    # Assess impact (25 points)
    if descriptions_with_achievements >= num_experiences / 2:
        category_scores["impact"] = 25
        feedback.append("Good focus on achievements in your experience descriptions.")
    else:
        category_scores["impact"] = 10
        feedback.append("Focus more on achievements rather than responsibilities in your descriptions.")
    
    # Assess keywords (25 points) 
    if descriptions_with_bullets >= num_experiences / 2:
        category_scores["keywords"] = 20
        feedback.append("Good use of bullet points in your experience descriptions.")
    else:
        category_scores["keywords"] = 10
        feedback.append("Consider using bullet points to make your experience descriptions more readable.")
    
    # Assess relevance (25 points)
    # Without a target role, we'll use a basic assessment based on descriptions and duration
    has_gaps = False  # This would require parsing dates and checking for gaps
    
    if has_gaps:
        category_scores["relevance"] = 10
        feedback.append("There appear to be gaps in your employment history. Consider explaining these.")
    else:
        category_scores["relevance"] = 20
    
    # Calculate overall score
    score = sum(category_scores.values())
    
    # Final assessment
    if score < 30:
        feedback.append("Your experience section needs significant improvement.")
    elif score < 60:
        feedback.append("Your experience section is basic and could be more compelling.")
    elif score < 80:
        feedback.append("Your experience section is good but has room for improvement.")
    else:
        feedback.append("Your experience section is excellent and effectively showcases your professional journey.")
    
    return min(100, score), feedback, category_scores

def analyze_education(education):
    """Analyze the education section"""
    score = 0
    feedback = []
    category_scores = {
        "completeness": 0,
        "relevance": 0,
        "impact": 0,
        "keywords": 0
    }
    
    if not education or len(education) == 0:
        feedback.append("Your education section is empty. Consider adding your educational background.")
        return 0, feedback, category_scores
    
    # Assess completeness (25 points)
    complete_entries = 0
    for edu in education:
        if all(key in edu and edu[key] for key in ["school", "degree", "field_of_study", "start_date", "end_date"]):
            complete_entries += 1
    
    if complete_entries == len(education):
        category_scores["completeness"] = 25
        feedback.append("Your education entries are complete with all relevant information.")
    else:
        category_scores["completeness"] = 12
        feedback.append("Some of your education entries are missing information. Consider completing them.")
    
    # Assess impact (25 points) - Check for descriptions/activities
    entries_with_description = 0
    for edu in education:
        if "description" in edu and edu["description"] and len(edu["description"]) > 50:
            entries_with_description += 1
    
    if entries_with_description > 0:
        category_scores["impact"] = 25
        feedback.append("Good job including details about your educational activities and achievements.")
    else:
        category_scores["impact"] = 10
        feedback.append("Consider adding descriptions to your education entries highlighting relevant coursework, achievements, or activities.")
    
    # Assess relevance (25 points) - Check for recency and continuous learning
    has_recent_education = False
    # This would require parsing dates
    
    if has_recent_education:
        category_scores["relevance"] = 25
        feedback.append("Your commitment to continuous learning is evident from your recent education.")
    else:
        category_scores["relevance"] = 15
        feedback.append("Consider adding recent courses or certifications to demonstrate continuous learning.")
    
    # Assess keywords (25 points) - Check for education-related keywords
    # Simplified approach for now
    category_scores["keywords"] = 15
    
    # Calculate overall score
    score = sum(category_scores.values())
    
    # Final assessment
    if score < 30:
        feedback.append("Your education section needs improvement.")
    elif score < 60:
        feedback.append("Your education section is adequate but could be enhanced.")
    elif score < 80:
        feedback.append("Your education section is good with minor room for improvement.")
    else:
        feedback.append("Your education section is excellent and effectively showcases your academic background.")
    
    return min(100, score), feedback, category_scores

def analyze_skills(skills):
    """Analyze the skills section"""
    score = 0
    feedback = []
    category_scores = {
        "completeness": 0,
        "relevance": 0,
        "impact": 0,
        "keywords": 0
    }
    
    if not skills or len(skills) == 0:
        feedback.append("Your skills section is empty. Adding relevant skills is crucial for discoverability.")
        return 0, feedback, category_scores
    
    # Assess completeness (25 points) - based on number of skills
    num_skills = len(skills)
    if num_skills < 5:
        category_scores["completeness"] = 5
        feedback.append("Consider adding more skills to your profile. Aim for at least 15-20 relevant skills.")
    elif num_skills < 10:
        category_scores["completeness"] = 12
        feedback.append("You have a good start with your skills, but adding more would improve visibility.")
    elif num_skills < 20:
        category_scores["completeness"] = 20
        feedback.append("You have a good number of skills listed.")
    else:
        category_scores["completeness"] = 25
        feedback.append("You have an impressive list of skills. Ensure they're all relevant and current.")
    
    # Assess keywords (25 points) - check for skill categories and industry relevance
    technical_skills = ["programming", "coding", "software", "development", "engineering"]
    soft_skills = ["leadership", "communication", "teamwork", "collaboration", "problem-solving"]
    domain_skills = ["marketing", "sales", "finance", "hr", "design", "product"]
    
    has_technical = any(any(tech in skill.lower() for tech in technical_skills) for skill in skills)
    has_soft = any(any(soft in skill.lower() for soft in soft_skills) for skill in skills)
    has_domain = any(any(domain in skill.lower() for domain in domain_skills) for skill in skills)
    
    keyword_score = 0
    if has_technical:
        keyword_score += 8
    if has_soft:
        keyword_score += 8
    if has_domain:
        keyword_score += 9
    
    category_scores["keywords"] = keyword_score
    
    if keyword_score < 8:
        feedback.append("Try to include a more diverse set of skills across different categories.")
    elif keyword_score < 17:
        feedback.append("You have skills in a couple of categories. Consider adding more diverse skills.")
    else:
        feedback.append("Great job showcasing a diverse range of skills across different categories.")
    
    # Assess relevance (25 points) 
    # Since we don't have the target role, we'll use a placeholder approach
    # In a full implementation, we'd compare skills against a target role's requirements
    category_scores["relevance"] = min(25, num_skills / 20 * 25)  # Placeholder: more skills = more likely to be relevant
    
    # Assess impact (25 points)
    # For skills, "impact" is less applicable, so we'll focus on endorsements and skill arrangement
    # This is a placeholder since we don't have endorsement data
    category_scores["impact"] = min(25, num_skills / 25 * 25)  # Placeholder
    
    # Calculate overall score
    score = sum(category_scores.values())
    
    # Final assessment
    if score < 30:
        feedback.append("Your skills section needs significant improvement.")
    elif score < 60:
        feedback.append("Your skills section is basic and could be more comprehensive.")
    elif score < 80:
        feedback.append("Your skills section is good but could be more strategic.")
    else:
        feedback.append("Your skills section is excellent and strategically positions you in your field.")
    
    return min(100, score), feedback, category_scores

def analyze_certifications(certifications):
    """Analyze certifications section"""
    score = 0
    feedback = []
    category_scores = {
        "completeness": 0,
        "relevance": 0,
        "impact": 0,
        "keywords": 0
    }
    
    if not certifications or len(certifications) == 0:
        feedback.append("You don't have any certifications listed. Consider adding relevant certifications to demonstrate your expertise.")
        return 0, feedback, category_scores
    
    # Assess completeness (25 points)
    num_certs = len(certifications)
    if num_certs == 1:
        category_scores["completeness"] = 10
        feedback.append("You have one certification listed. Consider adding more if applicable.")
    elif num_certs <= 3:
        category_scores["completeness"] = 20
        feedback.append("You have a good number of certifications listed.")
    else:
        category_scores["completeness"] = 25
        feedback.append("You have an impressive list of certifications.")
    
    # Assess relevance (25 points) - placeholder calculation
    category_scores["relevance"] = 15  # Default middle value
    
    # Assess impact (25 points) - placeholder calculation
    category_scores["impact"] = 15  # Default middle value
    
    # Assess keywords (25 points) - placeholder calculation
    category_scores["keywords"] = 15  # Default middle value
    
    # Add general feedback
    feedback.append("Make sure your certifications are current and from reputable organizations.")
    feedback.append("Consider highlighting your most prestigious or relevant certifications in your featured section.")
    
    # Calculate overall score
    score = sum(category_scores.values())
    
    return min(100, score), feedback, category_scores

def analyze_recommendations(recommendations):
    """Analyze recommendations section"""
    score = 0
    feedback = []
    category_scores = {
        "completeness": 0,
        "relevance": 0,
        "impact": 0,
        "keywords": 0
    }
    
    if not recommendations or len(recommendations) == 0:
        feedback.append("You don't have any recommendations. Request recommendations from colleagues, managers, or clients to boost credibility.")
        return 0, feedback, category_scores
    
    # Assess completeness (25 points)
    num_recs = len(recommendations)
    if num_recs == 1:
        category_scores["completeness"] = 10
        feedback.append("You have one recommendation. Try to get 3-5 quality recommendations.")
    elif num_recs <= 3:
        category_scores["completeness"] = 20
        feedback.append("You have a good number of recommendations.")
    else:
        category_scores["completeness"] = 25
        feedback.append("You have an impressive number of recommendations.")
    
    # Assess impact (25 points) - placeholder calculation
    category_scores["impact"] = min(25, num_recs * 5)  # Each recommendation adds "impact"
    
    # Assess relevance (25 points) - placeholder calculation
    category_scores["relevance"] = 15  # Default middle value
    
    # Assess keywords (25 points) - placeholder calculation
    category_scores["keywords"] = 15  # Default middle value
    
    # Add general feedback
    feedback.append("Aim for recommendations that highlight specific skills and accomplishments.")
    feedback.append("Request recommendations from diverse sources: supervisors, peers, and subordinates.")
    
    # Calculate overall score
    score = sum(category_scores.values())
    
    return min(100, score), feedback, category_scores

def analyze_visuals(visuals):
    """Analyze profile and banner images"""
    score = 0
    feedback = []
    category_scores = {
        "completeness": 0,
        "relevance": 0,
        "impact": 0,
        "keywords": 0
    }
    
    has_profile = visuals.get("has_profile_image", False)
    has_banner = visuals.get("has_banner", False)
    
    # Assess completeness (25 points)
    if has_profile and has_banner:
        category_scores["completeness"] = 25
        feedback.append("Great job having both a profile picture and banner image.")
    elif has_profile:
        category_scores["completeness"] = 15
        feedback.append("You have a profile picture but no banner image. Adding a banner can enhance your profile's visual appeal.")
    elif has_banner:
        category_scores["completeness"] = 10
        feedback.append("You have a banner image but no profile picture. A professional profile picture is essential.")
    else:
        category_scores["completeness"] = 0
        feedback.append("You're missing both profile picture and banner image. These visuals are crucial for a complete profile.")
    
    # Assess impact (25 points)
    # Without seeing the actual images, we'll use placeholder values
    if has_profile:
        category_scores["impact"] = 15
        feedback.append("Ensure your profile picture is professional, clear, and friendly.")
    else:
        category_scores["impact"] = 0
    
    if has_banner:
        category_scores["impact"] += 10
        feedback.append("Make sure your banner image reflects your personal brand and professional identity.")
    
    # Relevance and keywords don't apply as strongly to visuals
    category_scores["relevance"] = has_profile * 15 + has_banner * 10  # Simple calculation
    category_scores["keywords"] = 0  # Not applicable to images
    
    # Calculate overall score
    score = sum(category_scores.values())
    
    return min(100, score), feedback, category_scores

def analyze_featured(featured):
    """Analyze featured section"""
    score = 0
    feedback = []
    category_scores = {
        "completeness": 0,
        "relevance": 0,
        "impact": 0,
        "keywords": 0
    }
    
    if not featured or len(featured) == 0:
        feedback.append("Your featured section is empty. Add articles, posts, or projects to showcase your expertise.")
        return 0, feedback, category_scores
    
    # Assess completeness (25 points)
    num_featured = len(featured)
    if num_featured == 1:
        category_scores["completeness"] = 10
        feedback.append("You have one item in your featured section. Consider adding 3-5 items for a more comprehensive showcase.")
    elif num_featured <= 3:
        category_scores["completeness"] = 20
        feedback.append("You have a good number of items in your featured section.")
    else:
        category_scores["completeness"] = 25
        feedback.append("Your featured section has an impressive number of items.")
    
    # Assess impact (25 points) - placeholder calculation
    category_scores["impact"] = min(25, num_featured * 5)  # Each featured item adds "impact"
    
    # Assess relevance (25 points) - placeholder calculation
    category_scores["relevance"] = 15  # Default middle value
    
    # Assess keywords (25 points) - placeholder calculation
    category_scores["keywords"] = 15  # Default middle value
    
    # Add general feedback
    feedback.append("Include a diverse mix of content types in your featured section (articles, posts, projects, etc.).")
    feedback.append("Regularly update your featured content to show your latest work and thinking.")
    
    # Calculate overall score
    score = sum(category_scores.values())
    
    return min(100, score), feedback, category_scores

def analyze_activity(activity):
    """Analyze recent LinkedIn activity"""
    score = 0
    feedback = []
    category_scores = {
        "completeness": 0,
        "relevance": 0,
        "impact": 0,
        "keywords": 0
    }
    
    if not activity or len(activity) == 0:
        feedback.append("You don't have any recent activity. Regular posting and engagement is crucial for visibility.")
        return 0, feedback, category_scores
    
    # Assess completeness (25 points)
    num_activity = len(activity)
    if num_activity == 1:
        category_scores["completeness"] = 10
        feedback.append("You have very limited recent activity. Aim for at least weekly posting or engagement.")
    elif num_activity <= 3:
        category_scores["completeness"] = 20
        feedback.append("You have some recent activity, which is good. Consider increasing frequency for better visibility.")
    else:
        category_scores["completeness"] = 25
        feedback.append("You're actively engaging on LinkedIn, which is excellent for visibility.")
    
    # Assess impact (25 points) - placeholder calculation
    category_scores["impact"] = min(25, num_activity * 6)  # Each activity adds "impact"
    
    # Assess relevance (25 points) - placeholder calculation
    category_scores["relevance"] = 15  # Default middle value
    
    # Assess keywords (25 points) - placeholder calculation
    category_scores["keywords"] = 15  # Default middle value
    
    # Add general feedback
    feedback.append("Focus on creating original content rather than just sharing others' posts.")
    feedback.append("Engage with your network by commenting thoughtfully on others' posts.")
    feedback.append("Consistency is key - establish a regular posting schedule.")
    
    # Calculate overall score
    score = sum(category_scores.values())
    
    return min(100, score), feedback, category_scores

def generate_mock_profile_data(username):
    """Generate mock LinkedIn profile data for demonstration purposes"""
    return {
        "public_identifier": username,
        "first_name": "John" if username != "williamhgates" else "Bill",
        "last_name": "Doe" if username != "williamhgates" else "Gates",
        "full_name": "John Doe" if username != "williamhgates" else "Bill Gates",
        "headline": "Software Developer at Tech Company" if username != "williamhgates" else "Co-chair, Bill & Melinda Gates Foundation",
        "summary": "Experienced software developer with a passion for creating innovative solutions." if username != "williamhgates" else "Co-chair of the Bill & Melinda Gates Foundation. Founder of Breakthrough Energy. Co-founder of Microsoft. Voracious reader. Avid traveler.",
        "country": "United States",
        "country_full_name": "United States of America",
        "city": "San Francisco" if username != "williamhgates" else "Seattle",
        "state": "California" if username != "williamhgates" else "Washington",
        "experience": [
            {
                "company": "Tech Company" if username != "williamhgates" else "Bill & Melinda Gates Foundation",
                "title": "Senior Software Developer" if username != "williamhgates" else "Co-chair",
                "description": "Leading the development of key features and improving application performance.",
                "location": "San Francisco, CA" if username != "williamhgates" else "Seattle, WA",
                "starts_at": {"month": 6, "year": 2018},
                "ends_at": None
            },
            {
                "company": "Startup Inc." if username != "williamhgates" else "Microsoft",
                "title": "Junior Developer" if username != "williamhgates" else "CEO",
                "description": "Worked on front-end development and user experience design.",
                "location": "San Francisco, CA" if username != "williamhgates" else "Redmond, WA",
                "starts_at": {"month": 1, "year": 2015},
                "ends_at": {"month": 5, "year": 2018}
            }
        ],
        "education": [
            {
                "school": "University of Technology" if username != "williamhgates" else "Harvard University",
                "degree": "Bachelor's Degree" if username != "williamhgates" else "Bachelor of Arts",
                "field_of_study": "Computer Science" if username != "williamhgates" else "Applied Mathematics",
                "description": "Graduated with honors. Active in coding club and hackathons.",
                "start_date": {"year": 2011},
                "end_date": {"year": 2015}
            }
        ],
        "skills": [
            "JavaScript" if username != "williamhgates" else "Business Strategy",
            "React" if username != "williamhgates" else "Leadership",
            "Node.js" if username != "williamhgates" else "Philanthropy",
            "Python" if username != "williamhgates" else "Technology",
            "SQL" if username != "williamhgates" else "Innovation",
            "Git" if username != "williamhgates" else "Public Speaking",
            "AWS" if username != "williamhgates" else "Global Health"
        ],
        "industry": "Computer Software" if username != "williamhgates" else "Philanthropy"
    }

def generate_overall_recommendations(analysis):
    """Generate overall recommendations based on the analysis"""
    recommendations = []
    
    # Identify weakest sections
    section_scores = [(section, data["score"]) for section, data in analysis["sections"].items()]
    section_scores.sort(key=lambda x: x[1])
    
    if section_scores:
        weakest_section = section_scores[0][0]
        recommendations.append(f"Focus on improving your {weakest_section} section as a priority.")
    
    # General recommendations based on overall score
    overall_score = analysis["overall_score"]
    
    if overall_score < 40:
        recommendations.append("Your profile needs significant improvement across multiple sections.")
        recommendations.append("Consider rewriting key sections and adding more detailed information about your experience and skills.")
        recommendations.append("Look at profiles of professionals in your field for inspiration.")
    elif overall_score < 70:
        recommendations.append("Your profile is average. With some targeted improvements, you can make it stand out more.")
        recommendations.append("Focus on quantifying achievements and adding more specific details to your experiences.")
        recommendations.append("Ensure all sections are complete and tell a cohesive professional story.")
    else:
        recommendations.append("Your profile is strong overall. Fine-tune to maintain your competitive edge.")
        recommendations.append("Continue to update regularly with new achievements and skills.")
        recommendations.append("Consider getting more recommendations and endorsements to further validate your expertise.")
    
    return recommendations

def generate_content_suggestions(profile_data, analysis_results):
    """Generate content suggestions based on profile data and analysis"""
    suggestions = []
    
    # Extract key information
    industry = profile_data.get("industry", "")
    skills = profile_data.get("skills", [])
    experience = profile_data.get("experience", [])
    
    # Generate industry-specific content ideas
    if industry:
        suggestions.extend([
            f"Share your insights on the latest trends in {industry}",
            f"Write about challenges facing professionals in {industry} and how to overcome them",
            f"Create a post comparing different career paths within {industry}"
        ])
    
    # Generate skill-based content ideas
    if skills and len(skills) > 0:
        top_skills = skills[:5]  # Use top 5 skills
        for skill in top_skills:
            suggestions.append(f"Share a case study demonstrating how you've applied {skill} in your work")
            suggestions.append(f"Create a 'tips and tricks' post about {skill}")
            suggestions.append(f"Write about how {skill} is evolving and what professionals should know")
    
    # Generate experience-based content ideas
    if experience and len(experience) > 0:
        latest_role = experience[0].get("title", "")
        if latest_role:
            suggestions.extend([
                f"Share a 'day in the life' post about your role as a {latest_role}",
                f"Discuss a challenging project you worked on in your role as {latest_role}",
                f"Create a post about lessons learned in your journey to becoming a {latest_role}"
            ])
    
    # General content suggestions
    general_suggestions = [
        "Share your professional journey and key milestones",
        "Write about a mistake you made and what you learned from it",
        "Create a post celebrating a colleague or mentor who has influenced your career",
        "Share your thoughts on remote work or work-life balance",
        "Write about books or resources that have helped your professional development",
        "Create a poll asking your network about challenges they face in your industry",
        "Share an infographic about key trends in your field"
    ]
    
    suggestions.extend(general_suggestions)
    
    # Return unique suggestions (up to 10)
    unique_suggestions = list(set(suggestions))
    return unique_suggestions[:10]

# Helper functions for resume analysis and optimization

def extract_job_titles(text):
    """Extract potential job titles from text"""
    common_titles = [
        "Software Engineer", "Product Manager", "Marketing Specialist", "Data Scientist",
        "Project Manager", "UX Designer", "Sales Executive", "Financial Analyst",
        "Operations Manager", "Content Writer", "HR Specialist", "Business Analyst"
    ]
    
    found_titles = []
    for title in common_titles:
        if title.lower() in text.lower():
            found_titles.append(title)
    
    return found_titles[:3]  # Return top 3

def extract_key_qualifications(text):
    """Extract key qualifications from text"""
    qualifications = [
        "Leadership", "Problem Solving", "Communication", "Project Management",
        "Software Development", "Data Analysis", "Digital Marketing", "Customer Service",
        "Strategic Planning", "Design Thinking", "Sales", "Financial Planning"
    ]
    
    found_qualifications = []
    for qual in qualifications:
        if qual.lower() in text.lower():
            found_qualifications.append(qual)
    
    return found_qualifications[:5]  # Return top 5

def extract_career_highlights(text):
    """Extract career highlights from text"""
    # For demo purposes, we'll look for sentences with achievement indicators
    achievement_indicators = [
        "led", "managed", "created", "developed", "implemented",
        "increased", "improved", "reduced", "achieved", "awarded"
    ]
    
    sentences = re.split(r'[.!?]+', text)
    highlights = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence and any(indicator in sentence.lower() for indicator in achievement_indicators):
            if len(sentence) > 10 and len(sentence) < 150:  # Reasonable length
                highlights.append(sentence)
    
    return highlights[:5]  # Return top 5

def extract_professional_traits(text):
    """Extract professional personality traits from text"""
    traits = [
        "detail-oriented", "analytical", "creative", "innovative", "strategic",
        "collaborative", "team player", "self-motivated", "organized", "adaptable",
        "proactive", "resourceful", "passionate", "dedicated", "results-driven"
    ]
    
    found_traits = []
    for trait in traits:
        if trait.lower() in text.lower():
            found_traits.append(trait)
    
    return found_traits[:5]  # Return top 5

def extract_achievements_for_role(text, role, company):
    """Extract achievements related to a specific role"""
    # Find paragraphs that might contain the role and company
    paragraphs = text.split('\n\n')
    relevant_paragraphs = []
    
    for para in paragraphs:
        if role in para.lower() or company in para.lower():
            relevant_paragraphs.append(para)
    
    # Look for achievement indicators in relevant paragraphs
    achievements = []
    indicators = ["increased", "decreased", "improved", "achieved", "delivered", "led", "managed"]
    
    for para in relevant_paragraphs:
        sentences = re.split(r'[.!?]+', para)
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and any(indicator in sentence.lower() for indicator in indicators):
                if len(sentence) > 10 and len(sentence) < 200:  # Reasonable length
                    achievements.append(sentence)
    
    return achievements[:5]  # Return top 5

def extract_skills(text):
    """Extract skills from text"""
    common_skills = [
        "Python", "JavaScript", "React", "Project Management", "Data Analysis",
        "Marketing", "Sales", "Leadership", "Communication", "Design",
        "SQL", "Excel", "Social Media", "Customer Service", "Consulting",
        "Java", "C++", "Problem Solving", "Strategic Planning", "Agile",
        "UX/UI Design", "Product Management", "Content Creation", "SEO",
        "Financial Analysis", "Machine Learning", "Negotiation", "Public Speaking"
    ]
    
    found_skills = []
    for skill in common_skills:
        if skill.lower() in text.lower():
            found_skills.append(skill)
    
    return found_skills

def extract_projects(text):
    """Extract projects from text"""
    # Look for project indicators
    project_indicators = ["project:", "projects:", "project -", "project name:", "developed:", "implemented:"]
    
    projects = []
    lines = text.split('\n')
    
    for line in lines:
        if any(indicator in line.lower() for indicator in project_indicators):
            # Extract project name
            for indicator in project_indicators:
                if indicator in line.lower():
                    project_part = line.lower().split(indicator)[1].strip()
                    project_name = project_part.split(",")[0].split("-")[0].split(".")[0].strip()
                    if project_name and 3 < len(project_name) < 50:
                        projects.append(project_name.title())
    
    # If no projects found with indicators, look for capitalized noun phrases
    if not projects:
        words = text.split()
        for i in range(len(words) - 1):
            if words[i] == "Project" and i+1 < len(words) and words[i+1][0].isupper():
                project_name = words[i+1]
                if i+2 < len(words) and words[i+2][0].isupper():
                    project_name += " " + words[i+2]
                projects.append(project_name)
    
    return list(set(projects))  # Remove duplicates

def extract_publications(text):
    """Extract publications or presentations from text"""
    # Look for publication indicators
    publication_indicators = ["publication:", "published:", "article:", "journal:", "conference:", "presented:"]
    
    publications = []
    lines = text.split('\n')
    
    for line in lines:
        if any(indicator in line.lower() for indicator in publication_indicators):
            # Extract publication name
            for indicator in publication_indicators:
                if indicator in line.lower():
                    pub_part = line.lower().split(indicator)[1].strip()
                    pub_name = pub_part.split(",")[0].split("-")[0].split(".")[0].strip()
                    if pub_name and 3 < len(pub_name) < 100:
                        publications.append(pub_name.title())
    
    return list(set(publications))  # Remove duplicates

# Missing import
from datetime import datetime

def map_api_response_to_profile_data(api_response, username):
    """Map LinkedIn API response to our profile data structure"""
    try:
        profile_data = {
            "public_identifier": username,
            "first_name": api_response.get("first_name", ""),
            "last_name": api_response.get("last_name", ""),
            "full_name": api_response.get("full_name", ""),
            "headline": api_response.get("headline", ""),
            "summary": api_response.get("summary", api_response.get("about", "")),
            "country": api_response.get("country", ""),
            "country_full_name": api_response.get("country_full_name", ""),
            "city": api_response.get("city", ""),
            "state": api_response.get("state", ""),
            "industry": api_response.get("industry", ""),
            "experience": [],
            "education": [],
            "skills": []
        }

        # Map experience
        if "experience" in api_response:
            for exp in api_response["experience"]:
                experience = {
                    "company": exp.get("company", ""),
                    "title": exp.get("title", ""),
                    "description": exp.get("description", ""),
                    "location": exp.get("location", ""),
                    "starts_at": exp.get("starts_at", {}),
                    "ends_at": exp.get("ends_at")
                }
                profile_data["experience"].append(experience)

        # Map education
        if "education" in api_response:
            for edu in api_response["education"]:
                education = {
                    "school": edu.get("school", ""),
                    "degree": edu.get("degree", ""),
                    "field_of_study": edu.get("field_of_study", ""),
                    "description": edu.get("description", ""),
                    "start_date": edu.get("start_date", {}),
                    "end_date": edu.get("end_date", {})
                }
                profile_data["education"].append(education)

        # Map skills
        if "skills" in api_response:
            profile_data["skills"] = [skill for skill in api_response["skills"] if skill]

        return profile_data

    except Exception as e:
        logger.error(f"Error mapping API response: {str(e)}")
        # Fall back to mock data if mapping fails
        return generate_mock_profile_data(username)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
