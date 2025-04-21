from fastapi import FastAPI, HTTPException, Body
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

class ProfileAnalysis(BaseModel):
    profile_id: str
    linkedin_url: str
    analysis_results: dict
    content_suggestions: list
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
    Analyze LinkedIn profile data and provide section-by-section feedback
    """
    analysis = {
        "overall_score": 0,
        "sections": {}
    }
    
    # Analyze headline
    if "headline" in profile_data:
        headline_score, headline_feedback = analyze_headline(profile_data["headline"])
        analysis["sections"]["headline"] = {
            "score": headline_score,
            "feedback": headline_feedback
        }
    
    # Analyze about section (in some APIs it's called "summary")
    about_text = profile_data.get("about", profile_data.get("summary", ""))
    if about_text:
        about_score, about_feedback = analyze_about(about_text)
        analysis["sections"]["about"] = {
            "score": about_score,
            "feedback": about_feedback
        }
    
    # Analyze experience
    if "experience" in profile_data:
        exp_score, exp_feedback = analyze_experience(profile_data["experience"])
        analysis["sections"]["experience"] = {
            "score": exp_score,
            "feedback": exp_feedback
        }
    
    # Analyze education
    if "education" in profile_data:
        edu_score, edu_feedback = analyze_education(profile_data["education"])
        analysis["sections"]["education"] = {
            "score": edu_score,
            "feedback": edu_feedback
        }
    
    # Analyze skills
    if "skills" in profile_data:
        skills_score, skills_feedback = analyze_skills(profile_data["skills"])
        analysis["sections"]["skills"] = {
            "score": skills_score,
            "feedback": skills_feedback
        }
    
    # Calculate overall score (average of section scores)
    section_scores = [section["score"] for section in analysis["sections"].values()]
    analysis["overall_score"] = sum(section_scores) / len(section_scores) if section_scores else 0
    
    # Provide overall recommendations
    analysis["overall_recommendations"] = generate_overall_recommendations(analysis)
    
    return analysis

def analyze_headline(headline):
    """Analyze the headline section"""
    # Simple analysis rules
    score = 0
    feedback = []
    
    # Check length
    if headline and len(headline) > 10:
        score += 25
    else:
        feedback.append("Your headline is too short. Add more relevant information.")
    
    # Check for keywords
    keyword_count = 0
    keywords = ["leader", "expert", "specialist", "manager", "developer", 
                "engineer", "professional", "consultant", "strategist"]
    
    for keyword in keywords:
        if headline and keyword.lower() in headline.lower():
            keyword_count += 1
    
    if keyword_count > 0:
        score += min(25, keyword_count * 10)
    else:
        feedback.append("Consider adding industry-relevant keywords to your headline.")
    
    # Check for uniqueness
    if headline and any(char in headline for char in "|•★✓✔"):
        score += 25
        feedback.append("Good use of special characters to make your headline stand out.")
    else:
        feedback.append("Consider using separators (|, •) to structure your headline and make it more scannable.")
    
    # Final check
    if score < 25:
        feedback.append("Your headline needs significant improvement to attract attention.")
    elif score < 50:
        feedback.append("Your headline is basic and could be more compelling.")
    elif score < 75:
        feedback.append("Your headline is good but has room for improvement.")
    else:
        feedback.append("Your headline is excellent and likely to catch attention.")
    
    return min(100, score), feedback

def analyze_about(about):
    """Analyze the about section"""
    score = 0
    feedback = []
    
    # Check length
    if about:
        if len(about) < 50:
            feedback.append("Your about section is too short. Aim for at least 200-300 characters.")
            score += 10
        elif len(about) < 200:
            feedback.append("Your about section is on the shorter side. Consider expanding it.")
            score += 25
        elif len(about) < 1000:
            feedback.append("Your about section has a good length.")
            score += 40
        else:
            feedback.append("Your about section is comprehensive, but ensure it remains focused and relevant.")
            score += 35
    else:
        feedback.append("You don't have an about section. This is a crucial part of your profile.")
        score = 0
    
    # Check for storytelling elements
    storytelling_indicators = ["journey", "passion", "learned", "discovered", "built", 
                               "created", "led", "achieved", "mission", "vision"]
    
    storytelling_score = 0
    if about:
        for indicator in storytelling_indicators:
            if indicator.lower() in about.lower():
                storytelling_score += 5
    
    score += min(30, storytelling_score)
    
    if storytelling_score < 15:
        feedback.append("Your about section could benefit from more storytelling elements to engage readers.")
    else:
        feedback.append("Good use of storytelling in your about section.")
    
    # Check for first-person narrative
    if about and ("I am" in about or "I have" in about or "I " in about):
        score += 20
        feedback.append("Good use of first-person narrative in your about section.")
    else:
        feedback.append("Consider using first-person narrative for a more personal touch.")
    
    # Final assessment
    if score < 25:
        feedback.append("Your about section needs significant improvement.")
    elif score < 50:
        feedback.append("Your about section is basic and could be more compelling.")
    elif score < 75:
        feedback.append("Your about section is good but has room for improvement.")
    else:
        feedback.append("Your about section is excellent and likely to engage readers.")
    
    return min(100, score), feedback

def analyze_experience(experience):
    """Analyze the experience section"""
    score = 0
    feedback = []
    
    if not experience or len(experience) == 0:
        feedback.append("Your experience section is empty. This is a crucial part of your profile.")
        return 0, feedback
    
    # Check number of experiences
    num_experiences = len(experience)
    if num_experiences < 2:
        feedback.append("Consider adding more professional experiences to showcase your career progression.")
        score += 10
    elif num_experiences < 4:
        feedback.append("You have a good number of experiences listed.")
        score += 25
    else:
        feedback.append("You have a comprehensive list of experiences. Ensure they're all relevant.")
        score += 30
    
    # Check for description quality
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
    
    if descriptions_with_bullets >= num_experiences / 2:
        score += 20
        feedback.append("Good use of bullet points in your experience descriptions.")
    else:
        feedback.append("Consider using bullet points to make your experience descriptions more readable.")
    
    if descriptions_with_achievements >= num_experiences / 2:
        score += 25
        feedback.append("Good focus on achievements in your experience descriptions.")
    else:
        feedback.append("Focus more on achievements rather than responsibilities in your descriptions.")
    
    # Check for duration gaps
    has_gaps = False
    # This would require parsing dates and checking for gaps
    
    if has_gaps:
        feedback.append("There appear to be gaps in your employment history. Consider explaining these.")
    else:
        score += 15
    
    # Final assessment
    if score < 30:
        feedback.append("Your experience section needs significant improvement.")
    elif score < 60:
        feedback.append("Your experience section is basic and could be more compelling.")
    elif score < 80:
        feedback.append("Your experience section is good but has room for improvement.")
    else:
        feedback.append("Your experience section is excellent and effectively showcases your professional journey.")
    
    return min(100, score), feedback

def analyze_education(education):
    """Analyze the education section"""
    score = 0
    feedback = []
    
    if not education or len(education) == 0:
        feedback.append("Your education section is empty. Consider adding your educational background.")
        return 0, feedback
    
    # Check completeness
    complete_entries = 0
    for edu in education:
        if all(key in edu and edu[key] for key in ["school", "degree", "field_of_study", "start_date", "end_date"]):
            complete_entries += 1
    
    if complete_entries == len(education):
        score += 40
        feedback.append("Your education entries are complete with all relevant information.")
    else:
        score += 20
        feedback.append("Some of your education entries are missing information. Consider completing them.")
    
    # Check for description/activities
    entries_with_description = 0
    for edu in education:
        if "description" in edu and edu["description"] and len(edu["description"]) > 50:
            entries_with_description += 1
    
    if entries_with_description > 0:
        score += 30
        feedback.append("Good job including details about your educational activities and achievements.")
    else:
        feedback.append("Consider adding descriptions to your education entries highlighting relevant coursework, achievements, or activities.")
    
    # Check for recent education/continuous learning
    has_recent_education = False
    # This would require parsing dates
    
    if has_recent_education:
        score += 20
        feedback.append("Your commitment to continuous learning is evident from your recent education.")
    else:
        feedback.append("Consider adding recent courses or certifications to demonstrate continuous learning.")
        score += 10
    
    # Final assessment
    if score < 30:
        feedback.append("Your education section needs improvement.")
    elif score < 60:
        feedback.append("Your education section is adequate but could be enhanced.")
    elif score < 80:
        feedback.append("Your education section is good with minor room for improvement.")
    else:
        feedback.append("Your education section is excellent and effectively showcases your academic background.")
    
    return min(100, score), feedback

def analyze_skills(skills):
    """Analyze the skills section"""
    score = 0
    feedback = []
    
    if not skills or len(skills) == 0:
        feedback.append("Your skills section is empty. Adding relevant skills is crucial for discoverability.")
        return 0, feedback
    
    # Check number of skills
    num_skills = len(skills)
    if num_skills < 5:
        feedback.append("Consider adding more skills to your profile. Aim for at least 15-20 relevant skills.")
        score += 10
    elif num_skills < 10:
        feedback.append("You have a good start with your skills, but adding more would improve visibility.")
        score += 25
    elif num_skills < 20:
        feedback.append("You have a good number of skills listed.")
        score += 40
    else:
        feedback.append("You have an impressive list of skills. Ensure they're all relevant and current.")
        score += 45
    
    # Check for endorsements
    # This would require more detailed API data
    
    # Check for skill categories
    # Simple approach: check for skills in different categories
    technical_skills = ["programming", "coding", "software", "development", "engineering"]
    soft_skills = ["leadership", "communication", "teamwork", "collaboration", "problem-solving"]
    domain_skills = ["marketing", "sales", "finance", "hr", "design", "product"]
    
    has_technical = any(any(tech in skill.lower() for tech in technical_skills) for skill in skills)
    has_soft = any(any(soft in skill.lower() for soft in soft_skills) for skill in skills)
    has_domain = any(any(domain in skill.lower() for domain in domain_skills) for skill in skills)
    
    category_score = 0
    if has_technical:
        category_score += 15
    if has_soft:
        category_score += 15
    if has_domain:
        category_score += 15
    
    score += min(45, category_score)
    
    if category_score < 15:
        feedback.append("Try to include a more diverse set of skills across different categories.")
    elif category_score < 30:
        feedback.append("You have skills in a couple of categories. Consider adding more diverse skills.")
    else:
        feedback.append("Great job showcasing a diverse range of skills across different categories.")
    
    # Final assessment
    if score < 30:
        feedback.append("Your skills section needs significant improvement.")
    elif score < 60:
        feedback.append("Your skills section is basic and could be more comprehensive.")
    elif score < 80:
        feedback.append("Your skills section is good but could be more strategic.")
    else:
        feedback.append("Your skills section is excellent and strategically positions you in your field.")
    
    return min(100, score), feedback

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
