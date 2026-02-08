# utils/structures.py
from pydantic import BaseModel, Field
from typing import List, Optional

class WorkExperience(BaseModel):
    role: str = Field(description="Job title, e.g., 'Senior Software Engineer'")
    company: str = Field(description="Company name")
    duration: str = Field(description="Time period, e.g., 'Jan 2020 - Present'")
    technologies: List[str] = Field(description="Tech stack used in this specific role")
    key_achievements: List[str] = Field(description="Bullet points describing achievements")

class Project(BaseModel):
    name: str = Field(description="Name of the project")
    description: str = Field(description="Brief summary of what the project does")
    technologies: List[str] = Field(description="List of tools/languages used")
    url: Optional[str] = Field(description="Link to project if available", default=None)

class Education(BaseModel):
    degree: str = Field(description="Degree name, e.g., 'B.Sc. Computer Science'")
    institution: str = Field(description="University or College name")
    year: str = Field(description="Graduation year")

class ResumeSchema(BaseModel):
    full_name: str = Field(description="Candidate's full name")
    summary: str = Field(description="Professional summary or objective")
    email: str = Field(description="Email address")
    phone: str = Field(description="Phone number")
    skills: List[str] = Field(description="All technical skills listed")
    work_experience: List[WorkExperience] = Field(description="History of employment")
    projects: List[Project] = Field(description="Academic or personal projects")
    education: List[Education] = Field(description="Educational background")
    certifications: List[str] = Field(description="List of certifications")