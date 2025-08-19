from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.utils.html import format_html
from .models import WasteClassification

@admin.register(WasteClassification)
class WasteClassificationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'predicted_category', 'state', 'confidence_score',
        'image_preview', 'created_at'
    ]
    list_filter = [
        'predicted_category', 'state', 'created_at'
    ]
    search_fields = [
        'predicted_category', 'waste_description', 'state'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'image_preview', 'confidence_score',
        'predicted_category', 'gemini_raw_response'
    ]

    fieldsets = (
        ('Input Information', {
            'fields': ('image', 'image_preview', 'state')
        }),
        ('Classification Results', {
            'fields': (
                'predicted_category', 'confidence_score',
                'waste_description'
            )
        }),
        ('Disposal Information', {
            'fields': (
                'disposal_instructions', 'state_specific_laws',
                'authorized_facilities'
            )
        }),
        ('Risk Assessment', {
            'fields': (
                'health_hazards', 'environmental_risks'
            )
        }),
        ('Safety Measures', {
            'fields': (
                'precautions', 'protective_equipment',
                'emergency_procedures'
            )
        }),
        ('Additional Information', {
            'fields': (
                'recyclability_info', 'cost_implications'
            )
        }),
        ('System Information', {
            'fields': (
                'gemini_raw_response', 'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        })
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 100px; height: 100px; object-fit: cover;" />',
                obj.image.url
            )
        return "No Image"
    image_preview.short_description = "Image Preview"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()
