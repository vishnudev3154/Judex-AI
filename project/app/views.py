import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count
from .models import *

# --- Import Models ---
from .models import (
    Case,
    UserProfile, 
    CaseSubmission, 
    ChatSession, 
    ChatMessage, 
    LegalRepresentation, 
    CaseChat
)

# --- Import AI Helpers ---
# Ensure app/gemini_chat.py has both ask_ai and get_virtual_judge_verdict
from .gemini_chat import ask_ai, get_virtual_judge_verdict
from .ai_helper import analyze_case_file


# ==========================================
# 1. PUBLIC & AUTHENTICATION
# ==========================================

def home(request):
    return render(request, "index.html")

def register_client(request):
    if request.method == 'POST':
        fullname = request.POST.get('fullname')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return redirect('register_client')
        
        if User.objects.filter(username=email).exists():
            messages.error(request, "Email already registered!")
            return redirect('register_client')

        user = User.objects.create_user(username=email, email=email, password=password)
        user.first_name = fullname
        user.save()

        UserProfile.objects.create(user=user, fullname=fullname, is_lawyer=False)

        login(request, user)
        messages.success(request, "Client Account Created Successfully!")
        return redirect('user_dashboard') # Redirect to Client Dashboard

    return render(request, 'register_client.html')

def register_lawyer(request):
    if request.method == 'POST':
        fullname = request.POST.get('fullname')
        bar_id = request.POST.get('bar_id')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return redirect('register_lawyer')
        
        if User.objects.filter(username=email).exists():
            messages.error(request, "Email already registered!")
            return redirect('register_lawyer')

        user = User.objects.create_user(username=email, email=email, password=password)
        user.first_name = fullname
        user.save()

        UserProfile.objects.create(user=user, fullname=fullname, is_lawyer=True, bar_id=bar_id)

        login(request, user)
        messages.success(request, "Lawyer Account Created Successfully!")
        return redirect('lawyer_dashboard')

    return render(request, 'register_lawyer.html')

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages


def login_admin(request):
    """Strictly for System Administrators"""
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)

        if user is not None and user.is_staff:
            if not user.is_active:
                messages.error(request, "Admin account deactivated.")
                return render(request, 'login_admin.html')
            
            login(request, user)
            return redirect('admin_dashboard')
        else:
            # Generic error to prevent account discovery
            messages.error(request, "Invalid administrator credentials.")

    return render(request, 'login_admin.html')




def login_view(request):
    """Strictly for Clients and Admins only"""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        
        # Check if user exists and is active
        if user is not None and user.is_active:
            # Check if this user is a lawyer
            is_lawyer = hasattr(user, 'userprofile') and user.userprofile.is_lawyer
            
            # If they ARE a lawyer and NOT staff, treat them as "Invalid credentials"
            if is_lawyer and not user.is_staff:
                messages.error(request, "Invalid username or password")
                return render(request, "login.html")
            
            # Otherwise, log them in (Client or Admin)
            login(request, user)
            if user.is_staff:
                return redirect("admin_dashboard")
            else:
                return redirect("user_dashboard")
        
        elif user is not None and not user.is_active:
            messages.error(request, "Your account has been BLOCKED. Contact admin.")
        else:
            messages.error(request, "Invalid username or password")

    return render(request, "login.html")

def login_lawyer(request):
    """Strictly for Lawyers only"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_active:
            # Check if the user is actually a lawyer
            if hasattr(user, 'userprofile') and user.userprofile.is_lawyer:
                login(request, user)
                messages.success(request, f"Welcome back, Adv. {user.first_name}")
                return redirect('lawyer_dashboard')
            else:
                # If they are a Client or Admin, don't tell them; just show invalid
                messages.error(request, "Invalid username or password")
        
        elif user is not None and not user.is_active:
            messages.error(request, "Lawyer account blocked. Contact Admin.")
        else:
            messages.error(request, "Invalid username or password")

    return render(request, 'lowyer/login_lawyer.html')

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home")


# ==========================================
# 2. CLIENT DASHBOARD & CASE MANAGEMENT
# ==========================================

@login_required
def user_dashboard(request):
    """Client Dashboard"""
    if request.user.is_staff:
        return redirect('admin_dashboard')
    
    user = request.user
    total_cases = CaseSubmission.objects.filter(user=user).count()
    completed_cases = CaseSubmission.objects.filter(user=user, is_reviewed=True).count()
    recent_cases = CaseSubmission.objects.filter(user=user).order_by('-created_at')[:5]
    recent_chats = ChatSession.objects.filter(user=user).order_by('-updated_at')[:3]

    context = {
        "user_name": user.first_name if user.first_name else user.username,
        "total_cases": total_cases,
        "completed_cases": completed_cases,
        "recent_cases": recent_cases,
        "recent_chats": recent_chats,
    }
    # Ensure template name matches what you have (userpage.html or client/dashboard.html)
    return render(request, "userpage.html", context) 

@login_required
def my_cases_view(request):
    cases = CaseSubmission.objects.filter(user=request.user).order_by('-created_at')
    
    # This part is critical for the modal dropdown to work
    accepted_lawyers = LegalRepresentation.objects.filter(
        client=request.user, 
        status='Accepted'
    ).select_related('lawyer')

    return render(request, "my_cases.html", {
        "cases": cases, 
        "accepted_lawyers": accepted_lawyers
    })


@login_required
def create_case_view(request):
    if request.method == "POST":
        title = request.POST.get('title')
        description = request.POST.get('description')
        uploaded_file = request.FILES.get('document')

        new_case = CaseSubmission.objects.create(
            user=request.user,
            case_title=title,
            case_text=description,
            document=uploaded_file,
            is_reviewed=False
        )

        # Trigger AI Analysis
        analysis = analyze_case_file(new_case)
        new_case.analysis_result = analysis
        new_case.is_reviewed = True
        new_case.save()

        return redirect('my_cases')

    return render(request, "create_case.html")

@login_required
def case_analysis_view(request, case_id):
    if request.user.is_staff:
        case = get_object_or_404(CaseSubmission, id=case_id)
    else:
        case = get_object_or_404(CaseSubmission, id=case_id, user=request.user)
    return render(request, "case_analysis.html", {"case": case})


# ==========================================
# 3. LAWYER DASHBOARD & ACTIONS
# ==========================================

@login_required
def lawyer_dashboard(request):
    """Lawyer Dashboard"""
    if not hasattr(request.user, 'userprofile') or not request.user.userprofile.is_lawyer:
        messages.error(request, "Access Denied: Lawyer area only.")
        return redirect('home')

    # Fetch cases assigned to this lawyer via LegalRepresentation
    # You can also pass CaseSubmission if needed, but LegalRepresentation is the primary 'Client' link
    return render(request, 'lowyer/lawyer_dashboard.html')

@login_required
def update_case_status(request, case_id, status):
    """Lawyer accepts or rejects a client request"""
    case = get_object_or_404(LegalRepresentation, id=case_id)
    
    if request.user == case.lawyer:
        case.status = status
        case.save()
        messages.success(request, f"Case {status} successfully!")
    else:
        messages.error(request, "Unauthorized action.")
        
    return redirect('lawyer_dashboard')


# ==========================================
# 4. CLIENT-LAWYER INTERACTION
# ==========================================


@login_required
def find_lawyer(request):
    
    already_requested_ids = LegalRepresentation.objects.filter(client=request.user).values_list('lawyer__id', flat=True)

   
    lawyers = UserProfile.objects.filter(is_lawyer=True).exclude(user__id__in=already_requested_ids)

    return render(request, 'client/find_lawyer.html', {'lawyers': lawyers})

@login_required
def send_hiring_request(request, lawyer_id):
    """Client sends a request to a lawyer"""
    lawyer_profile = get_object_or_404(UserProfile, user__id=lawyer_id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        desc = request.POST.get('description')
        fir = request.FILES.get('fir')

        LegalRepresentation.objects.create(
            client=request.user,
            lawyer=lawyer_profile.user,
            case_title=title,
            case_description=desc,
            fir_document=fir
        )
        messages.success(request, "Request sent to lawyer! Wait for them to accept.")
        return redirect('find_lawyer')

    return render(request, 'client/hire_form.html', {'lawyer': lawyer_profile})


@login_required
def client_messages_view(request):
    """Dedicated messaging page for lawyers to see all client chats"""
    # Get all cases assigned to this lawyer
    assigned_cases = LegalRepresentation.objects.filter(lawyer=request.user, status='Accepted').select_related('client')
    
    context = {
        'cases': assigned_cases,
    }
    return render(request, 'lowyer/client_messages.html', context)




@login_required
def my_legal_requests(request):
    """Page to see status of requests sent to lawyers (Pending, Accepted, Rejected)"""
    # Fetch all requests made by the logged-in client
    requests = LegalRepresentation.objects.filter(client=request.user).select_related('lawyer').order_by('-created_at')
    
    return render(request, 'client/my_legal_requests.html', {'requests': requests})

    
# app/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import CaseSubmission
from .ai_helper import analyze_case_file # Assuming this is your AI function

@login_required
def create_case_view(request):
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        document = request.FILES.get("document")

        if not title or not description:
            messages.error(request, "Please provide both a title and description.")
            return render(request, "create_case.html")

        # Saving here triggers the auto-generation of the Case Number in models.py
        new_case = CaseSubmission.objects.create(
            user=request.user,
            case_title=title,
            case_text=description,
            document=document
        )

        # Optional: Run AI Analysis immediately
        try:
            analysis = analyze_case_file(new_case)
            new_case.analysis_result = analysis
            new_case.is_reviewed = True
            new_case.save()
            messages.success(request, f"Case {new_case.case_number} registered and analyzed!")
        except Exception:
            messages.warning(request, f"Case {new_case.case_number} registered. AI analysis is processing.")

        return redirect("my_cases")

    return render(request, "client/register_case.html")


@login_required
def case_chat_view(request, case_id):
    """Human Chat between Client and Lawyer"""
    case = get_object_or_404(LegalRepresentation, id=case_id)

    if request.user != case.client and request.user != case.lawyer:
        return redirect('home')

    if request.method == 'POST':
        msg_text = request.POST.get('message')
        msg_file = request.FILES.get('file')

        if msg_text or msg_file:
            CaseChat.objects.create(
                case=case,
                sender=request.user,
                message=msg_text,
                file=msg_file
            )
            return redirect('case_chat', case_id=case.id)

    return render(request, 'client/case_chat.html', {'case': case})

# app/views.py

@login_required
def load_client_case_to_court(request, case_id):
    """Pulls the client's original submission and sets it as the Court Context"""
    if request.method == 'POST':
        # 'case_id' here refers to the LegalRepresentation ID
        legal_case = get_object_or_404(LegalRepresentation, id=case_id)
        
        # 1. Find the AI Case Submission linked to this
        # Based on your flow, we find the message that contains the forwarded data
        forwarded_msg = CaseChat.objects.filter(case=legal_case, message__contains="FORWARDED CASE FILE").last()

        if not forwarded_msg:
            messages.error(request, "No forwarded case file found to load.")
            return redirect('virtual_court_view', case_id=case_id)

        # 2. Get or Create the Court Session
        court, created = VirtualCourt.objects.get_or_create(case_connection=legal_case)
        
        # 3. Inject the client's text as the Judge's foundation
        court.title = f"Debate: {legal_case.case_title}"
        court.description = forwarded_msg.message # This contains the client's case text
        court.save()

        messages.success(request, "Client case file loaded into Court successfully. You may now start the debate.")
        return redirect('virtual_court_view', case_id=case_id)

    return redirect('lawyer_dashboard')


# ==========================================
# 5. AI FEATURES (Chatbot & Virtual Court)
# ==========================================

@login_required
def chat_view(request):
    """AI Legal Assistant Chatbot"""
    if request.method == "GET":
        sessions = ChatSession.objects.filter(user=request.user).order_by('-updated_at')
        return render(request, 'chat.html', {'sessions': sessions})

    if request.method == "POST":
        try:
            user_text = request.POST.get('message', '')
            session_id = request.POST.get('session_id')
            uploaded_file = request.FILES.get('file')

            if not user_text and not uploaded_file:
                return JsonResponse({'error': 'Empty message'}, status=400)

            # Get or Create Session
            if session_id and session_id != 'null':
                session = ChatSession.objects.get(id=session_id, user=request.user)
            else:
                title_text = f"File: {uploaded_file.name}" if uploaded_file else user_text[:30]
                session = ChatSession.objects.create(user=request.user, title=title_text)

            # Save User Message
            display_text = user_text
            if uploaded_file:
                display_text += f"\n[Attached: {uploaded_file.name}]"
            
            ChatMessage.objects.create(session=session, text=display_text, is_user=True)
            
            # Get AI Reply
            ai_reply = ask_ai(user_text, uploaded_file)

            # Optional: Save as Case Submission if file exists
            if uploaded_file:
                CaseSubmission.objects.create(
                    user=request.user,
                    case_title=f"Chat Upload: {uploaded_file.name}",
                    case_text=user_text or "Uploaded via Chat",
                    document=uploaded_file,
                    analysis_result=ai_reply,
                    is_reviewed=True
                )

            # Save AI Message
            ChatMessage.objects.create(session=session, text=ai_reply, is_user=False)
            session.save()

            return JsonResponse({'reply': ai_reply, 'session_id': session.id, 'session_title': session.title})
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

# app/views.py
@login_required
def virtual_court(request):
    # Check if the user is a lawyer
    is_lawyer = hasattr(request.user, 'userprofile') and request.user.userprofile.is_lawyer

    # 1. AJAX: Handle the Debate Argument (LAWYERS ONLY)
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if not is_lawyer:
            return JsonResponse({'error': 'Only lawyers can present arguments.'}, status=403)

        import json
        data = json.loads(request.body)
        user_argument = data.get('argument')
        
        case_context = request.session.get('vc_case_details', 'General Legal Dispute')
        evidence_text = request.session.get('vc_evidence', 'No documents submitted.')
        
        ai_result = get_virtual_judge_verdict(user_argument, case_context, evidence_text)
        return JsonResponse(ai_result)

    # 2. POST FORM: Start the Case (LAWYERS ONLY)
    if request.method == 'POST' and 'start_case' in request.POST:
        if not is_lawyer:
            messages.error(request, "Only lawyers can initialize cases.")
            return redirect('virtual_court')

        case_title = request.POST.get('case_title')
        case_desc = request.POST.get('case_desc')
        uploaded_file = request.FILES.get('case_file')
        
        file_text = ""
        if uploaded_file and uploaded_file.name.endswith('.pdf'):
            try:
                import PyPDF2
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                for page in pdf_reader.pages[:5]:
                    file_text += page.extract_text() + "\n"
            except Exception:
                file_text = "Error reading file."

        request.session['vc_case_title'] = case_title
        request.session['vc_case_details'] = case_desc
        request.session['vc_evidence'] = file_text
        request.session['vc_active'] = True
        
        return redirect('virtual_court')

    # 3. GET: Show the Page
    is_active = request.session.get('vc_active', False)
    
    context = {
        'is_active': is_active,
        'is_lawyer': is_lawyer, # Pass this to template
        'case_title': request.session.get('vc_case_title', 'No Active Case'),
        'case_desc': request.session.get('vc_case_details', 'Waiting for lawyer to initialize...'),
        'has_file': bool(request.session.get('vc_evidence', ''))
    }
    return render(request, 'lowyer/virtual_court.html', context)


# app/views.py

from .models import LegalRepresentation, VirtualCourt, CourtDebateLog

@login_required
def virtual_court_view(request, case_id):
    # 1. Get the connection (Ensure user is allowed to see it)
    legal_case = get_object_or_404(LegalRepresentation, id=case_id)
    
    # Security: Only the specific Client or Lawyer can access
    if request.user != legal_case.client and request.user != legal_case.lawyer:
        messages.error(request, "Access Denied.")
        return redirect('user_dashboard')

    is_lawyer = (request.user == legal_case.lawyer)

    # 2. Get or Initialize the Virtual Court Session
    court_session, created = VirtualCourt.objects.get_or_create(
        case_connection=legal_case,
        defaults={
            'title': legal_case.case_title,
            'description': legal_case.case_description,
            'evidence_text': "Standard case file loaded."
        }
    )

    # 3. AJAX: Handle New Argument (Lawyer Only)
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if not is_lawyer:
            return JsonResponse({'error': 'Unauthorized'}, status=403)

        import json
        data = json.loads(request.body)
        user_argument = data.get('argument')

        # AI Logic
        ai_result = get_virtual_judge_verdict(
            user_argument, 
            court_session.description, 
            court_session.evidence_text
        )

        # Save to Database
        CourtDebateLog.objects.create(
            court=court_session,
            prosecutor_arg=user_argument,
            defense_arg=ai_result['defense_argument'],
            score_after=ai_result['score']
        )

        # Update Current Score
        court_session.current_score = ai_result['score']
        court_session.save()

        return JsonResponse(ai_result)

    # 4. Handle "Reset/Initialize" Form (Lawyer Only)
    if request.method == 'POST' and 'update_details' in request.POST:
        if is_lawyer:
            court_session.title = request.POST.get('case_title')
            court_session.description = request.POST.get('case_desc')
            
            # File Upload Logic (Extract Text)
            uploaded_file = request.FILES.get('case_file')
            if uploaded_file and uploaded_file.name.endswith('.pdf'):
                try:
                    import PyPDF2
                    pdf_reader = PyPDF2.PdfReader(uploaded_file)
                    text = ""
                    for page in pdf_reader.pages[:5]: text += page.extract_text()
                    court_session.evidence_text = text
                except: pass
            
            # Clear old logs if re-initializing
            court_session.logs.all().delete()
            court_session.current_score = 50
            court_session.save()
            messages.success(request, "Court Session Initialized!")
        return redirect('virtual_court_view', case_id=case_id)

    # 5. Fetch Logs for Template
    logs = court_session.logs.all().order_by('timestamp')

    context = {
        'court': court_session,
        'logs': logs,
        'is_lawyer': is_lawyer,
        'legal_case': legal_case
    }
    return render(request, 'lowyer/virtual_court.html', context)

## Add this to the bottom of app/views.py

@login_required
def api_get_case_messages(request, case_id):
    """Fetch chat history for the side panel (JSON)"""
    case = get_object_or_404(LegalRepresentation, id=case_id)
    if request.user != case.client and request.user != case.lawyer:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    messages = CaseChat.objects.filter(case=case).order_by('timestamp')
    data = [{
        'sender': msg.sender.first_name,
        'is_me': (msg.sender == request.user),
        'text': msg.message,
        'time': msg.timestamp.strftime("%H:%M")
    } for msg in messages]
    
    return JsonResponse({'messages': data})

@login_required
def api_send_case_message(request, case_id):
    """Send a message from the side panel (JSON)"""
    if request.method == 'POST':
        case = get_object_or_404(LegalRepresentation, id=case_id)
        import json
        data = json.loads(request.body)
        msg_text = data.get('message')
        
        if msg_text:
            CaseChat.objects.create(
                case=case,
                sender=request.user,
                message=msg_text
            )
            return JsonResponse({'status': 'ok'})
            
    return JsonResponse({'error': 'Invalid request'}, status=400)

# app/views.py

 # app/views.py

@login_required
def share_court_transcript(request, case_id):
    """Compiles the entire Virtual Court debate and sends it to the Client."""
    if request.method == 'POST':
        case = get_object_or_404(LegalRepresentation, id=case_id)
        
        # Security: Only the lawyer can do this
        if request.user != case.lawyer:
            return redirect('virtual_court_view', case_id=case.id)

        # 1. Get the Court Session
        try:
            court = VirtualCourt.objects.get(case_connection=case)
            logs = CourtDebateLog.objects.filter(court=court).order_by('timestamp')
        except VirtualCourt.DoesNotExist:
            messages.error(request, "No court session found.")
            return redirect('virtual_court_view', case_id=case.id)

        if not logs.exists():
            messages.warning(request, "No arguments to share yet.")
            return redirect('virtual_court_view', case_id=case.id)

        # 2. Build the Transcript Text
        transcript = "📜 **OFFICIAL COURT TRANSCRIPT**\n"
        transcript += f"Case: {case.case_title}\n"
        transcript += f"Date: {timezone.now().strftime('%Y-%m-%d')}\n"
        transcript += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        for i, log in enumerate(logs, 1):
            transcript += f"**turn {i}: Prosecution (You)**\n"
            transcript += f"{log.prosecutor_arg}\n\n"
            transcript += f"**turn {i}: Defense (AI)**\n"
            transcript += f"{log.defense_arg}\n"
            transcript += "----------------------------------------\n\n"

        transcript += f"**Current Score:** {court.current_score}/100"

        # 3. Send to Client Chat
        CaseChat.objects.create(
            case=case,
            sender=request.user,
            message=transcript
        )

        messages.success(request, "Full transcript forwarded to client successfully!")
        return redirect('virtual_court_view', case_id=case.id)

    return redirect('home')



    # app/views.py

@login_required
def forward_case_to_lawyer(request):
    """Takes an AI-analyzed Case and sends its details to a Lawyer Connection"""
    if request.method == 'POST':
        case_id = request.POST.get('case_id')
        lawyer_connection_id = request.POST.get('lawyer_connection_id')

        # 1. Get the AI Case from CaseSubmission
        ai_case = get_object_or_404(CaseSubmission, id=case_id, user=request.user)
        
        # 2. Get the existing Lawyer Connection from LegalRepresentation
        connection = get_object_or_404(LegalRepresentation, id=lawyer_connection_id, client=request.user)

        # 3. Format the message
        message_text = (
            f"📑 **FORWARDED CASE FILE: {ai_case.case_number}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 **Summary:** {ai_case.case_text}\n\n"
            f"🤖 **AI Analysis Summary:** {ai_case.analysis_result[:300]}..."
        )

        # 4. Create the Chat Message
        CaseChat.objects.create(
            case=connection,
            sender=request.user,
            message=message_text,
            file=ai_case.document 
        )

        messages.success(request, f"Case details forwarded to Adv. {connection.lawyer.first_name}!")
        return redirect('my_cases')
    
    return redirect('my_cases')



@login_required
def get_chat_history(request, session_id):
    """API to load chat history"""
    try:
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        messages = session.messages.all().order_by('created_at')
        data = [{'role': 'user' if m.is_user else 'ai', 'text': m.text} for m in messages]
        return JsonResponse({'messages': data})
    except Exception:
        return JsonResponse({'error': 'Session not found'}, status=404)


# ==========================================
# 6. ADMIN DASHBOARD
# ==========================================

def is_admin(user):
    return user.is_staff

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    total_users = User.objects.filter(is_staff=False).count()
    total_cases = CaseSubmission.objects.count()
    analyzed_cases = CaseSubmission.objects.filter(is_reviewed=True).count()
    pending_cases = CaseSubmission.objects.filter(is_reviewed=False).count()
    recent_cases = CaseSubmission.objects.select_related('user').order_by('-created_at')[:5]
    
    context = {
        "admin_name": request.user.first_name or "Admin",
        "total_users": total_users,
        "total_cases": total_cases,
        "analyzed_cases": analyzed_cases,
        "pending_cases": pending_cases,
        "recent_cases": recent_cases,
    }
    return render(request, "admin_dashboard.html", context)

@login_required
@user_passes_test(is_admin)
def manage_users(request):
    # Fetch all non-staff users
    all_users = User.objects.filter(is_staff=False).select_related('userprofile').order_by('-date_joined')
    
    # Separate them based on their profile attribute
    lawyers = [u for u in all_users if hasattr(u, 'userprofile') and u.userprofile.is_lawyer]
    clients = [u for u in all_users if not hasattr(u, 'userprofile') or not u.userprofile.is_lawyer]

    context = {
        "lawyers": lawyers,
        "clients": clients,
        "total_users": all_users.count(),
        "total_lawyers": len(lawyers),
        "total_clients": len(clients),
    }
    return render(request, "manage_users.html", context)


@login_required
@user_passes_test(is_admin)
def toggle_user_status(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    if target_user.is_staff or target_user.is_superuser:
        messages.error(request, "Cannot block Admin accounts.")
        return redirect('manage_users')

    target_user.is_active = not target_user.is_active
    target_user.save()

    if not target_user.is_active:
        # Force Logout
        for session in Session.objects.filter(expire_date__gte=timezone.now()):
            data = session.get_decoded()
            if str(data.get('_auth_user_id')) == str(target_user.id):
                session.delete()
        messages.warning(request, f"User {target_user.username} BLOCKED.")
    else:
        messages.success(request, f"User {target_user.username} UNBLOCKED.")
        
    return redirect('manage_users')

@login_required
@user_passes_test(is_admin)
def all_cases_view(request):
    cases = CaseSubmission.objects.select_related('user').order_by('-created_at')
    return render(request, "all_cases.html", {"cases": cases, "total_cases": cases.count()})

@login_required
@user_passes_test(is_admin)
def view_user_history(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    user_cases = CaseSubmission.objects.filter(user=target_user).order_by('-created_at')
    user_chats = ChatSession.objects.filter(user=target_user).prefetch_related('messages').order_by('-updated_at')
    
    context = {
        "target_user": target_user,
        "user_cases": user_cases,
        "user_chats": user_chats,
        "total_cases": user_cases.count(),
        "total_chats": user_chats.count()
    }
    return render(request, "user_history.html", context) # This renders the HTML dossier

@login_required
def predictions_view(request):
    """View to show AI predictions for the user's cases"""
    # Fetch all reviewed cases for the current user
    predictions = CaseSubmission.objects.filter(user=request.user, is_reviewed=True).order_by('-created_at')
    return render(request, 'predictions.html', {'predictions': predictions})