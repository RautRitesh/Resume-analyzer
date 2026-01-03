from django.shortcuts import render,redirect

# Create your views here.
def dashboard(request):
    latest_analysis=request.user.resume_analyses.first()
    if latest_analysis and latest_analysis.resume_file:
        context={
            "analysis":latest_analysis
        }
        return render("applicants/dashboard.html",context)
    else:
        return redirect('upload')
    
def get_analysis(request):
    if request.method=="POST":
        ... 
    else:
        return render("applications/upload.html")