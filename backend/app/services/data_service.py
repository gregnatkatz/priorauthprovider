"""
Data Service Layer - Abstract interface for data access
Supports switching between Synthetic (SQLite) and Fabric HDS data sources
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models import (
    DimPatient, DimPayer, DimFacility, DimDenialReason, DimProcedure, DimPhysician,
    FactClaim, FactDenial, FactPriorAuth, FactAppeal, FactRLTrace
)
from app.schemas import (
    DenialResponse, ClaimResponse, PriorAuthResponse, AppealResponse,
    PatientResponse, PayerResponse, DashboardMetrics, DenialByCategory,
    DenialByPayer, DenialTrend, StaffActionCreate, RLTraceResponse
)


class DataService(ABC):
    """Abstract base class for data service implementations"""
    
    @abstractmethod
    async def get_denials(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        payer_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        priority_min: Optional[float] = None,
        sort_by: str = "priority_score",
        sort_order: str = "desc",
        search: Optional[str] = None
    ) -> tuple[List[DenialResponse], int]:
        pass
    
    @abstractmethod
    async def get_denial_by_id(self, denial_id: int) -> Optional[DenialResponse]:
        pass
    
    @abstractmethod
    async def get_prior_auth_by_id(self, pa_id: int) -> Optional[PriorAuthResponse]:
        pass
    
    @abstractmethod
    async def get_prior_auths(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        payer_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        search: Optional[str] = None
    ) -> tuple[List[PriorAuthResponse], int]:
        pass
    
    @abstractmethod
    async def get_patient(self, patient_id: int) -> Optional[PatientResponse]:
        pass
    
    @abstractmethod
    async def get_dashboard_metrics(self) -> DashboardMetrics:
        pass
    
    @abstractmethod
    async def record_action(self, action: StaffActionCreate) -> int:
        pass


def format_queue_wait_time(seconds: int) -> str:
    """Format queue wait time in human-readable format (e.g., '2h 15m', '1d 4h')"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d {hours}h" if hours > 0 else f"{days}d"


class SQLiteDataService(DataService):
    """SQLite implementation of the data service for synthetic data"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _calc_queue_wait_seconds(self, created_at, denial_date) -> Optional[int]:
        """Calculate queue wait time in seconds, using created_at if available, otherwise denial_date"""
        base_time = created_at or denial_date
        if not base_time:
            return None
        if isinstance(base_time, date) and not isinstance(base_time, datetime):
            base_time = datetime.combine(base_time, datetime.min.time())
        return int((datetime.utcnow() - base_time).total_seconds())
    
    async def get_denials(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        payer_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        priority_min: Optional[float] = None,
        sort_by: str = "priority_score",
        sort_order: str = "desc",
        search: Optional[str] = None
    ) -> tuple[List[DenialResponse], int]:
        
        # Build base query with joins
        query = (
            select(FactDenial)
            .join(FactClaim, FactDenial.claim_id == FactClaim.claim_id)
            .join(DimPatient, FactClaim.patient_id == DimPatient.patient_id)
            .join(DimPayer, FactClaim.payer_id == DimPayer.payer_id)
            .outerjoin(DimProcedure, FactClaim.procedure_id == DimProcedure.procedure_id)
            .outerjoin(DimDenialReason, FactDenial.denial_reason_id == DimDenialReason.denial_reason_id)
            .outerjoin(DimPhysician, FactDenial.recommended_physician_id == DimPhysician.physician_id)
        )
        
        # Apply filters
        conditions = []
        if status:
            conditions.append(FactDenial.denial_status == status)
        if payer_id:
            conditions.append(FactClaim.payer_id == payer_id)
        if date_from:
            conditions.append(FactDenial.denial_date >= date_from)
        if date_to:
            conditions.append(FactDenial.denial_date <= date_to)
        if priority_min is not None:
            conditions.append(FactDenial.priority_score >= priority_min)
        if search:
            search_term = f"%{search}%"
            conditions.append(
                or_(
                    DimPatient.first_name.ilike(search_term),
                    DimPatient.last_name.ilike(search_term),
                    DimPatient.mrn.ilike(search_term),
                    FactClaim.claim_number.ilike(search_term),
                    FactDenial.carc_code.ilike(search_term)
                )
            )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply sorting
        sort_column = getattr(FactDenial, sort_by, FactDenial.priority_score)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Add columns for joined data
        query = query.add_columns(
            FactClaim.claim_number,
            FactClaim.billed_amount,
            DimPatient.patient_id,
            DimPatient.first_name,
            DimPatient.last_name,
            DimPatient.mrn,
            DimPayer.payer_name,
            DimProcedure.cpt_hcpcs_code,
            DimProcedure.description.label("procedure_description"),
            DimDenialReason.carc_description,
            DimDenialReason.denial_category,
            DimPhysician.first_name.label("physician_first_name"),
            DimPhysician.last_name.label("physician_last_name")
        )
        
        result = await self.session.execute(query)
        rows = result.all()
        
        denials = []
        for row in rows:
            denial = row[0]
            denial_dict = {
                "denial_id": denial.denial_id,
                "claim_id": denial.claim_id,
                "denial_reason_id": denial.denial_reason_id,
                "carc_code": denial.carc_code,
                "rarc_code": denial.rarc_code,
                "group_code": denial.group_code,
                "adjustment_amount": denial.adjustment_amount,
                "denial_date": denial.denial_date,
                "appeal_deadline": denial.appeal_deadline,
                "denial_status": denial.denial_status,
                "patient_sdoh_score": denial.patient_sdoh_score,
                "patient_vulnerability_flag": denial.patient_vulnerability_flag,
                "care_gap_identified": denial.care_gap_identified,
                "care_gap_description": denial.care_gap_description,
                "clinical_urgency_score": denial.clinical_urgency_score,
                "medical_necessity_flag": denial.medical_necessity_flag,
                "expected_recovery_amount": denial.expected_recovery_amount,
                "financial_priority_score": denial.financial_priority_score,
                "appeal_success_probability": denial.appeal_success_probability,
                "recommended_action": denial.recommended_action,
                "p2p_recommended": denial.p2p_recommended,
                "root_cause_category": denial.root_cause_category,
                "prevention_recommendation": denial.prevention_recommendation,
                "priority_score": denial.priority_score,
                "claim_number": row.claim_number,
                "billed_amount": row.billed_amount,
                "patient_id": row.patient_id,
                "patient_name": f"{row.first_name} {row.last_name}",
                "patient_mrn": row.mrn,
                "payer_name": row.payer_name,
                "procedure_code": row.cpt_hcpcs_code,
                "procedure_description": row.procedure_description,
                "denial_reason_description": row.carc_description,
                "denial_category": row.denial_category,
                "recommended_physician_name": f"{row.physician_first_name} {row.physician_last_name}" if row.physician_first_name else None,
                # Queue wait time calculation (use created_at if available, otherwise fall back to denial_date)
                "queue_wait_time_seconds": self._calc_queue_wait_seconds(denial.created_at, denial.denial_date),
                "queue_wait_time_display": format_queue_wait_time(self._calc_queue_wait_seconds(denial.created_at, denial.denial_date)) if self._calc_queue_wait_seconds(denial.created_at, denial.denial_date) else None
            }
            denials.append(DenialResponse(**denial_dict))
        
        return denials, total
    
    async def get_denial_by_id(self, denial_id: int) -> Optional[DenialResponse]:
        query = (
            select(FactDenial)
            .join(FactClaim, FactDenial.claim_id == FactClaim.claim_id)
            .join(DimPatient, FactClaim.patient_id == DimPatient.patient_id)
            .join(DimPayer, FactClaim.payer_id == DimPayer.payer_id)
            .outerjoin(DimProcedure, FactClaim.procedure_id == DimProcedure.procedure_id)
            .outerjoin(DimDenialReason, FactDenial.denial_reason_id == DimDenialReason.denial_reason_id)
            .outerjoin(DimPhysician, FactDenial.recommended_physician_id == DimPhysician.physician_id)
            .where(FactDenial.denial_id == denial_id)
            .add_columns(
                FactClaim.claim_number,
                FactClaim.billed_amount,
                DimPatient.patient_id,
                DimPatient.first_name,
                DimPatient.last_name,
                DimPatient.mrn,
                DimPayer.payer_name,
                DimProcedure.cpt_hcpcs_code,
                DimProcedure.description.label("procedure_description"),
                DimDenialReason.carc_description,
                DimDenialReason.denial_category,
                DimPhysician.first_name.label("physician_first_name"),
                DimPhysician.last_name.label("physician_last_name")
            )
        )
        
        result = await self.session.execute(query)
        row = result.first()
        
        if not row:
            return None
        
        denial = row[0]
        return DenialResponse(
            denial_id=denial.denial_id,
            claim_id=denial.claim_id,
            denial_reason_id=denial.denial_reason_id,
            carc_code=denial.carc_code,
            rarc_code=denial.rarc_code,
            group_code=denial.group_code,
            adjustment_amount=denial.adjustment_amount,
            denial_date=denial.denial_date,
            appeal_deadline=denial.appeal_deadline,
            denial_status=denial.denial_status,
            patient_sdoh_score=denial.patient_sdoh_score,
            patient_vulnerability_flag=denial.patient_vulnerability_flag,
            care_gap_identified=denial.care_gap_identified,
            care_gap_description=denial.care_gap_description,
            clinical_urgency_score=denial.clinical_urgency_score,
            medical_necessity_flag=denial.medical_necessity_flag,
            expected_recovery_amount=denial.expected_recovery_amount,
            financial_priority_score=denial.financial_priority_score,
            appeal_success_probability=denial.appeal_success_probability,
            recommended_action=denial.recommended_action,
            p2p_recommended=denial.p2p_recommended,
            root_cause_category=denial.root_cause_category,
            prevention_recommendation=denial.prevention_recommendation,
            priority_score=denial.priority_score,
            claim_number=row.claim_number,
            billed_amount=row.billed_amount,
            patient_id=row.patient_id,
            patient_name=f"{row.first_name} {row.last_name}",
            patient_mrn=row.mrn,
            payer_name=row.payer_name,
            procedure_code=row.cpt_hcpcs_code,
            procedure_description=row.procedure_description,
            denial_reason_description=row.carc_description,
            denial_category=row.denial_category,
            recommended_physician_name=f"{row.physician_first_name} {row.physician_last_name}" if row.physician_first_name else None
        )
    
    async def get_prior_auth_by_id(self, pa_id: int) -> Optional[PriorAuthResponse]:
        query = (
            select(FactPriorAuth)
            .join(DimPatient, FactPriorAuth.patient_id == DimPatient.patient_id)
            .join(DimPayer, FactPriorAuth.payer_id == DimPayer.payer_id)
            .outerjoin(DimProcedure, FactPriorAuth.procedure_id == DimProcedure.procedure_id)
            .outerjoin(DimPhysician, FactPriorAuth.physician_id == DimPhysician.physician_id)
            .where(FactPriorAuth.prior_auth_id == pa_id)
            .add_columns(
                DimPatient.first_name,
                DimPatient.last_name,
                DimPatient.mrn,
                DimPayer.payer_name,
                DimProcedure.cpt_hcpcs_code,
                DimProcedure.description.label("procedure_description"),
                DimPhysician.first_name.label("physician_first_name"),
                DimPhysician.last_name.label("physician_last_name")
            )
        )
        
        result = await self.session.execute(query)
        row = result.first()
        
        if not row:
            return None
        
        pa = row[0]
        return PriorAuthResponse(
            prior_auth_id=pa.prior_auth_id,
            patient_id=pa.patient_id,
            payer_id=pa.payer_id,
            procedure_id=pa.procedure_id,
            physician_id=pa.physician_id,
            auth_number=pa.auth_number,
            auth_status=pa.auth_status,
            request_date=pa.request_date,
            decision_date=pa.decision_date,
            effective_start_date=getattr(pa, 'effective_start_date', None),
            effective_end_date=getattr(pa, 'effective_end_date', None),
            denial_probability=pa.denial_probability,
            documentation_score=pa.documentation_score,
            patient_name=f"{row.first_name} {row.last_name}",
            payer_name=row.payer_name,
            procedure_code=row.cpt_hcpcs_code,
            procedure_description=row.procedure_description
        )
    
    async def get_prior_auths(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        payer_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        search: Optional[str] = None
    ) -> tuple[List[PriorAuthResponse], int]:
        
        query = (
            select(FactPriorAuth)
            .join(DimPatient, FactPriorAuth.patient_id == DimPatient.patient_id)
            .join(DimPayer, FactPriorAuth.payer_id == DimPayer.payer_id)
            .outerjoin(DimProcedure, FactPriorAuth.procedure_id == DimProcedure.procedure_id)
            .outerjoin(DimPhysician, FactPriorAuth.physician_id == DimPhysician.physician_id)
        )
        
        conditions = []
        if status:
            conditions.append(FactPriorAuth.auth_status == status)
        if payer_id:
            conditions.append(FactPriorAuth.payer_id == payer_id)
        if date_from:
            conditions.append(FactPriorAuth.request_date >= date_from)
        if date_to:
            conditions.append(FactPriorAuth.request_date <= date_to)
        if search:
            search_term = f"%{search}%"
            conditions.append(
                or_(
                    DimPatient.first_name.ilike(search_term),
                    DimPatient.last_name.ilike(search_term),
                    FactPriorAuth.auth_number.ilike(search_term),
                    DimProcedure.cpt_hcpcs_code.ilike(search_term),
                    DimProcedure.description.ilike(search_term)
                )
            )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply sorting and pagination
        query = query.order_by(desc(FactPriorAuth.request_date))
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        query = query.add_columns(
            DimPatient.first_name,
            DimPatient.last_name,
            DimPayer.payer_name,
            DimProcedure.cpt_hcpcs_code,
            DimProcedure.description.label("procedure_description"),
            DimPhysician.first_name.label("physician_first_name"),
            DimPhysician.last_name.label("physician_last_name")
        )
        
        result = await self.session.execute(query)
        rows = result.all()
        
        prior_auths = []
        for row in rows:
            pa = row[0]
            prior_auths.append(PriorAuthResponse(
                prior_auth_id=pa.prior_auth_id,
                auth_number=pa.auth_number,
                patient_id=pa.patient_id,
                payer_id=pa.payer_id,
                procedure_id=pa.procedure_id,
                physician_id=pa.physician_id,
                request_date=pa.request_date,
                decision_date=pa.decision_date,
                effective_start_date=pa.effective_start_date,
                effective_end_date=pa.effective_end_date,
                primary_diagnosis=pa.primary_diagnosis,
                auth_status=pa.auth_status,
                decision_reason=pa.decision_reason,
                denial_probability=pa.denial_probability,
                documentation_score=pa.documentation_score,
                policy_match_score=pa.policy_match_score,
                estimated_decision_days=pa.estimated_decision_days,
                missing_documents=pa.missing_documents,
                risk_factors=pa.risk_factors,
                patient_name=f"{row.first_name} {row.last_name}",
                payer_name=row.payer_name,
                procedure_code=row.cpt_hcpcs_code,
                procedure_description=row.procedure_description,
                physician_name=f"{row.physician_first_name} {row.physician_last_name}" if row.physician_first_name else None
            ))
        
        return prior_auths, total
    
    async def get_patient(self, patient_id: int) -> Optional[PatientResponse]:
        query = (
            select(DimPatient)
            .outerjoin(DimPayer, DimPatient.primary_payer_id == DimPayer.payer_id)
            .where(DimPatient.patient_id == patient_id)
            .add_columns(DimPayer.payer_name)
        )
        
        result = await self.session.execute(query)
        row = result.first()
        
        if not row:
            return None
        
        patient = row[0]
        return PatientResponse(
            patient_id=patient.patient_id,
            mrn=patient.mrn,
            first_name=patient.first_name,
            last_name=patient.last_name,
            date_of_birth=patient.date_of_birth,
            gender=patient.gender,
            city=patient.city,
            state=patient.state,
            zip_code=patient.zip_code,
            adi_national_rank=patient.adi_national_rank,
            sdoh_composite_score=patient.sdoh_composite_score,
            sdoh_food_insecurity_risk=patient.sdoh_food_insecurity_risk,
            sdoh_housing_instability_risk=patient.sdoh_housing_instability_risk,
            sdoh_transportation_risk=patient.sdoh_transportation_risk,
            sdoh_social_isolation_risk=patient.sdoh_social_isolation_risk,
            primary_payer_id=patient.primary_payer_id,
            member_id=patient.member_id,
            payer_name=row.payer_name
        )
    
    async def get_dashboard_metrics(self) -> DashboardMetrics:
        # Total claims
        claims_result = await self.session.execute(select(func.count(FactClaim.claim_id)))
        total_claims = claims_result.scalar() or 0
        
        # Total denials and amounts
        denials_query = select(
            func.count(FactDenial.denial_id),
            func.sum(FactDenial.adjustment_amount)
        )
        denials_result = await self.session.execute(denials_query)
        denials_row = denials_result.first()
        total_denials = denials_row[0] or 0
        total_denied_amount = denials_row[1] or 0
        
        # Denial rate
        denial_rate = (total_denials / total_claims * 100) if total_claims > 0 else 0
        
        # Recovery from appeals
        recovery_query = select(func.sum(FactAppeal.outcome_amount)).where(
            FactAppeal.appeal_status == "Won"
        )
        recovery_result = await self.session.execute(recovery_query)
        total_recovered = recovery_result.scalar() or 0
        
        recovery_rate = (total_recovered / total_denied_amount * 100) if total_denied_amount > 0 else 0
        
        # Pending appeals
        pending_appeals_result = await self.session.execute(
            select(func.count(FactAppeal.appeal_id)).where(FactAppeal.appeal_status == "Pending")
        )
        pending_appeals = pending_appeals_result.scalar() or 0
        
        # Appeal success rate
        appeals_query = select(
            func.count(FactAppeal.appeal_id).filter(FactAppeal.appeal_status == "Won"),
            func.count(FactAppeal.appeal_id).filter(FactAppeal.appeal_status.in_(["Won", "Lost"]))
        )
        appeals_result = await self.session.execute(appeals_query)
        appeals_row = appeals_result.first()
        won_appeals = appeals_row[0] or 0
        decided_appeals = appeals_row[1] or 0
        avg_appeal_success = (won_appeals / decided_appeals * 100) if decided_appeals > 0 else 0
        
        # High priority denials (priority_score > 0.7)
        high_priority_result = await self.session.execute(
            select(func.count(FactDenial.denial_id)).where(
                and_(
                    FactDenial.priority_score >= 0.7,
                    FactDenial.denial_status.in_(["New", "In Review"])
                )
            )
        )
        high_priority_denials = high_priority_result.scalar() or 0
        
        # PA metrics
        pa_pending_result = await self.session.execute(
            select(func.count(FactPriorAuth.prior_auth_id)).where(
                FactPriorAuth.auth_status == "Pending"
            )
        )
        pa_pending = pa_pending_result.scalar() or 0
        
        pa_approval_query = select(
            func.count(FactPriorAuth.prior_auth_id).filter(FactPriorAuth.auth_status == "Approved"),
            func.count(FactPriorAuth.prior_auth_id).filter(FactPriorAuth.auth_status.in_(["Approved", "Denied"]))
        )
        pa_result = await self.session.execute(pa_approval_query)
        pa_row = pa_result.first()
        approved_pa = pa_row[0] or 0
        decided_pa = pa_row[1] or 0
        pa_approval_rate = (approved_pa / decided_pa * 100) if decided_pa > 0 else 0
        
        # Average queue wait time for pending denials (use created_at if available, otherwise fall back to denial_date)
        pending_denials_query = select(FactDenial.created_at, FactDenial.denial_date).where(
            FactDenial.denial_status.in_(["New", "In Review", "Pending"])
        )
        pending_result = await self.session.execute(pending_denials_query)
        pending_rows = pending_result.all()
        
        avg_queue_wait_seconds = None
        avg_queue_wait_display = None
        if pending_rows:
            now = datetime.utcnow()
            wait_times = []
            for created_at, denial_date in pending_rows:
                base_time = created_at or denial_date
                if base_time:
                    if isinstance(base_time, date) and not isinstance(base_time, datetime):
                        base_time = datetime.combine(base_time, datetime.min.time())
                    wait_times.append((now - base_time).total_seconds())
            if wait_times:
                avg_queue_wait_seconds = int(sum(wait_times) / len(wait_times))
                avg_queue_wait_display = format_queue_wait_time(avg_queue_wait_seconds)
        
        return DashboardMetrics(
            total_claims=total_claims,
            total_denials=total_denials,
            denial_rate=round(denial_rate, 1),
            total_denied_amount=round(total_denied_amount, 2),
            total_recovered_amount=round(total_recovered, 2),
            recovery_rate=round(recovery_rate, 1),
            pending_appeals=pending_appeals,
            avg_appeal_success_rate=round(avg_appeal_success, 1),
            high_priority_denials=high_priority_denials,
            pa_pending=pa_pending,
            pa_approval_rate=round(pa_approval_rate, 1),
            avg_queue_wait_time_seconds=avg_queue_wait_seconds,
            avg_queue_wait_time_display=avg_queue_wait_display
        )
    
    async def get_denials_by_category(self) -> List[DenialByCategory]:
        query = (
            select(
                FactDenial.root_cause_category,
                func.count(FactDenial.denial_id),
                func.sum(FactDenial.adjustment_amount)
            )
            .group_by(FactDenial.root_cause_category)
            .order_by(desc(func.count(FactDenial.denial_id)))
        )
        
        result = await self.session.execute(query)
        rows = result.all()
        
        total_denials = sum(row[1] for row in rows)
        
        categories = []
        for row in rows:
            if row[0]:
                categories.append(DenialByCategory(
                    category=row[0],
                    count=row[1],
                    amount=round(row[2] or 0, 2),
                    percentage=round((row[1] / total_denials * 100) if total_denials > 0 else 0, 1)
                ))
        
        return categories
    
    async def get_denials_by_payer(self) -> List[DenialByPayer]:
        query = (
            select(
                DimPayer.payer_id,
                DimPayer.payer_name,
                func.count(FactDenial.denial_id),
                func.sum(FactDenial.adjustment_amount)
            )
            .join(FactClaim, FactDenial.claim_id == FactClaim.claim_id)
            .join(DimPayer, FactClaim.payer_id == DimPayer.payer_id)
            .group_by(DimPayer.payer_id, DimPayer.payer_name)
            .order_by(desc(func.count(FactDenial.denial_id)))
        )
        
        result = await self.session.execute(query)
        rows = result.all()
        
        # Get total claims per payer for denial rate
        claims_query = (
            select(
                DimPayer.payer_id,
                func.count(FactClaim.claim_id)
            )
            .join(DimPayer, FactClaim.payer_id == DimPayer.payer_id)
            .group_by(DimPayer.payer_id)
        )
        claims_result = await self.session.execute(claims_query)
        claims_by_payer = {row[0]: row[1] for row in claims_result.all()}
        
        payers = []
        for row in rows:
            payer_id = row[0]
            total_claims = claims_by_payer.get(payer_id, 0)
            denial_count = row[2]
            
            payers.append(DenialByPayer(
                payer_id=payer_id,
                payer_name=row[1],
                denial_count=denial_count,
                denial_amount=round(row[3] or 0, 2),
                denial_rate=round((denial_count / total_claims * 100) if total_claims > 0 else 0, 1),
                appeal_success_rate=0  # Would need to calculate from appeals
            ))
        
        return payers
    
    async def get_payers(self) -> List[PayerResponse]:
        query = select(DimPayer).order_by(DimPayer.payer_name)
        result = await self.session.execute(query)
        payers = result.scalars().all()
        
        return [PayerResponse(
            payer_id=p.payer_id,
            payer_name=p.payer_name,
            payer_type=p.payer_type,
            avg_denial_rate=p.avg_denial_rate,
            avg_appeal_success_rate=p.avg_appeal_success_rate,
            avg_days_to_decision=p.avg_days_to_decision,
            top_denial_reason_1=p.top_denial_reason_1,
            top_denial_reason_2=p.top_denial_reason_2,
            top_denial_reason_3=p.top_denial_reason_3
        ) for p in payers]
    
    async def get_rl_traces(
        self,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[RLTraceResponse], int]:
        query = select(FactRLTrace).order_by(desc(FactRLTrace.action_timestamp))
        
        count_query = select(func.count(FactRLTrace.trace_id))
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        result = await self.session.execute(query)
        traces = result.scalars().all()
        
        return [RLTraceResponse(
            trace_id=t.trace_id,
            denial_id=t.denial_id,
            prior_auth_id=t.prior_auth_id,
            staff_id=t.staff_id,
            action_type=t.action_type,
            action_timestamp=t.action_timestamp,
            ai_recommendation=t.ai_recommendation,
            ai_confidence=t.ai_confidence,
            staff_followed_ai=t.staff_followed_ai,
            outcome=t.outcome,
            outcome_amount=t.outcome_amount,
            reward_score=t.reward_score,
            feedback_rating=t.feedback_rating
        ) for t in traces], total
    
    async def get_learning_metrics(self) -> dict:
        # Total actions
        total_result = await self.session.execute(select(func.count(FactRLTrace.trace_id)))
        total_actions = total_result.scalar() or 0
        
        # AI followed rate
        followed_result = await self.session.execute(
            select(func.count(FactRLTrace.trace_id)).where(FactRLTrace.staff_followed_ai == True)
        )
        followed_count = followed_result.scalar() or 0
        ai_followed_rate = (followed_count / total_actions * 100) if total_actions > 0 else 0
        
        # Average reward score
        reward_result = await self.session.execute(
            select(func.avg(FactRLTrace.reward_score))
        )
        avg_reward = reward_result.scalar() or 0
        
        # Successful outcomes
        success_result = await self.session.execute(
            select(func.count(FactRLTrace.trace_id)).where(FactRLTrace.outcome == "Success")
        )
        successful = success_result.scalar() or 0
        
        # Action distribution
        action_query = (
            select(FactRLTrace.action_type, func.count(FactRLTrace.trace_id))
            .group_by(FactRLTrace.action_type)
        )
        action_result = await self.session.execute(action_query)
        action_distribution = {row[0]: row[1] for row in action_result.all()}
        
        return {
            "total_actions": total_actions,
            "ai_followed_rate": round(ai_followed_rate, 1),
            "avg_reward_score": round(avg_reward, 3),
            "successful_outcomes": successful,
            "action_distribution": action_distribution
        }
    
    async def record_action(self, action: StaffActionCreate) -> int:
        import json
        from datetime import datetime
        
        trace = FactRLTrace(
            denial_id=action.denial_id,
            prior_auth_id=action.prior_auth_id,
            staff_id=action.staff_id,
            action_type=action.action_type,
            action_timestamp=datetime.utcnow(),
            ai_recommendation=action.ai_recommendation,
            ai_confidence=action.ai_confidence,
            staff_followed_ai=action.staff_followed_ai,
            staff_feedback=action.staff_feedback,
            feedback_rating=action.feedback_rating
        )
        
        self.session.add(trace)
        await self.session.commit()
        await self.session.refresh(trace)
        
        return trace.trace_id


# Factory function for creating data service
def create_data_service(session: AsyncSession, data_source: str = "sqlite") -> DataService:
    """
    Factory function to create the appropriate data service.
    
    Args:
        session: Database session
        data_source: "sqlite" for synthetic data, "fabric" for Fabric HDS
    
    Returns:
        DataService implementation
    """
    if data_source == "sqlite":
        return SQLiteDataService(session)
    elif data_source == "fabric":
        # Future: return FabricDataService(fabric_endpoint)
        raise NotImplementedError("Fabric HDS integration not yet implemented")
    else:
        raise ValueError(f"Unknown data source: {data_source}")
