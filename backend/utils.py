import hashlib
import json


def compute_photo_hash(image_data, algo='sha256'):
    """Compute cryptographic hash of image data"""
    if isinstance(image_data, bytes):
        return hashlib.new(algo, image_data).hexdigest()
    return None


def should_show_field(conditions, responses):
    """Evaluate if a field should be shown based on current responses"""
    if not conditions:
        return True
    
    condition_list = conditions.get('conditions', [])
    logic = conditions.get('logic', 'AND')
    
    results = []
    for condition in condition_list:
        question_id = condition['question_id']
        operator = condition['operator']
        expected_value = condition['value']
        
        # Find response for this question
        response = next((r for r in responses if r.get('question_id') == question_id), None)
        if not response:
            results.append(False)
            continue
        
        actual_value = response.get('answer')
        
        if operator == 'equals':
            results.append(str(actual_value) == str(expected_value))
        elif operator == 'not_equals':
            results.append(str(actual_value) != str(expected_value))
        elif operator == 'in':
            results.append(str(actual_value) in [str(v) for v in expected_value])
        elif operator == 'not_in':
            results.append(str(actual_value) not in [str(v) for v in expected_value])
    
    return all(results) if logic == 'AND' else any(results)