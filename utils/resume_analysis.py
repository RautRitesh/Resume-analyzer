import os 
import json
import re 
from django.conf import settings
from langchain_community.document_loaders import PDFPlumberLoader
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

LLM_FAST=ChatGroq(model="llama3-8b-8192",temperature=0)
LLM_SMART=ChatGroq(model="llama3-70b-8192",temperature=0.1)
EMBEDDINGS=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def extract_text_from_pdf(file_path):
    try:
        loader=PDFPlumberLoader(file_path)
        pages=loader.load()
        return "\n\n".join([p.page_content for p in pages])
    except Exception as e:
        print(f"An error occured while loading pdf:{e}")
        return ""
    
def segment_resume(text):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n","\n"," ",""]
        
    )
    return splitter.create_documents([text])

def analyze_resume_compatiblilty(file_path,job_description):
    full_text=extract_text_from_pdf(file_path)
    if not full_text:
        return {"error":"Could not read resume"}
    chunks=segment_resume(full_text)
    vector_store=FAISS.from_documents(chunks,EMBEDDINGS)
    retriever=vector_store.as_retriever(search_kwargs={"k":4})
    
    req_prompt=f"""
    You are an expert technical recruiter. Extract the top 8-10 hard skills and key requirements from this job description.
    Return ONLY a list of strings. Do not use JSON. Just one skill per line.
    
    Job Description:
    {job_description[:4000]}
    """
    requirements=[]
    try:
        raw_reqs=LLM_FAST.invoke(req_prompt).content
        lines=raw_reqs.strip().split('\n')
        for line in lines:
            clean=re.sub('^[\d\.\-\*•]+\s*', '', line).strip() # cleaning lines form special character and . 
            if len(clean)>2 and len(clean) < 50  and "Here are " not in clean:
                requirements.append(clean)
    except Exception as e:
        print(f"Extraction failed:{e}")
        
    if not requirements:
        requirements=[w for w in job_description.split() if len(w)>6][:10]
        
    retrieved_evidence={}
    missing_keywords=[]
    hits=0
    for req in requirements:
        docs=retriever.invoke(req)
        context="\n".join([d.page_content for d in docs])
        verify_prompt=f"""
        Does the candidate have experience with "{req}"?
        Context from Resume:
        {context}
        
        Answer EXACTLY in this format:
        YES: [Quote short evidence snippet]
        or
        NO
        """
        verdict=LLM_FAST.invoke(verify_prompt).content
        if verdict.strip().upper().startswith("YES"):
            hits+=1
            evidence=verdict.replace("YES:","").replace("YES","").strip()
            retrieved_evidence[req]=evidence[:150]+"..." if len(evidence)>150 else evidence
        else:
            missing_keywords.append(req)       
            
    overall_match_score=round(hits/max(len(requirements,1))*100,1) 
    summary_prompt=f"""
    candidate_score"{overall_match_score}/100.
    Missing Skills:{','.join(missing_keywords[:5])}.  
    Write a 2-sentence executive summary  of their fit.  
    """
    analysis_summary=LLM_SMART.invoke(summary_prompt).content
    suggestion_prompt=f"""
    The candidate is missing these skills: {', '.join(missing_keywords[:3])}.
    Generate 3 distinct, professional bullet points they could add to their resume to address these gaps (assuming they have the skill). 
    Return ONLY the bullet points, one per line.
    """
    try:
        sugg_raw=LLM_SMART.invoke(suggestion_prompt).content
        improved_suggestion=[line.strip().replace("- ","") for line in  sugg_raw.split('\n') if line.strip()]  
    except Exception as e:
        improved_suggestion=[f"Highlight experience with {m}" for m in missing_keywords[:3]]
        
        
    section_match_score={
        "Skills":min(100,overall_match_score + 10),
        "Experience":overall_match_score,
        "Education":100.0 if overall_match_score > 50 else 80.0
    }
    
    return {
        "overall_match_score":overall_match_score,
        "section_match_score":section_match_score,
        "retrieved_evidence": retrieved_evidence,
        "missing_keywords": missing_keywords,
        "analysis_summary": analysis_summary,
        "improved_suggestion": improved_suggestion
    }