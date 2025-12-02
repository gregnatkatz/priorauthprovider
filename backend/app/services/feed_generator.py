"""
Clearinghouse Feed Generator Service

Generates realistic 835 EDI claims data simulating feeds from Availity and Change Healthcare.
"""

import random
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from app.models import (
    FactClaim, FactDenial, FeedIngestion, DimPatient, DimPayer, 
    DimFacility, DimProcedure, DimPhysician, DimDenialReason
)

# Payer distribution by source (per spec)
PAYER_DISTRIBUTION = {
    'Availity': {
        'Florida Blue': 0.40,
        'Humana': 0.25,
        'Cigna': 0.20,
        'Medicare': 0.15
    },
    'Change Healthcare': {
        'UnitedHealthcare': 0.35,
        'Aetna': 0.30,
        'Anthem Blue Cross': 0.20,
        'Medicaid': 0.15
    }
}

# CARC codes with categories and usage conditions (per spec)
CARC_CODES = [
    {'code': '96', 'category': 'Prior Authorization', 'description': 'Service not authorized', 'weight': 0.20},
    {'code': '197', 'category': 'Prior Authorization', 'description': 'Precertification absent', 'weight': 0.15},
    {'code': '50', 'category': 'Medical Necessity', 'description': 'Not medically necessary', 'weight': 0.15},
    {'code': '16', 'category': 'Coding', 'description': 'Lacks information/billing error', 'weight': 0.10},
    {'code': '18', 'category': 'Duplicate', 'description': 'Exact duplicate claim', 'weight': 0.08},
    {'code': '27', 'category': 'Eligibility', 'description': 'Coverage terminated', 'weight': 0.08},
    {'code': '29', 'category': 'Timely Filing', 'description': 'Time limit expired', 'weight': 0.07},
    {'code': '4', 'category': 'Coding', 'description': 'Procedure code inconsistent with modifier', 'weight': 0.07},
    {'code': '45', 'category': 'Bundling', 'description': 'Charge exceeds fee schedule', 'weight': 0.05},
    {'code': '97', 'category': 'Benefit Limit', 'description': 'Benefit maximum reached', 'weight': 0.05},
]

# Group codes for 835 CAS segment
GROUP_CODES = ['CO', 'PR', 'OA', 'PI', 'CR']

# Facility codes for claim number generation
FACILITY_CODES = ['AHO', 'AHT', 'AHK', 'AHD', 'AHW', 'AHC', 'AHL', 'AHS', 'AHM', 'AHP']


def get_payer_by_source(db: Session, source: str) -> DimPayer:
    """Get a random payer based on source distribution"""
    distribution = PAYER_DISTRIBUTION.get(source, PAYER_DISTRIBUTION['Availity'])
    
    # Get all payers
    payers = db.query(DimPayer).all()
    if not payers:
        return None
    
    # Try to match by name from distribution
    payer_names = list(distribution.keys())
    weights = list(distribution.values())
    selected_name = random.choices(payer_names, weights=weights, k=1)[0]
    
    # Find matching payer or return random
    for payer in payers:
        if selected_name.lower() in payer.payer_name.lower():
            return payer
    
    return random.choice(payers)


def get_random_carc() -> Dict:
    """Get a random CARC code based on weighted distribution"""
    weights = [c['weight'] for c in CARC_CODES]
    return random.choices(CARC_CODES, weights=weights, k=1)[0]


def generate_claim_number(facility_code: str, sequence: int) -> str:
    """Generate claim number in format: {facility_code}{YYYYMMDD}{sequence}"""
    today = datetime.now().strftime('%Y%m%d')
    return f"{facility_code}{today}{sequence:03d}"


def generate_claims(
    db: Session, 
    source: str, 
    count: int = None
) -> Tuple[int, int]:
    """
    Generate realistic claims from a clearinghouse source.
    
    Args:
        db: Database session
        source: 'Availity' or 'Change Healthcare'
        count: Number of claims to generate (5-15 if not specified)
    
    Returns:
        Tuple of (claims_added, denials_added)
    """
    if count is None:
        count = random.randint(5, 15)
    
    # Get existing dimension data
    patients = db.query(DimPatient).all()
    facilities = db.query(DimFacility).all()
    procedures = db.query(DimProcedure).all()
    physicians = db.query(DimPhysician).all()
    denial_reasons = db.query(DimDenialReason).all()
    
    if not patients or not facilities or not procedures:
        raise ValueError("Missing dimension data - run seed_data first")
    
    # Get max claim ID for sequence
    max_claim = db.query(FactClaim).order_by(FactClaim.claim_id.desc()).first()
    sequence_start = (max_claim.claim_id if max_claim else 0) + 1
    
    claims_added = 0
    denials_added = 0
    
    # Target denial rate: 28-32%
    denial_rate = random.uniform(0.28, 0.32)
    
    for i in range(count):
        # Select random entities
        patient = random.choice(patients)
        facility = random.choice(facilities)
        procedure = random.choice(procedures)
        physician = random.choice(physicians)
        payer = get_payer_by_source(db, source)
        
        # Generate claim details
        facility_code = random.choice(FACILITY_CODES)
        claim_number = generate_claim_number(facility_code, sequence_start + i)
        
        # Service date within last 7-30 days
        days_ago = random.randint(7, 30)
        service_date = date.today() - timedelta(days=days_ago)
        submission_date = service_date + timedelta(days=random.randint(1, 5))
        adjudication_date = submission_date + timedelta(days=random.randint(5, 14))
        
        # Amounts
        billed_amount = round(random.uniform(500, 15000), 2)
        
        # Determine if this claim will be denied
        is_denied = random.random() < denial_rate
        
        if is_denied:
            allowed_amount = 0.0
            paid_amount = 0.0
            adjustment_amount = billed_amount
            claim_status = 'Denied'
        else:
            allowed_amount = round(billed_amount * random.uniform(0.6, 0.9), 2)
            paid_amount = round(allowed_amount * random.uniform(0.8, 1.0), 2)
            patient_responsibility = round(allowed_amount - paid_amount, 2)
            adjustment_amount = round(billed_amount - allowed_amount, 2)
            claim_status = 'Paid'
        
        # Create claim
        claim = FactClaim(
            claim_number=claim_number,
            patient_control_number=f"PCN{claim_number}",
            payer_claim_number=f"PYR{random.randint(100000, 999999)}",
            patient_id=patient.patient_id,
            payer_id=payer.payer_id if payer else 1,
            facility_id=facility.facility_id,
            physician_id=physician.physician_id,
            procedure_id=procedure.procedure_id,
            service_date=service_date,
            submission_date=submission_date,
            adjudication_date=adjudication_date,
            primary_diagnosis=f"Z{random.randint(10, 99)}.{random.randint(0, 9)}",
            billed_amount=billed_amount,
            allowed_amount=allowed_amount,
            paid_amount=paid_amount,
            patient_responsibility=patient_responsibility if not is_denied else 0,
            adjustment_amount=adjustment_amount,
            claim_status=claim_status,
            claim_type=random.choice(['Professional', 'Institutional']),
            place_of_service=str(random.choice([11, 21, 22, 23, 31]))
        )
        
        db.add(claim)
        db.flush()  # Get claim_id
        claims_added += 1
        
        # Create denial record if denied
        if is_denied:
            carc = get_random_carc()
            
            # Find matching denial reason or use first one
            denial_reason = None
            for dr in denial_reasons:
                if dr.carc_code == carc['code']:
                    denial_reason = dr
                    break
            if not denial_reason and denial_reasons:
                denial_reason = denial_reasons[0]
            
            # Appeal deadline is typically 60-180 days from denial
            appeal_deadline = adjudication_date + timedelta(days=random.randint(60, 180))
            
            denial = FactDenial(
                claim_id=claim.claim_id,
                denial_reason_id=denial_reason.denial_reason_id if denial_reason else None,
                carc_code=carc['code'],
                rarc_code=f"N{random.randint(100, 999)}",
                group_code=random.choice(GROUP_CODES),
                adjustment_amount=adjustment_amount,
                denial_date=adjudication_date,
                appeal_deadline=appeal_deadline,
                denial_status='New',
                # AI enrichment fields (will be populated by AI agents)
                clinical_urgency_score=round(random.uniform(3, 9), 1),
                appeal_success_probability=round(random.uniform(0.3, 0.8), 2),
                expected_recovery_amount=round(billed_amount * random.uniform(0.4, 0.7), 2),
                priority_score=round(random.uniform(50, 95), 1),
                root_cause_category=carc['category'],
                ai_risk_level=random.choice(['LOW', 'MEDIUM', 'HIGH']),
                needs_reeval=False,
                created_at=datetime.utcnow()  # Set created_at for queue wait time tracking
            )
            
            db.add(denial)
            denials_added += 1
    
    db.commit()
    return claims_added, denials_added


def run_feed_ingestion(db: Session, source: str) -> FeedIngestion:
    """
    Run a complete feed ingestion job.
    
    Args:
        db: Database session
        source: 'Availity' or 'Change Healthcare'
    
    Returns:
        FeedIngestion record with results
    """
    # Create ingestion record
    ingestion = FeedIngestion(
        source=source,
        started_at=datetime.utcnow(),
        status='running'
    )
    db.add(ingestion)
    db.commit()
    
    try:
        # Generate claims
        claims_added, denials_added = generate_claims(db, source)
        
        # Update ingestion record
        ingestion.completed_at = datetime.utcnow()
        ingestion.status = 'complete'
        ingestion.claims_added = claims_added
        ingestion.denials_added = denials_added
        db.commit()
        
    except Exception as e:
        ingestion.completed_at = datetime.utcnow()
        ingestion.status = 'failed'
        ingestion.error_message = str(e)
        db.commit()
        raise
    
    return ingestion


def get_feed_status(db: Session) -> Dict:
    """Get current feed status and today's statistics"""
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    
    # Get today's ingestions
    today_ingestions = db.query(FeedIngestion).filter(
        FeedIngestion.started_at >= today_start
    ).all()
    
    claims_today = sum(i.claims_added for i in today_ingestions)
    denials_today = sum(i.denials_added for i in today_ingestions)
    
    # Get last ingestion
    last_ingestion = db.query(FeedIngestion).order_by(
        FeedIngestion.started_at.desc()
    ).first()
    
    return {
        'claims_today': claims_today,
        'denials_today': denials_today,
        'last_feed_time': last_ingestion.completed_at.isoformat() if last_ingestion and last_ingestion.completed_at else None,
        'last_feed_source': last_ingestion.source if last_ingestion else None,
        'last_feed_status': last_ingestion.status if last_ingestion else None,
        'total_ingestions_today': len(today_ingestions)
    }


def get_feed_history(db: Session, limit: int = 20) -> List[Dict]:
    """Get recent feed ingestion history"""
    ingestions = db.query(FeedIngestion).order_by(
        FeedIngestion.started_at.desc()
    ).limit(limit).all()
    
    return [
        {
            'id': i.id,
            'source': i.source,
            'started_at': i.started_at.isoformat() if i.started_at else None,
            'completed_at': i.completed_at.isoformat() if i.completed_at else None,
            'status': i.status,
            'claims_added': i.claims_added,
            'denials_added': i.denials_added,
            'error_message': i.error_message
        }
        for i in ingestions
    ]
