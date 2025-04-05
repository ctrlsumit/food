# scanner/views.py
import json
import base64
import requests
import os
from datetime import datetime
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# API keys - ideally store in environment variables
CLARIFAI_API_KEY = os.environ.get('CLARIFAI_API_KEY', 'd8d417db5d284c15bb299394296bf287')
SPOONACULAR_API_KEY = os.environ.get('SPOONACULAR_API_KEY', 'bdf06809579e4acbac431126686abb07')
CLARIFAI_MODEL = 'bd367be194cf45149e75f01d59f77ba7'  # Default food model ID

# Simple in-memory database for feedback
# In production, you'd use a proper database model
feedback_data = []

def index(request):
    """Render main page"""
    return render(request, 'scanner/index.html')

@csrf_exempt
def analyze_food(request):
    """API endpoint to analyze food image"""
    if request.method == 'POST':
        try:
            # Get and process image
            image_file = request.FILES.get('image')
            if not image_file:
                return JsonResponse({'error': 'No image file provided'}, status=400)
                
            # Convert to base64
            image_data = image_file.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')

            # Prepare request to Clarifai API
            headers = {
                'Authorization': f'Key {CLARIFAI_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            data = {
                "inputs": [{
                    "data": {
                        "image": {
                            "base64": image_base64
                        }
                    }
                }]
            }
            
            # Make request to Clarifai API
            response = requests.post(
                f'https://api.clarifai.com/v2/models/{CLARIFAI_MODEL}/outputs',
                json=data,
                headers=headers
            )
            
            # Handle API errors
            if response.status_code != 200:
                return JsonResponse({
                    'error': f'Clarifai API error: {response.status_code}',
                    'details': response.text
                }, status=500)
                
            # Parse response
            concepts = response.json()['outputs'][0]['data']['concepts']
            food_items = [item['name'] for item in concepts[:5]]  # Top 5 predictions
            
            # Get nutrition and suggestions
            nutrition_info = get_nutrition_info(food_items[0])
            meal_suggestions = get_meal_suggestions(food_items[0])
            
            return JsonResponse({
                'status': 'success',
                'foods': food_items,
                'nutrition': nutrition_info,
                'suggestions': meal_suggestions
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST requests allowed'}, status=405)

def get_nutrition_info(food_item):
    """Get nutritional information from Spoonacular API"""
    try:
        response = requests.get(
            'https://api.spoonacular.com/recipes/guessNutrition',
            params={
                'title': food_item,
                'apiKey': SPOONACULAR_API_KEY
            }
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            # Fallback data
            return {
                'calories': {'value': 250, 'unit': 'calories'},
                'protein': {'value': 10, 'unit': 'g'},
                'fat': {'value': 12, 'unit': 'g'},
                'carbs': {'value': 30, 'unit': 'g'}
            }
    except:
        # Fallback data
        return {
            'calories': {'value': 250, 'unit': 'calories'},
            'protein': {'value': 10, 'unit': 'g'},
            'fat': {'value': 12, 'unit': 'g'},
            'carbs': {'value': 30, 'unit': 'g'}
        }

def get_meal_suggestions(food_item):
    """Get healthy meal suggestions based on identified food"""
    try:
        response = requests.get(
            'https://api.spoonacular.com/recipes/complexSearch',
            params={
                'query': food_item,
                'number': 3,
                'diet': 'balanced',
                'apiKey': SPOONACULAR_API_KEY
            }
        )
        
        if response.status_code == 200:
            recipes = response.json().get('results', [])
            return [{'id': r['id'], 'title': r['title'], 'image': r['image']} for r in recipes]
        else:
            # Fallback data
            return [
                {'id': 1, 'title': f'Healthy {food_item} Salad', 'image': 'https://spoonacular.com/recipeImages/496369-312x231.jpg'},
                {'id': 2, 'title': f'Baked {food_item} with Vegetables', 'image': 'https://spoonacular.com/recipeImages/716432-312x231.jpg'},
                {'id': 3, 'title': f'{food_item} Protein Bowl', 'image': 'https://spoonacular.com/recipeImages/715497-312x231.jpg'}
            ]
    except:
        # Fallback data
        return [
            {'id': 1, 'title': f'Healthy {food_item} Salad', 'image': 'https://spoonacular.com/recipeImages/496369-312x231.jpg'},
            {'id': 2, 'title': f'Baked {food_item} with Vegetables', 'image': 'https://spoonacular.com/recipeImages/716432-312x231.jpg'},
            {'id': 3, 'title': f'{food_item} Protein Bowl', 'image': 'https://spoonacular.com/recipeImages/715497-312x231.jpg'}
        ]

@csrf_exempt
def submit_feedback(request):
    """Collect user feedback about food and suggestions"""
    if request.method == 'POST':
        try:
            feedback = json.loads(request.body)
            feedback['timestamp'] = datetime.now().isoformat()
            
            # Store feedback
            feedback_data.append(feedback)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Feedback received successfully',
                'feedback_id': len(feedback_data)
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Only POST requests allowed'}, status=405)

def feedback_stats(request):
    """Get statistics about collected feedback"""
    if request.method == 'GET':
        try:
            if not feedback_data:
                return JsonResponse({'message': 'No feedback data available yet'})
                
            # Calculate basic stats
            total = len(feedback_data)
            satisfaction = sum(item.get('satisfaction', 0) for item in feedback_data) / total if total > 0 else 0
            wastage_reduced = sum(item.get('wastage_reduced', 0) for item in feedback_data) / total if total > 0 else 0
            
            return JsonResponse({
                'total_feedback': total,
                'avg_satisfaction': round(satisfaction, 1),
                'avg_wastage_reduced': round(wastage_reduced, 1),
                'recent_feedback': feedback_data[-5:] if len(feedback_data) >= 5 else feedback_data
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Only GET requests allowed'}, status=405)
