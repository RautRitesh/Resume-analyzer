import os
import json
import re
from langchain_community.document_loaders import PDFPlumberLoader
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_experimental.text_splitter import SemanticChunker
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage

# Initialize AI Components
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("WARNING: GROQ_API_KEY not found.")

# Models
LLM_FAST = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=api_key)
LLM_SMART = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3, api_key=api_key)
EMBEDDINGS = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def clean_json_output(text):
    """
    Robustly extracts JSON from a string, handling Markdown and extra text.
    """
    if not text:
        return "{}"
    
    text = text.replace("```json", "").replace("```", "").strip()
    
    # 2. Find the start { and end } to ignore "Here is your JSON:" prefix
    start_index = text.find("{")
    end_index = text.rfind("}")
    
    if start_index != -1 and end_index != -1:
        text = text[start_index : end_index + 1]
    
    return text

def extract_text_from_pdf(file_path):
    try:
        loader = PDFPlumberLoader(file_path)
        pages = loader.load()
        text = "\n\n".join([p.page_content for p in pages])
        return text
    except Exception as e:
        print(f"Error loading PDF: {e}")
        return ""

def calculate_semantic_score(resume_text, job_description):
    """
    Phase 2.A: Semantic Match (Fixes float32 error)
    """
    try:
        if not resume_text or not job_description:
            return 0.0, []

        text_splitter = SemanticChunker(EMBEDDINGS)
        chunks = text_splitter.create_documents([resume_text])
        if not chunks:
            chunks = [Document(page_content=resume_text)]

        vector_store = FAISS.from_documents(chunks, EMBEDDINGS)
        results = vector_store.similarity_search_with_score(job_description, k=3)
        
        total_score = 0.0
        count = 0
        
        for res in results:
            # Handle (Document, score) or (score, Document) safely
            score = 1.0
            if isinstance(res, tuple):
                for item in res:
                    if isinstance(item, (int, float)):
                        score = float(item)  # <--- CRITICAL FIX: Convert float32 to float
            
            total_score += score
            count += 1
        
        if count == 0:
            return 0.0, []

        avg_distance = total_score / count
        # Normalize: L2 distance usually 0.5 to 1.5. 
        semantic_score = max(0, min(100, (1 / (1 + avg_distance * 0.5)) * 100))
        
        return float(round(semantic_score, 1)), results  # <--- Ensure float return
    except Exception as e:
        print(f"Semantic Error: {e}")
        return 50.0, []

def calculate_keyword_score(resume_text, job_description):
    """
    Phase 2.B: Keyword Match
    """
    prompt = f"""
    Act as a strict ATS system. Extract the top 15 most critical technical 'Hard Skills' from the JD.
    Return ONLY a valid JSON list of strings.
    JD: {job_description[:4000]}
    """
    try:
        # Use HumanMessage to prevent string errors
        response = LLM_FAST.invoke([HumanMessage(content=prompt)]).content
        clean_json = clean_json_output(response)
        keywords = json.loads(clean_json)
        if not isinstance(keywords, list): keywords = []
    except Exception as e:
        print(f"Keyword Error: {e}")
        keywords = []

    if not keywords: return 0.0, [], []

    found = []
    missing = []
    
    for kw in keywords:
        pattern = r"(?i)\b" + re.escape(kw) + r"\b"
        if re.search(pattern, resume_text):
            found.append(kw)
        else:
            missing.append(kw)

    score = (len(found) / len(keywords)) * 100
    return float(round(score, 1)), found, missing

def calculate_impact_score(resume_text):
    """
    Phase 2.C: Impact Analysis (Fixes JSON error)
    """
    prompt = f"""
    You are a Senior Technical Recruiter. Review the 'Experience' and 'Projects' sections.
    
    Task:
    1. Identify the 3 weakest bullet points (lack of metrics/action verbs).
    2. Identify the Context (Project Name or Job Title).
    3. Rewrite them.
    
    Resume Text:
    {resume_text[:4000]}
    
    Return a valid JSON object with this EXACT structure:
    {{
        "impact_score": <int 0-100>,
        "summary_verdict": "<short critique>",
        "weak_points": [
            {{
                "context": "<Project Name>",
                "original": "<original text>",
                "rewrite": "<improved text>",
                "issue": "<issue description>"
            }}
        ]
    }}
    """
    
    try:
        response = LLM_SMART.invoke([HumanMessage(content=prompt)]).content
        
        # USE THE NEW CLEANER FUNCTION
        clean_json = clean_json_output(response)
        
        data = json.loads(clean_json)
        return float(data.get("impact_score", 50)), data
    except Exception as e:
        print(f"Impact Error: {e}")
        return 50.0, {"summary_verdict": "Analysis unavailable", "weak_points": []}

def analyze_resume_compatiblilty(file_path, job_description):
    # 1. Ingestion
    full_text = extract_text_from_pdf(file_path)
    if not full_text:
        return {"error": "Could not read resume"}

    # 2. Parallel Scoring
    sem_score, sem_results = calculate_semantic_score(full_text, job_description)
    key_score, found, missing = calculate_keyword_score(full_text, job_description)
    imp_score, impact_data = calculate_impact_score(full_text)
    
    # 3. Final Score
    total_score = (0.4 * sem_score) + (0.4 * key_score) + (0.2 * imp_score)
    
    # 4. Evidence
    retrieved_evidence = {}
    if sem_results:
        for i, res in enumerate(sem_results):
            # Safe tuple unpacking
            doc = res[0] if isinstance(res, tuple) else res
            content = getattr(doc, 'page_content', str(doc))[:200]
            retrieved_evidence[f"Match {i+1}"] = content + "..."

    return {
        "overall_match_score": float(round(total_score, 1)), # Ensure float
        "section_match_score": {
            "Semantic_Match": sem_score,
            "Keyword_Match": key_score,
            "Impact_Score": imp_score
        },
        "retrieved_evidence": retrieved_evidence,
        "missing_keywords": missing,
        "analysis_summary": impact_data.get("summary_verdict", ""),
        "improved_suggestion": impact_data.get("weak_points", [])
    }