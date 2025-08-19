from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import TemplateView, DetailView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer
import json
import re
import logging

from .models import WasteClassification
from .serializers import WasteAnalysisInputSerializer, WasteClassificationSerializer
from .gemini_service import GeminiWasteAnalyzer

logger = logging.getLogger(__name__)

def parse_gemini_response(raw_response):
    """
    Parse Gemini API response that may be wrapped in markdown code blocks
    """
    logger.info(f"Raw response length: {len(raw_response)}")
    logger.info(f"Raw response first 200 chars: {repr(raw_response[:200])}")

    # Clean up the response
    cleaned_response = raw_response.strip()

    try:
        # First, try to parse as raw JSON
        return json.loads(cleaned_response)
    except json.JSONDecodeError as e:
        logger.info(f"Direct JSON parsing failed: {e}")

        # More aggressive markdown removal
        if '```json' in cleaned_response:
            # Find the start of the JSON
            start_idx = cleaned_response.find('```json') + 7
            # Find the end of the JSON (look for closing ```)
            end_idx = cleaned_response.rfind('```')

            if start_idx < end_idx:
                json_string = cleaned_response[start_idx:end_idx].strip()
                logger.info(f"Extracted JSON string length: {len(json_string)}")
                logger.info(f"Extracted JSON first 100 chars: {repr(json_string[:100])}")

                try:
                    return json.loads(json_string)
                except json.JSONDecodeError as e2:
                    logger.error(f"Failed to parse extracted JSON: {e2}")
                    # Log the problematic part
                    logger.error(f"JSON string around error: {repr(json_string[max(0, e2.pos-50):e2.pos+50])}")

        # Try regex approach as fallback
        json_match = re.search(r'```json\s*(.*?)\s*```', cleaned_response, re.DOTALL)
        if json_match:
            json_string = json_match.group(1).strip()
            logger.info(f"Regex extracted JSON: {repr(json_string[:100])}")
            try:
                return json.loads(json_string)
            except json.JSONDecodeError as e3:
                logger.error(f"Regex extracted JSON parsing failed: {e3}")

        # Try to find any JSON-like content
        json_match = re.search(r'(\{.*\})', cleaned_response, re.DOTALL)
        if json_match:
            json_candidate = json_match.group(1)
            logger.info(f"Found JSON candidate: {repr(json_candidate[:100])}")
            try:
                return json.loads(json_candidate)
            except json.JSONDecodeError as e4:
                logger.error(f"JSON candidate parsing failed: {e4}")

        # If all else fails, save the raw response for debugging
        logger.error(f"Complete raw response: {repr(raw_response)}")
        raise ValueError(f"No valid JSON found in response. All parsing methods failed.")

class HomeView(TemplateView):
    template_name = 'waste_classifier/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['states'] = WasteClassification.INDIAN_STATES
        classifications = WasteClassification.objects.all()[:6]
        # add confidence percentages
        for c in classifications:
            c.confidence_percentage = round(c.confidence_score * 100, 2) if c.confidence_score else 0
        context['recent_classifications'] = classifications
        context['total_classifications'] = WasteClassification.objects.count()
        return context


class HistoryView(TemplateView):
    template_name = 'waste_classifier/history.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        classifications = WasteClassification.objects.all()
        for c in classifications:
            c.confidence_percentage = round(c.confidence_score * 100, 2) if c.confidence_score else 0
        context['classifications'] = classifications
        return context


class ClassificationDetailView(DetailView):
    model = WasteClassification
    template_name = 'waste_classifier/detail.html'
    context_object_name = 'classification'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['confidence_percentage'] = round(self.object.confidence_score * 100, 2) if self.object.confidence_score else 0
        return context


class WasteAnalysisAPIView(APIView):
    """API endpoint for waste image analysis using Gemini"""
    parser_classes = [MultiPartParser, FormParser]
    renderer_classes = [JSONRenderer, BrowsableAPIRenderer]

    def get(self, request):
        """Return API information and upload form data for browsable API"""
        return Response({
            'message': 'Waste Analysis API - POST an image and state to analyze waste',
            'endpoint': '/api/analyze/',
            'method': 'POST',
            'required_fields': {
                'image': 'Image file (jpg, png, webp, bmp) - Max 10MB',
                'state': 'Indian state code'
            },
            'available_states': dict(WasteClassification.INDIAN_STATES),
            'waste_categories': [
                {'code': choice[0], 'name': choice[1]}
                for choice in WasteClassification.WASTE_CATEGORIES
            ],
            'example_curl': """
curl -X POST http://127.0.0.1:8000/api/analyze/ \\
  -F "image=@/path/to/image.jpg" \\
  -F "state=MH"
            """.strip()
        })

    def post(self, request):
        """Process waste image analysis"""
        serializer = WasteAnalysisInputSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Extract validated data
            image = serializer.validated_data['image']
            state_code = serializer.validated_data['state']

            # Create WasteClassification instance
            waste_classification = WasteClassification.objects.create(
                image=image,
                state=state_code
            )

            # Initialize Gemini analyzer
            analyzer = GeminiWasteAnalyzer()
            state_name = analyzer.get_state_name_from_code(state_code)

            # Analyze image using Gemini API
            analysis_result = analyzer.analyze_waste_image(
                image_path=waste_classification.image.path,
                state_code=state_code,
                state_name=state_name
            )

            if not analysis_result['success']:
                return Response({
                    'success': False,
                    'error': analysis_result['error']
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Extract and parse analysis data with improved JSON handling
            raw_response = analysis_result['raw_response']

            try:
                data = parse_gemini_response(raw_response)
                logger.info(f"Successfully parsed Gemini response: {list(data.keys())}")
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"JSON parsing error: {e}")
                logger.error(f"Raw response type: {type(raw_response)}")
                logger.error(f"Raw response repr: {repr(raw_response[:200])}")
                return Response({
                    'success': False,
                    'error': 'Failed to parse API response as JSON',
                    'debug_info': {
                        'error_message': str(e),
                        'response_type': str(type(raw_response)),
                        'response_preview': raw_response[:200] if isinstance(raw_response, str) else str(raw_response)[:200]
                    }
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Update model instance with Gemini results
            waste_class = data.get('waste_classification', {})
            disposal = data.get('disposal_instructions', {})
            risks = data.get('risk_assessment', {})
            safety = data.get('safety_measures', {})
            additional = data.get('additional_info', {})

            waste_classification.predicted_category = waste_class.get('category', 'GENERAL')
            waste_classification.confidence_score = float(waste_class.get('confidence', 0.5))
            waste_classification.waste_description = waste_class.get('description', '')

            waste_classification.disposal_instructions = disposal.get('general_method', '')
            waste_classification.state_specific_laws = disposal.get('state_specific_laws', '')
            waste_classification.authorized_facilities = disposal.get('authorized_facilities', '')

            waste_classification.health_hazards = risks.get('health_hazards', '')
            waste_classification.environmental_risks = risks.get('environmental_risks', '')

            waste_classification.precautions = safety.get('precautions', '')
            waste_classification.protective_equipment = safety.get('protective_equipment', '')
            waste_classification.emergency_procedures = safety.get('emergency_procedures', '')

            waste_classification.recyclability_info = additional.get('recyclability', '')
            waste_classification.cost_implications = additional.get('cost_implications', '')

            waste_classification.gemini_raw_response = raw_response
            waste_classification.save()

            # Prepare API response
            response_data = {
                'success': True,
                'data': {
                    'id': waste_classification.id,
                    'waste_category': waste_classification.predicted_category,
                    'category_display': waste_classification.get_predicted_category_display(),
                    'confidence_score': round(waste_classification.confidence_score * 100, 2),
                    'state': state_code,
                    'state_display': state_name,
                    'waste_description': waste_classification.waste_description,
                    'disposal_instructions': waste_classification.disposal_instructions,
                    'state_specific_laws': waste_classification.state_specific_laws,
                    'authorized_facilities': waste_classification.authorized_facilities,
                    'health_hazards': waste_classification.health_hazards,
                    'environmental_risks': waste_classification.environmental_risks,
                    'precautions': waste_classification.precautions,
                    'protective_equipment': waste_classification.protective_equipment,
                    'emergency_procedures': waste_classification.emergency_procedures,
                    'recyclability_info': waste_classification.recyclability_info,
                    'cost_implications': waste_classification.cost_implications,
                    'image_url': waste_classification.image.url,
                    'created_at': waste_classification.created_at.isoformat()
                }
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Waste analysis error: {e}")
            return Response({
                'success': False,
                'error': f'Analysis failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WasteAnalysisView(TemplateView):
    """Traditional Django view for form submission"""
    template_name = 'waste_classifier/analyze.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['states'] = WasteClassification.INDIAN_STATES
        return context

    def post(self, request, *args, **kwargs):
        image = request.FILES.get('image')
        state = request.POST.get('state')

        if not image or not state:
            messages.error(request, 'Please provide both image and state.')
            return redirect('analyze')

        try:
            # Create classification instance
            waste_classification = WasteClassification.objects.create(
                image=image,
                state=state
            )

            # Analyze with Gemini
            analyzer = GeminiWasteAnalyzer()
            state_name = analyzer.get_state_name_from_code(state)

            analysis_result = analyzer.analyze_waste_image(
                image_path=waste_classification.image.path,
                state_code=state,
                state_name=state_name
            )

            if analysis_result['success']:
                # Parse the response with improved JSON handling
                raw_response = analysis_result['raw_response']

                try:
                    data = parse_gemini_response(raw_response)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"JSON parsing error in form view: {e}")
                    logger.error(f"Raw response: {raw_response}")
                    messages.error(request, 'Failed to parse analysis response. Please try again.')
                    return redirect('analyze')

                # Update instance with results (same as API view)
                waste_class = data.get('waste_classification', {})
                disposal = data.get('disposal_instructions', {})
                risks = data.get('risk_assessment', {})
                safety = data.get('safety_measures', {})
                additional = data.get('additional_info', {})

                waste_classification.predicted_category = waste_class.get('category', 'GENERAL')
                waste_classification.confidence_score = float(waste_class.get('confidence', 0.5))
                waste_classification.waste_description = waste_class.get('description', '')
                waste_classification.disposal_instructions = disposal.get('general_method', '')
                waste_classification.state_specific_laws = disposal.get('state_specific_laws', '')
                waste_classification.authorized_facilities = disposal.get('authorized_facilities', '')
                waste_classification.health_hazards = risks.get('health_hazards', '')
                waste_classification.environmental_risks = risks.get('environmental_risks', '')
                waste_classification.precautions = safety.get('precautions', '')
                waste_classification.protective_equipment = safety.get('protective_equipment', '')
                waste_classification.emergency_procedures = safety.get('emergency_procedures', '')
                waste_classification.recyclability_info = additional.get('recyclability', '')
                waste_classification.cost_implications = additional.get('cost_implications', '')
                waste_classification.gemini_raw_response = raw_response
                waste_classification.save()

                return redirect('results', pk=waste_classification.id)
            else:
                messages.error(request, f'Analysis failed: {analysis_result["error"]}')
                return redirect('analyze')

        except Exception as e:
            logger.error(f"Waste analysis error in form view: {e}")
            messages.error(request, f'Analysis failed: {str(e)}')
            return redirect('analyze')


class ResultsView(DetailView):
    model = WasteClassification
    template_name = 'waste_classifier/results.html'
    context_object_name = 'classification'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['confidence_percentage'] = round(self.object.confidence_score * 100, 2) if self.object.confidence_score else 0
        return context
