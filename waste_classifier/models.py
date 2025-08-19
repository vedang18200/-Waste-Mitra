from django.db import models

# Create your models here.
from django.db import models
from django.core.validators import FileExtensionValidator
import json

class WasteClassification(models.Model):
    WASTE_CATEGORIES = [
        ('MEDICAL', 'Medical Waste'),
        ('E_WASTE', 'E-Waste'),
        ('GENERAL', 'General Waste'),
        ('RECYCLABLE', 'Recyclable Waste'),
        ('NON_RECYCLABLE', 'Non-Recyclable Waste'),
        ('HAZARDOUS', 'Hazardous Waste'),
        ('ORGANIC', 'Organic Waste'),
    ]

    INDIAN_STATES = [
        ('AP', 'Andhra Pradesh'), ('AR', 'Arunachal Pradesh'), ('AS', 'Assam'),
        ('BR', 'Bihar'), ('CT', 'Chhattisgarh'), ('GA', 'Goa'), ('GJ', 'Gujarat'),
        ('HR', 'Haryana'), ('HP', 'Himachal Pradesh'), ('JH', 'Jharkhand'),
        ('KA', 'Karnataka'), ('KL', 'Kerala'), ('MP', 'Madhya Pradesh'),
        ('MH', 'Maharashtra'), ('MN', 'Manipur'), ('ML', 'Meghalaya'),
        ('MZ', 'Mizoram'), ('NL', 'Nagaland'), ('OR', 'Odisha'), ('PB', 'Punjab'),
        ('RJ', 'Rajasthan'), ('SK', 'Sikkim'), ('TN', 'Tamil Nadu'),
        ('TG', 'Telangana'), ('TR', 'Tripura'), ('UP', 'Uttar Pradesh'),
        ('UT', 'Uttarakhand'), ('WB', 'West Bengal'), ('AN', 'Andaman and Nicobar'),
        ('CH', 'Chandigarh'), ('DH', 'Dadra and Nagar Haveli'), ('DD', 'Daman and Diu'),
        ('DL', 'Delhi'), ('JK', 'Jammu and Kashmir'), ('LA', 'Ladakh'),
        ('LD', 'Lakshadweep'), ('PY', 'Puducherry'),
    ]

    image = models.ImageField(
        upload_to='waste_images/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'bmp', 'webp'])]
    )
    state = models.CharField(max_length=2, choices=INDIAN_STATES)

    # Gemini API Response Fields
    predicted_category = models.CharField(max_length=20, choices=WASTE_CATEGORIES, blank=True)
    confidence_score = models.FloatField(blank=True, null=True)
    waste_description = models.TextField(blank=True)

    # Disposal Information
    disposal_instructions = models.TextField(blank=True)
    state_specific_laws = models.TextField(blank=True)
    authorized_facilities = models.TextField(blank=True)

    # Risk Assessment
    health_hazards = models.TextField(blank=True)
    environmental_risks = models.TextField(blank=True)

    # Safety Measures
    precautions = models.TextField(blank=True)
    protective_equipment = models.TextField(blank=True)
    emergency_procedures = models.TextField(blank=True)

    # Additional Information
    recyclability_info = models.TextField(blank=True)
    cost_implications = models.TextField(blank=True)

    # Gemini raw response (for debugging)
    gemini_raw_response = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Waste Classification'
        verbose_name_plural = 'Waste Classifications'

    def __str__(self):
        return f"{self.get_predicted_category_display()} - {self.get_state_display()} - {self.created_at.strftime('%Y-%m-%d')}"
