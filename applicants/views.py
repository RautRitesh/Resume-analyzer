from django.shortcuts import render,redirect
from .models import ResumeAnalysis
from django.contrib import auth,messages
from utils.resume_analysis import analyze_resume_compatiblilty
from django.contrib.auth.decorators import login_required
# Create your views here.
@login_required(login_url='login')
def dashboard(request):
    latest_analysis=request.user.resume_analysis.first()
    if latest_analysis and latest_analysis.resume_file:
        context={
            "analysis":latest_analysis
        }
        return render(request,"applicants/dashboard.html",context)
    else:
        return redirect('upload')
   
@login_required(login_url='login') 
def resumeanalysis(request):
    if request.method=="POST":
        job_title=request.POST.get("job_title")
        job_description=request.POST.get("job_description")
        resume_file=request.FILES.get("resume_file")
        if not job_description or not resume_file or not job_title:
            messages.error(request,"Job descriptions and resume file and all other contents are required")
            return redirect('upload')
        else:
            analysis=ResumeAnalysis.objects.create(
                user=request.user ,
                job_title=job_title,
                job_description=job_description,
                resume_file=resume_file
            )
            try:
                results=analyze_resume_compatiblilty(analysis.resume_file.path,job_description)
                analysis.overall_match_score=results["overall_match_score"]
                analysis.section_match_score=results["section_match_score"]
                analysis.retrieved_evidence=results["retrieved_evidence"]
                analysis.missing_keywords=results["missing_keywords"]
                analysis.analysis_summary=results["analysis_summary"]
                analysis.improved_suggestion=results["improved_suggestion"]
                analysis.save()
                messages.success(request,"Analysis Sucessfull")
                return redirect('home')
            except Exception as e:
                analysis.delete()
                print(f"Analysis error{e}")
                messages.error(request,"An error occured during analysis")
                return redirect('upload')
        
    else:
        return render(request,"applicants/upload.html")