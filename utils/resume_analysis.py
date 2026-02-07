import os
import re
import json
from langchain_community.document_loaders import PDFPlumberLoader
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import List

# Initialize LLM
api_key = os.getenv("GROQ_API_KEY")
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=api_key)

# --- 1. Helpers & Extraction ---

def extract_text_from_pdf(file_path):
    try:
        loader = PDFPlumberLoader(file_path)
        pages = loader.load()
        text = "\n\n".join([p.page_content for p in pages])
        return text
    except Exception as e:
        print(f"Error loading PDF: {e}")
        return ""

class JobDescriptionSchema(BaseModel):
    required_skills: List[str] = Field(description="Must-have technical skills")
    nice_to_have: List[str] = Field(description="Bonus skills")
    min_experience_years: int = Field(description="Minimum years of experience required")

def parse_job_description(jd_text):
    """Extracts structured requirements from the JD text."""
    structured_llm = llm.with_structured_output(JobDescriptionSchema)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Extract technical requirements from the Job Description. Normalize skill names (e.g., 'Py' -> 'Python')."),
        ("human", "{jd_text}"),
    ])
    chain = prompt | structured_llm
    return chain.invoke({"jd_text": jd_text})

# --- 2. The BS Detector (Heuristics) ---

def analyze_impact_heuristics(work_experience):
    """
    Checks bullet points for numbers, metrics, and strong verbs.
    Returns a score (0-100) and specific feedback.
    """
    if not work_experience:
        return 0, ["No work experience section found."]

    total_bullets = 0
    strong_bullets = 0
    feedback = []
    
    # Regex for metrics (e.g., 20%, $50k, +10x, 500 users)
    metric_pattern = r"(\d+%|\$\d+|\d+x|\+\d+|\d+ users|\d+ customers|\d+ requests)"

    for role in work_experience:
        if not role.key_achievements:
            feedback.append(f"Role '{role.role}' has no bullet points.")
            continue
            
        for bullet in role.key_achievements:
            total_bullets += 1
            if re.search(metric_pattern, bullet):
                strong_bullets += 1
            else:
                # Limit feedback to first 3 issues to avoid clutter
                if len(feedback) < 3:
                    feedback.append(f"Weak point in '{role.role}': '{bullet[:50]}...' lacks metrics.")

    if total_bullets == 0:
        return 0, ["Add bullet points to your experience."]

    score = int((strong_bullets / total_bullets) * 100)
    return score, feedback

# --- 3. The Main Coordinator ---

def analyze_resume_compatibility(parsed_resume, jd_text):
    """
    Orchestrates the comparison between Structured Resume and JD.
    """
    # 1. Parse JD into Structure
    parsed_jd = parse_job_description(jd_text)
    
    # 2. Skill Match (Set Intersection)
    resume_skills = set([s.lower() for s in parsed_resume['skills']])
    jd_skills = set([s.lower() for s in parsed_jd.required_skills])
    
    matched_skills = resume_skills.intersection(jd_skills)
    missing_skills = jd_skills - resume_skills
    
    skill_score = (len(matched_skills) / len(jd_skills) * 100) if jd_skills else 100
    
    # 3. Impact Score (Heuristics)
    # Note: parsing Pydantic objects back from JSON might require converting lists to objects
    # For simplicity, we assume parsed_resume is the Dictionary we saved to DB
    
    # We need to access the 'work_experience' list from the dictionary
    experience_list = parsed_resume.get('work_experience', [])
    
    # We need to treat them as objects for the helper function, or adjust helper.
    # Let's adjust helper inputs quickly via a temporary object-like wrapper or just processing dicts
    # Re-using the logic above, but adapted for Dicts:
    impact_score = 0
    impact_feedback = []
    
    total_bullets = 0
    strong_bullets = 0
    metric_pattern = r"(\d+%|\$\d+|\d+x|\+\d+|\d+ users|\d+ customers)"
    
    for role in experience_list:
        achievements = role.get('key_achievements', [])
        for bullet in achievements:
            total_bullets += 1
            if re.search(metric_pattern, bullet):
                strong_bullets += 1
            elif len(impact_feedback) < 3:
                role_name = role.get('role', 'Unknown Role')
                impact_feedback.append(f"Weak Point ({role_name}): Add metrics to '{bullet[:40]}...'")

    if total_bullets > 0:
        impact_score = int((strong_bullets / total_bullets) * 100)
    
    # 4. Final Weighted Score
    # Skills (60%), Formatting/Impact (40%)
    overall_score = (skill_score * 0.6) + (impact_score * 0.4)
    
    return {
        "overall_match_score": round(overall_score, 1),
        "section_match_score": {
            "Skill_Match": round(skill_score, 1),
            "Impact_Score": round(impact_score, 1)
        },
        "missing_keywords": list(missing_skills),
        "improved_suggestion": impact_feedback
    }