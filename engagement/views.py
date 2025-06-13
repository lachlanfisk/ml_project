import re
import csv
import os
import pandas as pd
import requests
from requests.exceptions import RequestException
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import HttpResponse
from django.http import JsonResponse
from django.contrib.sessions.models import Session
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.utils.timezone import now
from datetime import timedelta
from django.db.models import Avg, F, ExpressionWrapper, DurationField
from .models import (
    TextbookSection, TextbookPage, TextbookSlide, 
    RevisionQuestion, RevisionQuestionAttempt, RevisionQuestionAttemptDetail, 
    UserSlideRead, UserSlideReadSession, 
    WritingInteraction, User,
    StudyEngagementFact,  
    ContentDimension, 
)
from engagement.train_model import train_model
from .train_model import train_model
from django import forms
from django import forms
import joblib
from .tree_model import train_and_visualise_tree
from .linear_model import train_linear_model
from .plot_linear_regression import plot_linear_relationships
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import matplotlib.pyplot as plt
import os

DATA_API_URL = "https://se.eforge.online/textbook/api/user-engagement/"

class PredictionForm(forms.Form):
    page = forms.ModelChoiceField(
        queryset=ContentDimension.objects.filter(
            studyengagementfact__isnull=False
        ).distinct(),
        empty_label="Select a textbook page",
        label="Choose a Page"
    )
    model_choice = forms.ChoiceField(
        choices=[
            ("random_forest", "Random Forest"),
            ("linear_regression", "Linear Regression"),
        ],
        widget=forms.RadioSelect,
        initial="random_forest",
        label="Select Model"
    )

def populate_olap_cube(request):
    student = User.objects.first()
    if not student:
        return JsonResponse({"error": "No user record found."}, status=400)
    slides = UserSlideRead.objects.all()
    questions = RevisionQuestionAttempt.objects.all()
    processed_pages = set()
    slide_time_per_page = {}
    slides_opened_per_page = {}
    for slide_read in slides:
        page = slide_read.slide.pages.first() if slide_read.slide.pages.exists() else None
        if not page:
            continue
        processed_pages.add(page.id)
        slide_time = sum([session.read_duration() for session in slide_read.review_sessions.all()])
        slide_time_per_page[page.id] = slide_time_per_page.get(page.id, 0) + slide_time
        slides_opened_per_page.setdefault(page.id, set()).add(slide_read.slide.id)
    for page_id in processed_pages:
        page = TextbookPage.objects.get(id=page_id)
        content_dim, _ = ContentDimension.objects.get_or_create(subject="Software Engineering", page=page)
        if page.sections.exists():
            content_dim.sections.set(page.sections.all())
        total_slides = TextbookSlide.objects.filter(pages=page).count()
        slides_opened = len(slides_opened_per_page.get(page.id, set()))
        slides_opened_ratio = slides_opened / total_slides if total_slides > 0 else 0
        total_slide_time = slide_time_per_page.get(page.id, 0)
        page_questions = questions.filter(question__textbook_page=page)
        total_questions = page_questions.count()
        correct = page_questions.filter(details__is_correct=True).count()
        first_attempt_accuracy = correct / total_questions if total_questions > 0 else 0
        overall_accuracy = correct / total_questions if total_questions > 0 else 0
        writing = WritingInteraction.objects.filter(page_id=page.id, grade__isnull=False).order_by('-timestamp').first()
        if not writing:
            continue
        score = writing.grade
        StudyEngagementFact.objects.update_or_create(
            student=student,
            content_dim=content_dim,
            defaults={
                "total_slide_time": total_slide_time,
                "slides_opened_ratio": slides_opened_ratio,
                "first_attempt_accuracy": first_attempt_accuracy,
                "overall_accuracy": overall_accuracy,
                "score": score,
                "total_slides": total_slides,
            }
        )
    request.session['olap_populated'] = True
    return JsonResponse({"message": "OLAP cube populated for single-user environment."})

def check_olap_status(request):
    olap_status = request.session.get('olap_populated', False)
    return JsonResponse({"olap_populated": olap_status})

def calculate_total_questions_attempted(new_questions_for_page):
    total_attempts = new_questions_for_page.count()
    return total_attempts

def calculate_first_attempt_accuracy(new_questions_for_page):
    correct_first_attempts = new_questions_for_page.exclude(
        id__in=RevisionQuestionAttemptDetail.objects.values_list('attempt_id', flat=True)
    ).filter(correct__isnull=False)
    total_questions_attempted = new_questions_for_page.count()
    first_attempt_accuracy = correct_first_attempts.count() / total_questions_attempted if total_questions_attempted > 0 else 0
    return first_attempt_accuracy

def calculate_overall_accuracy(new_questions_for_page):
    correct_answers = new_questions_for_page.filter(correct__isnull=False).count()
    total_questions_attempted = new_questions_for_page.count()
    overall_accuracy = correct_answers / total_questions_attempted if total_questions_attempted > 0 else 0
    return overall_accuracy

def compute_engagement_metrics(page):
    new_questions_for_page = get_new_questions_for_page(page)
    total_questions_attempted = new_questions_for_page.count()
    metrics = {
        "first_attempt_accuracy": calculate_first_attempt_accuracy(new_questions_for_page),
        "overall_accuracy": calculate_overall_accuracy(new_questions_for_page),
        "recall_fluency": calculate_recall_fluency(new_questions_for_page),
        "total_questions_attempted": total_questions_attempted
    }
    return metrics

def calculate_recall_fluency(new_questions_for_page):
    correct_first_attempts_with_times = new_questions_for_page.exclude(
        id__in=RevisionQuestionAttemptDetail.objects.values_list('attempt_id', flat=True)
    ).filter(correct__isnull=False, viewed__isnull=False)
    recall_times = correct_first_attempts_with_times.annotate(
        response_time=ExpressionWrapper(F('correct') - F('viewed'), output_field=DurationField())
    ).filter(response_time__lte=timedelta(seconds=120))
    avg_recall_time = recall_times.aggregate(avg_recall_time=Avg('response_time'))['avg_recall_time']
    if avg_recall_time is None:
        recall_fluency = 0
    else:
        recall_fluency = avg_recall_time.total_seconds()
    return recall_fluency

def get_student_for_page(page):
    slide_read_entry = UserSlideRead.objects.filter(slide__pages=page).first()
    student = slide_read_entry.user if slide_read_entry else None
    return student

def get_new_questions_for_page(page):
    page_questions = RevisionQuestion.objects.filter(textbook_page=page)
    if not page_questions.exists():
        return RevisionQuestionAttempt.objects.none()  
    new_questions = RevisionQuestionAttempt.objects.filter(question__in=page_questions, processed=False)
    return new_questions

def calculate_slide_read_time():    
    slide_time_per_page = {}
    slides_opened_per_page = {}
    slides = UserSlideRead.objects.all()  
    for slide in slides:
        page = slide.slide.pages.first() if slide.slide.pages.exists() else None
        if page is None:
            continue
        slide_read_time = sum([
            min(session.read_duration(), 180) for session in slide.review_sessions.all()
        ])
        if page.id not in slide_time_per_page:
            slide_time_per_page[page.id] = 0 
        slide_time_per_page[page.id] += slide_read_time  
        if page.id not in slides_opened_per_page:
            slides_opened_per_page[page.id] = set()
        slides_opened_per_page[page.id].add(slide.slide.id)  
    return slide_time_per_page, slides_opened_per_page

def scale_recall_fluency(seconds):
    if seconds is None or seconds > 60:
        return 0
    elif seconds <= 5:
        return 0.1
    else:
        return round((1 - ((seconds - 5) / 55)) * 0.1, 4)

def scale_slide_time_with_slide_count(total_seconds, num_slides):
    if total_seconds is None or num_slides is None or num_slides == 0:
        return 0.0
    seconds_per_slide = total_seconds / num_slides
    min_time = 10     # seconds per slide for 0 score
    max_time = 180    # seconds per slide for full score (0.2)
    if seconds_per_slide <= min_time:
        return 0.0
    elif seconds_per_slide >= max_time:
        return 0.2
    else:
        return round(((seconds_per_slide - min_time) / (max_time - min_time)) * 0.2, 4)

def fetch_data_from_textbook(request, sessionid=None, csrftoken=None):  
    if not sessionid:
        sessionid = request.headers.get("X-Session-ID")
    if not csrftoken:
        csrftoken = request.headers.get("X-CSRFToken")
    if not sessionid:
        return render(request, "engagement/auth_reminder.html")
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "X-Session-ID": sessionid,  
        "X-CSRFToken": csrftoken,
    }
    cookies = {
        "sessionid": sessionid,
        "csrftoken": csrftoken,
    }
    try:
        response = requests.get(DATA_API_URL, headers=headers, cookies=cookies, timeout=5)
        response.raise_for_status()  
    except RequestException as e:
        print(f"API Down or Connection Error: {str(e)}")
        return render(request, "engagement/auth_reminder.html")
    if response.status_code == 403: 
        return render(request, "engagement/auth_reminder.html")
        return None
    if response.status_code == 200:
        data = response.json()
        user_mapping = {}
        for user_id in {item["user"] for item in data.get('user_slide_reads', [])} | {item["user"] for item in data.get('attempts', [])}:
            user_obj, created = User.objects.get_or_create(id=user_id, defaults={"username": f"user_{user_id}"})
            user_mapping[user_id] = user_obj
            if created:
                print(f"Created new User: {user_obj.username} (ID: {user_id})")
        section_mapping = {}
        for section_data in data.get('sections', []):
            section_obj, _ = TextbookSection.objects.update_or_create(
                id=section_data['id'], 
                defaults={"section_title": section_data['section_title']}
            )
            section_mapping[section_data['id']] = section_obj  
        page_mapping = {}
        for page_data in data.get('pages', []):
            page_obj, _ = TextbookPage.objects.update_or_create(
                id=page_data['id'], 
                defaults={"page_title": page_data['page_title']}
            )
            page_mapping[page_data['id']] = page_obj  

            # Ensure the page is linked to the correct sections
            if 'sections' in page_data:  # Check if the API provides section links
                linked_sections = []
                for section_id in page_data['sections']:  # Iterate through section IDs
                    if section_id in section_mapping:
                        linked_sections.append(section_mapping[section_id])
                    else:
                        print(f"Warning: Section ID {section_id} not found for Page ID {page_data['id']}")

                if linked_sections:
                    page_obj.sections.set(linked_sections)  # Properly link sections to page

        slide_mapping = {}
        for slide_data in data.get('slides', []):
            slide_obj, _ = TextbookSlide.objects.update_or_create(
                id=slide_data['id'], 
                defaults={"slide_title": slide_data['slide_title']}
            )
            slide_mapping[slide_data['id']] = slide_obj  

            # Ensure the slide is linked to the correct pages
            if 'pages' in slide_data:  # Check if pages are included in API data
                linked_pages = []
                for page_id in slide_data['pages']:
                    if page_id in page_mapping:
                        linked_pages.append(page_mapping[page_id])
                    else:
                        print(f"Warning: Page ID {page_id} not found for Slide ID {slide_data['id']}")

                if linked_pages:
                    slide_obj.pages.set(linked_pages)  # Properly link pages to slide

        user_slide_mapping = {}
        for user_slide_data in data.get('user_slide_reads', []):
            slide_id = user_slide_data['slide']
            user_id = user_slide_data['user']
            if slide_id not in slide_mapping:
                print(f"Skipping UserSlideRead {user_slide_data['id']}: Slide {slide_id} not found.")
                continue  
            user_obj = User.objects.filter(id=user_id).first()
            if not user_obj:
                print(f"Skipping UserSlideRead {user_slide_data['id']}: User {user_id} not found.")
                continue 
            slide_read_obj, _ = UserSlideRead.objects.update_or_create(
                id=user_slide_data['id'], 
                defaults={
                    "user": user_obj, 
                    "slide": slide_mapping[slide_id],  
                    "slide_status": user_slide_data['slide_status']
                }
            )
            user_slide_mapping[user_slide_data['id']] = slide_read_obj
        for session_data in data.get('user_slide_sessions', []):
            if session_data['slide_read'] in user_slide_mapping:
                UserSlideReadSession.objects.update_or_create(
                    id=session_data['id'], 
                    defaults={
                        "slide_read": user_slide_mapping[session_data['slide_read']],
                        "expanded": session_data['expanded'],
                        "collapsed": session_data['collapsed'],
                        "read": session_data['read']
                    }
                )
            else:
                print(f"Skipping UserSlideReadSession {session_data['id']}: No matching UserSlideRead found.")
        question_mapping = {}
        for question_data in data.get('questions', []):
            page_id = question_data.get('textbook_page')
            if page_id in page_mapping:
                question_obj, _ = RevisionQuestion.objects.update_or_create(
                    id=question_data['id'], 
                    defaults={"textbook_page": page_mapping[page_id]}  
                )
                question_mapping[question_data['id']] = question_obj
        attempt_mapping = {}
        for attempt_data in data.get('attempts', []):
            user_id = attempt_data.get('user')
            question_id = attempt_data.get('question')
            if question_id in question_mapping and User.objects.filter(id=user_id).exists():
                attempt_obj, _ = RevisionQuestionAttempt.objects.update_or_create(
                    id=attempt_data['id'], 
                    defaults={
                        "user_id": user_id,
                        "question": question_mapping[question_id],
                        "viewed": attempt_data['viewed'],
                        "correct": attempt_data['correct']
                    }
                )
                attempt_mapping[attempt_data['id']] = attempt_obj
        for detail_data in data.get('attempt_details', []):
            attempt_id = detail_data.get('attempt')
            if attempt_id in attempt_mapping:
                RevisionQuestionAttemptDetail.objects.update_or_create(
                    id=detail_data['id'], 
                    defaults={
                        "attempt": attempt_mapping[attempt_id],
                        "is_correct": detail_data['is_correct'],
                        "timestamp": detail_data['timestamp']
                    }
                )
        for interaction_data in data.get('writing_interactions', []):
            if User.objects.filter(id=interaction_data['user_id']).exists():
                grade_raw = interaction_data.get('grade')
                print(f"Raw grade: {interaction_data.get('grade')} (type: {type(interaction_data.get('grade'))})")
                try:
                    grade_clean = int(float(grade_raw))  # handles "1", 1.0, "1.0"
                except (TypeError, ValueError):
                    grade_clean = None
                print(f"Clean grade: {grade_clean}")
                print(f"[Client] Received grade for ID {interaction_data['id']}: {interaction_data.get('grade')}")
                WritingInteraction.objects.update_or_create(
                    id=interaction_data['id'],
                    defaults={
                        "user_id": interaction_data['user_id'],
                        "page_id": interaction_data['page_id'],
                        "user_input": interaction_data['user_input'],
                        "openai_response": interaction_data['openai_response'],
                        "grade": grade_clean,
                        "timestamp": interaction_data['timestamp']
                    }
                )
        return data  
    else:
        print(f"Error {response.status_code}: {response.text}")
        return None

def homepage(request):
    return render(request, "engagement/homepage.html")

def manual_import(request):
    sessionid = request.POST.get("sessionid")
    csrftoken = request.POST.get("csrftoken")
    if not sessionid:
        messages.error(request, "No session found. Please log in to the textbook first.")
        return redirect("homepage")
    data = fetch_data_from_textbook(request, sessionid, csrftoken)
    if data:
        messages.success(request, "Data manually imported successfully.")
        response = redirect("engagement:homepage")
        response.set_cookie("data_imported", "true")  
    else:
        messages.error(request, "Manual import failed.")
        response = redirect("engagement:homepage")
    return response

def auth_reminder(request):
    return render(request, "engagement/auth_reminder.html")

def csrf_failure(request, reason=""):
    return redirect("engagement:auth_reminder")

def clear_session(request):
    if request.user.is_authenticated:
        logout(request)  
    session_key = request.session.session_key
    if session_key:
        try:
            Session.objects.get(session_key=session_key).delete()  
            print(f"Deleted session {session_key} from the database.")
        except Session.DoesNotExist:
            print("No session found in database.")
    request.session.flush()
    response = JsonResponse({"message": "Session cleared successfully"})
    response.delete_cookie("sessionid")
    response.delete_cookie("csrftoken")
    print("All session data removed.")
    return redirect("engagement:auth_reminder")

def export_engagement_csv(request):
    file_path = os.path.join(settings.BASE_DIR, "student_engagement.csv")
    row_count = 0
    with open(file_path, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            "student_id", "page", "total_slide_time", "slides_opened_ratio",
            "first_attempt_accuracy", "overall_accuracy", "recall_fluency",
            "total_slides", "score"
        ])

        for record in StudyEngagementFact.objects.all():
            writer.writerow([
                record.student.id,
                str(record.content_dim.page),
                record.total_slide_time,
                record.slides_opened_ratio,
                record.first_attempt_accuracy,
                record.overall_accuracy,
                record.recall_fluency,
                record.total_slides,
                record.score,
            ])
            row_count += 1
    messages.success(request, "Step 3 complete: Engagement data exported to server.")
    response = redirect("engagement:homepage")
    response.set_cookie("step3_complete", "true", max_age=10)
    response.set_cookie("row_count", str(row_count), max_age=10)
    return response

@csrf_exempt 
def select_features_and_target(request):
    if request.method == "POST":
        try:
            df = pd.read_csv("student_engagement.csv")
            features = [
                "total_slide_time", "slides_opened_ratio", "first_attempt_accuracy",
                "overall_accuracy", "recall_fluency", "total_slides"
            ]
            target = "score"
            # Save features and target to disk for use in training step
            df[features + [target]].to_csv("training_data.csv", index=False)
            return JsonResponse({"message": "Step 2 Complete: Features &Target Selected."})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

def run_model_training(request):
    try:
        importances = train_model()
        importance_text = ", ".join([f"{k}: {v}" for k, v in importances.items()])
        messages.success(request, f"Step 5 complete: Model trained. Importances: {importance_text}")
        response = redirect("engagement:homepage")
        response.set_cookie("step5_complete", "true", max_age=10)
        print("Step 5: Model trained.")
        return response
    except Exception as e:
        messages.error(request, f"Error in model training: {str(e)}")
        return redirect("engagement:homepage")

class PredictionForm(forms.Form):
    page = forms.ModelChoiceField(
        queryset=ContentDimension.objects.filter(
            studyengagementfact__isnull=False
        ).distinct(),
        empty_label="Select a textbook page",
        label="Choose a Page"
    )

def predict_form_view(request):
    prediction_result = None
    form = PredictionForm(request.POST or None)
    tree_rules_text = None
    if request.method == "POST" and form.is_valid():
        page = form.cleaned_data["page"].page
        student = User.objects.first()  # replace with actual logged-in student
        content_dim = form.cleaned_data["page"]
        model_choice = form.cleaned_data["model_choice"]
        try:
            if model_choice == "linear_regression":
                model = joblib.load("linear_model.joblib")
            else:
                model = joblib.load("ml_model.joblib")
            engagement = StudyEngagementFact.objects.get(student=student, content_dim=content_dim)
            features = [
                engagement.total_slide_time,
                engagement.slides_opened_ratio,
                engagement.first_attempt_accuracy,
                engagement.overall_accuracy,
                engagement.recall_fluency,
                engagement.total_slides,
            ]
            prediction = model.predict([features])[0]
            score = round(prediction, 2)
            label, feedback = categorise_score(score)
            feedback_message = interpret_tree_path(
                engagement.slides_opened_ratio,
                engagement.recall_fluency
            )
            prediction_result = {
                "score": score,
                "label": label,
                "feedback": feedback,
                "hint": feedback_message,
                "model": "Linear Regression" if model_choice == "linear_regression" else "Random Forest"
            }
            tree_rules_text = read_tree_rules()
        except Exception as e:
            prediction_result = f"Error: {str(e)}"
    return render(request, "engagement/homepage.html", {
        "form": form,
        "prediction_result": prediction_result,
        "tree_rules_text": tree_rules_text,
    })

def categorise_score(score):
    if score < 1.0:
        return "Needs Improvement", "The response is limited or off-topic. Try to expand your ideas and answer more directly."
    elif score < 2.0:
        return "Developing", "There’s some structure and effort, but more detail or accuracy would improve your work."
    elif score < 2.8:
        return "Competent", "Well done! The response shows understanding and effort. You’re almost there!"
    else:
        return "Excellent", "Outstanding! Clear, structured, and insightful writing. Great job!"

def train_decision_tree(request):
    try:
        train_and_visualise_tree()
        messages.success(request, "Step 6 complete: Decision tree trained and visualised.")
    except Exception as e:
        messages.error(request, f"Error running tree visualiser: {e}")
    return redirect("engagement:homepage")

def interpret_tree_path(slides_opened_ratio, recall_fluency, total_slide_time=None, accuracy=None):
    if slides_opened_ratio <= 0.45:
        if recall_fluency is None or recall_fluency > 35:
            return (
                "You're opening less than half the slides and your recall speed is slow. "
                "Try reviewing more slides and answering faster to improve your score."
            )
        else:
            return (
                "You're opening fewer slides, but your recall is decent. "
                "Try exploring more content for stronger performance."
            )
    elif slides_opened_ratio > 0.45:
        if recall_fluency is None:
            return (
                "You're reviewing enough slides, but we couldn’t measure your recall fluency. "
                "Try completing more review questions to improve fluency tracking."
            )
        elif recall_fluency <= 35:
            return (
                "Excellent! You're reviewing thoroughly and answering quickly. Keep it up!"
            )
        else:
            return (
                "You're engaging well with the material, but try to answer review questions "
                "more quickly for a better score."
            )
    return (
        "Your engagement is good overall. Keep focusing on both content coverage and recall speed "
        "to achieve your best results."
    )

def read_tree_rules():
    import os
    rules_path = os.path.join(os.path.dirname(__file__), "static", "images", "tree_rules.txt")
    try:
        with open(rules_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return None 

def run_linear_plot_view(request):
    try:
        plot_linear_relationships()
        messages.success(request, "Linear regression plots generated.")
    except Exception as e:
        messages.error(request, f"Error generating plots: {e}")
    return redirect("engagement:homepage")

def train_linear_model_view(request):
    try:
        coefs = train_linear_model()
        messages.success(request, "Linear Regression trained. Coefficients: " + ", ".join([f"{k}: {v}" for k, v in coefs.items()]))
        response = redirect("engagement:homepage")
        response.set_cookie("step6_linear_complete", "true", max_age=10)
        return response
    except Exception as e:
        messages.error(request, f"Error training linear regression model: {str(e)}")
        return redirect("engagement:homepage")