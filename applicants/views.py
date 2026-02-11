from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import ResumeAnalysis, InterviewSession
# Importing your existing utility functions
from utils.resume_analysis import extract_text_from_pdf, analyze_resume_compatibility, parse_job_description
from utils.resume_parser import parse_resume_content
# Import the new agent builder from Step 1
from utils.interview_agent import build_interview_graph
from langchain_core.messages import HumanMessage, AIMessage
import json

@login_required(login_url='login')
def dashboard(request):
    """
    Existing dashboard view to show the latest analysis.
    """
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
    """
    Handles Resume Upload, Analysis, and triggers Interview if qualified.
    """
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
            results = analyze_resume_compatibility(structured_data, analysis.job_description)
            
            # 5. Save Results
            analysis.overall_match_score = results["overall_match_score"]
            analysis.section_match_score = results["section_match_score"]
            analysis.missing_keywords = results["missing_keywords"]
            analysis.improved_suggestion = results["improved_suggestion"]
            
            analysis.save()

            # --- NEW: Check Score & Trigger Simulation ---
            if analysis.overall_match_score >= 70.0:
                # Create an Interview Session
                InterviewSession.objects.create(
                    user=request.user,
                    analysis=analysis,
                    chat_history=[], # Start empty
                    current_stage="hr_agent"
                )
                messages.success(request, f"Great Score ({analysis.overall_match_score}%)! You've qualified for the AI Interview.")
                return redirect('dashboard')
            
            messages.success(request, "Analysis Successful!")
            return redirect('dashboard')
            
        except Exception as e:
            print(f"Error: {e}")
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('upload')
        
    else:
        return render(request, "applicants/upload.html")

# ... imports ...

@login_required(login_url='login')
def interview_room(request, analysis_id):
    analysis = get_object_or_404(ResumeAnalysis, id=analysis_id, user=request.user)
    
    if analysis.overall_match_score < 40.0:
        messages.error(request, "Interview locked. Score must be >= 70%.")
        return redirect('dashboard')

    # Get or Create Session
    session, created = InterviewSession.objects.get_or_create(
        analysis=analysis,
        defaults={
            'user': request.user,
            'chat_history': [],
            'current_stage': 'hr_agent'
        }
    )

    # --- NEW: TRIGGER AGENT GREETING IF HISTORY IS EMPTY ---
    if not session.chat_history:
        # 1. Prepare State with a hidden system trigger
        resume_data = analysis.parsed_resume_data or {}
        
        # We send a hidden message "Start Interview" to wake up the agent
        # But we WON'T save this "Start Interview" text to the DB, so the user only sees the greeting.
        lc_messages = [HumanMessage(content="Hello, I am ready for the interview. Please introduce yourself.")]

        initial_state = {
            "messages": lc_messages,
            "full_name": resume_data.get("full_name", "Candidate"),
            "job_description": analysis.job_description,
            "workexperience": resume_data.get("work_experience", []),
            "projects": resume_data.get("projects", [])
        }

        # 2. Run Graph
        app = build_interview_graph()
        result_state = app.invoke(initial_state)
        ai_response = result_state["messages"][-1].content

        # 3. Save ONLY the AI's greeting to DB
        session.chat_history.append({"role": "ai", "content": ai_response})
        session.save()
    
    return render(request, "applicants/interview_room.html", {
        "analysis": analysis,
        "chat_history": session.chat_history
    })  
    
@csrf_exempt
@login_required(login_url='login')
def chat_api(request, analysis_id):
    """
    API to handle chat messages.
    Receives user message -> Updates State -> Runs Agent -> Returns AI Response.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_message = data.get("message")
            
            analysis = get_object_or_404(ResumeAnalysis, id=analysis_id, user=request.user)
            session = get_object_or_404(InterviewSession, analysis=analysis)
            
            # 1. Reconstruct Chat History for LangChain
            lc_messages = []
            for msg in session.chat_history:
                if msg['role'] == 'user':
                    lc_messages.append(HumanMessage(content=msg['content']))
                else:
                    lc_messages.append(AIMessage(content=msg['content']))
            
            # Add new user message to the history used for the agent
            lc_messages.append(HumanMessage(content=user_message))
            
            # 2. Prepare State for the Graph
            resume_data = analysis.parsed_resume_data or {}
            
            initial_state = {
                "messages": lc_messages,
                "full_name": resume_data.get("full_name", "Candidate"),
                "job_description": analysis.job_description,
                "workexperience": resume_data.get("work_experience", []),
                "projects": resume_data.get("projects", [])
            }
            
            # 3. Run Graph
            # This calls the supervisor -> specific agent -> generates ONE response -> END
            app = build_interview_graph()
            result_state = app.invoke(initial_state)
            
            # 4. Get AI Response (Last message in the returned state)
            ai_message_obj = result_state["messages"][-1]
            ai_response = ai_message_obj.content
            
            # 5. Update Database with User Input and AI Response
            session.chat_history.append({"role": "user", "content": user_message})
            session.chat_history.append({"role": "ai", "content": ai_response})
            session.save()
            
            return JsonResponse({"response": ai_response})

        except Exception as e:
            print(f"Chat Error: {e}")
            return JsonResponse({"error": str(e)}, status=500)
        
    return JsonResponse({"error": "Invalid request"}, status=400)