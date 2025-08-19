import google.generativeai as genai
import json
import logging
from PIL import Image
from django.conf import settings
from typing import Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

class GeminiWasteAnalyzer:
    def __init__(self):
        """Initialize Gemini API client"""
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in settings")

        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

        # State code to name mapping
        self.INDIAN_STATES = {
            'AP': 'Andhra Pradesh', 'AR': 'Arunachal Pradesh', 'AS': 'Assam',
            'BR': 'Bihar', 'CT': 'Chhattisgarh', 'GA': 'Goa', 'GJ': 'Gujarat',
            'HR': 'Haryana', 'HP': 'Himachal Pradesh', 'JH': 'Jharkhand',
            'KA': 'Karnataka', 'KL': 'Kerala', 'MP': 'Madhya Pradesh',
            'MH': 'Maharashtra', 'MN': 'Manipur', 'ML': 'Meghalaya',
            'MZ': 'Mizoram', 'NL': 'Nagaland', 'OR': 'Odisha', 'PB': 'Punjab',
            'RJ': 'Rajasthan', 'SK': 'Sikkim', 'TN': 'Tamil Nadu',
            'TG': 'Telangana', 'TR': 'Tripura', 'UP': 'Uttar Pradesh',
            'UT': 'Uttarakhand', 'WB': 'West Bengal', 'AN': 'Andaman and Nicobar',
            'CH': 'Chandigarh', 'DH': 'Dadra and Nagar Haveli', 'DD': 'Daman and Diu',
            'DL': 'Delhi', 'JK': 'Jammu and Kashmir', 'LA': 'Ladakh',
            'LD': 'Lakshadweep', 'PY': 'Puducherry',
        }

    def get_state_name_from_code(self, state_code: str) -> str:
        """Convert state code to full name"""
        return self.INDIAN_STATES.get(state_code, state_code)

    def _parse_gemini_json_response(self, raw_response: str) -> Dict[str, Any]:
        """
        Parse Gemini response that may be wrapped in markdown code blocks
        """
        logger.info(f"Parsing Gemini response of length: {len(raw_response)}")

        # Clean up the response
        cleaned = raw_response.strip()

        # Remove markdown code blocks
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]  # Remove '```json'
        elif cleaned.startswith('```'):
            cleaned = cleaned[3:]  # Remove '```'

        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]  # Remove '```'

        # Clean up any remaining whitespace
        cleaned = cleaned.strip()

        logger.info(f"Cleaned response first 100 chars: {repr(cleaned[:100])}")

        try:
            parsed_data = json.loads(cleaned)
            logger.info("Successfully parsed JSON from Gemini response")
            return parsed_data
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.error(f"Error at position {e.pos}")
            if e.pos < len(cleaned):
                logger.error(f"Text around error: {repr(cleaned[max(0, e.pos-20):e.pos+20])}")
            logger.error(f"Full cleaned response: {repr(cleaned)}")
            raise

    def analyze_waste_image(self, image_path: str, state_code: str, state_name: str) -> Dict[str, Any]:
        """
        Analyze waste image using Gemini Vision API

        Args:
            image_path: Path to the uploaded image
            state_code: Indian state code (e.g., 'MH', 'KA')
            state_name: Full state name

        Returns:
            Dictionary with analysis results
        """
        try:
            # Load and validate image
            if not os.path.exists(image_path):
                return {
                    'success': False,
                    'error': f'Image file not found: {image_path}'
                }

            # Open image with PIL
            image = Image.open(image_path)

            # Create comprehensive prompt for waste analysis
            prompt = self._create_analysis_prompt(state_name, state_code)

            # Generate content using Gemini
            response = self.model.generate_content([prompt, image])

            if not response or not response.text:
                return {
                    'success': False,
                    'error': 'No response received from Gemini API'
                }

            logger.info(f"Raw Gemini response: {repr(response.text[:200])}")

            # Parse JSON response with improved handling
            try:
                parsed_data = self._parse_gemini_json_response(response.text)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}")
                logger.error(f"Full raw response: {response.text}")
                return {
                    'success': False,
                    'error': 'Failed to parse API response as JSON',
                    'raw_response': response.text
                }

            # Validate required fields
            if not self._validate_response_structure(parsed_data):
                return {
                    'success': False,
                    'error': 'Invalid response structure from Gemini API',
                    'raw_response': response.text
                }

            return {
                'success': True,
                'data': parsed_data,
                'raw_response': response.text
            }

        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return {
                'success': False,
                'error': f'Gemini API error: {str(e)}'
            }

    def _create_analysis_prompt(self, state_name: str, state_code: str) -> str:
        """Create comprehensive prompt for waste analysis"""
        return f"""
You are an expert waste management consultant specializing in Indian waste disposal regulations and environmental safety. Analyze the uploaded image and provide comprehensive waste classification and disposal guidance.

CRITICAL: Respond with ONLY valid JSON. Do not wrap your response in markdown code blocks or add any additional text. Your entire response must be parseable as JSON.

Required JSON Response Format:
{{
    "waste_classification": {{
        "category": "MEDICAL|E_WASTE|GENERAL|RECYCLABLE|NON_RECYCLABLE|HAZARDOUS|ORGANIC",
        "confidence": 0.85,
        "description": "Detailed description of the waste type identified"
    }},
    "disposal_instructions": {{
        "general_method": "Step-by-step disposal instructions",
        "state_specific_laws": "Specific regulations for {state_name} ({state_code})",
        "authorized_facilities": "List of authorized disposal facilities in {state_name}"
    }},
    "risk_assessment": {{
        "health_hazards": "Potential health risks and symptoms",
        "environmental_risks": "Environmental impact and contamination risks"
    }},
    "safety_measures": {{
        "precautions": "Safety precautions when handling this waste",
        "protective_equipment": "Required PPE and protective gear",
        "emergency_procedures": "Emergency response for accidents/exposure"
    }},
    "additional_info": {{
        "recyclability": "Recycling potential and processes",
        "cost_implications": "Estimated disposal costs and economic factors"
    }}
}}

Analysis Guidelines:
1. Classify waste into one of these categories: MEDICAL, E_WASTE, GENERAL, RECYCLABLE, NON_RECYCLABLE, HAZARDOUS, ORGANIC
2. Provide confidence score between 0.1-1.0
3. Include state-specific regulations for {state_name}
4. Focus on Indian waste management rules (Waste Management Rules 2016, Plastic Waste Management Rules, etc.)
5. Provide practical, actionable advice for common citizens
6. Include contact information for local authorities when relevant
7. Consider cultural and regional disposal practices in {state_name}

REMEMBER: Return ONLY the JSON object. No markdown, no additional text, no code blocks.
"""

    def _validate_response_structure(self, data: Dict[str, Any]) -> bool:
        """Validate that the response has the expected structure"""
        required_keys = [
            'waste_classification',
            'disposal_instructions',
            'risk_assessment',
            'safety_measures',
            'additional_info'
        ]

        # Check main keys exist
        for key in required_keys:
            if key not in data:
                logger.error(f"Missing required key: {key}")
                return False

        # Check waste_classification has required fields
        waste_class = data.get('waste_classification', {})
        if not all(k in waste_class for k in ['category', 'confidence', 'description']):
            logger.error("Invalid waste_classification structure")
            return False

        # Validate category
        valid_categories = ['MEDICAL', 'E_WASTE', 'GENERAL', 'RECYCLABLE', 'NON_RECYCLABLE', 'HAZARDOUS', 'ORGANIC']
        if waste_class.get('category') not in valid_categories:
            logger.error(f"Invalid category: {waste_class.get('category')}")
            return False

        # Validate confidence score
        confidence = waste_class.get('confidence')
        if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
            logger.error(f"Invalid confidence score: {confidence}")
            return False

        return True

    def test_api_connection(self) -> Dict[str, Any]:
        """Test Gemini API connection"""
        try:
            # Simple test prompt
            response = self.model.generate_content("Reply with 'API connection successful'")

            if response and response.text:
                return {
                    'success': True,
                    'message': 'Gemini API connection successful',
                    'response': response.text
                }
            else:
                return {
                    'success': False,
                    'error': 'No response from Gemini API'
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'API connection failed: {str(e)}'
            }
