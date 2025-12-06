from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


# ==================== DIMENSION TABLES ====================

class DimPatient(Base):
    """Patient dimension table with demographics and SDOH scores"""
    __tablename__ = "dim_patient"
    
    patient_id = Column(Integer, primary_key=True, autoincrement=True)
    mrn = Column(String(50), unique=True, nullable=False)  # Medical Record Number
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(20))
    address_line1 = Column(String(200))
    address_line2 = Column(String(200))
    city = Column(String(100))
    state = Column(String(2))
    zip_code = Column(String(10))
    phone = Column(String(20))
    email = Column(String(100))
    
    # SDOH (Social Determinants of Health) scores
    adi_national_rank = Column(Integer)  # Area Deprivation Index (1-100)
    adi_state_rank = Column(Integer)
    sdoh_food_insecurity_risk = Column(Float)  # 0-1 score
    sdoh_housing_instability_risk = Column(Float)
    sdoh_transportation_risk = Column(Float)
    sdoh_social_isolation_risk = Column(Float)
    sdoh_composite_score = Column(Float)  # Overall SDOH risk score
    
    # Insurance info
    primary_payer_id = Column(Integer, ForeignKey("dim_payer.payer_id"))
    member_id = Column(String(50))
    group_number = Column(String(50))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    primary_payer = relationship("DimPayer", back_populates="patients")
    claims = relationship("FactClaim", back_populates="patient")
    prior_auths = relationship("FactPriorAuth", back_populates="patient")


class DimPayer(Base):
    """Insurance payer dimension with denial patterns"""
    __tablename__ = "dim_payer"
    
    payer_id = Column(Integer, primary_key=True, autoincrement=True)
    payer_name = Column(String(200), nullable=False)
    payer_type = Column(String(50))  # Commercial, Medicare, Medicaid, etc.
    
    # Contact info
    address = Column(String(300))
    phone = Column(String(20))
    fax = Column(String(20))
    website = Column(String(200))
    
    # Denial pattern metrics
    avg_denial_rate = Column(Float)  # Historical denial rate
    avg_appeal_success_rate = Column(Float)
    avg_days_to_decision = Column(Integer)
    p2p_availability = Column(Boolean, default=True)
    electronic_submission = Column(Boolean, default=True)
    
    # Common denial reasons for this payer
    top_denial_reason_1 = Column(String(10))  # CARC code
    top_denial_reason_2 = Column(String(10))
    top_denial_reason_3 = Column(String(10))
    
    # Clearinghouse routing (from Clearinghouse Addendum)
    clearinghouse = Column(String(50))  # 'availity' or 'change_healthcare'
    avg_days_to_pay = Column(Integer)  # Average days from submission to payment
    base_denial_rate = Column(Float)  # Payer-specific denial rate
    base_yield = Column(Float)  # Expected yield percentage
    top_denial_carc = Column(String(10))  # Most common CARC code for this payer
    payer_volume_pct = Column(Float)  # Percentage of total volume (e.g., 0.22 for FL Blue)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    patients = relationship("DimPatient", back_populates="primary_payer")
    claims = relationship("FactClaim", back_populates="payer")


class DimFacility(Base):
    """Healthcare facility dimension (AdventHealth hospitals)"""
    __tablename__ = "dim_facility"
    
    facility_id = Column(Integer, primary_key=True, autoincrement=True)
    facility_name = Column(String(200), nullable=False)
    facility_type = Column(String(50))  # Hospital, Clinic, ASC, etc.
    npi = Column(String(10))  # National Provider Identifier
    tax_id = Column(String(15))
    
    address_line1 = Column(String(200))
    city = Column(String(100))
    state = Column(String(2))
    zip_code = Column(String(10))
    
    # Performance metrics
    avg_denial_rate = Column(Float)
    avg_collection_rate = Column(Float)
    total_beds = Column(Integer)
    
    # Clearinghouse routing (from Clearinghouse Addendum)
    volume_weight = Column(Float)  # Percentage of total volume (e.g., 0.25 for Orlando flagship)
    primary_clearinghouse = Column(String(50))  # 'availity' or 'change_healthcare'
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    claims = relationship("FactClaim", back_populates="facility")


class DimDenialReason(Base):
    """CARC/RARC denial reason codes from RHAIL"""
    __tablename__ = "dim_denial_reason"
    
    denial_reason_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # CARC (Claim Adjustment Reason Code) - X12 835
    carc_code = Column(String(10), nullable=False)
    carc_description = Column(Text)
    carc_category = Column(String(100))  # CO, PR, OA, PI, CR
    
    # RARC (Remittance Advice Remark Code)
    rarc_code = Column(String(10))
    rarc_description = Column(Text)
    
    # Classification
    denial_category = Column(String(100))  # Medical Necessity, Auth Required, etc.
    is_appealable = Column(Boolean, default=True)
    typical_resolution = Column(String(200))
    
    # Success metrics
    historical_appeal_success_rate = Column(Float)
    avg_resolution_days = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    denials = relationship("FactDenial", back_populates="denial_reason")


class DimProcedure(Base):
    """CPT/HCPCS procedure codes with PA requirements"""
    __tablename__ = "dim_procedure"
    
    procedure_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Code info
    cpt_hcpcs_code = Column(String(10), nullable=False)
    code_type = Column(String(10))  # CPT, HCPCS
    description = Column(Text)
    short_description = Column(String(100))
    
    # Categorization
    category = Column(String(100))
    subcategory = Column(String(100))
    
    # PA requirements
    pa_required = Column(Boolean, default=False)
    pa_required_payers = Column(Text)  # JSON list of payer IDs requiring PA
    typical_pa_turnaround_days = Column(Integer)
    
    # Pricing
    medicare_rate = Column(Float)
    avg_commercial_rate = Column(Float)
    
    # Denial risk
    denial_risk_score = Column(Float)  # 0-1 probability of denial
    common_denial_reasons = Column(Text)  # JSON list of CARC codes
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    claims = relationship("FactClaim", back_populates="procedure")
    prior_auths = relationship("FactPriorAuth", back_populates="procedure")


class DimPhysician(Base):
    """Physician dimension with P2P success rates"""
    __tablename__ = "dim_physician"
    
    physician_id = Column(Integer, primary_key=True, autoincrement=True)
    npi = Column(String(10), unique=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    
    # Credentials
    credentials = Column(String(50))  # MD, DO, NP, etc.
    specialty = Column(String(100))
    subspecialty = Column(String(100))
    
    # Facility affiliation
    primary_facility_id = Column(Integer, ForeignKey("dim_facility.facility_id"))
    
    # P2P (Peer-to-Peer) success metrics by payer
    p2p_success_rate_overall = Column(Float)
    p2p_success_rate_by_payer = Column(Text)  # JSON: {payer_id: rate}
    total_p2p_reviews = Column(Integer, default=0)
    
    # Performance
    avg_denial_rate = Column(Float)
    avg_appeal_success_rate = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    primary_facility = relationship("DimFacility")
    claims = relationship("FactClaim", back_populates="physician")
    prior_auths = relationship("FactPriorAuth", back_populates="physician")


# ==================== FACT TABLES ====================

class FactClaim(Base):
    """Claims fact table (base data for denials) - 835/837 format"""
    __tablename__ = "fact_claim"
    
    claim_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Claim identifiers (835/837 standard)
    claim_number = Column(String(50), unique=True, nullable=False)
    patient_control_number = Column(String(50))  # CLM01 in 837
    payer_claim_number = Column(String(50))  # CLP01 in 835
    
    # Foreign keys
    patient_id = Column(Integer, ForeignKey("dim_patient.patient_id"), nullable=False)
    payer_id = Column(Integer, ForeignKey("dim_payer.payer_id"), nullable=False)
    facility_id = Column(Integer, ForeignKey("dim_facility.facility_id"))
    physician_id = Column(Integer, ForeignKey("dim_physician.physician_id"))
    procedure_id = Column(Integer, ForeignKey("dim_procedure.procedure_id"))
    
    # Dates
    service_date = Column(Date, nullable=False)
    submission_date = Column(Date)
    adjudication_date = Column(Date)
    
    # Diagnosis codes (ICD-10)
    primary_diagnosis = Column(String(10))
    secondary_diagnosis = Column(String(10))
    diagnosis_codes = Column(Text)  # JSON list of all ICD-10 codes
    
    # Amounts (835 standard fields)
    billed_amount = Column(Float, nullable=False)
    allowed_amount = Column(Float)
    paid_amount = Column(Float)
    patient_responsibility = Column(Float)
    adjustment_amount = Column(Float)
    
    # Status
    claim_status = Column(String(50))  # Pending, Paid, Denied, Partial
    claim_type = Column(String(20))  # Professional, Institutional
    place_of_service = Column(String(5))
    
    # 835 specific fields
    claim_frequency_code = Column(String(2))
    claim_filing_indicator = Column(String(5))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = relationship("DimPatient", back_populates="claims")
    payer = relationship("DimPayer", back_populates="claims")
    facility = relationship("DimFacility", back_populates="claims")
    physician = relationship("DimPhysician", back_populates="claims")
    procedure = relationship("DimProcedure", back_populates="claims")
    denials = relationship("FactDenial", back_populates="claim")


class FactDenial(Base):
    """Denials fact table with AI agent enrichments"""
    __tablename__ = "fact_denial"
    
    denial_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    claim_id = Column(Integer, ForeignKey("fact_claim.claim_id"), nullable=False)
    denial_reason_id = Column(Integer, ForeignKey("dim_denial_reason.denial_reason_id"))
    
    # Denial details (835 CAS segment)
    carc_code = Column(String(10), nullable=False)
    rarc_code = Column(String(10))
    group_code = Column(String(5))  # CO, PR, OA, PI, CR
    adjustment_amount = Column(Float)
    
    # Dates
    denial_date = Column(Date, nullable=False)
    appeal_deadline = Column(Date)
    
    # Status
    denial_status = Column(String(50))  # New, In Review, Appealed, Resolved, Written Off
    
    # AI Agent Enrichments
    # SDOH Scorer
    patient_sdoh_score = Column(Float)
    patient_vulnerability_flag = Column(Boolean, default=False)
    
    # Care Gap Detector
    care_gap_identified = Column(Boolean, default=False)
    care_gap_description = Column(Text)
    
    # Clinical Urgency Agent
    clinical_urgency_score = Column(Float)  # 0-10 scale
    medical_necessity_flag = Column(Boolean)
    
    # Financial Value Agent
    expected_recovery_amount = Column(Float)
    financial_priority_score = Column(Float)
    
    # Recovery Predictor
    appeal_success_probability = Column(Float)  # 0-1
    recommended_action = Column(String(100))
    
    # P2P Optimizer
    recommended_physician_id = Column(Integer, ForeignKey("dim_physician.physician_id"))
    p2p_recommended = Column(Boolean, default=False)
    
    # Root Cause Analyzer
    root_cause_category = Column(String(100))
    prevention_recommendation = Column(Text)
    
    # Composite priority score
    priority_score = Column(Float)  # Combined score for work queue ordering
    
    # AI-Resolved Queue fields
    ai_last_reviewed_at = Column(DateTime)  # When 18-agent validation completed
    ai_risk_level = Column(String(20))  # LOW, MEDIUM, HIGH
    ai_ready_for_staff_approval = Column(Boolean, default=False)  # True if AI-resolved & low risk
    ai_recommended_action = Column(String(200))  # e.g., "Submit appeal letter", "Schedule P2P"
    ai_change_summary = Column(Text)  # Summary of what AI found/recommends
    
    # Staff approval workflow
    staff_approval_status = Column(String(20), default='PENDING')  # PENDING, APPROVED, REJECTED
    staff_approval_at = Column(DateTime)
    staff_approval_by = Column(String(100))  # Staff name/ID
    staff_approval_notes = Column(Text)  # Optional rationale
    
    # Policy change re-evaluation flag
    needs_reeval = Column(Boolean, default=False)  # True when policy change affects this denial
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    claim = relationship("FactClaim", back_populates="denials")
    denial_reason = relationship("DimDenialReason", back_populates="denials")
    recommended_physician = relationship("DimPhysician")
    appeals = relationship("FactAppeal", back_populates="denial")


class FactPriorAuth(Base):
    """Prior Authorization requests with AI predictions"""
    __tablename__ = "fact_prior_auth"
    
    prior_auth_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Identifiers
    auth_number = Column(String(50), unique=True)
    reference_number = Column(String(50))
    
    # Foreign keys
    patient_id = Column(Integer, ForeignKey("dim_patient.patient_id"), nullable=False)
    payer_id = Column(Integer, ForeignKey("dim_payer.payer_id"), nullable=False)
    procedure_id = Column(Integer, ForeignKey("dim_procedure.procedure_id"))
    physician_id = Column(Integer, ForeignKey("dim_physician.physician_id"))
    facility_id = Column(Integer, ForeignKey("dim_facility.facility_id"))
    
    # Dates
    request_date = Column(Date, nullable=False)
    decision_date = Column(Date)
    effective_start_date = Column(Date)
    effective_end_date = Column(Date)
    
    # Clinical info
    primary_diagnosis = Column(String(10))
    diagnosis_codes = Column(Text)  # JSON list
    clinical_notes = Column(Text)
    
    # Status
    auth_status = Column(String(50))  # Pending, Approved, Denied, Partial, Expired
    decision_reason = Column(Text)
    
    # AI Agent Predictions
    # PA Risk Predictor
    denial_probability = Column(Float)  # 0-1
    risk_factors = Column(Text)  # JSON list of risk factors
    
    # Doc Completeness Agent
    documentation_score = Column(Float)  # 0-100
    missing_documents = Column(Text)  # JSON list
    
    # Policy Monitor Agent
    policy_match_score = Column(Float)
    policy_concerns = Column(Text)
    
    # Queue Wait Time Agent
    estimated_decision_days = Column(Integer)
    optimal_submission_time = Column(String(50))
    
    # AI-Resolved Queue fields
    ai_last_reviewed_at = Column(DateTime)  # When 18-agent validation completed
    ai_risk_level = Column(String(20))  # LOW, MEDIUM, HIGH
    ai_ready_for_staff_approval = Column(Boolean, default=False)  # True if AI-resolved & low risk
    ai_recommended_action = Column(String(200))  # e.g., "Submit PA", "Add clinical notes"
    ai_change_summary = Column(Text)  # Summary of what AI found/recommends
    
    # Staff approval workflow
    staff_approval_status = Column(String(20), default='PENDING')  # PENDING, APPROVED, REJECTED
    staff_approval_at = Column(DateTime)
    staff_approval_by = Column(String(100))  # Staff name/ID
    staff_approval_notes = Column(Text)  # Optional rationale
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = relationship("DimPatient", back_populates="prior_auths")
    payer = relationship("DimPayer")
    procedure = relationship("DimProcedure", back_populates="prior_auths")
    physician = relationship("DimPhysician", back_populates="prior_auths")
    facility = relationship("DimFacility")


class FactAppeal(Base):
    """Appeals fact table with outcomes for learning"""
    __tablename__ = "fact_appeal"
    
    appeal_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    denial_id = Column(Integer, ForeignKey("fact_denial.denial_id"), nullable=False)
    
    # Appeal details
    appeal_number = Column(String(50), unique=True)
    appeal_level = Column(Integer, default=1)  # 1st, 2nd, 3rd level
    appeal_type = Column(String(50))  # first_level, second_level, external_review
    
    # Dates
    appeal_submitted_date = Column(Date, nullable=False)
    appeal_decision_date = Column(Date)
    
    # Outcome
    appeal_status = Column(String(50))  # submitted, in_review, decided
    outcome = Column(String(50))  # overturned, upheld, partial
    outcome_amount = Column(Float)  # Amount recovered
    recovered_amount = Column(Float, default=0.0)  # Alias for outcome_amount
    
    # P2P details
    p2p_scheduled = Column(Boolean, default=False)
    p2p_date = Column(DateTime)
    p2p_physician_id = Column(Integer, ForeignKey("dim_physician.physician_id"))
    p2p_outcome = Column(String(50))
    
    # Documentation
    appeal_letter = Column(Text)
    supporting_docs = Column(Text)  # JSON list of document references
    
    # Learning data - links to RL trace
    followed_ai = Column(Boolean, default=False)  # Whether staff followed AI recommendation
    success_factors = Column(Text)  # JSON - what worked
    failure_factors = Column(Text)  # JSON - what didn't work
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    denial = relationship("FactDenial", back_populates="appeals")
    p2p_physician = relationship("DimPhysician")


# ==================== FEED INGESTION & WORKFLOW TABLES ====================

class FeedIngestion(Base):
    """Track clearinghouse feed ingestion jobs"""
    __tablename__ = "feed_ingestion"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False)  # 'Availity', 'Change Healthcare'
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), default='running')  # running, complete, failed
    claims_added = Column(Integer, default=0)
    denials_added = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)


class StaffAction(Base):
    """Track staff actions on denials for RL feedback loop"""
    __tablename__ = "staff_action"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    denial_id = Column(Integer, ForeignKey("fact_denial.denial_id"), nullable=False)
    staff_id = Column(String(50), nullable=False)  # Simulated user ID
    action_type = Column(String(50), nullable=False)  # follow_ai, custom_plan, escalate, dismiss
    ai_recommendation = Column(String(200))  # What AI suggested
    actual_action = Column(String(200))  # What staff did
    timestamp = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    
    # Relationships
    denial = relationship("FactDenial")


class PolicyChange(Base):
    """Track payer policy changes that affect denials"""
    __tablename__ = "policy_change"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    payer_id = Column(Integer, ForeignKey("dim_payer.payer_id"), nullable=False)
    change_type = Column(String(50), nullable=False)  # coverage_expanded, criteria_updated, pa_removed
    affected_procedures = Column(Text)  # JSON array of CPT codes
    effective_date = Column(Date, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    payer = relationship("DimPayer")


class AuditLog(Base):
    """Audit trail for compliance"""
    __tablename__ = "audit_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String(50), nullable=False)  # Simulated user
    user_role = Column(String(20), nullable=False)  # clinical, admin, executive
    action = Column(String(50), nullable=False)  # view_denial, run_ai, submit_appeal, export_data
    resource_type = Column(String(50))  # denial, prior_auth, patient, report
    resource_id = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)  # JSON for additional context


class FactRLTrace(Base):
    """Staff actions for Agent Lightning reinforcement learning"""
    __tablename__ = "fact_rl_trace"
    
    trace_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Context
    denial_id = Column(Integer, ForeignKey("fact_denial.denial_id"))
    prior_auth_id = Column(Integer, ForeignKey("fact_prior_auth.prior_auth_id"))
    
    # Staff action
    staff_id = Column(String(50))
    action_type = Column(String(100), nullable=False)  # Appeal, P2P Request, Write Off, etc.
    action_timestamp = Column(DateTime, default=datetime.utcnow)
    
    # State before action
    state_before = Column(Text)  # JSON snapshot of denial/PA state
    
    # AI recommendation at time of action
    ai_recommendation = Column(String(100))
    ai_confidence = Column(Float)
    staff_followed_ai = Column(Boolean)
    
    # Outcome (filled in later)
    outcome = Column(String(100))  # Success, Failure, Partial
    outcome_amount = Column(Float)
    outcome_timestamp = Column(DateTime)
    
    # Reward signal for RL
    reward_score = Column(Float)  # Calculated reward for RL training
    
    # Feedback
    staff_feedback = Column(Text)
    feedback_rating = Column(Integer)  # 1-5 rating of AI recommendation
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    denial = relationship("FactDenial")
    prior_auth = relationship("FactPriorAuth")


# ==================== TREATMENT GUIDANCE TABLES ====================

class DimTreatmentGuideline(Base):
    """Treatment guidelines by procedure and diagnosis"""
    __tablename__ = "dim_treatment_guideline"
    
    guideline_id = Column(Integer, primary_key=True, autoincrement=True)
    procedure_code = Column(String(20), nullable=False)  # CPT/HCPCS code
    diagnosis_code = Column(String(20))  # ICD-10 code
    
    # Guideline details
    guideline_name = Column(String(200), nullable=False)
    guideline_source = Column(String(100))  # e.g., "CMS LCD", "Payer Policy", "Clinical Guidelines"
    guideline_version = Column(String(50))
    effective_date = Column(Date)
    expiration_date = Column(Date)
    
    # Treatment recommendation
    treatment_recommendation = Column(Text)  # What treatment is recommended
    medical_necessity_criteria = Column(Text)  # Criteria for medical necessity
    contraindications = Column(Text)  # When treatment should NOT be given
    alternative_treatments = Column(Text)  # Alternative treatment options
    
    # Prior auth requirements
    prior_auth_required = Column(Boolean, default=True)
    typical_approval_rate = Column(Float)  # Historical approval rate for this procedure
    avg_days_to_approval = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DimClinicalCriteria(Base):
    """Clinical criteria required for treatment approval"""
    __tablename__ = "dim_clinical_criteria"
    
    criteria_id = Column(Integer, primary_key=True, autoincrement=True)
    guideline_id = Column(Integer, ForeignKey("dim_treatment_guideline.guideline_id"))
    
    # Criteria details
    criteria_name = Column(String(200), nullable=False)
    criteria_type = Column(String(50))  # e.g., "Lab Result", "Imaging", "Clinical Finding", "Prior Treatment"
    criteria_description = Column(Text)
    
    # Requirements
    required_value = Column(String(100))  # e.g., "HbA1c > 7.0", "BMI > 30"
    required_documentation = Column(String(200))  # What documentation is needed
    is_mandatory = Column(Boolean, default=True)
    
    # Payer-specific
    payer_id = Column(Integer, ForeignKey("dim_payer.payer_id"))  # NULL means applies to all payers
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    guideline = relationship("DimTreatmentGuideline")
    payer = relationship("DimPayer")


class DimDocumentationRequirement(Base):
    """Documentation requirements for treatment approval"""
    __tablename__ = "dim_documentation_requirement"
    
    requirement_id = Column(Integer, primary_key=True, autoincrement=True)
    guideline_id = Column(Integer, ForeignKey("dim_treatment_guideline.guideline_id"))
    
    # Requirement details
    document_type = Column(String(100), nullable=False)  # e.g., "Clinical Notes", "Lab Results", "Imaging Report"
    document_description = Column(Text)
    is_mandatory = Column(Boolean, default=True)
    
    # Timing requirements
    max_age_days = Column(Integer)  # How recent the document must be (e.g., 30 days for labs)
    
    # Payer-specific
    payer_id = Column(Integer, ForeignKey("dim_payer.payer_id"))  # NULL means applies to all payers
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    guideline = relationship("DimTreatmentGuideline")
    payer = relationship("DimPayer")


class FactTreatmentGuidanceResult(Base):
    """Results of treatment guidance evaluation for prior auths"""
    __tablename__ = "fact_treatment_guidance_result"
    
    result_id = Column(Integer, primary_key=True, autoincrement=True)
    prior_auth_id = Column(Integer, ForeignKey("fact_prior_auth.prior_auth_id"))
    guideline_id = Column(Integer, ForeignKey("dim_treatment_guideline.guideline_id"))
    
    # Evaluation results
    can_treat = Column(String(20))  # YES, NO, PENDING, CONDITIONAL
    can_treat_reason = Column(Text)  # Explanation of why/why not
    
    # Criteria evaluation
    criteria_met_count = Column(Integer)
    criteria_total_count = Column(Integer)
    criteria_met_percentage = Column(Float)
    missing_criteria = Column(Text)  # JSON list of missing criteria
    
    # Documentation evaluation
    docs_complete = Column(Boolean)
    missing_documents = Column(Text)  # JSON list of missing documents
    
    # AI recommendation
    ai_treatment_recommendation = Column(Text)
    ai_confidence_score = Column(Float)
    ai_alternative_suggestion = Column(Text)
    
    # Clinical urgency
    clinical_urgency_score = Column(Integer)  # 1-10
    urgency_reason = Column(Text)
    
    evaluated_at = Column(DateTime, default=datetime.utcnow)
    evaluated_by = Column(String(100))  # AI agent or staff ID
    
    # Relationships
    prior_auth = relationship("FactPriorAuth")
    guideline = relationship("DimTreatmentGuideline")


# ==================== CFO CHURN PREDICTION TABLES ====================

class ChurnPrediction(Base):
    """AI prediction made at 837 submission for churn forecasting"""
    __tablename__ = "fact_churn_prediction"
    
    prediction_id = Column(Integer, primary_key=True, autoincrement=True)
    claim_id = Column(Integer, ForeignKey("fact_claim.claim_id"))
    batch_id = Column(String(100))
    predicted_at = Column(DateTime, default=datetime.utcnow)
    
    # Amounts
    billed_amount = Column(Float)
    predicted_paid = Column(Float)
    predicted_churn_rate = Column(Float)  # 0-1
    confidence_score = Column(Float)  # 0-1
    
    # Breakdown
    predicted_contractual = Column(Float)
    predicted_denial = Column(Float)
    predicted_patient_resp = Column(Float)
    
    # Risk analysis
    risk_factors = Column(Text)  # JSON
    preventive_actions = Column(Text)  # JSON
    risk_score = Column(Float)  # 0-1
    risk_level = Column(String(20))  # LOW, MEDIUM, HIGH
    
    # Collection timeline
    expected_days_to_payment = Column(Integer)
    expected_payment_date = Column(Date)
    
    model_version = Column(String(50))
    
    # Relationships
    claim = relationship("FactClaim")


class Submission837(Base):
    """837 claim submission tracking"""
    __tablename__ = "fact_837_submission"
    
    submission_id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(100), ForeignKey("ingestion_batch.batch_id"))
    claim_id = Column(Integer, ForeignKey("fact_claim.claim_id"))
    
    transaction_type = Column(String(10))  # '837P', '837I'
    submitter_id = Column(String(50))
    receiver_id = Column(String(50))
    submitted_at = Column(DateTime, default=datetime.utcnow)
    
    edi_segments = Column(Text)  # Key segments as JSON
    prediction_id = Column(Integer, ForeignKey("fact_churn_prediction.prediction_id"))
    
    # Relationships
    claim = relationship("FactClaim")
    prediction = relationship("ChurnPrediction")


class Response835(Base):
    """835 remittance response tracking"""
    __tablename__ = "fact_835_response"
    
    response_id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(100), ForeignKey("ingestion_batch.batch_id"))
    claim_id = Column(Integer, ForeignKey("fact_claim.claim_id"))
    submission_id = Column(Integer, ForeignKey("fact_837_submission.submission_id"))
    
    payer_claim_number = Column(String(50))
    check_number = Column(String(50))
    payment_method = Column(String(20))
    payment_date = Column(Date)
    received_at = Column(DateTime, default=datetime.utcnow)
    
    billed_amount = Column(Float)
    paid_amount = Column(Float)
    patient_responsibility = Column(Float)
    
    claim_status_code = Column(String(5))  # 1=Processed, 2=Denied, etc.
    
    total_contractual = Column(Float)
    total_denials = Column(Float)
    
    edi_segments = Column(Text)
    
    # Relationships
    claim = relationship("FactClaim")
    submission = relationship("Submission837")


class Adjustment835(Base):
    """Individual adjustments from 835"""
    __tablename__ = "fact_835_adjustment"
    
    adjustment_id = Column(Integer, primary_key=True, autoincrement=True)
    response_id = Column(Integer, ForeignKey("fact_835_response.response_id"))
    claim_id = Column(Integer, ForeignKey("fact_claim.claim_id"))
    
    group_code = Column(String(5))  # CO, PR, OA, PI, CR
    reason_code = Column(String(10))  # CARC
    remark_codes = Column(Text)  # RARC JSON array
    
    adjustment_amount = Column(Float)
    quantity = Column(Integer)
    
    adjustment_category = Column(String(50))  # 'contractual', 'denial', 'patient'
    
    # Relationships
    response = relationship("Response835")
    claim = relationship("FactClaim")


class ChurnReconciliation(Base):
    """Prediction vs Actual reconciliation"""
    __tablename__ = "fact_churn_reconciliation"
    
    reconciliation_id = Column(Integer, primary_key=True, autoincrement=True)
    claim_id = Column(Integer, ForeignKey("fact_claim.claim_id"))
    prediction_id = Column(Integer, ForeignKey("fact_churn_prediction.prediction_id"))
    response_id = Column(Integer, ForeignKey("fact_835_response.response_id"))
    
    predicted_paid = Column(Float)
    actual_paid = Column(Float)
    variance_amount = Column(Float)
    variance_pct = Column(Float)
    
    contractual_variance = Column(Float)
    denial_variance = Column(Float)
    patient_resp_variance = Column(Float)
    
    variance_root_cause = Column(Text)  # JSON from AI
    forecast_accuracy_score = Column(Float)
    
    reconciled_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    claim = relationship("FactClaim")
    prediction = relationship("ChurnPrediction")
    response = relationship("Response835")


class BudgetForecast(Base):
    """Aggregated budget forecasts for CFO dashboard"""
    __tablename__ = "fact_budget_forecast"
    
    forecast_id = Column(Integer, primary_key=True, autoincrement=True)
    forecast_date = Column(Date)
    period_type = Column(String(20))  # 'daily', 'weekly', 'monthly'
    period_start = Column(Date)
    period_end = Column(Date)
    
    submitted_amount = Column(Float)
    predicted_collection = Column(Float)
    predicted_churn_rate = Column(Float)
    confidence_low = Column(Float)
    confidence_high = Column(Float)
    
    actual_collection = Column(Float)
    actual_variance = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class IngestionBatch(Base):
    """Track ingestion batches for 837/835 files"""
    __tablename__ = "ingestion_batch"
    
    batch_id = Column(String(100), primary_key=True)
    source = Column(String(50))  # 'availity', 'change_healthcare', 'waystar'
    file_name = Column(String(200))
    file_type = Column(String(10))  # '835', '837P', '837I'
    file_size_bytes = Column(Integer)
    received_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    status = Column(String(20))  # 'processing', 'complete', 'error'
    total_records = Column(Integer)
    processed_records = Column(Integer)
    error_records = Column(Integer)
    denials_detected = Column(Integer)
    processing_time_ms = Column(Integer)


class IngestionSource(Base):
    """Clearinghouse connection config"""
    __tablename__ = "ingestion_source"
    
    source_id = Column(String(50), primary_key=True)
    source_name = Column(String(100))
    connection_type = Column(String(20))  # 'SFTP', 'API', 'FHIR'
    status = Column(String(20))  # 'active', 'inactive', 'error'
    last_sync_at = Column(DateTime)
    records_today = Column(Integer, default=0)
    error_rate = Column(Float, default=0)
