"""
Store Survey Template - Comprehensive site survey for retail stores
This template covers electrical, structural, safety, and maintenance inspections
"""

from shared.enums import SurveySection, QuestionType

STORE_SURVEY_TEMPLATE = {
    'name': 'Store Survey Template',
    'description': 'Comprehensive survey template for retail stores covering electrical, structural, and safety aspects',
    'category': 'store',
    'is_default': True,
    'section_tags': {
        SurveySection.GENERAL.value: ['overview'],
        SurveySection.ELECTRICAL.value: ['panel', 'breaker', 'wiring'],
        SurveySection.STRUCTURAL.value: ['roof', 'foundation', 'framing'],
        SurveySection.SAFETY.value: ['fire-safety', 'egress'],
        SurveySection.MAINTENANCE.value: ['hvac', 'plumbing'],
        SurveySection.PHOTOS.value: ['survey-wide'],
        SurveySection.SUMMARY.value: ['final']
    },
    'fields': [
        # General Information
        {
            'field_type': QuestionType.TEXT.value,
            'question': 'Store Name',
            'description': 'Full business name of the retail location',
            'required': True,
            'section': SurveySection.GENERAL.value,
            'order_index': 1
        },
        {
            'field_type': QuestionType.TEXT.value,
            'question': 'Store Address',
            'description': 'Complete street address including city, state, zip',
            'required': True,
            'section': SurveySection.GENERAL.value,
            'order_index': 2
        },
        {
            'field_type': QuestionType.TEXT.value,
            'question': 'Store Manager Contact',
            'description': 'Name and phone number of store manager or key contact',
            'required': False,
            'section': SurveySection.GENERAL.value,
            'order_index': 3
        },
        {
            'field_type': QuestionType.TEXT.value,
            'question': 'Survey Date',
            'description': 'Date when survey was conducted',
            'required': True,
            'section': SurveySection.GENERAL.value,
            'order_index': 4
        },

        # Electrical Section
        {
            'field_type': QuestionType.YESNO.value,
            'question': 'Are all electrical outlets functional?',
            'description': 'Check that outlets work and are not damaged',
            'required': True,
            'section': SurveySection.ELECTRICAL.value,
            'order_index': 5
        },
        {
            'field_type': QuestionType.YESNO.value,
            'question': 'Are there any exposed electrical wires?',
            'description': 'Look for frayed wires, exposed connections, or improper installations',
            'required': True,
            'section': SurveySection.ELECTRICAL.value,
            'order_index': 6
        },
        {
            'field_type': QuestionType.TEXT.value,
            'question': 'Electrical panel condition (Good/Fair/Poor)',
            'description': 'Assess the main electrical panel for damage, corrosion, or age',
            'required': True,
            'section': SurveySection.ELECTRICAL.value,
            'order_index': 7,
            'options': ['Good', 'Fair', 'Poor']
        },
        {
            'field_type': QuestionType.YESNO.value,
            'question': 'Are emergency exit lights working?',
            'description': 'Test all emergency lighting and signage',
            'required': True,
            'section': SurveySection.ELECTRICAL.value,
            'order_index': 8
        },
        {
            'field_type': QuestionType.PHOTO.value,
            'question': 'Photo of electrical panel',
            'description': 'Photograph the main electrical panel',
            'required': False,
            'section': SurveySection.ELECTRICAL.value,
            'photo_requirements': '{"description": "Must clearly show panel door, labels, and breakers", "required": true}',
            'order_index': 9
        },
        {
            'field_type': QuestionType.TEXT.value,
            'question': 'Additional electrical notes',
            'description': 'Any other electrical observations or concerns',
            'required': False,
            'section': SurveySection.ELECTRICAL.value,
            'order_index': 10
        },
        {
            'field_type': QuestionType.TEXT.value,
            'question': 'Describe any electrical safety issues found',
            'description': 'Detail location, severity, and recommended action for electrical problems',
            'required': True,
            'section': SurveySection.ELECTRICAL.value,
            'order_index': 10.5,
            'conditions': '{"conditions": [{"question_id": 6, "operator": "equals", "value": "Yes"}], "logic": "AND"}'
        },

        # Structural Section
        {
            'field_type': QuestionType.TEXT.value,
            'question': 'Overall structural condition (Good/Fair/Poor)',
            'description': 'General assessment of building structure',
            'required': True,
            'section': SurveySection.STRUCTURAL.value,
            'order_index': 11,
            'options': ['Good', 'Fair', 'Poor']
        },
        {
            'field_type': QuestionType.YESNO.value,
            'question': 'Are there any visible cracks in walls/ceiling?',
            'description': 'Check for structural cracks, especially around doors/windows',
            'required': True,
            'section': SurveySection.STRUCTURAL.value,
            'order_index': 12
        },
        {
            'field_type': QuestionType.YESNO.value,
            'question': 'Is the roof in good condition (no leaks/water damage)?',
            'description': 'Inspect for leaks, missing shingles, or water damage',
            'required': True,
            'section': SurveySection.STRUCTURAL.value,
            'order_index': 13
        },
        {
            'field_type': QuestionType.YESNO.value,
            'question': 'Are all doors and windows functional?',
            'description': 'Test operation of all entry/exit points',
            'required': True,
            'section': SurveySection.STRUCTURAL.value,
            'order_index': 14
        },
        {
            'field_type': QuestionType.PHOTO.value,
            'question': 'Photo of any structural issues',
            'description': 'Document any structural problems found',
            'required': True,
            'section': SurveySection.STRUCTURAL.value,
            'photo_requirements': '{"description": "Must clearly show crack location, size, and severity", "required": true}',
            'order_index': 15,
            'conditions': '{"conditions": [{"question_id": 12, "operator": "equals", "value": "Yes"}], "logic": "AND"}'
        },
        {
            'field_type': QuestionType.TEXT.value,
            'question': 'Floor condition (tile/carpet/concrete)',
            'description': 'Describe floor type and condition',
            'required': True,
            'section': SurveySection.STRUCTURAL.value,
            'order_index': 16
        },
        {
            'field_type': QuestionType.TEXT.value,
            'question': 'Additional structural notes',
            'description': 'Other structural observations or concerns',
            'required': False,
            'section': SurveySection.STRUCTURAL.value,
            'order_index': 17
        },

        # Safety & Compliance
        {
            'field_type': QuestionType.YESNO.value,
            'question': 'Are fire extinguishers present and accessible?',
            'description': 'Verify fire extinguishers are mounted properly and accessible',
            'required': True,
            'section': SurveySection.SAFETY.value,
            'order_index': 18
        },
        {
            'field_type': QuestionType.TEXT.value,
            'question': 'Fire extinguisher inspection date',
            'description': 'Check the last inspection date on fire extinguishers',
            'required': False,
            'section': SurveySection.SAFETY.value,
            'order_index': 19
        },
        {
            'field_type': QuestionType.YESNO.value,
            'question': 'Are emergency exits clear and marked?',
            'description': 'Ensure exit paths are unobstructed and properly signed',
            'required': True,
            'section': SurveySection.SAFETY.value,
            'order_index': 20
        },
        {
            'field_type': QuestionType.YESNO.value,
            'question': 'Is the store ADA compliant?',
            'description': 'Check for wheelchair accessibility, ramps, etc.',
            'required': True,
            'section': SurveySection.SAFETY.value,
            'order_index': 21
        },
        {
            'field_type': QuestionType.YESNO.value,
            'question': 'Are there any trip hazards?',
            'description': 'Look for uneven floors, cords, merchandise blocking aisles',
            'required': True,
            'section': SurveySection.SAFETY.value,
            'order_index': 22
        },
        {
            'field_type': QuestionType.PHOTO.value,
            'question': 'Photo of trip hazards',
            'description': 'Document any trip hazards found',
            'required': True,
            'section': SurveySection.SAFETY.value,
            'order_index': 22.5,
            'conditions': '{"conditions": [{"question_id": 22, "operator": "equals", "value": "Yes"}], "logic": "AND"}',
            'photo_requirements': '{"description": "Must clearly show hazard location and nature", "required": true}'
        },
        {
            'field_type': QuestionType.PHOTO.value,
            'question': 'Photo of safety equipment',
            'description': 'Photograph fire extinguishers, emergency exits, etc.',
            'required': False,
            'section': SurveySection.SAFETY.value,
            'order_index': 23
        },

        # Maintenance & Cleanliness
        {
            'field_type': QuestionType.TEXT.value,
            'question': 'Overall cleanliness (Excellent/Good/Fair/Poor)',
            'description': 'General assessment of store cleanliness and maintenance',
            'required': True,
            'section': SurveySection.MAINTENANCE.value,
            'order_index': 24,
            'options': ['Excellent', 'Good', 'Fair', 'Poor']
        },
        {
            'field_type': QuestionType.YESNO.value,
            'question': 'Are HVAC systems working properly?',
            'description': 'Check heating, ventilation, and air conditioning',
            'required': True,
            'section': SurveySection.MAINTENANCE.value,
            'order_index': 25
        },
        {
            'field_type': QuestionType.YESNO.value,
            'question': 'Is the plumbing in good condition?',
            'description': 'Inspect sinks, toilets, pipes for leaks or damage',
            'required': True,
            'section': SurveySection.MAINTENANCE.value,
            'order_index': 26
        },
        {
            'field_type': QuestionType.TEXT.value,
            'question': 'Lighting condition (Good/Fair/Poor)',
            'description': 'Assess overall lighting quality and functionality',
            'required': True,
            'section': SurveySection.MAINTENANCE.value,
            'order_index': 27,
            'options': ['Good', 'Fair', 'Poor']
        },
        {
            'field_type': QuestionType.TEXT.value,
            'question': 'Store layout and merchandising condition',
            'description': 'Comment on store organization and display quality',
            'required': False,
            'section': SurveySection.MAINTENANCE.value,
            'order_index': 28
        },

        # Photos
        {
            'field_type': QuestionType.PHOTO.value,
            'question': 'Front entrance photo',
            'description': 'Photograph the main store entrance',
            'required': True,
            'section': SurveySection.PHOTOS.value,
            'order_index': 29
        },
        {
            'field_type': QuestionType.PHOTO.value,
            'question': 'Main sales floor photo',
            'description': 'Wide shot of the main shopping area',
            'required': True,
            'section': SurveySection.PHOTOS.value,
            'order_index': 30
        },
        {
            'field_type': QuestionType.PHOTO.value,
            'question': 'Back room/storage photo',
            'description': 'Photograph storage areas and back rooms',
            'required': False,
            'section': SurveySection.PHOTOS.value,
            'order_index': 31
        },
        {
            'field_type': QuestionType.PHOTO.value,
            'question': 'Restroom photo',
            'description': 'Photograph customer restrooms',
            'required': False,
            'section': SurveySection.PHOTOS.value,
            'order_index': 32
        },

        # Summary
        {
            'field_type': QuestionType.TEXT.value,
            'question': 'Overall assessment summary',
            'description': 'Provide a comprehensive summary of the store condition',
            'required': True,
            'section': SurveySection.SUMMARY.value,
            'order_index': 33
        },
        {
            'field_type': QuestionType.TEXT.value,
            'question': 'Priority issues requiring immediate attention',
            'description': 'List any critical issues that need urgent repair',
            'required': False,
            'section': SurveySection.SUMMARY.value,
            'order_index': 34
        },
        {
            'field_type': QuestionType.TEXT.value,
            'question': 'Recommended maintenance schedule',
            'description': 'Suggest timeline for routine maintenance tasks',
            'required': False,
            'section': SurveySection.SUMMARY.value,
            'order_index': 35
        },
        {
            'field_type': QuestionType.TEXT.value,
            'question': 'Additional recommendations',
            'description': 'Any other suggestions for improvement',
            'required': False,
            'section': SurveySection.SUMMARY.value,
            'order_index': 36
        }
    ]
}
