from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now
import logging
logger = logging.getLogger(__name__)

# Content Dimension
class ContentDimension(models.Model):
    subject = models.CharField(max_length=200)
    page = models.ForeignKey('TextbookPage', on_delete=models.CASCADE, related_name='content_pages')
    sections = models.ManyToManyField('TextbookSection', related_name='content_sections')  # Add sections
    def __str__(self):
        section_titles = ", ".join([section.section_title for section in self.sections.all()])
        return f"{self.subject} - {self.page.page_title} (Sections: {section_titles})"

# Fact Table: Study Engagement Cube
class StudyEngagementFact(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    content_dim = models.ForeignKey(ContentDimension, on_delete=models.CASCADE)

    # Aggregated Metrics
    total_slide_time = models.IntegerField(default=0)  # Viewing time in seconds
    slides_opened_ratio = models.FloatField(default=0.0)  # % of slides opened
    first_attempt_accuracy = models.FloatField(default=0.0)  # % of correct first-attempt answers
    overall_accuracy = models.FloatField(default=0.0)  # % of correct answers overall
    recall_fluency = models.FloatField(default=0.0)  # Average time taken to answer correctly
    total_slides = models.IntegerField(default=0) # Total slides on page

    # Score for ML
    score = models.IntegerField(default=0)
    def __str__(self):
        return f"{self.student.username} - Page {self.content_dim.page}"

# Textbook Structure Models
class TextbookSection(models.Model):
    section_title = models.CharField(max_length=200)
    def __str__(self):
        return self.section_title

class TextbookPage(models.Model):
    page_title = models.CharField(max_length=200)
    sections = models.ManyToManyField(TextbookSection, related_name='pages')
    def __str__(self):
        return self.page_title

class TextbookSlide(models.Model):    
    slide_title = models.CharField(max_length=200, default='')
    pages = models.ManyToManyField(TextbookPage, related_name='slides')
    def __str__(self):
        return self.slide_title

# Question & Attempt Models
class RevisionQuestion(models.Model):
    textbook_page = models.ForeignKey(TextbookPage, on_delete=models.CASCADE, related_name='rq_questions')

class RevisionQuestionAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='revision_attempts')
    question = models.ForeignKey(RevisionQuestion, on_delete=models.CASCADE, related_name='attempts')
    viewed = models.DateTimeField(null=True, blank=True)  # Timestamp when the user first viewed the question
    correct = models.DateTimeField(null=True, blank=True)  # Timestamp when the correct answer was submitted
    processed = models.BooleanField(default=False) # Flag to mark processed attempts
    def __str__(self):
        return f"Attempt by {self.user.username} on Question {self.question}"
class RevisionQuestionAttemptDetail(models.Model):
    attempt = models.ForeignKey(RevisionQuestionAttempt, on_delete=models.CASCADE, related_name='details')
    is_correct = models.BooleanField()  
    timestamp = models.DateTimeField(default=now)  # Timestamp when the answer was submitted
    processed = models.BooleanField(default=False)  # Flag to mark processed incorrect attempts
    def __str__(self):
        result = "Correct" if self.is_correct else "Incorrect"
        return f"{result} at {self.timestamp}"

# Writing Interaction Model
class WritingInteraction(models.Model):
    user_id = models.IntegerField(null=True, blank=True)
    page_id = models.IntegerField()
    user_input = models.TextField()
    openai_response = models.TextField()
    grade = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Interaction - Page {self.page_id}"

# Tracking User Engagement with Slides
class UserSlideRead(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    slide = models.ForeignKey(TextbookSlide, on_delete=models.CASCADE)
    slide_status = models.CharField(
        max_length=10,
        choices=[('read', 'Read'), ('unread', 'Unread'), ('revise', 'Revise')],
        default='unread'
    )
    class Meta:
        unique_together = ('user', 'slide')
    def __str__(self):
        return f'{self.user.username} - {self.slide.slide_title} - Status:{self.slide_status}'

class UserSlideReadSession(models.Model):
    slide_read = models.ForeignKey('UserSlideRead', on_delete=models.CASCADE, related_name='review_sessions')
    expanded = models.DateTimeField(default=now)
    collapsed = models.DateTimeField(null=True, blank=True)
    read = models.DateTimeField(null=True, blank=True)
    def read_duration(self):
        if self.expanded:
            if self.read:
                duration = self.read - self.expanded
            elif self.collapsed:
                duration = self.collapsed - self.expanded
            else:
                return 0
            total_seconds = int(duration.total_seconds())  
            if total_seconds >= 0:
                return total_seconds
            else:
                return 0
        return 0  