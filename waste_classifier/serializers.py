from rest_framework import serializers
from .models import WasteClassification

class WasteClassificationSerializer(serializers.ModelSerializer):
    state_display = serializers.CharField(source='get_state_display', read_only=True)
    category_display = serializers.CharField(source='get_predicted_category_display', read_only=True)

    class Meta:
        model = WasteClassification
        fields = '__all__'
        read_only_fields = [
            'predicted_category', 'confidence_score', 'waste_description',
            'disposal_instructions', 'state_specific_laws', 'authorized_facilities',
            'health_hazards', 'environmental_risks', 'precautions',
            'protective_equipment', 'emergency_procedures', 'recyclability_info',
            'cost_implications', 'gemini_raw_response', 'created_at', 'updated_at'
        ]

class WasteAnalysisInputSerializer(serializers.Serializer):
    image = serializers.ImageField(required=True)
    state = serializers.ChoiceField(choices=WasteClassification.INDIAN_STATES, required=True)

    def validate_image(self, value):
        """Validate image file"""
        if value.size > 10 * 1024 * 1024:  # 10MB limit
            raise serializers.ValidationError("Image size should not exceed 10MB")

        if not value.content_type.startswith('image/'):
            raise serializers.ValidationError("File must be an image")

        return value
