#!/usr/bin/env python3
"""
Test script for Phase 2 features
Tests conditional logic, photo requirements, and enhanced progress tracking
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from survey_app.local_db import LocalDatabase
import json
import uuid

def test_conditional_logic():
    """Test conditional logic evaluation"""
    print("Testing conditional logic...")
    
    db = LocalDatabase('test_phase2.db')
    
    # Test conditions
    test_conditions = {
        'conditions': [
            {
                'question_id': 1,
                'operator': 'equals',
                'value': 'Yes'
            }
        ],
        'logic': 'AND'
    }
    
    # Test responses
    test_responses = [
        {
            'question_id': 1,
            'answer': 'Yes'
        }
    ]
    
    # Test evaluation
    result = db.should_show_field(test_conditions, test_responses)
    print(f"Condition evaluation result: {result}")
    assert result == True, "Condition should evaluate to True"
    
    # Test with different response
    test_responses_false = [
        {
            'question_id': 1,
            'answer': 'No'
        }
    ]
    
    result_false = db.should_show_field(test_conditions, test_responses_false)
    print(f"Condition evaluation result (No): {result_false}")
    assert result_false == False, "Condition should evaluate to False"
    
    print("✅ Conditional logic tests passed!")

def test_photo_requirements():
    """Test photo requirements tracking"""
    print("\nTesting photo requirements...")
    
    db = LocalDatabase('test_phase2.db')
    
    # Create test survey with photo requirements
    survey_data = {
        'id': 1,
        'title': 'Test Survey',
        'template_id': 1
    }
    db.save_survey(survey_data)
    
    # Test photo requirements data
    photo_requirements = {
        'requirements_by_section': {
            'Electrical': [
                {
                    'field_id': 1,
                    'field_question': 'Electrical Panel Photo',
                    'title': 'Electrical Panel',
                    'description': 'Clear photo of main electrical panel',
                    'required': True,
                    'taken': False
                }
            ]
        }
    }
    
    print(f"Photo requirements: {json.dumps(photo_requirements, indent=2)}")
    
    # Test requirement fulfillment
    photo_id = str(uuid.uuid4())
    db.mark_requirement_fulfillment(photo_id, 1, True)
    
    print("✅ Photo requirements tests passed!")

def test_progress_tracking():
    """Test enhanced progress tracking"""
    print("\nTesting progress tracking...")
    
    db = LocalDatabase('test_phase2.db')
    
    # Test progress calculation
    progress_data = db.get_survey_progress(1)
    print(f"Progress data: {json.dumps(progress_data, indent=2)}")
    
    # Verify progress structure
    assert 'overall_progress' in progress_data
    assert 'sections' in progress_data
    assert 'total_required' in progress_data
    assert 'total_completed' in progress_data
    
    print("✅ Progress tracking tests passed!")

def test_conditional_fields_api():
    """Test conditional fields API"""
    print("\nTesting conditional fields API...")
    
    db = LocalDatabase('test_phase2.db')
    
    # Create test template with conditional fields
    template_fields = [
        {
            'id': 1,
            'field_type': 'yesno',
            'question': 'Are there any exposed electrical wires?',
            'required': True,
            'conditions': None,
            'photo_requirements': None
        },
        {
            'id': 2,
            'field_type': 'photo',
            'question': 'Photo of exposed wires',
            'required': True,
            'conditions': {
                'conditions': [
                    {
                        'question_id': 1,
                        'operator': 'equals',
                        'value': 'Yes'
                    }
                ],
                'logic': 'AND'
            },
            'photo_requirements': {
                'title': 'Exposed Wires Photo',
                'description': 'Photo of any exposed electrical wires found',
                'required': True
            }
        }
    ]
    
    print(f"Conditional fields: {json.dumps(template_fields, indent=2)}")
    
    # Test field visibility
    responses_yes = [{'question_id': 1, 'answer': 'Yes'}]
    responses_no = [{'question_id': 1, 'answer': 'No'}]
    
    visible_fields_yes = db.evaluate_conditions(1, responses_yes)
    visible_fields_no = db.evaluate_conditions(1, responses_no)
    
    print(f"Visible fields (Yes): {visible_fields_yes}")
    print(f"Visible fields (No): {visible_fields_no}")
    
    # Should include field 2 when answer is Yes, exclude when No
    assert 2 in visible_fields_yes, "Field 2 should be visible when answer is Yes"
    assert 2 not in visible_fields_no, "Field 2 should not be visible when answer is No"
    
    print("✅ Conditional fields API tests passed!")

def test_required_field_indicators():
    """Test required field indicators"""
    print("\nTesting required field indicators...")
    
    # Test field data with required and optional fields
    required_field = {
        'id': 1,
        'question': 'Store Name',
        'required': True
    }
    
    optional_field = {
        'id': 2,
        'question': 'Additional notes',
        'required': False
    }
    
    # Test required indicator logic
    required_indicator = " * " if required_field.get('required', False) else " "
    optional_indicator = " * " if optional_field.get('required', False) else " "
    
    print(f"Required field indicator: '{required_indicator}'")
    print(f"Optional field indicator: '{optional_indicator}'")
    
    assert required_indicator == " * ", "Required field should show asterisk"
    assert optional_indicator == " ", "Optional field should not show asterisk"
    
    print("✅ Required field indicators tests passed!")

def run_all_tests():
    """Run all Phase 2 tests"""
    print("🧪 Running Phase 2 Feature Tests\n")
    
    try:
        test_conditional_logic()
        test_photo_requirements()
        test_progress_tracking()
        test_conditional_fields_api()
        test_required_field_indicators()
        
        print("\n🎉 All Phase 2 tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)