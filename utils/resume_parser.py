# utils/resume_parser.py
import os
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from .structures import ResumeSchema  # Importing the blueprint we just created

# Initialize LLM
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY environment variable is not set")

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=api_key)

# Configure the LLM to strictly follow our Pydantic schema
structured_llm = llm.with_structured_output(ResumeSchema)

def parse_resume_content(resume_text: str) -> dict:
    """
    Parses raw PDF text into a structured JSON dictionary.
    """
    
    system_prompt = """
    You are an expert Resume Parser. 
    Extract details from the resume text below and structure them strictly.
    
    Rules:
    1. Normalize skills: Convert 'Reactjs' to 'React.js', 'Py' to 'Python'.
    2. If a section is missing, return an empty list.
    3. Do not invent information. If it's not there, leave it blank.
    4. For 'technologies' in Work Experience, infer them from the bullet points if not explicitly listed.
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{resume_text}"),
    ])

    chain = prompt | structured_llm

    try:
        # Invoke the chain
        print("Parsing resume with AI...")
        result = chain.invoke({"resume_text": resume_text})
        
        # Convert Pydantic object back to standard Python Dictionary
        return result.dict()
        
    except Exception as e:
        print(f"Parsing Error: {e}")
        return {}