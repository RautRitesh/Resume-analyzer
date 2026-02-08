from django.shortcuts import render, redirect
from .models import ResumeAnalysis
from django.contrib import messages
from django.contrib.auth.decorators import login_required
# --- FIX: Import the correct new functions ---
from utils.resume_analysis import extract_text_from_pdf, analyze_resume_compatibility
from utils.resume_parser import parse_resume_content

@login_required(login_url='login')
def dashboard(request):
    latest_analysis = request.user.resume_analysis.last()
    if latest_analysis:
        context = {
            "analysis": latest_analysis,
            "resume": latest_analysis.parsed_resume_data 
        }
        return render(request, "applicants/dashboard.html", context)
    else:
        return redirect('upload')

@login_required(login_url='login') 
def resumeanalysis(request):
    if request.method == "POST":
        job_title = request.POST.get("job_title")
        job_description = request.POST.get("job_description")
        resume_file = request.FILES.get("resume_file")

        if not job_description or not resume_file or not job_title:
            messages.error(request, "All fields are required")
            return redirect('upload')

        # 1. Create Object
        analysis = ResumeAnalysis.objects.create(
            user=request.user,
            job_title=job_title,
            job_description=job_description,
            resume_file=resume_file
        )

        try:
            # 2. Extract Text
            raw_text = extract_text_from_pdf(analysis.resume_file.path)
            
            # 3. Parse Resume (AI Extraction)
            print("Parsing Resume...")
            structured_data = parse_resume_content(raw_text)
            analysis.parsed_resume_data = structured_data
            
            # 4. Analyze (Comparison & Heuristics)
            print("Analyzing Compatibility...")
            # --- FIX: Call the correct function name ---
            results = analyze_resume_compatibility(structured_data, job_description)
            print(results)
            
            # 5. Save Results
            analysis.overall_match_score = results["overall_match_score"]
            analysis.section_match_score = results["section_match_score"]
            analysis.missing_keywords = results["missing_keywords"]
            analysis.improved_suggestion = results["improved_suggestion"]
            print(analysis.section_match_score)
            
            analysis.save()
            
            messages.success(request, "Analysis Successful!")
            return redirect('dashboard')
            
        except Exception as e:
            print(f"Error: {e}")
            # Don't delete immediately while debugging so you can see if it was created
            # analysis.delete() 
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('upload')
        
    else:
        return render(request, "applicants/upload.html")