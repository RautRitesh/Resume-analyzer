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

def analyze_resume_compatiblilty(file_path,job_description):
    ...