#!/usr/bin/env python3
"""Create field mapping for SFDC fields."""

# Mapping from config field names to actual SFDC field names
FIELD_MAPPING = {
    "Case_Number": "CaseNumber",
    "Subject_Description": "Subject_description__c", 
    "Description_Description": "Description",
    "Issue_Plain_Text": "Issue__c",
    "Cause_Plain_Text": "Cause_plain_text__c", 
    "Resolution_Plain_Text": "Resulution_plain_text__c",  # Note: typo in SFDC field name
    "Status_Text": "Status",
    "TextBody": "BodyText__c"
}

def get_actual_field_names(config_fields):
    """Map config field names to actual SFDC field names."""
    return [FIELD_MAPPING.get(field, field) for field in config_fields]

if __name__ == "__main__":
    config_fields = [
        "Case_Number",
        "Subject_Description", 
        "Description_Description",
        "Issue_Plain_Text",
        "Cause_Plain_Text",
        "Resolution_Plain_Text",
        "Status_Text",
        "TextBody"
    ]
    
    actual_fields = get_actual_field_names(config_fields)
    
    print("Field Mapping:")
    for config, actual in zip(config_fields, actual_fields):
        print(f"  {config} -> {actual}")