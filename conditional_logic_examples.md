# Conditional Logic Examples for Site Survey App

## Overview
This document provides practical examples of how conditional logic will work in the site survey app, showing real-world scenarios for the store survey template.

## Example 1: Electrical Issues Follow-up

### Scenario
If the user reports "Are there any exposed electrical wires?" as "Yes", then additional questions should appear about the electrical issues.

### Template Field Definition
```json
{
  "id": 6,
  "field_type": "yesno",
  "question": "Are there any exposed electrical wires?",
  "description": "Look for frayed wires, exposed connections, or improper installations",
  "required": true,
  "section": "Electrical",
  "order_index": 6
},
{
  "id": 7,
  "field_type": "text",
  "question": "Please describe the exposed wires location",
  "description": "Specify where the exposed wires are located",
  "required": true,
  "section": "Electrical",
  "order_index": 7,
  "conditions": {
    "conditions": [
      {
        "question_id": 6,
        "operator": "equals",
        "value": "Yes"
      }
    ],
    "logic": "AND"
  }
},
{
  "id": 8,
  "field_type": "photo",
  "question": "Photo of exposed electrical wires",
  "description": "Take a clear photo of the exposed wires",
  "required": true,
  "section": "Electrical",
  "order_index": 8,
  "conditions": {
    "conditions": [
      {
        "question_id": 6,
        "operator": "equals",
        "value": "Yes"
      }
    ],
    "logic": "AND"
  }
}
```

## Example 2: Structural Issues Cascade

### Scenario
If the overall structural condition is "Poor", then additional detailed questions should appear about specific structural problems.

### Template Field Definition
```json
{
  "id": 11,
  "field_type": "text",
  "question": "Overall structural condition (Good/Fair/Poor)",
  "description": "General assessment of building structure",
  "required": true,
  "section": "Structural",
  "order_index": 11,
  "options": ["Good", "Fair", "Poor"]
},
{
  "id": 12,
  "field_type": "yesno",
  "question": "Are there visible foundation cracks?",
  "description": "Check for cracks in the foundation or load-bearing walls",
  "required": true,
  "section": "Structural",
  "order_index": 12,
  "conditions": {
    "conditions": [
      {
        "question_id": 11,
        "operator": "in",
        "value": ["Poor", "Fair"]
      }
    ],
    "logic": "AND"
  }
},
{
  "id": 13,
  "field_type": "text",
  "question": "Foundation crack details",
  "description": "Describe the size, location, and severity of foundation cracks",
  "required": true,
  "section": "Structural",
  "order_index": 13,
  "conditions": {
    "conditions": [
      {
        "question_id": 11,
        "operator": "in",
        "value": ["Poor", "Fair"]
      },
      {
        "question_id": 12,
        "operator": "equals",
        "value": "Yes"
      }
    ],
    "logic": "AND"
  }
}
```

## Example 3: Safety Equipment Requirements

### Scenario
If fire extinguishers are not present or not accessible, then additional safety compliance questions should appear.

### Template Field Definition
```json
{
  "id": 18,
  "field_type": "yesno",
  "question": "Are fire extinguishers present and accessible?",
  "description": "Verify fire extinguishers are mounted properly and accessible",
  "required": true,
  "section": "Safety",
  "order_index": 18
},
{
  "id": 19,
  "field_type": "yesno",
  "question": "Is there a fire safety plan posted?",
  "description": "Check if fire evacuation routes and procedures are displayed",
  "required": true,
  "section": "Safety",
  "order_index": 19,
  "conditions": {
    "conditions": [
      {
        "question_id": 18,
        "operator": "equals",
        "value": "No"
      }
    ],
    "logic": "AND"
  }
},
{
  "id": 20,
  "field_type": "text",
  "question": "Safety deficiencies summary",
  "description": "List all safety equipment that is missing or non-compliant",
  "required": true,
  "section": "Safety",
  "order_index": 20,
  "conditions": {
    "conditions": [
      {
        "question_id": 18,
        "operator": "equals",
        "value": "No"
      }
    ],
    "logic": "AND"
  }
}
```

## Example 4: Multiple Condition Logic

### Scenario
If either HVAC systems are not working properly OR plumbing is in poor condition, then additional maintenance questions should appear.

### Template Field Definition
```json
{
  "id": 25,
  "field_type": "yesno",
  "question": "Are HVAC systems working properly?",
  "description": "Check heating, ventilation, and air conditioning",
  "required": true,
  "section": "Maintenance",
  "order_index": 25
},
{
  "id": 26,
  "field_type": "yesno",
  "question": "Is the plumbing in good condition?",
  "description": "Inspect sinks, toilets, pipes for leaks or damage",
  "required": true,
  "section": "Maintenance",
  "order_index": 26
},
{
  "id": 27,
  "field_type": "text",
  "question": "Maintenance contact information",
  "description": "Provide contact information for maintenance services",
  "required": true,
  "section": "Maintenance",
  "order_index": 27,
  "conditions": {
    "conditions": [
      {
        "question_id": 25,
        "operator": "equals",
        "value": "No"
      },
      {
        "question_id": 26,
        "operator": "equals",
        "value": "No"
      }
    ],
    "logic": "OR"
  }
},
{
  "id": 28,
  "field_type": "photo",
  "question": "Photo of maintenance issues",
  "description": "Document the HVAC or plumbing problems found",
  "required": true,
  "section": "Maintenance",
  "order_index": 28,
  "conditions": {
    "conditions": [
      {
        "question_id": 25,
        "operator": "equals",
        "value": "No"
      },
      {
        "question_id": 26,
        "operator": "equals",
        "value": "No"
      }
    ],
    "logic": "OR"
  }
}
```

## Photo Requirements Examples

### Example 1: Required Photos by Section
```json
{
  "section": "Electrical",
  "photo_requirements": {
    "required_photos": [
      {
        "id": "electrical_panel",
        "title": "Electrical Panel",
        "description": "Clear photo of main electrical panel with door open",
        "required": true
      },
      {
        "id": "exposed_wires",
        "title": "Exposed Wires",
        "description": "Photo of any exposed electrical wires found",
        "required": false,
        "conditions": {
          "conditions": [
            {
              "question_id": 6,
              "operator": "equals",
              "value": "Yes"
            }
          ],
          "logic": "AND"
        }
      }
    ]
  }
}
```

### Example 2: Photo Requirements Checklist UI
```
Electrical Section Photos:
● Electrical Panel (Required) [📷] ✓
○ Exposed Wires (Conditional) [📷] - Only if exposed wires reported

Structural Section Photos:
● Front Entrance (Required) [📷] ✓
● Main Sales Floor (Required) [📷] ✓
○ Foundation Cracks (Conditional) [📷] - Only if structural issues reported
```

## Progress Tracking Examples

### Example 1: Section-wise Progress
```json
{
  "overall_progress": 75.0,
  "sections": {
    "General": {
      "required": 4,
      "completed": 4,
      "photos_required": 0,
      "photos_taken": 0,
      "progress": 100.0
    },
    "Electrical": {
      "required": 5,
      "completed": 3,
      "photos_required": 2,
      "photos_taken": 1,
      "progress": 60.0
    },
    "Structural": {
      "required": 6,
      "completed": 4,
      "photos_required": 3,
      "photos_taken": 2,
      "progress": 66.7
    },
    "Safety": {
      "required": 5,
      "completed": 5,
      "photos_required": 1,
      "photos_taken": 1,
      "progress": 100.0
    }
  }
}
```

### Example 2: Progress UI Display
```
Overall Progress: 75.0%
████████████████████████████████████████████████████████████████████████████████
████████████████████████████████████████████████████████████████████████████████

General:          4/4 ████████████████████████████████████████████████████████████ 100%
Electrical:       3/5 ████████████████████████████████████████████                 60%
Structural:       4/6 ████████████████████████████████████████████████             67%
Safety:           5/5 ████████████████████████████████████████████████████████████ 100%
```

## Implementation Benefits

1. **Dynamic Surveys**: Questions appear only when relevant, reducing survey fatigue
2. **Contextual Photos**: Photo requirements adapt to the specific issues found
3. **Accurate Progress**: Progress tracking reflects the actual work completed
4. **Better UX**: Users only see relevant fields, making surveys more efficient
5. **Data Quality**: Conditional logic ensures consistent and complete data collection

## Testing Scenarios

1. **Basic Conditional Logic**: Test simple yes/no conditions
2. **Multi-condition Logic**: Test AND/OR logic with multiple conditions
3. **Nested Conditions**: Test conditions that depend on other conditional fields
4. **Photo Requirements**: Test conditional photo requirements
5. **Progress Calculation**: Test accurate progress tracking with conditional fields
6. **Edge Cases**: Test empty responses, missing conditions, etc.