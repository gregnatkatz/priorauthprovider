"""
LangGraph Agent Workflows - Graph-based orchestration for 40 AI agents
Provides intelligent routing, parallel execution, and conditional branching
"""
import json
import asyncio
from typing import TypedDict, Annotated, Sequence, Literal, Optional, Any
from datetime import datetime
from operator import add

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from .ai_agents import (
    AGENT_MODEL_MAP,
    AGENT_REGISTRY,
    get_model_for_agent,
    record_agent_call,
    SDOHScorerAgent,
    CareGapDetectorAgent,
    ClinicalUrgencyAgent,
    FinancialValueAgent,
    RecoveryPredictorAgent,
    P2POptimizerAgent,
    QueueWaitTimeAgent,
    PARiskPredictorAgent,
    DocCompletenessAgent,
    PolicyMonitorAgent,
    RootCauseAnalyzerAgent,
    StaffFeedbackProcessorAgent,
    SafetyValidatorAgent,
    ConsensusCheckerAgent,
    PolicyMatchGraderAgent,
    ViabilityScorerAgent,
    EligibilityVerifierAgent,
    FollowupSchedulerAgent,
    FrontEndRejectionAnalyzerAgent,
    AppealDeadlineRiskAssessorAgent,
    PendingClaimRiskScorerAgent,
    AgingTrendForecasterAgent,
    PayerSLAMonitorAgent,
    COBCoordinationAnalyzerAgent,
    StatusPatternDetectorAgent,
    StatusIntelligenceSummarizerAgent,
    AuditAgent,
    HealthCheckAgent,
)


class DenialAnalysisState(TypedDict):
    """State for denial analysis workflow."""
    claim_id: str
    denial_data: dict
    patient_context: dict
    payer_context: dict
    agent_results: Annotated[dict, add]
    validation_results: dict
    final_recommendation: dict
    workflow_stage: str
    errors: list
    metadata: dict


class StatusIntelligenceState(TypedDict):
    """State for 277/277CA status intelligence workflow."""
    transaction_id: str
    status_data: dict
    historical_context: dict
    agent_results: Annotated[dict, add]
    alerts: list
    summary: dict
    workflow_stage: str


class AuditState(TypedDict):
    """State for audit workflow."""
    claim_id: str
    all_outputs: dict
    audit_result: dict
    discrepancies: list
    confidence_score: float


def create_denial_analysis_workflow() -> StateGraph:
    """
    Create LangGraph workflow for comprehensive denial analysis.
    
    Flow:
    1. Patient Context Analysis (parallel: SDOH, Care Gap, Clinical Urgency)
    2. Financial Analysis (parallel: Financial Value, Recovery Predictor)
    3. Documentation Review (parallel: Doc Completeness, PA Risk)
    4. Validation Layer (parallel: Safety, Consensus, Policy Match)
    5. Synthesis & Recommendation
    """
    
    workflow = StateGraph(DenialAnalysisState)
    
    async def analyze_patient_context(state: DenialAnalysisState) -> dict:
        """Run patient-centric agents in parallel."""
        denial_data = state["denial_data"]
        patient_context = state.get("patient_context", {})
        
        sdoh_agent = SDOHScorerAgent()
        care_gap_agent = CareGapDetectorAgent()
        clinical_agent = ClinicalUrgencyAgent()
        
        results = await asyncio.gather(
            sdoh_agent.analyze(denial_data),
            care_gap_agent.analyze(denial_data),
            clinical_agent.analyze(denial_data),
            return_exceptions=True
        )
        
        return {
            "agent_results": {
                "sdoh_score": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
                "care_gaps": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
                "clinical_urgency": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
            },
            "workflow_stage": "patient_context_complete"
        }
    
    async def analyze_financial(state: DenialAnalysisState) -> dict:
        """Run financial analysis agents in parallel."""
        denial_data = state["denial_data"]
        
        financial_agent = FinancialValueAgent()
        recovery_agent = RecoveryPredictorAgent()
        
        results = await asyncio.gather(
            financial_agent.analyze(denial_data),
            recovery_agent.analyze(denial_data),
            return_exceptions=True
        )
        
        return {
            "agent_results": {
                "financial_value": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
                "recovery_prediction": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
            },
            "workflow_stage": "financial_complete"
        }
    
    async def analyze_documentation(state: DenialAnalysisState) -> dict:
        """Run documentation review agents in parallel."""
        denial_data = state["denial_data"]
        
        doc_agent = DocCompletenessAgent()
        pa_agent = PARiskPredictorAgent()
        
        results = await asyncio.gather(
            doc_agent.analyze(denial_data),
            pa_agent.analyze(denial_data),
            return_exceptions=True
        )
        
        return {
            "agent_results": {
                "doc_completeness": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
                "pa_risk": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
            },
            "workflow_stage": "documentation_complete"
        }
    
    async def run_validation_layer(state: DenialAnalysisState) -> dict:
        """Run multi-model validation for life-critical decisions."""
        agent_results = state["agent_results"]
        denial_data = state["denial_data"]
        
        validation_input = {
            "denial_data": denial_data,
            "agent_outputs": agent_results
        }
        
        safety_agent = SafetyValidatorAgent()
        consensus_agent = ConsensusCheckerAgent()
        policy_agent = PolicyMatchGraderAgent()
        
        results = await asyncio.gather(
            safety_agent.analyze(validation_input),
            consensus_agent.analyze(validation_input),
            policy_agent.analyze(validation_input),
            return_exceptions=True
        )
        
        return {
            "validation_results": {
                "safety_check": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
                "consensus_check": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
                "policy_match": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
            },
            "workflow_stage": "validation_complete"
        }
    
    async def synthesize_recommendation(state: DenialAnalysisState) -> dict:
        """Synthesize all agent outputs into final recommendation."""
        agent_results = state["agent_results"]
        validation_results = state["validation_results"]
        
        sdoh = agent_results.get("sdoh_score", {})
        clinical = agent_results.get("clinical_urgency", {})
        financial = agent_results.get("financial_value", {})
        recovery = agent_results.get("recovery_prediction", {})
        
        priority_score = (
            sdoh.get("vulnerability_score", 50) * 0.2 +
            clinical.get("urgency_score", 50) * 0.3 +
            financial.get("value_score", 50) * 0.25 +
            recovery.get("recovery_probability", 0.5) * 100 * 0.25
        )
        
        safety_passed = validation_results.get("safety_check", {}).get("safe", True)
        consensus_reached = validation_results.get("consensus_check", {}).get("consensus", True)
        
        recommendation = {
            "claim_id": state["claim_id"],
            "priority_score": round(priority_score, 2),
            "recommended_action": "appeal" if recovery.get("recovery_probability", 0) > 0.5 else "write_off",
            "confidence": recovery.get("confidence", 0.7),
            "validation_passed": safety_passed and consensus_reached,
            "key_factors": [
                f"SDOH vulnerability: {sdoh.get('vulnerability_score', 'N/A')}",
                f"Clinical urgency: {clinical.get('urgency_level', 'N/A')}",
                f"Recovery probability: {recovery.get('recovery_probability', 'N/A')}",
            ],
            "next_steps": recovery.get("recommended_actions", []),
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return {
            "final_recommendation": recommendation,
            "workflow_stage": "complete"
        }
    
    def should_validate(state: DenialAnalysisState) -> Literal["validate", "synthesize"]:
        """Determine if validation is needed based on financial value."""
        financial = state["agent_results"].get("financial_value", {})
        amount = financial.get("claim_amount", 0)
        if amount > 5000:
            return "validate"
        return "synthesize"
    
    workflow.add_node("patient_context", analyze_patient_context)
    workflow.add_node("financial", analyze_financial)
    workflow.add_node("documentation", analyze_documentation)
    workflow.add_node("validation", run_validation_layer)
    workflow.add_node("synthesize", synthesize_recommendation)
    
    workflow.set_entry_point("patient_context")
    workflow.add_edge("patient_context", "financial")
    workflow.add_edge("financial", "documentation")
    workflow.add_conditional_edges(
        "documentation",
        should_validate,
        {
            "validate": "validation",
            "synthesize": "synthesize"
        }
    )
    workflow.add_edge("validation", "synthesize")
    workflow.add_edge("synthesize", END)
    
    return workflow


def create_status_intelligence_workflow() -> StateGraph:
    """
    Create LangGraph workflow for 277/277CA status intelligence.
    
    Flow:
    1. Front-End Analysis (277CA rejections)
    2. Status Pattern Detection
    3. Risk Assessment (parallel: Pending Risk, Aging, SLA)
    4. Summary Generation
    """
    
    workflow = StateGraph(StatusIntelligenceState)
    
    async def analyze_frontend_rejections(state: StatusIntelligenceState) -> dict:
        """Analyze 277CA front-end rejections."""
        status_data = state["status_data"]
        
        if status_data.get("transaction_type") == "277CA":
            agent = FrontEndRejectionAnalyzerAgent()
            result = await agent.analyze(status_data)
            return {
                "agent_results": {"frontend_analysis": result},
                "workflow_stage": "frontend_complete"
            }
        
        return {
            "agent_results": {"frontend_analysis": {"skipped": True, "reason": "Not 277CA"}},
            "workflow_stage": "frontend_complete"
        }
    
    async def detect_status_patterns(state: StatusIntelligenceState) -> dict:
        """Detect anomalies in status flows."""
        status_data = state["status_data"]
        historical = state.get("historical_context", {})
        
        agent = StatusPatternDetectorAgent()
        result = await agent.analyze({
            "status_flow_data": status_data.get("status_history", []),
            "baseline_days": historical.get("avg_adjudication_days", 14),
            "baseline_stuck_rate": historical.get("stuck_rate", 5),
            "baseline_regression_rate": historical.get("regression_rate", 2)
        })
        
        return {
            "agent_results": {"pattern_detection": result},
            "workflow_stage": "patterns_complete"
        }
    
    async def assess_risks(state: StatusIntelligenceState) -> dict:
        """Run risk assessment agents in parallel."""
        status_data = state["status_data"]
        
        pending_agent = PendingClaimRiskScorerAgent()
        aging_agent = AgingTrendForecasterAgent()
        sla_agent = PayerSLAMonitorAgent()
        
        results = await asyncio.gather(
            pending_agent.analyze(status_data),
            aging_agent.analyze(status_data),
            sla_agent.analyze(status_data),
            return_exceptions=True
        )
        
        return {
            "agent_results": {
                "pending_risk": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
                "aging_forecast": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
                "sla_compliance": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
            },
            "workflow_stage": "risk_complete"
        }
    
    async def generate_summary(state: StatusIntelligenceState) -> dict:
        """Generate executive summary of status intelligence."""
        agent_results = state["agent_results"]
        
        agent = StatusIntelligenceSummarizerAgent()
        summary = await agent.analyze({"agent_outputs": agent_results})
        
        alerts = []
        if agent_results.get("pending_risk", {}).get("risk_level") == "critical":
            alerts.append({"type": "critical_risk", "message": "Critical pending claim risk detected"})
        if agent_results.get("sla_compliance", {}).get("escalation_recommended"):
            alerts.append({"type": "sla_breach", "message": "SLA breach escalation recommended"})
        
        return {
            "summary": summary,
            "alerts": alerts,
            "workflow_stage": "complete"
        }
    
    workflow.add_node("frontend", analyze_frontend_rejections)
    workflow.add_node("patterns", detect_status_patterns)
    workflow.add_node("risks", assess_risks)
    workflow.add_node("summary", generate_summary)
    
    workflow.set_entry_point("frontend")
    workflow.add_edge("frontend", "patterns")
    workflow.add_edge("patterns", "risks")
    workflow.add_edge("risks", "summary")
    workflow.add_edge("summary", END)
    
    return workflow


def create_audit_workflow() -> StateGraph:
    """
    Create LangGraph workflow for out-of-band audit validation.
    
    Flow:
    1. Collect all agent outputs
    2. Run audit agent for consistency check
    3. Generate discrepancy report
    """
    
    workflow = StateGraph(AuditState)
    
    async def run_audit(state: AuditState) -> dict:
        """Run audit agent on all outputs."""
        agent = AuditAgent()
        result = await agent.analyze({
            "claim_id": state["claim_id"],
            "all_outputs": state["all_outputs"],
            "historical_accuracy": {}
        })
        
        return {
            "audit_result": result,
            "confidence_score": result.get("overall_confidence", 0.0)
        }
    
    async def generate_discrepancy_report(state: AuditState) -> dict:
        """Generate report of any discrepancies found."""
        audit_result = state["audit_result"]
        
        discrepancies = []
        if audit_result.get("contradictions_found"):
            for contradiction in audit_result.get("contradictions", []):
                discrepancies.append({
                    "type": "contradiction",
                    "agents": contradiction.get("agents", []),
                    "description": contradiction.get("description", ""),
                    "severity": contradiction.get("severity", "medium")
                })
        
        return {"discrepancies": discrepancies}
    
    workflow.add_node("audit", run_audit)
    workflow.add_node("report", generate_discrepancy_report)
    
    workflow.set_entry_point("audit")
    workflow.add_edge("audit", "report")
    workflow.add_edge("report", END)
    
    return workflow


class LangGraphOrchestrator:
    """
    Main orchestrator using LangGraph for agent workflows.
    Provides intelligent routing, parallel execution, and state management.
    """
    
    def __init__(self):
        self.memory = MemorySaver()
        self.denial_workflow = create_denial_analysis_workflow().compile(checkpointer=self.memory)
        self.status_workflow = create_status_intelligence_workflow().compile(checkpointer=self.memory)
        self.audit_workflow = create_audit_workflow().compile(checkpointer=self.memory)
        
        self.workflow_runs = []
    
    async def analyze_denial(self, claim_id: str, denial_data: dict, 
                            patient_context: Optional[dict] = None, payer_context: Optional[dict] = None) -> dict:
        """
        Run full denial analysis workflow.
        
        Args:
            claim_id: Unique claim identifier
            denial_data: Denial details from 835
            patient_context: Optional patient demographics/history
            payer_context: Optional payer-specific context
            
        Returns:
            Complete analysis with recommendation
        """
        initial_state = DenialAnalysisState(
            claim_id=claim_id,
            denial_data=denial_data,
            patient_context=patient_context or {},
            payer_context=payer_context or {},
            agent_results={},
            validation_results={},
            final_recommendation={},
            workflow_stage="started",
            errors=[],
            metadata={"started_at": datetime.utcnow().isoformat()}
        )
        
        config = {"configurable": {"thread_id": f"denial_{claim_id}"}}
        
        try:
            result = await self.denial_workflow.ainvoke(initial_state, config)
            
            self.workflow_runs.append({
                "type": "denial_analysis",
                "claim_id": claim_id,
                "completed_at": datetime.utcnow().isoformat(),
                "success": True
            })
            
            return result
        except Exception as e:
            self.workflow_runs.append({
                "type": "denial_analysis",
                "claim_id": claim_id,
                "completed_at": datetime.utcnow().isoformat(),
                "success": False,
                "error": str(e)
            })
            raise
    
    async def analyze_status(self, transaction_id: str, status_data: dict,
                            historical_context: Optional[dict] = None) -> dict:
        """
        Run status intelligence workflow for 277/277CA.
        
        Args:
            transaction_id: EDI transaction ID
            status_data: Parsed 277/277CA data
            historical_context: Optional historical patterns
            
        Returns:
            Status intelligence summary with alerts
        """
        initial_state = StatusIntelligenceState(
            transaction_id=transaction_id,
            status_data=status_data,
            historical_context=historical_context or {},
            agent_results={},
            alerts=[],
            summary={},
            workflow_stage="started"
        )
        
        config = {"configurable": {"thread_id": f"status_{transaction_id}"}}
        
        result = await self.status_workflow.ainvoke(initial_state, config)
        
        self.workflow_runs.append({
            "type": "status_intelligence",
            "transaction_id": transaction_id,
            "completed_at": datetime.utcnow().isoformat(),
            "success": True
        })
        
        return result
    
    async def run_audit(self, claim_id: str, all_outputs: dict) -> dict:
        """
        Run audit workflow to validate agent consistency.
        
        Args:
            claim_id: Claim being audited
            all_outputs: All agent outputs to validate
            
        Returns:
            Audit result with discrepancies
        """
        initial_state = AuditState(
            claim_id=claim_id,
            all_outputs=all_outputs,
            audit_result={},
            discrepancies=[],
            confidence_score=0.0
        )
        
        config = {"configurable": {"thread_id": f"audit_{claim_id}"}}
        
        result = await self.audit_workflow.ainvoke(initial_state, config)
        
        return result
    
    def get_workflow_stats(self) -> dict:
        """Get statistics on workflow executions."""
        total = len(self.workflow_runs)
        successful = sum(1 for r in self.workflow_runs if r.get("success"))
        
        by_type = {}
        for run in self.workflow_runs:
            wf_type = run.get("type", "unknown")
            if wf_type not in by_type:
                by_type[wf_type] = {"total": 0, "successful": 0}
            by_type[wf_type]["total"] += 1
            if run.get("success"):
                by_type[wf_type]["successful"] += 1
        
        return {
            "total_runs": total,
            "successful_runs": successful,
            "success_rate": successful / total if total > 0 else 0,
            "by_workflow_type": by_type,
            "recent_runs": self.workflow_runs[-10:]
        }


langgraph_orchestrator = LangGraphOrchestrator()


async def run_denial_workflow(claim_id: str, denial_data: dict) -> dict:
    """Convenience function to run denial analysis workflow."""
    return await langgraph_orchestrator.analyze_denial(claim_id, denial_data)


async def run_status_workflow(transaction_id: str, status_data: dict) -> dict:
    """Convenience function to run status intelligence workflow."""
    return await langgraph_orchestrator.analyze_status(transaction_id, status_data)


async def run_audit_workflow(claim_id: str, all_outputs: dict) -> dict:
    """Convenience function to run audit workflow."""
    return await langgraph_orchestrator.run_audit(claim_id, all_outputs)
