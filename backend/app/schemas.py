"""
Pydantic schemas for API request/response models
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


# ==================== DIMENSION SCHEMAS ====================

class PatientBase(BaseModel):
    mrn: str
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    
class PatientResponse(PatientBase):
    patient_id: int
    adi_national_rank: Optional[int] = None
    sdoh_composite_score: Optional[float] = None
    sdoh_food_insecurity_risk: Optional[float] = None
    sdoh_housing_instability_risk: Optional[float] = None
    sdoh_transportation_risk: Optional[float] = None
    sdoh_social_isolation_risk: Optional[float] = None
    primary_payer_id: Optional[int] = None
    member_id: Optional[str] = None
    payer_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class PayerResponse(BaseModel):
    payer_id: int
    payer_name: str
    payer_type: Optional[str] = None
    avg_denial_rate: Optional[float] = None
    avg_appeal_success_rate: Optional[float] = None
    avg_days_to_decision: Optional[int] = None
    top_denial_reason_1: Optional[str] = None
    top_denial_reason_2: Optional[str] = None
    top_denial_reason_3: Optional[str] = None
    
    class Config:
        from_attributes = True


class FacilityResponse(BaseModel):
    facility_id: int
    facility_name: str
    facility_type: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    avg_denial_rate: Optional[float] = None
    total_beds: Optional[int] = None
    
    class Config:
        from_attributes = True


class DenialReasonResponse(BaseModel):
    denial_reason_id: int
    carc_code: str
    carc_description: Optional[str] = None
    carc_category: Optional[str] = None
    rarc_code: Optional[str] = None
    rarc_description: Optional[str] = None
    denial_category: Optional[str] = None
    is_appealable: bool = True
    historical_appeal_success_rate: Optional[float] = None
    
    class Config:
        from_attributes = True


class ProcedureResponse(BaseModel):
    procedure_id: int
    cpt_hcpcs_code: str
    code_type: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    pa_required: bool = False
    medicare_rate: Optional[float] = None
    denial_risk_score: Optional[float] = None
    
    class Config:
        from_attributes = True


class PhysicianResponse(BaseModel):
    physician_id: int
    npi: str
    first_name: str
    last_name: str
    credentials: Optional[str] = None
    specialty: Optional[str] = None
    p2p_success_rate_overall: Optional[float] = None
    total_p2p_reviews: int = 0
    
    class Config:
        from_attributes = True


# ==================== FACT SCHEMAS ====================

class ClaimResponse(BaseModel):
    claim_id: int
    claim_number: str
    patient_id: int
    payer_id: int
    facility_id: Optional[int] = None
    physician_id: Optional[int] = None
    procedure_id: Optional[int] = None
    service_date: date
    submission_date: Optional[date] = None
    adjudication_date: Optional[date] = None
    primary_diagnosis: Optional[str] = None
    billed_amount: float
    allowed_amount: Optional[float] = None
    paid_amount: Optional[float] = None
    adjustment_amount: Optional[float] = None
    claim_status: Optional[str] = None
    claim_type: Optional[str] = None
    
    # Joined fields
    patient_name: Optional[str] = None
    payer_name: Optional[str] = None
    facility_name: Optional[str] = None
    procedure_code: Optional[str] = None
    procedure_description: Optional[str] = None
    
    class Config:
        from_attributes = True


class DenialResponse(BaseModel):
    denial_id: int
    claim_id: int
    denial_reason_id: Optional[int] = None
    carc_code: str
    rarc_code: Optional[str] = None
    group_code: Optional[str] = None
    adjustment_amount: Optional[float] = None
    denial_date: date
    appeal_deadline: Optional[date] = None
    denial_status: Optional[str] = None
    
    # AI Agent Enrichments
    patient_sdoh_score: Optional[float] = None
    patient_vulnerability_flag: bool = False
    care_gap_identified: bool = False
    care_gap_description: Optional[str] = None
    clinical_urgency_score: Optional[float] = None
    medical_necessity_flag: Optional[bool] = None
    expected_recovery_amount: Optional[float] = None
    financial_priority_score: Optional[float] = None
    appeal_success_probability: Optional[float] = None
    recommended_action: Optional[str] = None
    p2p_recommended: bool = False
    root_cause_category: Optional[str] = None
    prevention_recommendation: Optional[str] = None
    priority_score: Optional[float] = None
    
    # Joined fields
    claim_number: Optional[str] = None
    patient_id: Optional[int] = None
    patient_name: Optional[str] = None
    patient_mrn: Optional[str] = None
    payer_name: Optional[str] = None
    billed_amount: Optional[float] = None
    procedure_code: Optional[str] = None
    procedure_description: Optional[str] = None
    denial_reason_description: Optional[str] = None
    denial_category: Optional[str] = None
    recommended_physician_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class PriorAuthResponse(BaseModel):
    prior_auth_id: int
    auth_number: Optional[str] = None
    patient_id: int
    payer_id: int
    procedure_id: Optional[int] = None
    physician_id: Optional[int] = None
    request_date: date
    decision_date: Optional[date] = None
    effective_start_date: Optional[date] = None
    effective_end_date: Optional[date] = None
    primary_diagnosis: Optional[str] = None
    auth_status: Optional[str] = None
    decision_reason: Optional[str] = None
    
    # AI Predictions
    denial_probability: Optional[float] = None
    documentation_score: Optional[float] = None
    policy_match_score: Optional[float] = None
    estimated_decision_days: Optional[int] = None
    missing_documents: Optional[str] = None
    risk_factors: Optional[str] = None
    
    # Joined fields
    patient_name: Optional[str] = None
    payer_name: Optional[str] = None
    procedure_code: Optional[str] = None
    procedure_description: Optional[str] = None
    physician_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class AppealResponse(BaseModel):
    appeal_id: int
    denial_id: int
    appeal_number: Optional[str] = None
    appeal_level: int = 1
    appeal_type: Optional[str] = None
    appeal_submitted_date: date
    appeal_decision_date: Optional[date] = None
    appeal_status: Optional[str] = None
    outcome_amount: Optional[float] = None
    p2p_scheduled: bool = False
    p2p_outcome: Optional[str] = None
    
    # Joined fields
    claim_number: Optional[str] = None
    patient_name: Optional[str] = None
    denial_amount: Optional[float] = None
    
    class Config:
        from_attributes = True


class RLTraceResponse(BaseModel):
    trace_id: int
    denial_id: Optional[int] = None
    prior_auth_id: Optional[int] = None
    staff_id: Optional[str] = None
    action_type: str
    action_timestamp: datetime
    ai_recommendation: Optional[str] = None
    ai_confidence: Optional[float] = None
    staff_followed_ai: Optional[bool] = None
    outcome: Optional[str] = None
    outcome_amount: Optional[float] = None
    reward_score: Optional[float] = None
    feedback_rating: Optional[int] = None
    
    class Config:
        from_attributes = True


# ==================== ACTION SCHEMAS ====================

class StaffActionCreate(BaseModel):
    denial_id: Optional[int] = None
    prior_auth_id: Optional[int] = None
    staff_id: str
    action_type: str
    ai_recommendation: Optional[str] = None
    ai_confidence: Optional[float] = None
    staff_followed_ai: Optional[bool] = None
    staff_feedback: Optional[str] = None
    feedback_rating: Optional[int] = None


class StaffActionResponse(BaseModel):
    trace_id: int
    message: str


# ==================== DASHBOARD SCHEMAS ====================

class DashboardMetrics(BaseModel):
    total_claims: int
    total_denials: int
    denial_rate: float
    total_denied_amount: float
    total_recovered_amount: float
    recovery_rate: float
    pending_appeals: int
    avg_appeal_success_rate: float
    high_priority_denials: int
    pa_pending: int
    pa_approval_rate: float


class DenialByCategory(BaseModel):
    category: str
    count: int
    amount: float
    percentage: float


class DenialByPayer(BaseModel):
    payer_name: str
    payer_id: int
    denial_count: int
    denial_amount: float
    denial_rate: float
    appeal_success_rate: float


class DenialTrend(BaseModel):
    date: str
    denial_count: int
    denial_amount: float
    recovery_amount: float


class AIAgentInsight(BaseModel):
    agent_name: str
    insight_type: str
    description: str
    impact_score: float
    affected_count: int
    recommended_action: str


class LearningMetrics(BaseModel):
    total_actions: int
    ai_followed_rate: float
    avg_reward_score: float
    successful_outcomes: int
    action_distribution: dict


# ==================== QUERY PARAMS ====================

class QueryParams(BaseModel):
    page: int = 1
    page_size: int = 20
    sort_by: Optional[str] = None
    sort_order: str = "desc"
    status: Optional[str] = None
    payer_id: Optional[int] = None
    facility_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    priority_min: Optional[float] = None
    search: Optional[str] = None
