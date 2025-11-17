# Commercial Building Site Survey Template

## Overview
This comprehensive survey template is designed for professional commercial building assessments. It covers all critical aspects of building condition, safety, and maintenance needs.

## Survey Sections

### 1. GENERAL INFORMATION
**Purpose**: Basic building identification and survey metadata

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| survey_date | date | Yes | Date of survey inspection |
| survey_time | time | No | Time survey began |
| building_name | text | Yes | Official building name |
| building_address | text | Yes | Complete street address |
| building_type | select_one | Yes | Office, Retail, Industrial, Mixed-Use, Warehouse |
| building_size_sqft | integer | No | Total building square footage |
| num_floors | integer | No | Number of floors above ground |
| year_built | integer | No | Year building was constructed |
| last_renovation | integer | No | Year of last major renovation |
| surveyor_name | text | Yes | Name of person conducting survey |
| surveyor_company | text | No | Survey company name |
| contact_phone | phone | No | Contact phone for follow-up |
| contact_email | email | No | Contact email for reports |

### 2. EXTERIOR ASSESSMENT
**Purpose**: Evaluate building envelope and site conditions

#### Building Envelope
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| exterior_condition | select_one | Yes | Excellent, Good, Fair, Poor, Critical |
| exterior_notes | text | No | General exterior condition notes |
| roof_condition | select_one | Yes | Excellent, Good, Fair, Poor, Critical |
| roof_type | select_one | No | Flat, Pitched, Mansard, Other |
| roof_age_years | integer | No | Age of roof in years |
| roof_photos | image | No | Photos of roof condition (multiple allowed) |

#### Windows & Doors
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| windows_condition | select_one | Yes | Excellent, Good, Fair, Poor, Critical |
| num_windows_broken | integer | No | Number of broken/missing windows |
| doors_condition | select_one | Yes | Excellent, Good, Fair, Poor, Critical |
| num_doors_damaged | integer | No | Number of damaged doors |
| exterior_photos | image | No | Exterior building photos |

#### Site & Grounds
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| parking_condition | select_one | Yes | Excellent, Good, Fair, Poor, Critical |
| landscaping_condition | select_one | No | Excellent, Good, Fair, Poor, Critical |
| signage_condition | select_one | No | Excellent, Good, Fair, Poor, Critical |
| drainage_condition | select_one | No | Excellent, Good, Fair, Poor, Critical |
| grounds_photos | image | No | Site and grounds photos |

### 3. STRUCTURAL ASSESSMENT
**Purpose**: Evaluate building structural integrity

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| foundation_condition | select_one | Yes | Excellent, Good, Fair, Poor, Critical |
| foundation_issues | text | No | Description of foundation problems |
| framing_condition | select_one | Yes | Excellent, Good, Fair, Poor, Critical |
| load_bearing_walls | select_one | Yes | Excellent, Good, Fair, Poor, Critical |
| floor_structure | select_one | Yes | Excellent, Good, Fair, Poor, Critical |
| structural_photos | image | No | Structural issues photos |
| structural_notes | text | No | Additional structural observations |

### 4. MECHANICAL SYSTEMS
**Purpose**: Assess building systems functionality

#### HVAC System
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| hvac_condition | select_one | Yes | Excellent, Good, Fair, Poor, Critical |
| hvac_age_years | integer | No | Age of HVAC system |
| hvac_type | select_one | No | Central Air, Roof-top Units, Heat Pumps, Other |
| hvac_last_service | date | No | Date of last maintenance |
| heating_works | select_one | Yes | Yes, No, Unknown |
| cooling_works | select_one | Yes | Yes, No, Unknown |

#### Electrical System
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| electrical_condition | select_one | Yes | Excellent, Good, Fair, Poor, Critical |
| electrical_panel_location | text | No | Location of main electrical panel |
| electrical_panel_photo | image | No | Photo of main electrical panel |
| num_breakers | integer | No | Number of circuit breakers |
| electrical_notes | text | No | Electrical system observations |

#### Plumbing System
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| plumbing_condition | select_one | Yes | Excellent, Good, Fair, Poor, Critical |
| water_pressure | select_one | No | Good, Low, High, Unknown |
| plumbing_leaks | select_one | No | None visible, Minor leaks, Major leaks |
| sewer_backup | select_one | No | No, Yes - minor, Yes - major |
| plumbing_photos | image | No | Plumbing issues photos |

### 5. INTERIOR ASSESSMENT
**Purpose**: Evaluate interior spaces and finishes

#### Common Areas
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| lobby_condition | select_one | No | Excellent, Good, Fair, Poor, Critical |
| hallways_condition | select_one | No | Excellent, Good, Fair, Poor, Critical |
| elevator_condition | select_one | No | Excellent, Good, Fair, Poor, Critical |
| num_elevators | integer | No | Number of elevators |
| elevator_certified | select_one | No | Yes, No, Unknown |

#### Office/Retail Spaces
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| office_spaces_condition | select_one | No | Excellent, Good, Fair, Poor, Critical |
| floor_condition | select_one | No | Excellent, Good, Fair, Poor, Critical |
| ceiling_condition | select_one | No | Excellent, Good, Fair, Poor, Critical |
| wall_condition | select_one | No | Excellent, Good, Fair, Poor, Critical |
| interior_photos | image | No | Interior space photos |

#### Restrooms
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| restroom_condition | select_one | No | Excellent, Good, Fair, Poor, Critical |
| num_restrooms | integer | No | Number of restroom facilities |
| restroom_cleanliness | select_one | No | Excellent, Good, Fair, Poor, Critical |
| plumbing_fixtures | select_one | No | Working, Some issues, Major problems |

### 6. SAFETY & COMPLIANCE
**Purpose**: Check safety systems and regulatory compliance

#### Fire Safety
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| fire_alarm_condition | select_one | Yes | Excellent, Good, Fair, Poor, Critical |
| sprinkler_system | select_one | Yes | Working, Not working, No system |
| fire_extinguishers | select_one | Yes | Present & charged, Missing, Expired |
| emergency_exits | select_one | Yes | Clear & marked, Obstructed, Inadequate |
| exit_signs | select_one | Yes | Working, Not working, Missing |

#### ADA Compliance
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| ada_entrance | select_one | No | Compliant, Non-compliant, Unknown |
| ada_parking | select_one | No | Compliant, Non-compliant, Unknown |
| ada_restrooms | select_one | No | Compliant, Non-compliant, Unknown |
| ada_ramps | select_one | No | Compliant, Non-compliant, Unknown |

#### Security
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| security_system | select_one | No | Present & working, Present but issues, No system |
| locks_condition | select_one | No | Excellent, Good, Fair, Poor, Critical |
| lighting_condition | select_one | No | Excellent, Good, Fair, Poor, Critical |

### 7. MAINTENANCE ISSUES
**Purpose**: Document needed repairs and improvements

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| issue_description | text | No | Description of maintenance issue |
| issue_location | text | No | Where in building is the issue |
| issue_priority | select_one | No | Critical, High, Medium, Low |
| issue_category | select_one | No | Structural, Electrical, Plumbing, HVAC, Safety, Cosmetic |
| estimated_cost | integer | No | Rough cost estimate in dollars |
| issue_photo | image | No | Photo of the maintenance issue |
| repair_notes | text | No | Additional repair recommendations |

### 8. SUMMARY & RECOMMENDATIONS
**Purpose**: Overall assessment and next steps

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| overall_condition | select_one | Yes | Excellent, Good, Fair, Poor, Critical |
| immediate_action_needed | select_one | Yes | Yes, No |
| immediate_action_description | text | No | What immediate actions are needed |
| recommended_timeline | select_one | No | Immediate (1-3 months), Short-term (3-12 months), Long-term (1-3 years) |
| total_estimated_cost | integer | No | Total estimated repair costs |
| priority_repairs | text | No | List of highest priority repairs |
| general_notes | text | No | Any additional observations or recommendations |
| final_photos | image | No | Additional photos as needed |

## XLSForm Structure

To create this survey in KoboToolbox, create an Excel file with these tabs:

### survey tab:
```
type,name,label,required,hint,relevant
start,start,,
end,end,,
date,survey_date,Survey Date,yes,
time,survey_time,Survey Time,no,
text,building_name,Building Name,yes,
text,building_address,Building Address,yes,
select_one building_type,building_type,Building Type,yes,
integer,building_size_sqft,Building Size (sq ft),no,
integer,num_floors,Number of Floors,no,
integer,year_built,Year Built,no,
integer,last_renovation,Year of Last Renovation,no,
text,surveyor_name,Surveyor Name,yes,
text,surveyor_company,Survey Company,no,
text,contact_phone,Contact Phone,no,
text,contact_email,Contact Email,no,
select_one condition_rating,exterior_condition,Exterior Condition,yes,
text,exterior_notes,Exterior Notes,no,
select_one condition_rating,roof_condition,Roof Condition,yes,
select_one roof_type,roof_type,Roof Type,no,
integer,roof_age_years,Roof Age (years),no,
image,roof_photos,Roof Photos,no,,
select_one condition_rating,windows_condition,Windows Condition,yes,
integer,num_windows_broken,Broken Windows Count,no,
select_one condition_rating,doors_condition,Doors Condition,yes,
integer,num_doors_damaged,Damaged Doors Count,no,
image,exterior_photos,Exterior Photos,no,,
select_one condition_rating,parking_condition,Parking Condition,yes,
select_one condition_rating,landscaping_condition,Landscaping Condition,no,
select_one condition_rating,signage_condition,Signage Condition,no,
select_one condition_rating,drainage_condition,Drainage Condition,no,
image,grounds_photos,Grounds Photos,no,,
select_one condition_rating,foundation_condition,Foundation Condition,yes,
text,foundation_issues,Foundation Issues,no,
select_one condition_rating,framing_condition,Framing Condition,yes,
select_one condition_rating,load_bearing_walls,Load Bearing Walls Condition,yes,
select_one condition_rating,floor_structure,Floor Structure Condition,yes,
image,structural_photos,Structural Photos,no,,
text,structural_notes,Structural Notes,no,
select_one condition_rating,hvac_condition,HVAC Condition,yes,
integer,hvac_age_years,HVAC Age (years),no,
select_one hvac_type,hvac_type,HVAC Type,no,
date,hvac_last_service,Last HVAC Service,no,
select_one yes_no,heating_works,Heating Works,yes,
select_one yes_no,cooling_works,Cooling Works,yes,
select_one condition_rating,electrical_condition,Electrical Condition,yes,
text,electrical_panel_location,Electrical Panel Location,no,
image,electrical_panel_photo,Electrical Panel Photo,no,
integer,num_breakers,Number of Breakers,no,
text,electrical_notes,Electrical Notes,no,
select_one condition_rating,plumbing_condition,Plumbing Condition,yes,
select_one water_pressure,water_pressure,Water Pressure,no,
select_one leak_severity,plumbing_leaks,Visible Plumbing Leaks,no,
select_one sewer_backup,sewer_backup,Sewer Backup History,no,
image,plumbing_photos,Plumbing Photos,no,,
select_one condition_rating,lobby_condition,Lobby Condition,no,
select_one condition_rating,hallways_condition,Hallways Condition,no,
select_one condition_rating,elevator_condition,Elevator Condition,no,
integer,num_elevators,Number of Elevators,no,
select_one yes_no,elevator_certified,Elevator Certified,no,
select_one condition_rating,office_spaces_condition,Office Spaces Condition,no,
select_one condition_rating,floor_condition,Floor Condition,no,
select_one condition_rating,ceiling_condition,Ceiling Condition,no,
select_one condition_rating,wall_condition,Wall Condition,no,
image,interior_photos,Interior Photos,no,,
select_one condition_rating,restroom_condition,Restroom Condition,no,
integer,num_restrooms,Number of Restrooms,no,
select_one condition_rating,restroom_cleanliness,Restroom Cleanliness,no,
select_one plumbing_condition,plumbing_fixtures,Plumbing Fixtures Condition,no,
select_one condition_rating,fire_alarm_condition,Fire Alarm Condition,yes,
select_one sprinkler_condition,sprinkler_system,Sprinkler System,yes,
select_one extinguisher_condition,fire_extinguishers,Fire Extinguishers,yes,
select_one exit_condition,emergency_exits,Emergency Exits,yes,
select_one exit_sign_condition,exit_signs,Exit Signs,yes,
select_one ada_compliance,ada_entrance,ADA Entrance Compliant,no,
select_one ada_compliance,ada_parking,ADA Parking Compliant,no,
select_one ada_compliance,ada_restrooms,ADA Restrooms Compliant,no,
select_one ada_compliance,ada_ramps,ADA Ramps Compliant,no,
select_one security_condition,security_system,Security System,no,
select_one condition_rating,locks_condition,Locks Condition,no,
select_one condition_rating,lighting_condition,Lighting Condition,no,
begin_repeat,maintenance_issues,Maintenance Issues,
text,issue_description,Issue Description,no,
text,issue_location,Issue Location,no,
select_one priority_level,issue_priority,Issue Priority,no,
select_one issue_category,issue_category,Issue Category,no,
integer,estimated_cost,Estimated Cost ($),no,
image,issue_photo,Issue Photo,no,
text,repair_notes,Repair Notes,no,
end_repeat,,
select_one condition_rating,overall_condition,Overall Building Condition,yes,
select_one yes_no,immediate_action_needed,Immediate Action Needed,yes,
text,immediate_action_description,Immediate Action Description,no,${immediate_action_needed} = 'yes',
select_one timeline,recommended_timeline,Recommended Timeline,no,
integer,total_estimated_cost,Total Estimated Cost ($),no,
text,priority_repairs,Priority Repairs List,no,
text,general_notes,General Notes,no,
image,final_photos,Additional Photos,no,,
```

### choices tab:
```
list_name,name,label
building_type,office,Office Building
building_type,retail,Retail/Commercial
building_type,industrial,Industrial
building_type,mixed_use,Mixed-Use
building_type,warehouse,Warehouse
condition_rating,excellent,Excellent
condition_rating,good,Good
condition_rating,fair,Fair
condition_rating,poor,Poor
condition_rating,critical,Critical
roof_type,flat,Flat
roof_type,pitched,Pitched
roof_type,mansard,Mansard
roof_type,other,Other
water_pressure,good,Good
water_pressure,low,Low
water_pressure,high,High
water_pressure,unknown,Unknown
leak_severity,none,None visible
leak_severity,minor,Minor leaks
leak_severity,major,Major leaks
sewer_backup,no,No
sewer_backup,minor_yes,Yes - minor
sewer_backup,major_yes,Yes - major
hvac_type,central_air,Central Air
hvac_type,roof_top,Roof-top Units
hvac_type,heat_pumps,Heat Pumps
hvac_type,other,Other
yes_no,yes,Yes
yes_no,no,No
yes_no,unknown,Unknown
sprinkler_condition,working,Working
sprinkler_condition,not_working,Not working
sprinkler_condition,no_system,No system
extinguisher_condition,present_charged,Present & charged
extinguisher_condition,missing,Missing
extinguisher_condition,expired,Expired
exit_condition,clear_marked,Clear & marked
exit_condition,obstructed,Obstructed
exit_condition,inadequate,Inadequate
exit_sign_condition,working,Working
exit_sign_condition,not_working,Not working
exit_sign_condition,missing,Missing
ada_compliance,compliant,Compliant
ada_compliance,non_compliant,Non-compliant
ada_compliance,unknown,Unknown
security_condition,present_working,Present & working
security_condition,present_issues,Present but issues
security_condition,no_system,No system
priority_level,critical,Critical
priority_level,high,High
priority_level,medium,Medium
priority_level,low,Low
issue_category,structural,Structural
issue_category,electrical,Electrical
issue_category,plumbing,Plumbing
issue_category,hvac,HVAC
issue_category,safety,Safety
issue_category,cosmetic,Cosmetic
timeline,immediate,Immediate (1-3 months)
timeline,short_term,Short-term (3-12 months)
timeline,long_term,Long-term (1-3 years)
```

## How to Use This Template

1. **Create Excel File**: Create a new Excel workbook with tabs named `survey` and `choices`
2. **Copy Data**: Copy the survey and choices data above into the respective tabs
3. **Import to KoboToolbox**: Go to your KoboToolbox form builder and import the XLSForm
4. **Test**: Deploy the form and test it on your device before using in production
5. **Customize**: Modify questions based on your specific survey requirements

## Key Features

- **Comprehensive Coverage**: All major building systems and safety requirements
- **Photo Documentation**: Multiple photo fields for visual evidence
- **Priority System**: Issues categorized by urgency and type
- **Cost Estimation**: Fields for repair cost tracking
- **ADA Compliance**: Accessibility assessment built-in
- **Repeat Groups**: Maintenance issues can be added as needed
- **Conditional Logic**: Some questions only appear based on previous answers

This template provides a solid foundation for professional commercial building surveys and can be customized based on specific client requirements or building types.
