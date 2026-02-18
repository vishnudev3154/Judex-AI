from django.db import models
from django.contrib.auth.models import User

# ---------------- USER PROFILE (New) ----------------
# This extends the default Django User to add "Lawyer" fields
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    fullname = models.CharField(max_length=200, blank=True)
    
    # Distinguish between Client and Lawyer
    is_lawyer = models.BooleanField(default=False)
    
    # Specific field for Lawyers
    bar_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} ({'Lawyer' if self.is_lawyer else 'Client'})"


# ... existing imports ...

# ---------------- LAWYER-CLIENT SYSTEM ----------------

class LegalRepresentation(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Accepted', 'Accepted'),
        ('Rejected', 'Rejected'),
    ]

    client = models.ForeignKey(User, related_name='client_requests', on_delete=models.CASCADE)
    lawyer = models.ForeignKey(User, related_name='lawyer_cases', on_delete=models.CASCADE)
    
    # Initial Case Details
    case_title = models.CharField(max_length=200)
    case_description = models.TextField()
    fir_document = models.FileField(upload_to='case_docs/fir/', blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.case_title} - {self.status}"

class CaseChat(models.Model):
    case = models.ForeignKey(LegalRepresentation, related_name='chat_messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='chat_files/', blank=True, null=True) # For sending documents during chat
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Msg from {self.sender.username}"
    
    

# ---------------- AI CHAT MODELS ----------------
class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, blank=True, null=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Chat {self.id} by {self.user.username}"

class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, related_name='messages', on_delete=models.CASCADE)
    text = models.TextField()
    is_user = models.BooleanField(default=True) # True = User, False = AI
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{'User' if self.is_user else 'AI'}: {self.text[:20]}"


# ---------------- PREDICTION & FEEDBACK ----------------
class Prediction(models.Model):
    result = models.CharField(max_length=100)
    confidence = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.result

class Feedback(models.Model):
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message[:40]


# ---------------- CASE SUBMISSION ----------------
class CaseSubmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    case_title = models.CharField(max_length=200)
    case_text = models.TextField(blank=True, null=True) 
    document = models.FileField(upload_to="case_docs/", blank=True, null=True)
    analysis_result = models.TextField(blank=True, null=True)
    is_reviewed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.case_title
    

    # app/models.py

class VirtualCourt(models.Model):
    # Link this to the existing Client-Lawyer Case
    case_connection = models.OneToOneField(LegalRepresentation, on_delete=models.CASCADE, related_name='virtual_court')
    
    # Simulation Details
    title = models.CharField(max_length=200)
    description = models.TextField()
    evidence_text = models.TextField(blank=True, null=True)
    
    # State
    current_score = models.IntegerField(default=50) # 0-100
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Court: {self.title}"

class CourtDebateLog(models.Model):
    court = models.ForeignKey(VirtualCourt, on_delete=models.CASCADE, related_name='logs')
    prosecutor_arg = models.TextField() # What the Lawyer said
    defense_arg = models.TextField()    # What the AI said
    score_after = models.IntegerField() # The score after this turn
    timestamp = models.DateTimeField(auto_now_add=True)

    from django.db import models
from django.contrib.auth.models import User

class Case(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    case_title = models.CharField(max_length=200, default="Untitled Case")
    description = models.TextField(blank=True)
    document = models.FileField(upload_to='case_documents/', null=True, blank=True)
    is_reviewed = models.BooleanField(default=False)  # Handles the Processing/Analyzed status
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.case_title
    
    from django.db import models
from django.contrib.auth.models import User


class Case_register(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Under Review', 'Under Review'),
        ('Closed', 'Closed'),
    ]

    client = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    document = models.FileField(upload_to='case_documents/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


# app/models.py
import random
import string
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class CaseSubmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    case_title = models.CharField(max_length=200)
    
    # Auto-generated unique ID
    case_number = models.CharField(max_length=30, unique=True, blank=True)
    
    case_text = models.TextField()
    document = models.FileField(upload_to='case_documents/', null=True, blank=True)
    analysis_result = models.TextField(blank=True, null=True)
    is_reviewed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Logic: If ID is missing, generate it
        if not self.case_number:
            year = timezone.now().year
            # Generate 6 random digits
            rand_id = ''.join(random.choices(string.digits, k=6))
            # Format: CN-2026-123456
            self.case_number = f"CN-{year}-{rand_id}"
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.case_number} - {self.case_title}"
    
    