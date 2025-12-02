"""
Synthetic Data Generator for Denial Management System
Generates RHAIL-compatible data with realistic healthcare scenarios
"""

import random
import json
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from app.database import sync_engine, Base
from app.models import (
    DimPatient, DimPayer, DimFacility, DimDenialReason, DimProcedure, DimPhysician,
    FactClaim, FactDenial, FactPriorAuth, FactAppeal, FactRLTrace,
    DimTreatmentGuideline, DimClinicalCriteria, DimDocumentationRequirement, FactTreatmentGuidanceResult
)

random.seed(42)  # For reproducibility

# ==================== REFERENCE DATA ====================

# Common CARC codes used in RHAIL
CARC_CODES = [
    {"code": "1", "description": "Deductible Amount", "category": "PR", "denial_category": "Patient Responsibility", "appealable": False, "success_rate": 0.0},
    {"code": "2", "description": "Coinsurance Amount", "category": "PR", "denial_category": "Patient Responsibility", "appealable": False, "success_rate": 0.0},
    {"code": "3", "description": "Co-payment Amount", "category": "PR", "denial_category": "Patient Responsibility", "appealable": False, "success_rate": 0.0},
    {"code": "4", "description": "The procedure code is inconsistent with the modifier used", "category": "CO", "denial_category": "Coding Error", "appealable": True, "success_rate": 0.75},
    {"code": "5", "description": "The procedure code/bill type is inconsistent with the place of service", "category": "CO", "denial_category": "Coding Error", "appealable": True, "success_rate": 0.70},
    {"code": "16", "description": "Claim/service lacks information needed for adjudication", "category": "CO", "denial_category": "Missing Information", "appealable": True, "success_rate": 0.85},
    {"code": "18", "description": "Exact duplicate claim/service", "category": "CO", "denial_category": "Duplicate Claim", "appealable": True, "success_rate": 0.60},
    {"code": "22", "description": "This care may be covered by another payer per coordination of benefits", "category": "OA", "denial_category": "COB", "appealable": True, "success_rate": 0.55},
    {"code": "27", "description": "Expenses incurred after coverage terminated", "category": "CO", "denial_category": "Coverage", "appealable": True, "success_rate": 0.30},
    {"code": "29", "description": "The time limit for filing has expired", "category": "CO", "denial_category": "Timely Filing", "appealable": True, "success_rate": 0.25},
    {"code": "31", "description": "Patient cannot be identified as our insured", "category": "CO", "denial_category": "Eligibility", "appealable": True, "success_rate": 0.65},
    {"code": "32", "description": "Our records indicate that this dependent is not an eligible dependent", "category": "CO", "denial_category": "Eligibility", "appealable": True, "success_rate": 0.60},
    {"code": "35", "description": "Lifetime benefit maximum has been reached", "category": "CO", "denial_category": "Benefit Limit", "appealable": True, "success_rate": 0.20},
    {"code": "39", "description": "Services denied at the time authorization/pre-certification was requested", "category": "CO", "denial_category": "Prior Auth", "appealable": True, "success_rate": 0.45},
    {"code": "45", "description": "Charge exceeds fee schedule/maximum allowable", "category": "CO", "denial_category": "Fee Schedule", "appealable": True, "success_rate": 0.40},
    {"code": "50", "description": "These are non-covered services because this is not deemed a medical necessity", "category": "CO", "denial_category": "Medical Necessity", "appealable": True, "success_rate": 0.55},
    {"code": "55", "description": "Procedure/treatment is deemed experimental or investigational", "category": "CO", "denial_category": "Experimental", "appealable": True, "success_rate": 0.35},
    {"code": "96", "description": "Non-covered charge(s). At least one Remark Code must be provided", "category": "CO", "denial_category": "Non-Covered", "appealable": True, "success_rate": 0.50},
    {"code": "97", "description": "The benefit for this service is included in the payment/allowance for another service", "category": "CO", "denial_category": "Bundling", "appealable": True, "success_rate": 0.65},
    {"code": "109", "description": "Claim/service not covered by this payer/contractor", "category": "CO", "denial_category": "Non-Covered", "appealable": True, "success_rate": 0.40},
    {"code": "119", "description": "Benefit maximum for this time period or occurrence has been reached", "category": "CO", "denial_category": "Benefit Limit", "appealable": True, "success_rate": 0.25},
    {"code": "167", "description": "This (these) diagnosis(es) is (are) not covered", "category": "CO", "denial_category": "Diagnosis", "appealable": True, "success_rate": 0.50},
    {"code": "170", "description": "Payment is denied when performed/billed by this type of provider", "category": "CO", "denial_category": "Provider Type", "appealable": True, "success_rate": 0.45},
    {"code": "197", "description": "Precertification/authorization/notification absent", "category": "CO", "denial_category": "Prior Auth", "appealable": True, "success_rate": 0.70},
    {"code": "198", "description": "Precertification/authorization exceeded", "category": "CO", "denial_category": "Prior Auth", "appealable": True, "success_rate": 0.60},
    {"code": "204", "description": "This service/equipment/drug is not covered under the patient's current benefit plan", "category": "CO", "denial_category": "Non-Covered", "appealable": True, "success_rate": 0.35},
    {"code": "227", "description": "Information requested from the patient/insured/responsible party was not provided", "category": "CO", "denial_category": "Missing Information", "appealable": True, "success_rate": 0.80},
    {"code": "234", "description": "This procedure is not paid separately", "category": "CO", "denial_category": "Bundling", "appealable": True, "success_rate": 0.55},
    {"code": "236", "description": "This procedure or procedure/modifier combination is not compatible with another procedure", "category": "CO", "denial_category": "Coding Error", "appealable": True, "success_rate": 0.70},
    {"code": "242", "description": "Services not provided by network/primary care providers", "category": "CO", "denial_category": "Network", "appealable": True, "success_rate": 0.40},
]

# Common RARC codes
RARC_CODES = [
    {"code": "M1", "description": "X-ray not taken within the past 12 months"},
    {"code": "M15", "description": "Separately billed services/tests have been bundled"},
    {"code": "M20", "description": "Missing/incomplete/invalid HCPCS"},
    {"code": "M51", "description": "Missing/incomplete/invalid procedure code(s)"},
    {"code": "M76", "description": "Missing/incomplete/invalid diagnosis or condition"},
    {"code": "M79", "description": "Missing/incomplete/invalid charge"},
    {"code": "M80", "description": "Not covered when performed during the same session/date as a previously processed service"},
    {"code": "N30", "description": "Patient ineligible for this service"},
    {"code": "N115", "description": "This decision was based on a National Coverage Determination"},
    {"code": "N362", "description": "The number of Days or Units of Service exceeds our acceptable maximum"},
    {"code": "N386", "description": "This decision was based on a Local Coverage Determination"},
    {"code": "N432", "description": "Alert: Adjustment based on the Medical Fee Schedule"},
    {"code": "N479", "description": "Missing Explanation of Benefits"},
    {"code": "N519", "description": "Invalid procedure code with this place of service"},
    {"code": "N657", "description": "This should be billed with the appropriate code for the service/supply provided"},
]

# Payer data - AdventHealth's primary payers
PAYERS = [
    # Primary AdventHealth Payers (Medicare, BCBS FL, United, Aetna, Cigna, Humana)
    {"name": "Medicare", "type": "Medicare", "denial_rate": 0.12, "appeal_success": 0.65, "days_to_decision": 30},
    {"name": "BCBS FL", "type": "Commercial", "denial_rate": 0.18, "appeal_success": 0.57, "days_to_decision": 13},
    {"name": "United", "type": "Commercial", "denial_rate": 0.20, "appeal_success": 0.52, "days_to_decision": 14},
    {"name": "Aetna", "type": "Commercial", "denial_rate": 0.22, "appeal_success": 0.58, "days_to_decision": 10},
    {"name": "Cigna", "type": "Commercial", "denial_rate": 0.16, "appeal_success": 0.60, "days_to_decision": 11},
    {"name": "Humana", "type": "Commercial", "denial_rate": 0.19, "appeal_success": 0.50, "days_to_decision": 15},
    # Secondary payers
    {"name": "Florida Medicaid", "type": "Medicaid", "denial_rate": 0.20, "appeal_success": 0.45, "days_to_decision": 45},
    {"name": "Tricare", "type": "Government", "denial_rate": 0.11, "appeal_success": 0.70, "days_to_decision": 21},
]

# Payer-specific denial patterns for high-denial procedures
PAYER_PROCEDURE_DENIAL_RATES = {
    "BCBS FL": {
        "J9271": 0.25,  # Stricter on oncology (Keytruda)
        "70553": 0.32,  # RBM requirement for MRI
        "J9299": 0.25,  # Opdivo
        "78815": 0.38,  # PET scan
    },
    "Aetna": {
        "27447": 0.30,  # Very strict on ortho (TKA)
        "27130": 0.30,  # THA
        "64483": 0.40,  # Pain management scrutiny
        "22551": 0.35,  # Cervical fusion
    },
    "United": {
        "70553": 0.28,  # Optum RBM
        "78815": 0.38,  # PET scan restrictions
        "72148": 0.30,  # MRI lumbar
        "74177": 0.28,  # CT abdomen
    },
    "Medicare": {
        "99215": 0.25,  # Downcoding risk
        "J9271": 0.18,  # LCD-based (more predictable)
        "99285": 0.22,  # ED level 5
        "93458": 0.20,  # Left heart cath
    },
    "Cigna": {
        "J9299": 0.22,  # Opdivo
        "33361": 0.32,  # TAVR
        "J9035": 0.28,  # Avastin
    },
    "Humana": {
        "J2505": 0.22,  # Neulasta
        "93653": 0.28,  # EP study
        "33285": 0.25,  # Loop recorder
    }
}

# AdventHealth facilities
FACILITIES = [
    {"name": "AdventHealth Orlando", "type": "Hospital", "beds": 1368, "city": "Orlando", "state": "FL"},
    {"name": "AdventHealth Tampa", "type": "Hospital", "beds": 542, "city": "Tampa", "state": "FL"},
    {"name": "AdventHealth Celebration", "type": "Hospital", "beds": 237, "city": "Celebration", "state": "FL"},
    {"name": "AdventHealth Altamonte Springs", "type": "Hospital", "beds": 398, "city": "Altamonte Springs", "state": "FL"},
    {"name": "AdventHealth Daytona Beach", "type": "Hospital", "beds": 323, "city": "Daytona Beach", "state": "FL"},
    {"name": "AdventHealth Winter Park", "type": "Hospital", "beds": 305, "city": "Winter Park", "state": "FL"},
    {"name": "AdventHealth Fish Memorial", "type": "Hospital", "beds": 175, "city": "Orange City", "state": "FL"},
    {"name": "AdventHealth Waterman", "type": "Hospital", "beds": 269, "city": "Tavares", "state": "FL"},
    {"name": "AdventHealth Ocala", "type": "Hospital", "beds": 284, "city": "Ocala", "state": "FL"},
    {"name": "AdventHealth Palm Coast", "type": "Hospital", "beds": 99, "city": "Palm Coast", "state": "FL"},
]

# High-denial procedures for realistic AdventHealth demo
# Based on AdventHealth's service mix (55 hospitals, cancer centers, heart institutes, orthopedics)
HIGH_DENIAL_PROCEDURES = {
    # Imaging (Highest Denial Category)
    "70553": {"name": "MRI Brain w/wo contrast", "avg_billed": 2800, "denial_rate": 0.30, "category": "imaging", "denial_reason": "Pre-cert required, medical necessity"},
    "74177": {"name": "CT Abdomen/Pelvis w/contrast", "avg_billed": 1800, "denial_rate": 0.24, "category": "imaging", "denial_reason": "Overutilization scrutiny"},
    "78815": {"name": "PET Scan (Tumor Imaging)", "avg_billed": 6500, "denial_rate": 0.35, "category": "imaging", "denial_reason": "Prior auth + LCD criteria"},
    "93306": {"name": "Echocardiogram complete", "avg_billed": 850, "denial_rate": 0.22, "category": "imaging", "denial_reason": "Frequency limits"},
    "71271": {"name": "CT Chest low-dose lung cancer screen", "avg_billed": 350, "denial_rate": 0.26, "category": "imaging", "denial_reason": "Specific eligibility criteria"},
    
    # Surgery/Procedural
    "27447": {"name": "Total Knee Replacement", "avg_billed": 28000, "denial_rate": 0.25, "category": "surgery", "denial_reason": "PA required, BMI/conservative tx first"},
    "27130": {"name": "Total Hip Replacement", "avg_billed": 32000, "denial_rate": 0.25, "category": "surgery", "denial_reason": "PA required, conservative tx first"},
    "22551": {"name": "Cervical Fusion (ACDF)", "avg_billed": 45000, "denial_rate": 0.30, "category": "surgery", "denial_reason": "Medical necessity, conservative tx"},
    "43239": {"name": "Upper GI Endoscopy w/biopsy", "avg_billed": 2200, "denial_rate": 0.18, "category": "surgery", "denial_reason": "Frequency, medical necessity"},
    "64483": {"name": "Epidural Injection", "avg_billed": 3200, "denial_rate": 0.33, "category": "pain", "denial_reason": "Step therapy, frequency limits"},
    
    # Oncology (J-Codes) - Big $ at Risk
    "J9271": {"name": "Pembrolizumab (Keytruda)", "avg_billed": 45000, "denial_rate": 0.22, "category": "oncology", "denial_reason": "PA required, specific indications"},
    "J9299": {"name": "Nivolumab (Opdivo)", "avg_billed": 38000, "denial_rate": 0.22, "category": "oncology", "denial_reason": "PA required, specific indications"},
    "J9035": {"name": "Bevacizumab (Avastin)", "avg_billed": 8500, "denial_rate": 0.25, "category": "oncology", "denial_reason": "Off-label use scrutiny"},
    "J2505": {"name": "Pegfilgrastim (Neulasta)", "avg_billed": 6800, "denial_rate": 0.18, "category": "oncology", "denial_reason": "Medical necessity timing"},
    "J9305": {"name": "Pemetrexed (Alimta)", "avg_billed": 12000, "denial_rate": 0.26, "category": "oncology", "denial_reason": "Line of therapy requirements"},
    
    # Cardiology (AdventHealth Heart Institute)
    "93458": {"name": "Left Heart Cath w/imaging", "avg_billed": 12000, "denial_rate": 0.22, "category": "cardiology", "denial_reason": "Medical necessity, prior testing"},
    "33361": {"name": "TAVR (Transcatheter Aortic Valve)", "avg_billed": 85000, "denial_rate": 0.30, "category": "cardiology", "denial_reason": "Very high $ - strict PA"},
    "93653": {"name": "EP Study + Ablation", "avg_billed": 18000, "denial_rate": 0.24, "category": "cardiology", "denial_reason": "PA required"},
    "33285": {"name": "Implantable Loop Recorder", "avg_billed": 8500, "denial_rate": 0.25, "category": "cardiology", "denial_reason": "Medical necessity criteria"},
    
    # E/M Codes (Volume Play)
    "99215": {"name": "Office Visit Level 5", "avg_billed": 250, "denial_rate": 0.35, "category": "em", "denial_reason": "Downcoded to 99214"},
    "99223": {"name": "Initial Hospital Care Level 3", "avg_billed": 350, "denial_rate": 0.22, "category": "em", "denial_reason": "Documentation insufficiency"},
    "99291": {"name": "Critical Care 30-74 min", "avg_billed": 450, "denial_rate": 0.24, "category": "em", "denial_reason": "Time documentation"},
    "99285": {"name": "ED Visit Level 5", "avg_billed": 950, "denial_rate": 0.30, "category": "em", "denial_reason": "Downcoded, medical necessity"},
}

# Common procedures with PA requirements (expanded with high-denial codes)
PROCEDURES = [
    # E/M Codes (high volume)
    {"code": "99213", "type": "CPT", "desc": "Office visit, established patient, low complexity", "category": "E&M", "pa_required": False, "medicare_rate": 92.0, "denial_risk": 0.05},
    {"code": "99214", "type": "CPT", "desc": "Office visit, established patient, moderate complexity", "category": "E&M", "pa_required": False, "medicare_rate": 130.0, "denial_risk": 0.08},
    {"code": "99215", "type": "CPT", "desc": "Office visit, established patient, high complexity", "category": "E&M", "pa_required": False, "medicare_rate": 250.0, "denial_risk": 0.35},
    {"code": "99223", "type": "CPT", "desc": "Initial hospital care, high complexity", "category": "E&M", "pa_required": False, "medicare_rate": 350.0, "denial_risk": 0.22},
    {"code": "99283", "type": "CPT", "desc": "Emergency department visit, moderate severity", "category": "E&M", "pa_required": False, "medicare_rate": 145.0, "denial_risk": 0.10},
    {"code": "99284", "type": "CPT", "desc": "Emergency department visit, high severity", "category": "E&M", "pa_required": False, "medicare_rate": 252.0, "denial_risk": 0.12},
    {"code": "99285", "type": "CPT", "desc": "Emergency department visit, level 5", "category": "E&M", "pa_required": False, "medicare_rate": 950.0, "denial_risk": 0.30},
    {"code": "99291", "type": "CPT", "desc": "Critical care, first 30-74 minutes", "category": "E&M", "pa_required": False, "medicare_rate": 450.0, "denial_risk": 0.24},
    
    # Imaging (Highest Denial Category)
    {"code": "70553", "type": "CPT", "desc": "MRI brain with and without contrast", "category": "Radiology", "pa_required": True, "medicare_rate": 2800.0, "denial_risk": 0.30},
    {"code": "74177", "type": "CPT", "desc": "CT abdomen/pelvis with contrast", "category": "Radiology", "pa_required": True, "medicare_rate": 1800.0, "denial_risk": 0.24},
    {"code": "78815", "type": "CPT", "desc": "PET scan tumor imaging", "category": "Radiology", "pa_required": True, "medicare_rate": 6500.0, "denial_risk": 0.35},
    {"code": "71271", "type": "CPT", "desc": "CT chest low-dose lung cancer screening", "category": "Radiology", "pa_required": True, "medicare_rate": 350.0, "denial_risk": 0.26},
    {"code": "72148", "type": "CPT", "desc": "MRI lumbar spine without contrast", "category": "Radiology", "pa_required": True, "medicare_rate": 2800.0, "denial_risk": 0.28},
    {"code": "73721", "type": "CPT", "desc": "MRI joint of lower extremity", "category": "Radiology", "pa_required": True, "medicare_rate": 2200.0, "denial_risk": 0.22},
    
    # Surgery/Procedural (High $ at risk)
    {"code": "27447", "type": "CPT", "desc": "Total knee arthroplasty (TKA)", "category": "Surgery", "pa_required": True, "medicare_rate": 28000.0, "denial_risk": 0.25},
    {"code": "27130", "type": "CPT", "desc": "Total hip arthroplasty (THA)", "category": "Surgery", "pa_required": True, "medicare_rate": 32000.0, "denial_risk": 0.25},
    {"code": "22551", "type": "CPT", "desc": "Cervical fusion (ACDF)", "category": "Surgery", "pa_required": True, "medicare_rate": 45000.0, "denial_risk": 0.30},
    {"code": "43239", "type": "CPT", "desc": "Upper GI endoscopy with biopsy", "category": "Surgery", "pa_required": False, "medicare_rate": 2200.0, "denial_risk": 0.18},
    {"code": "45380", "type": "CPT", "desc": "Colonoscopy with biopsy", "category": "Surgery", "pa_required": False, "medicare_rate": 1800.0, "denial_risk": 0.08},
    {"code": "64483", "type": "CPT", "desc": "Epidural injection", "category": "Pain", "pa_required": True, "medicare_rate": 3200.0, "denial_risk": 0.33},
    
    # Cardiology (AdventHealth Heart Institute)
    {"code": "93000", "type": "CPT", "desc": "Electrocardiogram, complete", "category": "Cardiology", "pa_required": False, "medicare_rate": 45.0, "denial_risk": 0.05},
    {"code": "93306", "type": "CPT", "desc": "Echocardiography, complete", "category": "Cardiology", "pa_required": False, "medicare_rate": 850.0, "denial_risk": 0.22},
    {"code": "93458", "type": "CPT", "desc": "Left heart catheterization with imaging", "category": "Cardiology", "pa_required": True, "medicare_rate": 12000.0, "denial_risk": 0.22},
    {"code": "33361", "type": "CPT", "desc": "TAVR (Transcatheter Aortic Valve Replacement)", "category": "Cardiology", "pa_required": True, "medicare_rate": 85000.0, "denial_risk": 0.30},
    {"code": "93653", "type": "CPT", "desc": "EP study with ablation", "category": "Cardiology", "pa_required": True, "medicare_rate": 18000.0, "denial_risk": 0.24},
    {"code": "33285", "type": "CPT", "desc": "Implantable loop recorder", "category": "Cardiology", "pa_required": True, "medicare_rate": 8500.0, "denial_risk": 0.25},
    
    # Oncology J-Codes (Big $ at Risk)
    {"code": "J9271", "type": "HCPCS", "desc": "Pembrolizumab (Keytruda)", "category": "Oncology", "pa_required": True, "medicare_rate": 45000.0, "denial_risk": 0.22},
    {"code": "J9299", "type": "HCPCS", "desc": "Nivolumab (Opdivo)", "category": "Oncology", "pa_required": True, "medicare_rate": 38000.0, "denial_risk": 0.22},
    {"code": "J9035", "type": "HCPCS", "desc": "Bevacizumab (Avastin)", "category": "Oncology", "pa_required": True, "medicare_rate": 8500.0, "denial_risk": 0.25},
    {"code": "J2505", "type": "HCPCS", "desc": "Pegfilgrastim (Neulasta)", "category": "Oncology", "pa_required": True, "medicare_rate": 6800.0, "denial_risk": 0.18},
    {"code": "J9305", "type": "HCPCS", "desc": "Pemetrexed (Alimta)", "category": "Oncology", "pa_required": True, "medicare_rate": 12000.0, "denial_risk": 0.26},
    
    # Other common procedures
    {"code": "J0585", "type": "HCPCS", "desc": "Botulinum toxin type A", "category": "Drug", "pa_required": True, "medicare_rate": 520.0, "denial_risk": 0.30},
    {"code": "J1745", "type": "HCPCS", "desc": "Infliximab injection", "category": "Drug", "pa_required": True, "medicare_rate": 1250.0, "denial_risk": 0.35},
    {"code": "90834", "type": "CPT", "desc": "Psychotherapy, 45 minutes", "category": "Behavioral Health", "pa_required": False, "medicare_rate": 105.0, "denial_risk": 0.15},
    {"code": "90837", "type": "CPT", "desc": "Psychotherapy, 60 minutes", "category": "Behavioral Health", "pa_required": False, "medicare_rate": 155.0, "denial_risk": 0.18},
    {"code": "97110", "type": "CPT", "desc": "Therapeutic exercises", "category": "Physical Therapy", "pa_required": False, "medicare_rate": 35.0, "denial_risk": 0.12},
    {"code": "97140", "type": "CPT", "desc": "Manual therapy techniques", "category": "Physical Therapy", "pa_required": False, "medicare_rate": 38.0, "denial_risk": 0.14},
    {"code": "G0438", "type": "HCPCS", "desc": "Annual wellness visit, initial", "category": "Preventive", "pa_required": False, "medicare_rate": 175.0, "denial_risk": 0.08},
]

# Demo scenarios for AdventHealth presentation
DEMO_SCENARIOS = [
    {
        "name": "Scenario 1: The $45K Oncology Claim",
        "patient_type": "Cancer patient needing Keytruda infusion",
        "procedure_code": "J9271",
        "procedure_name": "Pembrolizumab (Keytruda)",
        "billed_amount": 45000,
        "payer": "BCBS FL",
        "churn_risk": 0.72,
        "risk_level": "HIGH",
        "risk_factors": [
            {"factor": "No prior auth on file", "impact": 0.35},
            {"factor": "Off-label indication (not in FDA label)", "impact": 0.25},
            {"factor": "Missing genetic testing results (PD-L1)", "impact": 0.12}
        ],
        "preventive_action": "Submit PA with PD-L1 test results NOW",
        "potential_save": 32400
    },
    {
        "name": "Scenario 2: The Orthopedic Bundle",
        "patient_type": "68-year-old needing total knee replacement",
        "procedure_code": "27447",
        "procedure_name": "Total Knee Arthroplasty (TKA)",
        "billed_amount": 28000,
        "payer": "Aetna",
        "churn_risk": 0.58,
        "risk_level": "MEDIUM-HIGH",
        "risk_factors": [
            {"factor": "BMI 38 (payer requires <40 but scrutinizes >35)", "impact": 0.20},
            {"factor": "Only 4 weeks PT documented (payer wants 6+)", "impact": 0.25},
            {"factor": "Missing X-ray report in submission", "impact": 0.13}
        ],
        "preventive_action": "Attach PT notes showing 6 weeks conservative treatment",
        "potential_save": 16240
    },
    {
        "name": "Scenario 3: The Imaging Cascade",
        "patient_type": "Back pain patient getting MRI",
        "procedure_code": "72148",
        "procedure_name": "MRI Lumbar Spine w/o contrast",
        "billed_amount": 2800,
        "payer": "United",
        "churn_risk": 0.45,
        "risk_level": "MEDIUM",
        "risk_factors": [
            {"factor": "No conservative treatment documented", "impact": 0.18},
            {"factor": "Radiology benefit manager (RBM) pre-cert missing", "impact": 0.20},
            {"factor": "Similar MRI done 10 months ago (frequency limit)", "impact": 0.07}
        ],
        "preventive_action": "Get RBM authorization before submission",
        "potential_save": 1260
    }
]

# Physician specialties
SPECIALTIES = [
    "Internal Medicine", "Family Medicine", "Cardiology", "Orthopedic Surgery",
    "General Surgery", "Neurology", "Oncology", "Pulmonology", "Gastroenterology",
    "Emergency Medicine", "Radiology", "Psychiatry", "Physical Medicine"
]

# Common ICD-10 diagnosis codes
ICD10_CODES = [
    "I10", "E11.9", "J06.9", "M54.5", "K21.0", "F32.9", "J44.1", "I25.10",
    "M17.11", "M16.11", "G43.909", "N39.0", "J18.9", "E78.5", "I48.91",
    "M79.3", "R10.9", "K59.00", "J45.909", "E03.9", "M25.561", "M25.562",
    "Z23", "Z12.11", "Z00.00", "R51.9", "M62.830", "G89.29", "F41.1"
]

FIRST_NAMES = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth",
               "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen",
               "Christopher", "Nancy", "Daniel", "Lisa", "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra",
               "Donald", "Ashley", "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
               "Jose", "Maria", "Carlos", "Rosa", "Luis", "Carmen", "Miguel", "Ana", "Juan", "Elena"]

LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
              "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
              "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
              "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores"]

CITIES_FL = ["Orlando", "Tampa", "Jacksonville", "Miami", "Daytona Beach", "Altamonte Springs", "Winter Park",
             "Kissimmee", "Sanford", "Ocala", "Gainesville", "Palm Coast", "Tavares", "Celebration", "Lake Mary"]


def generate_mrn():
    return f"MRN{random.randint(100000, 999999)}"


def generate_npi():
    return f"{random.randint(1000000000, 9999999999)}"


def generate_phone():
    return f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"


def generate_date_in_range(start_date: date, end_date: date) -> date:
    delta = (end_date - start_date).days
    random_days = random.randint(0, delta)
    return start_date + timedelta(days=random_days)


def seed_database():
    """Main function to seed the database with synthetic data"""
    
    # Create all tables
    Base.metadata.create_all(bind=sync_engine)
    
    with Session(sync_engine) as session:
        print("Seeding dimension tables...")
        
        # Seed Payers
        payers = []
        for p in PAYERS:
            payer = DimPayer(
                payer_name=p["name"],
                payer_type=p["type"],
                phone=generate_phone(),
                avg_denial_rate=p["denial_rate"],
                avg_appeal_success_rate=p["appeal_success"],
                avg_days_to_decision=p["days_to_decision"],
                p2p_availability=p["type"] in ["Commercial", "Medicare"],
                electronic_submission=True,
                top_denial_reason_1=random.choice(["50", "197", "16"]),
                top_denial_reason_2=random.choice(["96", "29", "18"]),
                top_denial_reason_3=random.choice(["45", "4", "22"]),
            )
            session.add(payer)
            payers.append(payer)
        session.flush()
        print(f"  Created {len(payers)} payers")
        
        # Seed Facilities
        facilities = []
        for f in FACILITIES:
            facility = DimFacility(
                facility_name=f["name"],
                facility_type=f["type"],
                npi=generate_npi(),
                tax_id=f"{random.randint(10, 99)}-{random.randint(1000000, 9999999)}",
                address_line1=f"{random.randint(100, 9999)} Healthcare Blvd",
                city=f["city"],
                state=f["state"],
                zip_code=f"3{random.randint(2000, 4999)}",
                avg_denial_rate=random.uniform(0.12, 0.20),
                avg_collection_rate=random.uniform(0.85, 0.95),
                total_beds=f["beds"],
            )
            session.add(facility)
            facilities.append(facility)
        session.flush()
        print(f"  Created {len(facilities)} facilities")
        
        # Seed Denial Reasons (CARC/RARC codes)
        denial_reasons = []
        for carc in CARC_CODES:
            rarc = random.choice(RARC_CODES)
            reason = DimDenialReason(
                carc_code=carc["code"],
                carc_description=carc["description"],
                carc_category=carc["category"],
                rarc_code=rarc["code"],
                rarc_description=rarc["description"],
                denial_category=carc["denial_category"],
                is_appealable=carc["appealable"],
                typical_resolution="Submit corrected claim" if carc["denial_category"] == "Coding Error" else "Appeal with documentation",
                historical_appeal_success_rate=carc["success_rate"],
                avg_resolution_days=random.randint(14, 60),
            )
            session.add(reason)
            denial_reasons.append(reason)
        session.flush()
        print(f"  Created {len(denial_reasons)} denial reasons")
        
        # Seed Procedures
        procedures = []
        for proc in PROCEDURES:
            procedure = DimProcedure(
                cpt_hcpcs_code=proc["code"],
                code_type=proc["type"],
                description=proc["desc"],
                short_description=proc["desc"][:50],
                category=proc["category"],
                pa_required=proc["pa_required"],
                typical_pa_turnaround_days=random.randint(3, 14) if proc["pa_required"] else None,
                medicare_rate=proc["medicare_rate"],
                avg_commercial_rate=proc["medicare_rate"] * random.uniform(1.2, 1.8),
                denial_risk_score=proc["denial_risk"],
            )
            session.add(procedure)
            procedures.append(procedure)
        session.flush()
        print(f"  Created {len(procedures)} procedures")
        
        # Seed Physicians
        physicians = []
        for i in range(50):
            specialty = random.choice(SPECIALTIES)
            physician = DimPhysician(
                npi=generate_npi(),
                first_name=random.choice(FIRST_NAMES),
                last_name=random.choice(LAST_NAMES),
                credentials=random.choice(["MD", "DO", "MD", "MD"]),
                specialty=specialty,
                primary_facility_id=random.choice(facilities).facility_id,
                p2p_success_rate_overall=random.uniform(0.45, 0.85),
                p2p_success_rate_by_payer=json.dumps({str(p.payer_id): round(random.uniform(0.4, 0.9), 2) for p in random.sample(payers, 5)}),
                total_p2p_reviews=random.randint(5, 100),
                avg_denial_rate=random.uniform(0.08, 0.22),
                avg_appeal_success_rate=random.uniform(0.45, 0.75),
            )
            session.add(physician)
            physicians.append(physician)
        session.flush()
        print(f"  Created {len(physicians)} physicians")
        
        # Seed Patients
        patients = []
        for i in range(500):
            payer = random.choice(payers)
            patient = DimPatient(
                mrn=generate_mrn(),
                first_name=random.choice(FIRST_NAMES),
                last_name=random.choice(LAST_NAMES),
                date_of_birth=date(random.randint(1940, 2005), random.randint(1, 12), random.randint(1, 28)),
                gender=random.choice(["Male", "Female"]),
                address_line1=f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Pine', 'Maple', 'Cedar'])} {random.choice(['St', 'Ave', 'Blvd', 'Dr'])}",
                city=random.choice(CITIES_FL),
                state="FL",
                zip_code=f"3{random.randint(2000, 4999)}",
                phone=generate_phone(),
                email=f"patient{i}@email.com",
                adi_national_rank=random.randint(1, 100),
                adi_state_rank=random.randint(1, 100),
                sdoh_food_insecurity_risk=random.uniform(0, 1),
                sdoh_housing_instability_risk=random.uniform(0, 1),
                sdoh_transportation_risk=random.uniform(0, 1),
                sdoh_social_isolation_risk=random.uniform(0, 1),
                sdoh_composite_score=random.uniform(0, 1),
                primary_payer_id=payer.payer_id,
                member_id=f"{payer.payer_name[:3].upper()}{random.randint(100000000, 999999999)}",
                group_number=f"GRP{random.randint(10000, 99999)}",
            )
            session.add(patient)
            patients.append(patient)
        session.flush()
        print(f"  Created {len(patients)} patients")
        
        print("\nSeeding fact tables...")
        
        # Generate 1000 claims for a month of data
        # Date range: November 2025 (one month of data)
        start_date = date(2025, 11, 1)
        end_date = date(2025, 11, 30)
        
        claims = []
        denials = []
        prior_auths = []
        appeals = []
        rl_traces = []
        
        # Track denial scenarios for realistic distribution - expanded with edge cases
        denial_scenarios = {
            "medical_necessity": 0.22,
            "prior_auth": 0.18,
            "coding_error": 0.12,
            "timely_filing": 0.06,
            "duplicate": 0.05,
            "cob": 0.08,
            "eligibility": 0.07,
            "bundling": 0.06,
            "retroactive_termination": 0.04,
            "out_of_network": 0.04,
            "experimental": 0.03,
            "benefit_limit": 0.03,
            "provider_type": 0.02,
        }
        
        # Complex scenario patterns for realistic edge cases
        complex_scenarios = [
            {"name": "multi_payer_cob", "description": "Primary/secondary payer coordination failure", "frequency": 0.05},
            {"name": "retroactive_auth", "description": "PA obtained after service rendered", "frequency": 0.03},
            {"name": "step_therapy", "description": "Step therapy protocol not followed", "frequency": 0.04},
            {"name": "site_of_service", "description": "Service at wrong facility type", "frequency": 0.03},
            {"name": "quantity_limit", "description": "Exceeded quantity limits", "frequency": 0.02},
            {"name": "gender_mismatch", "description": "Procedure/diagnosis gender mismatch", "frequency": 0.01},
            {"name": "age_limit", "description": "Patient age outside coverage range", "frequency": 0.02},
            {"name": "frequency_limit", "description": "Service frequency exceeded", "frequency": 0.03},
            {"name": "lcd_ncd_violation", "description": "Local/National Coverage Determination not met", "frequency": 0.04},
            {"name": "modifier_missing", "description": "Required modifier not present", "frequency": 0.03},
        ]
        
        # Store claim data for denial creation
        claims_to_deny = []
        
        for i in range(1000):
            patient = random.choice(patients)
            payer = patient.primary_payer
            facility = random.choice(facilities)
            physician = random.choice(physicians)
            procedure = random.choice(procedures)
            
            service_date = generate_date_in_range(start_date, end_date)
            submission_date = service_date + timedelta(days=random.randint(1, 5))
            
            # Determine if claim will be denied based on payer denial rate and procedure risk
            base_denial_prob = payer.avg_denial_rate + procedure.denial_risk_score
            is_denied = random.random() < min(base_denial_prob, 0.35)  # Cap at 35%
            
            billed_amount = procedure.avg_commercial_rate * random.uniform(0.9, 1.1)
            
            if is_denied:
                claim_status = "Denied"
                paid_amount = 0
                allowed_amount = 0
                adjustment_amount = billed_amount
                adjudication_date = submission_date + timedelta(days=random.randint(7, 30))
            else:
                claim_status = random.choice(["Paid", "Paid", "Paid", "Partial"])
                allowed_amount = billed_amount * random.uniform(0.6, 0.9)
                if claim_status == "Partial":
                    paid_amount = allowed_amount * random.uniform(0.5, 0.8)
                else:
                    paid_amount = allowed_amount * random.uniform(0.85, 1.0)
                adjustment_amount = billed_amount - paid_amount
                adjudication_date = submission_date + timedelta(days=random.randint(10, 25))
            
            claim = FactClaim(
                claim_number=f"CLM{2025110000 + i}",
                patient_control_number=f"PCN{random.randint(100000, 999999)}",
                payer_claim_number=f"PYR{random.randint(1000000000, 9999999999)}" if not is_denied else None,
                patient_id=patient.patient_id,
                payer_id=payer.payer_id,
                facility_id=facility.facility_id,
                physician_id=physician.physician_id,
                procedure_id=procedure.procedure_id,
                service_date=service_date,
                submission_date=submission_date,
                adjudication_date=adjudication_date,
                primary_diagnosis=random.choice(ICD10_CODES),
                secondary_diagnosis=random.choice(ICD10_CODES) if random.random() > 0.3 else None,
                diagnosis_codes=json.dumps(random.sample(ICD10_CODES, random.randint(1, 4))),
                billed_amount=round(billed_amount, 2),
                allowed_amount=round(allowed_amount, 2) if allowed_amount else None,
                paid_amount=round(paid_amount, 2) if paid_amount else 0,
                patient_responsibility=round(billed_amount * random.uniform(0.05, 0.20), 2),
                adjustment_amount=round(adjustment_amount, 2),
                claim_status=claim_status,
                claim_type=random.choice(["Professional", "Institutional"]),
                place_of_service=random.choice(["11", "21", "22", "23"]),
                claim_frequency_code="1",
                claim_filing_indicator="CI",
            )
            session.add(claim)
            claims.append(claim)
            
            # Store denial info for later creation
            if is_denied:
                claims_to_deny.append({
                    "claim": claim,
                    "patient": patient,
                    "procedure": procedure,
                    "billed_amount": billed_amount,
                    "adjudication_date": adjudication_date,
                })
        
        # Flush claims to get their IDs
        session.flush()
        print(f"  Created {len(claims)} claims")
        
        # Now create denials with valid claim IDs
        for deny_info in claims_to_deny:
            claim = deny_info["claim"]
            patient = deny_info["patient"]
            procedure = deny_info["procedure"]
            billed_amount = deny_info["billed_amount"]
            adjudication_date = deny_info["adjudication_date"]
            
            # Select denial scenario
            scenario = random.choices(
                list(denial_scenarios.keys()),
                weights=list(denial_scenarios.values())
            )[0]
            
            # Map scenario to CARC codes - expanded for all scenarios
            scenario_carc_map = {
                "medical_necessity": ["50", "55", "167"],
                "prior_auth": ["197", "198", "39"],
                "coding_error": ["4", "5", "236"],
                "timely_filing": ["29"],
                "duplicate": ["18"],
                "cob": ["22"],
                "eligibility": ["31", "32", "27"],
                "bundling": ["97", "234"],
                "retroactive_termination": ["27", "31"],
                "out_of_network": ["242", "109"],
                "experimental": ["55", "96"],
                "benefit_limit": ["35", "119"],
                "provider_type": ["170", "109"],
            }
            
            carc_code = random.choice(scenario_carc_map[scenario])
            denial_reason = next((dr for dr in denial_reasons if dr.carc_code == carc_code), random.choice(denial_reasons))
            
            # AI agent enrichments
            sdoh_score = patient.sdoh_composite_score
            clinical_urgency = random.uniform(3, 9) if procedure.category in ["Surgery", "Cardiology"] else random.uniform(1, 6)
            appeal_success_prob = denial_reason.historical_appeal_success_rate * random.uniform(0.8, 1.2)
            appeal_success_prob = min(max(appeal_success_prob, 0.1), 0.95)
            
            # Calculate priority score (composite of multiple factors)
            financial_value = billed_amount / 5000  # Normalize
            priority_score = (
                0.25 * sdoh_score +
                0.20 * (clinical_urgency / 10) +
                0.25 * appeal_success_prob +
                0.30 * min(financial_value, 1.0)
            )
            
            # Generate random created_at timestamp (between 1 minute and 3 days ago)
            # This simulates denials that have been waiting in queue for different amounts of time
            queue_wait_seconds = random.randint(60, 259200)  # 1 min to 3 days
            denial_created_at = datetime.utcnow() - timedelta(seconds=queue_wait_seconds)
            
            denial = FactDenial(
                claim_id=claim.claim_id,
                denial_reason_id=denial_reason.denial_reason_id,
                carc_code=carc_code,
                rarc_code=denial_reason.rarc_code,
                group_code=denial_reason.carc_category,
                adjustment_amount=round(billed_amount, 2),
                denial_date=adjudication_date,
                appeal_deadline=adjudication_date + timedelta(days=random.choice([60, 90, 120, 180])),
                denial_status=random.choice(["New", "New", "In Review", "Appealed"]),
                patient_sdoh_score=round(sdoh_score, 3),
                patient_vulnerability_flag=sdoh_score > 0.7,
                care_gap_identified=random.random() > 0.7,
                care_gap_description="Potential gap in preventive care identified" if random.random() > 0.7 else None,
                clinical_urgency_score=round(clinical_urgency, 1),
                medical_necessity_flag=scenario == "medical_necessity",
                expected_recovery_amount=round(billed_amount * appeal_success_prob, 2),
                financial_priority_score=round(financial_value, 3),
                appeal_success_probability=round(appeal_success_prob, 3),
                recommended_action="P2P Review" if appeal_success_prob > 0.6 else "Written Appeal",
                recommended_physician_id=random.choice(physicians).physician_id if appeal_success_prob > 0.5 else None,
                p2p_recommended=appeal_success_prob > 0.6,
                root_cause_category=scenario.replace("_", " ").title(),
                prevention_recommendation=f"Implement {scenario.replace('_', ' ')} prevention protocol",
                priority_score=round(priority_score, 3),
                created_at=denial_created_at,
            )
            session.add(denial)
            denials.append(denial)
        
        session.flush()
        print(f"  Created {len(denials)} denials ({len(denials)/len(claims)*100:.1f}% denial rate)")
        
        # Create Prior Authorizations (for procedures that require PA)
        pa_procedures = [p for p in procedures if p.pa_required]
        for i in range(200):
            patient = random.choice(patients)
            procedure = random.choice(pa_procedures)
            physician = random.choice(physicians)
            facility = random.choice(facilities)
            payer = patient.primary_payer
            
            request_date = generate_date_in_range(start_date, end_date)
            
            # Determine PA outcome
            denial_prob = procedure.denial_risk_score + random.uniform(-0.1, 0.1)
            is_approved = random.random() > denial_prob
            
            decision_date = request_date + timedelta(days=random.randint(2, 14))
            
            prior_auth = FactPriorAuth(
                auth_number=f"PA{2025110000 + i}",
                reference_number=f"REF{random.randint(100000, 999999)}",
                patient_id=patient.patient_id,
                payer_id=payer.payer_id,
                procedure_id=procedure.procedure_id,
                physician_id=physician.physician_id,
                facility_id=facility.facility_id,
                request_date=request_date,
                decision_date=decision_date if random.random() > 0.2 else None,
                effective_start_date=decision_date if is_approved else None,
                effective_end_date=decision_date + timedelta(days=90) if is_approved else None,
                primary_diagnosis=random.choice(ICD10_CODES),
                diagnosis_codes=json.dumps(random.sample(ICD10_CODES, random.randint(1, 3))),
                auth_status="Approved" if is_approved else random.choice(["Denied", "Pending", "Partial"]),
                decision_reason="Meets medical necessity criteria" if is_approved else "Additional documentation required",
                denial_probability=round(denial_prob, 3),
                risk_factors=json.dumps(["High-cost procedure", "Limited prior history"]) if denial_prob > 0.2 else None,
                documentation_score=round(random.uniform(60, 100), 1),
                missing_documents=json.dumps(["Clinical notes", "Prior imaging"]) if random.random() > 0.7 else None,
                policy_match_score=round(random.uniform(0.5, 1.0), 3),
                estimated_decision_days=random.randint(3, 14),
            )
            session.add(prior_auth)
            prior_auths.append(prior_auth)
        
        session.flush()
        print(f"  Created {len(prior_auths)} prior authorizations")
        
        # Create Appeals for some denials
        appealable_denials = [d for d in denials if d.denial_status in ["In Review", "Appealed"]]
        for denial in random.sample(appealable_denials, min(100, len(appealable_denials))):
            appeal_date = denial.denial_date + timedelta(days=random.randint(5, 30))
            
            # Determine appeal outcome
            success_prob = denial.appeal_success_probability
            is_won = random.random() < success_prob
            
            appeal = FactAppeal(
                denial_id=denial.denial_id,
                appeal_number=f"APL{random.randint(100000, 999999)}",
                appeal_level=random.choice([1, 1, 1, 2]),
                appeal_type=random.choice(["Written", "Written", "P2P"]) if denial.p2p_recommended else "Written",
                appeal_submitted_date=appeal_date,
                appeal_decision_date=appeal_date + timedelta(days=random.randint(14, 45)) if random.random() > 0.3 else None,
                appeal_status="Won" if is_won else random.choice(["Lost", "Pending", "Partial"]),
                outcome_amount=round(denial.adjustment_amount * random.uniform(0.7, 1.0), 2) if is_won else 0,
                p2p_scheduled=denial.p2p_recommended and random.random() > 0.3,
                p2p_physician_id=denial.recommended_physician_id,
                success_factors=json.dumps(["Strong clinical documentation", "P2P review"]) if is_won else None,
                failure_factors=json.dumps(["Insufficient documentation"]) if not is_won else None,
            )
            session.add(appeal)
            appeals.append(appeal)
            
            # Update denial status
            denial.denial_status = "Resolved" if is_won else "Appealed"
        
        session.flush()
        print(f"  Created {len(appeals)} appeals")
        
        # Create RL Traces for staff actions - with correlated outcomes for AI-assisted cases
        action_types = ["Appeal Submitted", "P2P Requested", "Documentation Added", "Write Off", "Escalated", "Corrected Claim"]
        
        # Track metrics for AI impact demonstration
        ai_followed_successes = 0
        ai_not_followed_successes = 0
        ai_followed_total = 0
        ai_not_followed_total = 0
        
        for i in range(500):  # Increased to 500 traces for better analytics
            denial = random.choice(denials)
            
            # Staff follows AI recommendation ~65% of the time
            staff_followed_ai = random.random() > 0.35
            
            # When staff follows AI, outcomes are significantly better
            if staff_followed_ai:
                ai_followed_total += 1
                # Higher success rate when following AI (70% success, 15% partial, 10% pending, 5% failure)
                outcome_roll = random.random()
                if outcome_roll < 0.70:
                    outcome = "Success"
                    ai_followed_successes += 1
                    outcome_amount = round(denial.adjustment_amount * random.uniform(0.75, 1.0), 2)
                    reward_score = round(random.uniform(0.5, 1.0), 3)
                elif outcome_roll < 0.85:
                    outcome = "Partial"
                    outcome_amount = round(denial.adjustment_amount * random.uniform(0.4, 0.7), 2)
                    reward_score = round(random.uniform(0.1, 0.5), 3)
                elif outcome_roll < 0.95:
                    outcome = "Pending"
                    outcome_amount = 0
                    reward_score = round(random.uniform(-0.2, 0.3), 3)
                else:
                    outcome = "Failure"
                    outcome_amount = 0
                    reward_score = round(random.uniform(-0.5, 0), 3)
                
                # Faster resolution when following AI (1-7 days)
                action_days = random.randint(1, 7)
            else:
                ai_not_followed_total += 1
                # Lower success rate when not following AI (35% success, 20% partial, 25% pending, 20% failure)
                outcome_roll = random.random()
                if outcome_roll < 0.35:
                    outcome = "Success"
                    ai_not_followed_successes += 1
                    outcome_amount = round(denial.adjustment_amount * random.uniform(0.5, 0.85), 2)
                    reward_score = round(random.uniform(0.2, 0.7), 3)
                elif outcome_roll < 0.55:
                    outcome = "Partial"
                    outcome_amount = round(denial.adjustment_amount * random.uniform(0.2, 0.5), 2)
                    reward_score = round(random.uniform(-0.1, 0.3), 3)
                elif outcome_roll < 0.80:
                    outcome = "Pending"
                    outcome_amount = 0
                    reward_score = round(random.uniform(-0.4, 0.1), 3)
                else:
                    outcome = "Failure"
                    outcome_amount = 0
                    reward_score = round(random.uniform(-1.0, -0.3), 3)
                
                # Slower resolution when not following AI (5-14 days)
                action_days = random.randint(5, 14)
            
            # Select action type based on AI recommendation alignment
            if staff_followed_ai:
                if denial.recommended_action == "P2P Review":
                    action_type = random.choice(["P2P Requested", "Appeal Submitted", "Documentation Added"])
                else:
                    action_type = random.choice(["Appeal Submitted", "Documentation Added", "Corrected Claim"])
            else:
                # When not following AI, more likely to write off or escalate
                action_type = random.choice(["Write Off", "Escalated", "Appeal Submitted", "Documentation Added"])
            
            trace = FactRLTrace(
                denial_id=denial.denial_id,
                staff_id=f"STAFF{random.randint(100, 999)}",
                action_type=action_type,
                action_timestamp=denial.denial_date + timedelta(days=action_days),
                state_before=json.dumps({
                    "status": "New", 
                    "priority": denial.priority_score,
                    "urgency": denial.clinical_urgency_score,
                    "expected_recovery": denial.expected_recovery_amount
                }),
                ai_recommendation=denial.recommended_action,
                ai_confidence=denial.appeal_success_probability,
                staff_followed_ai=staff_followed_ai,
                outcome=outcome,
                outcome_amount=outcome_amount,
                reward_score=reward_score,
                feedback_rating=random.randint(4, 5) if staff_followed_ai and outcome == "Success" else (random.randint(1, 3) if not staff_followed_ai else random.randint(2, 4)),
            )
            session.add(trace)
            rl_traces.append(trace)
        
        # Print AI impact summary
        ai_followed_rate = ai_followed_successes / ai_followed_total * 100 if ai_followed_total > 0 else 0
        ai_not_followed_rate = ai_not_followed_successes / ai_not_followed_total * 100 if ai_not_followed_total > 0 else 0
        print(f"  AI Impact: Followed AI success rate: {ai_followed_rate:.1f}%, Not followed: {ai_not_followed_rate:.1f}%")
        
        session.commit()
        print(f"  Created {len(rl_traces)} RL traces")
        
        # ==================== TREATMENT GUIDANCE DATA ====================
        print("\nSeeding treatment guidance data...")
        
        # Treatment guidelines for procedures that require PA
        treatment_guidelines = []
        guideline_data = [
            {
                "procedure_code": "27447", "diagnosis_code": "M17.11",
                "name": "Total Knee Arthroplasty Guidelines",
                "source": "CMS LCD", "version": "2024.1",
                "recommendation": "Total knee replacement is indicated for patients with severe osteoarthritis who have failed conservative treatment including physical therapy, NSAIDs, and corticosteroid injections for at least 3 months.",
                "criteria": "Kellgren-Lawrence Grade 3-4 OA, BMI < 40, failed conservative treatment",
                "contraindications": "Active infection, severe peripheral vascular disease, recent DVT",
                "alternatives": "Partial knee replacement, osteotomy, continued conservative management",
                "approval_rate": 0.85, "days_to_approval": 5
            },
            {
                "procedure_code": "27130", "diagnosis_code": "M16.11",
                "name": "Total Hip Arthroplasty Guidelines",
                "source": "CMS LCD", "version": "2024.1",
                "recommendation": "Total hip replacement is indicated for patients with severe hip osteoarthritis or avascular necrosis who have failed conservative treatment.",
                "criteria": "Severe hip OA or AVN, failed conservative treatment for 3+ months, significant functional limitation",
                "contraindications": "Active infection, severe cardiopulmonary disease, recent stroke",
                "alternatives": "Hip resurfacing, core decompression, continued conservative management",
                "approval_rate": 0.82, "days_to_approval": 5
            },
            {
                "procedure_code": "70553", "diagnosis_code": "G43.909",
                "name": "Brain MRI with Contrast Guidelines",
                "source": "Payer Policy", "version": "2024.2",
                "recommendation": "MRI brain with contrast is indicated for evaluation of suspected intracranial pathology, tumor surveillance, or MS evaluation.",
                "criteria": "New neurological symptoms, tumor surveillance, MS diagnosis/monitoring",
                "contraindications": "Pacemaker, cochlear implant, severe renal impairment (for contrast)",
                "alternatives": "CT head, MRI without contrast",
                "approval_rate": 0.78, "days_to_approval": 3
            },
            {
                "procedure_code": "72148", "diagnosis_code": "M54.5",
                "name": "Lumbar Spine MRI Guidelines",
                "source": "CMS LCD", "version": "2024.1",
                "recommendation": "MRI lumbar spine is indicated for evaluation of radiculopathy, suspected spinal stenosis, or cauda equina syndrome after failed conservative treatment.",
                "criteria": "Radicular symptoms > 6 weeks, failed conservative treatment, red flag symptoms",
                "contraindications": "Pacemaker, cochlear implant, severe claustrophobia",
                "alternatives": "CT lumbar spine, X-ray lumbar spine, continued conservative management",
                "approval_rate": 0.75, "days_to_approval": 3
            },
            {
                "procedure_code": "73721", "diagnosis_code": "M25.561",
                "name": "Lower Extremity Joint MRI Guidelines",
                "source": "Payer Policy", "version": "2024.2",
                "recommendation": "MRI of lower extremity joint is indicated for evaluation of suspected internal derangement, ligament injury, or unexplained joint pain.",
                "criteria": "Suspected ligament/meniscus tear, failed conservative treatment > 4 weeks, mechanical symptoms",
                "contraindications": "Pacemaker, cochlear implant",
                "alternatives": "X-ray, ultrasound, CT scan",
                "approval_rate": 0.80, "days_to_approval": 3
            },
            {
                "procedure_code": "93458", "diagnosis_code": "I25.10",
                "name": "Cardiac Catheterization Guidelines",
                "source": "Clinical Guidelines", "version": "2024.1",
                "recommendation": "Cardiac catheterization is indicated for patients with suspected CAD, positive stress test, or acute coronary syndrome.",
                "criteria": "Positive stress test, unstable angina, NSTEMI/STEMI, high-risk features",
                "contraindications": "Active bleeding, severe renal impairment, recent stroke",
                "alternatives": "CT coronary angiography, stress testing, medical management",
                "approval_rate": 0.88, "days_to_approval": 2
            },
            {
                "procedure_code": "J0585", "diagnosis_code": "G43.909",
                "name": "Botulinum Toxin Guidelines",
                "source": "Payer Policy", "version": "2024.2",
                "recommendation": "Botulinum toxin is indicated for chronic migraine (15+ headache days/month) after failure of 2+ preventive medications.",
                "criteria": "Chronic migraine diagnosis, failed 2+ preventive medications, documented headache diary",
                "contraindications": "Infection at injection site, myasthenia gravis, pregnancy",
                "alternatives": "CGRP inhibitors, other preventive medications, nerve blocks",
                "approval_rate": 0.70, "days_to_approval": 7
            },
            {
                "procedure_code": "J1745", "diagnosis_code": "M06.9",
                "name": "Infliximab Injection Guidelines",
                "source": "CMS LCD", "version": "2024.1",
                "recommendation": "Infliximab is indicated for moderate-severe rheumatoid arthritis, Crohn's disease, or ulcerative colitis after failure of conventional therapy.",
                "criteria": "Failed methotrexate or other DMARDs, moderate-severe disease activity, negative TB test",
                "contraindications": "Active infection, TB, heart failure NYHA III-IV, demyelinating disease",
                "alternatives": "Other biologics (adalimumab, etanercept), JAK inhibitors",
                "approval_rate": 0.72, "days_to_approval": 10
            },
            {
                "procedure_code": "J2505", "diagnosis_code": "C34.90",
                "name": "Pegfilgrastim Injection Guidelines",
                "source": "Clinical Guidelines", "version": "2024.1",
                "recommendation": "Pegfilgrastim is indicated for prevention of febrile neutropenia in patients receiving myelosuppressive chemotherapy.",
                "criteria": "Receiving myelosuppressive chemotherapy, high risk of febrile neutropenia (>20%)",
                "contraindications": "Hypersensitivity to E. coli-derived proteins",
                "alternatives": "Filgrastim, biosimilars",
                "approval_rate": 0.90, "days_to_approval": 2
            },
        ]
        
        for gd in guideline_data:
            guideline = DimTreatmentGuideline(
                procedure_code=gd["procedure_code"],
                diagnosis_code=gd["diagnosis_code"],
                guideline_name=gd["name"],
                guideline_source=gd["source"],
                guideline_version=gd["version"],
                effective_date=date(2024, 1, 1),
                treatment_recommendation=gd["recommendation"],
                medical_necessity_criteria=gd["criteria"],
                contraindications=gd["contraindications"],
                alternative_treatments=gd["alternatives"],
                prior_auth_required=True,
                typical_approval_rate=gd["approval_rate"],
                avg_days_to_approval=gd["days_to_approval"]
            )
            session.add(guideline)
            treatment_guidelines.append(guideline)
        
        session.commit()
        print(f"  Created {len(treatment_guidelines)} treatment guidelines")
        
        # Clinical criteria for each guideline
        clinical_criteria = []
        criteria_data = {
            "27447": [  # Total Knee
                {"name": "Kellgren-Lawrence Grade", "type": "Imaging", "value": "Grade 3 or 4", "doc": "X-ray report", "mandatory": True},
                {"name": "BMI", "type": "Clinical Finding", "value": "< 40", "doc": "Recent vitals", "mandatory": True},
                {"name": "Conservative Treatment Trial", "type": "Prior Treatment", "value": "3+ months PT, NSAIDs, injections", "doc": "Clinical notes", "mandatory": True},
                {"name": "Functional Assessment", "type": "Clinical Finding", "value": "WOMAC score documented", "doc": "Assessment form", "mandatory": False},
            ],
            "27130": [  # Total Hip
                {"name": "Hip OA Severity", "type": "Imaging", "value": "Severe OA or AVN on imaging", "doc": "X-ray/MRI report", "mandatory": True},
                {"name": "Conservative Treatment Trial", "type": "Prior Treatment", "value": "3+ months PT, NSAIDs, injections", "doc": "Clinical notes", "mandatory": True},
                {"name": "Functional Limitation", "type": "Clinical Finding", "value": "Significant ADL impairment", "doc": "Clinical notes", "mandatory": True},
            ],
            "70553": [  # Brain MRI
                {"name": "Neurological Symptoms", "type": "Clinical Finding", "value": "New or worsening symptoms", "doc": "Clinical notes", "mandatory": True},
                {"name": "Prior Imaging", "type": "Prior Treatment", "value": "CT or MRI without contrast if applicable", "doc": "Prior imaging report", "mandatory": False},
            ],
            "72148": [  # Lumbar MRI
                {"name": "Radicular Symptoms", "type": "Clinical Finding", "value": "Present > 6 weeks", "doc": "Clinical notes", "mandatory": True},
                {"name": "Conservative Treatment", "type": "Prior Treatment", "value": "Failed PT, medications", "doc": "Clinical notes", "mandatory": True},
                {"name": "Red Flag Assessment", "type": "Clinical Finding", "value": "Documented red flag screening", "doc": "Clinical notes", "mandatory": True},
            ],
            "J0585": [  # Botox
                {"name": "Chronic Migraine Diagnosis", "type": "Clinical Finding", "value": "15+ headache days/month", "doc": "Headache diary", "mandatory": True},
                {"name": "Failed Preventives", "type": "Prior Treatment", "value": "2+ medications failed", "doc": "Medication history", "mandatory": True},
            ],
            "J1745": [  # Infliximab
                {"name": "Disease Activity", "type": "Clinical Finding", "value": "Moderate-severe activity score", "doc": "Disease activity assessment", "mandatory": True},
                {"name": "Failed DMARDs", "type": "Prior Treatment", "value": "Methotrexate or other DMARD failure", "doc": "Medication history", "mandatory": True},
                {"name": "TB Test", "type": "Lab Result", "value": "Negative", "doc": "TB test result", "mandatory": True},
            ],
        }
        
        for guideline in treatment_guidelines:
            if guideline.procedure_code in criteria_data:
                for cd in criteria_data[guideline.procedure_code]:
                    criteria = DimClinicalCriteria(
                        guideline_id=guideline.guideline_id,
                        criteria_name=cd["name"],
                        criteria_type=cd["type"],
                        criteria_description=f"{cd['name']}: {cd['value']}",
                        required_value=cd["value"],
                        required_documentation=cd["doc"],
                        is_mandatory=cd["mandatory"]
                    )
                    session.add(criteria)
                    clinical_criteria.append(criteria)
        
        session.commit()
        print(f"  Created {len(clinical_criteria)} clinical criteria")
        
        # Documentation requirements
        doc_requirements = []
        doc_data = {
            "27447": [
                {"type": "X-ray Report", "desc": "Weight-bearing AP and lateral knee X-rays", "mandatory": True, "max_age": 90},
                {"type": "Clinical Notes", "desc": "Documentation of conservative treatment trial", "mandatory": True, "max_age": 30},
                {"type": "Physical Therapy Records", "desc": "PT notes showing treatment and progress", "mandatory": True, "max_age": 90},
            ],
            "27130": [
                {"type": "X-ray Report", "desc": "AP pelvis and lateral hip X-rays", "mandatory": True, "max_age": 90},
                {"type": "Clinical Notes", "desc": "Documentation of conservative treatment trial", "mandatory": True, "max_age": 30},
            ],
            "70553": [
                {"type": "Clinical Notes", "desc": "Documentation of neurological symptoms", "mandatory": True, "max_age": 30},
                {"type": "Prior Imaging", "desc": "CT or prior MRI if available", "mandatory": False, "max_age": 365},
            ],
            "72148": [
                {"type": "Clinical Notes", "desc": "Documentation of radicular symptoms and duration", "mandatory": True, "max_age": 30},
                {"type": "Physical Therapy Records", "desc": "PT notes if applicable", "mandatory": False, "max_age": 90},
            ],
            "J0585": [
                {"type": "Headache Diary", "desc": "30-day headache diary", "mandatory": True, "max_age": 30},
                {"type": "Medication History", "desc": "Documentation of failed preventive medications", "mandatory": True, "max_age": 180},
            ],
            "J1745": [
                {"type": "Disease Activity Assessment", "desc": "DAS28 or similar score", "mandatory": True, "max_age": 30},
                {"type": "Lab Results", "desc": "TB test, hepatitis panel", "mandatory": True, "max_age": 90},
                {"type": "Medication History", "desc": "Documentation of DMARD failure", "mandatory": True, "max_age": 180},
            ],
        }
        
        for guideline in treatment_guidelines:
            if guideline.procedure_code in doc_data:
                for dd in doc_data[guideline.procedure_code]:
                    doc_req = DimDocumentationRequirement(
                        guideline_id=guideline.guideline_id,
                        document_type=dd["type"],
                        document_description=dd["desc"],
                        is_mandatory=dd["mandatory"],
                        max_age_days=dd["max_age"]
                    )
                    session.add(doc_req)
                    doc_requirements.append(doc_req)
        
        session.commit()
        print(f"  Created {len(doc_requirements)} documentation requirements")
        
        # Generate treatment guidance results for prior auths
        guidance_results = []
        
        # Build a lookup of procedure_id to procedure_code (cpt_hcpcs_code)
        procedure_code_lookup = {}
        for proc in procedures:
            procedure_code_lookup[proc.procedure_id] = proc.cpt_hcpcs_code
        
        for pa in prior_auths:
            # Get procedure code from the procedure_id
            pa_procedure_code = procedure_code_lookup.get(pa.procedure_id)
            
            # Find matching guideline
            matching_guideline = None
            for g in treatment_guidelines:
                if g.procedure_code == pa_procedure_code:
                    matching_guideline = g
                    break
            
            if matching_guideline:
                # Determine can_treat based on PA status (auth_status field)
                if pa.auth_status == "Approved":
                    can_treat = "YES"
                    can_treat_reason = "Prior authorization approved. All clinical criteria met and documentation complete."
                    criteria_met_pct = random.uniform(0.85, 1.0)
                    docs_complete = True
                elif pa.auth_status == "Denied":
                    can_treat = "NO"
                    can_treat_reason = "Prior authorization denied. Missing criteria or documentation."
                    criteria_met_pct = random.uniform(0.4, 0.7)
                    docs_complete = False
                else:  # Pending, Partial, Expired
                    can_treat = "PENDING"
                    can_treat_reason = "Prior authorization pending review. Awaiting payer decision."
                    criteria_met_pct = random.uniform(0.7, 0.9)
                    docs_complete = random.choice([True, False])
                
                criteria_total = random.randint(3, 5)
                criteria_met = int(criteria_total * criteria_met_pct)
                
                missing_criteria = []
                if criteria_met < criteria_total:
                    possible_missing = ["Conservative treatment documentation", "Recent imaging", "Lab results", "Specialist consultation"]
                    missing_criteria = random.sample(possible_missing, min(criteria_total - criteria_met, len(possible_missing)))
                
                missing_docs = []
                if not docs_complete:
                    possible_missing_docs = ["Clinical notes", "Imaging report", "Lab results", "PT records"]
                    missing_docs = random.sample(possible_missing_docs, random.randint(1, 2))
                
                result = FactTreatmentGuidanceResult(
                    prior_auth_id=pa.prior_auth_id,
                    guideline_id=matching_guideline.guideline_id,
                    can_treat=can_treat,
                    can_treat_reason=can_treat_reason,
                    criteria_met_count=criteria_met,
                    criteria_total_count=criteria_total,
                    criteria_met_percentage=criteria_met_pct * 100,
                    missing_criteria=json.dumps(missing_criteria) if missing_criteria else None,
                    docs_complete=docs_complete,
                    missing_documents=json.dumps(missing_docs) if missing_docs else None,
                    ai_treatment_recommendation=matching_guideline.treatment_recommendation,
                    ai_confidence_score=random.uniform(0.75, 0.95),
                    ai_alternative_suggestion=matching_guideline.alternative_treatments if can_treat == "NO" else None,
                    clinical_urgency_score=random.randint(3, 8),
                    urgency_reason="Based on diagnosis severity and patient condition",
                    evaluated_by="AI Treatment Guidance Agent"
                )
                session.add(result)
                guidance_results.append(result)
        
        session.commit()
        print(f"  Created {len(guidance_results)} treatment guidance results")
        
        print("\nDatabase seeding complete!")
        print(f"  Total claims: {len(claims)}")
        print(f"  Total denials: {len(denials)}")
        print(f"  Total prior auths: {len(prior_auths)}")
        print(f"  Total appeals: {len(appeals)}")
        print(f"  Total RL traces: {len(rl_traces)}")
        print(f"  Total treatment guidelines: {len(treatment_guidelines)}")
        print(f"  Total guidance results: {len(guidance_results)}")


if __name__ == "__main__":
    seed_database()
