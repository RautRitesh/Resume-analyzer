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
        ("system", "Extract technical requirements from the Job Description. Return a clean list of strings."),
        ("human", "{jd_text}"),
    ])
    chain = prompt | structured_llm
    return chain.invoke({"jd_text": jd_text})

# --- 2. Semantic Skill Matcher (NEW) ---

class SkillMatchSchema(BaseModel):
    match_percentage: float = Field(description="0-100 score based on semantic coverage. E.g., 'Tensorflow' matches 'Neural Networks'.")
    missing_skills: List[str] = Field(description="Skills from the JD that are completely missing (semantically) from the resume.")
    matching_skills: List[str] = Field(description="Skills from the JD that were found in the resume (directly or semantically).")

def evaluate_semantic_match(resume_skills, jd_skills):
    """
    Uses LLM to compare skills semantically instead of exact string matching.
    """
    if not jd_skills:
        return SkillMatchSchema(match_percentage=100.0, missing_skills=[], matching_skills=[])
    
    if not resume_skills:
        return SkillMatchSchema(match_percentage=0.0, missing_skills=jd_skills, matching_skills=[])

    structured_llm = llm.with_structured_output(SkillMatchSchema)
    
    system_prompt = """
    You are a Technical Recruiter. Compare the Candidate's Skills vs Job Requirements.
    
    Rules:
    1. USE SEMANTIC MATCHING. 
       - If JD asks for "Neural Networks" and Candidate has "TensorFlow" or "Deep Learning", COUNT IT AS A MATCH.
       - If JD asks for "AI/ML" and Candidate has "Scikit-learn" or "Computer Vision", COUNT IT AS A MATCH.
       - If JD asks for "Python" and Candidate has "Django", COUNT IT AS A MATCH.
    2. Be generous with related technologies.
    3. Return a score (0-100) representing how well the candidate covers the requirements.
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Candidate Skills: {resume_skills}\n\nJob Requirements: {jd_skills}"),
    ])
    
    chain = prompt | structured_llm
    return chain.invoke({"resume_skills": str(resume_skills), "jd_skills": str(jd_skills)})

# --- 3. The BS Detector (Heuristics) ---

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
    
    # Expanded Regex for Impact
    metric_pattern = r"(\d+%|\$\d+|\d+x|\+\d+|increased|decreased|improved|reduced|saved|generated|managed|led|scaled|launched|users|customers|accuracy|latency)"

    for role in work_experience:
        achievements = role.get('key_achievements', [])
        if not achievements:
            continue
            
        for bullet in achievements:
            total_bullets += 1
            if re.search(metric_pattern, bullet, re.IGNORECASE):
                strong_bullets += 1
            else:
                if len(feedback) < 3:
                    role_title = role.get('role', 'Role')
                    feedback.append(f"Weak point in '{role_title}': '{bullet[:40]}...' - Add metrics/results.")

    if total_bullets == 0:
        return 0, ["Add bullet points with metrics to your experience."]

    score = int((strong_bullets / total_bullets) * 100)
    return score, feedback

# --- 4. The Main Coordinator ---

def analyze_resume_compatibility(parsed_resume, jd_text):
    """
    Orchestrates the comparison between Structured Resume and JD.
    """
    # 1. Parse JD into Structure
    parsed_jd = parse_job_description(jd_text)
    
    resume_skills = parsed_resume.get('skills', [])
    jd_skills = parsed_jd.required_skills
    
    print(f"JD Requirements: {jd_skills}")
    print(f"Resume Skills: {resume_skills}")

    # 2. Semantic Skill Match (AI Powered)
    print("Performing Semantic Analysis...")
    semantic_result = evaluate_semantic_match(resume_skills, jd_skills)
    
    skill_score = semantic_result.match_percentage
    missing_skills = semantic_result.missing_skills
    
    print(f"Semantic Score: {skill_score}")
    print(f"Actually Missing: {missing_skills}")

    # 3. Impact Score (Heuristics)
    experience_list = parsed_resume.get('work_experience', [])
    impact_score, impact_feedback = analyze_impact_heuristics(experience_list)
    
    # 4. Final Weighted Score
    # Skills (60%), Formatting/Impact (40%)
    overall_score = (skill_score * 0.6) + (impact_score * 0.4)
    
    return {
        "overall_match_score": round(overall_score, 1),
        "section_match_score": {
            "Skill_Match": round(skill_score, 1),
            "Impact_Score": round(impact_score, 1)
        },
        "missing_keywords": missing_skills,
        "improved_suggestion": impact_feedback
    }