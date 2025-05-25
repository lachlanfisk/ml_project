from django.contrib import admin
from .models import (
    TextbookSection, TextbookPage, TextbookSlide,
    RevisionQuestion, RevisionQuestionAttempt, RevisionQuestionAttemptDetail,
    WritingInteraction, UserSlideRead, UserSlideReadSession
)
from .models import StudyEngagementFact, ContentDimension

@admin.register(StudyEngagementFact)
class StudyEngagementFactAdmin(admin.ModelAdmin):
    list_display = (
        'student',
        'get_page_title',
        'total_slide_time',
        'slides_opened_ratio',
        'first_attempt_accuracy',
        'overall_accuracy',
        'recall_fluency',
        'total_slides',
    )
    search_fields = ('student__username', 'content_dim__page__page_title')
    list_filter = ('content_dim__subject',)

    def get_page_title(self, obj):
        return obj.content_dim.page.page_title
    get_page_title.short_description = 'Page Title'

@admin.register(ContentDimension)
class ContentDimensionAdmin(admin.ModelAdmin):
    list_display = ('subject', 'page', 'get_linked_sections')  # Show linked sections
    search_fields = ('subject', 'page__page_title')

    def get_linked_sections(self, obj):
        return ", ".join([section.section_title for section in obj.sections.all()])
    get_linked_sections.short_description = "Linked Sections"  # Set column name in admin

@admin.register(TextbookSection)
class TextbookSectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'section_title')
    search_fields = ('section_title',)

@admin.register(TextbookPage)
class TextbookPageAdmin(admin.ModelAdmin):
    list_display = ('id', 'page_title', 'get_linked_sections')  # Show linked sections
    search_fields = ('page_title',)
    filter_horizontal = ('sections',)  # Enables multi-select interface in admin

    def get_linked_sections(self, obj):
        return ", ".join([section.section_title for section in obj.sections.all()])
    get_linked_sections.short_description = "Linked Sections"  # Set column name in admin

@admin.register(TextbookSlide)
class TextbookSlideAdmin(admin.ModelAdmin):
    list_display = ('id', 'slide_title', 'get_linked_pages')
    search_fields = ('slide_title',)
    filter_horizontal = ('pages',)  

    def get_linked_pages(self, obj):
        return ", ".join([str(page.id) for page in obj.pages.all()])
    get_linked_pages.short_description = "Linked Page IDs"

@admin.register(RevisionQuestion)
class RevisionQuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'textbook_page')
    list_filter = ('textbook_page',)

@admin.register(RevisionQuestionAttempt)
class RevisionQuestionAttemptAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'question', 'viewed', 'correct', 'processed')
    list_filter = ('user', 'question', 'viewed', 'correct', 'processed')
    actions = ['mark_as_unprocessed']

    def mark_as_unprocessed(self, request, queryset):
        queryset.update(processed=False)
        self.message_user(request, "Selected attempts have been marked as unprocessed.")
    mark_as_unprocessed.short_description = "Mark selected attempts as unprocessed"

@admin.register(RevisionQuestionAttemptDetail)
class RevisionQuestionAttemptDetailAdmin(admin.ModelAdmin):
    list_display = ('id', 'attempt', 'is_correct', 'timestamp', 'processed')  # Added 'processed'
    list_filter = ('is_correct', 'processed')  # Added 'processed' to filters
    actions = ['mark_as_unprocessed']

    def mark_as_unprocessed(self, request, queryset):
        queryset.update(processed=False)
        self.message_user(request, "Selected attempts have been marked as unprocessed.")
    mark_as_unprocessed.short_description = "Mark selected attempts as unprocessed"

@admin.register(WritingInteraction)
class WritingInteractionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_id', 'page_id', 'timestamp')
    search_fields = ('user_id', 'page_id')

@admin.register(UserSlideRead)
class UserSlideReadAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'slide', 'slide_status')
    list_filter = ('slide_status',)

@admin.register(UserSlideReadSession)
class UserSlideReadSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'slide_read', 'formatted_expanded', 'formatted_collapsed', 'formatted_read')
    list_filter = ('expanded', 'collapsed', 'read')

    def formatted_expanded(self, obj):
        return obj.expanded.strftime("%Y-%m-%d %H:%M:%S") if obj.expanded else "N/A"
    formatted_expanded.short_description = "Expanded (Full Time)"

    def formatted_collapsed(self, obj):
        return obj.collapsed.strftime("%Y-%m-%d %H:%M:%S") if obj.collapsed else "N/A"
    formatted_collapsed.short_description = "Collapsed (Full Time)"

    def formatted_read(self, obj):
        return obj.read.strftime("%Y-%m-%d %H:%M:%S") if obj.read else "N/A"
    formatted_read.short_description = "Read (Full Time)"