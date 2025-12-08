"""
MCP Tool Definitions for all 42+ AI Agents in Denial Intelligence Platform
Each agent is exposed as an MCP tool with proper input/output schemas
"""
import json
import os
import sys
from typing import Any, Dict, List, Optional

# Add backend to path for agent imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

# Agent Registry - Maps agent IDs to their definitions
AGENT_DEFINITIONS = {
    # ==================== DENIAL AGENTS (DEN-001 to DEN-012) ====================
    "DEN-001": {
        "id": "DEN-001",
        "name": "sdoh_scorer",
        "display_name": "SDOH Scorer Agent",
        "description": "Scores social determinants of health (SDOH) impact on patient outcomes. Analyzes ADI index, housing stability, food security, and transportation access.",
        "category": "denial",
        "model": "gpt-4.1",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_name": {"type": "string", "description": "Patient name"},
                "diagnosis_code": {"type": "string", "description": "ICD-10 diagnosis code"},
                "procedure_description": {"type": "string", "description": "Description of procedure"},
                "payer_name": {"type": "string", "description": "Insurance payer name"},
                "denial_reason_description": {"type": "string", "description": "Reason for denial"}
            },
            "required": ["patient_name"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "sdoh_score": {"type": "number", "description": "SDOH vulnerability score 0-100"},
                "risk_factors": {"type": "array", "items": {"type": "string"}},
                "recommendations": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    "DEN-002": {
        "id": "DEN-002",
        "name": "care_gap_detector",
        "display_name": "Care Gap Detector Agent",
        "description": "Identifies potential gaps in patient care when services are denied. Detects treatment delays and care continuity issues.",
        "category": "denial",
        "model": "gpt-4.1",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_name": {"type": "string"},
                "diagnosis_code": {"type": "string"},
                "procedure_description": {"type": "string"},
                "denial_reason": {"type": "string"}
            },
            "required": ["diagnosis_code"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "care_gaps": {"type": "array", "items": {"type": "string"}},
                "urgency_level": {"type": "string"},
                "recommendations": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    "DEN-003": {
        "id": "DEN-003",
        "name": "clinical_urgency",
        "display_name": "Clinical Urgency Agent",
        "description": "Assesses clinical urgency of denied cases. Prioritizes cases based on patient health impact.",
        "category": "denial",
        "model": "gpt-4.1",
        "input_schema": {
            "type": "object",
            "properties": {
                "diagnosis_code": {"type": "string"},
                "procedure_code": {"type": "string"},
                "patient_age": {"type": "number"},
                "comorbidities": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["diagnosis_code"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "urgency_score": {"type": "number"},
                "urgency_level": {"type": "string"},
                "clinical_rationale": {"type": "string"}
            }
        }
    },
    "DEN-004": {
        "id": "DEN-004",
        "name": "financial_value",
        "display_name": "Financial Value Agent",
        "description": "Calculates financial value and expected recovery for denied claims.",
        "category": "denial",
        "model": "gpt-4.1-mini",
        "input_schema": {
            "type": "object",
            "properties": {
                "billed_amount": {"type": "number"},
                "payer_name": {"type": "string"},
                "procedure_code": {"type": "string"},
                "denial_reason": {"type": "string"}
            },
            "required": ["billed_amount"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "expected_recovery": {"type": "number"},
                "recovery_probability": {"type": "number"},
                "roi_score": {"type": "number"}
            }
        }
    },
    "DEN-005": {
        "id": "DEN-005",
        "name": "recovery_predictor",
        "display_name": "Recovery Predictor Agent",
        "description": "Predicts likelihood of successful appeal and recovery using advanced reasoning.",
        "category": "denial",
        "model": "o3",
        "input_schema": {
            "type": "object",
            "properties": {
                "denial_reason": {"type": "string"},
                "payer_name": {"type": "string"},
                "procedure_code": {"type": "string"},
                "historical_success_rate": {"type": "number"}
            },
            "required": ["denial_reason"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "success_probability": {"type": "number"},
                "confidence": {"type": "number"},
                "key_factors": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    "DEN-006": {
        "id": "DEN-006",
        "name": "p2p_optimizer",
        "display_name": "P2P Optimizer Agent",
        "description": "Optimizes peer-to-peer review scheduling and preparation using DeepSeek reasoning.",
        "category": "denial",
        "model": "deepseek",
        "input_schema": {
            "type": "object",
            "properties": {
                "denial_reason": {"type": "string"},
                "clinical_notes": {"type": "string"},
                "payer_name": {"type": "string"},
                "physician_specialty": {"type": "string"}
            },
            "required": ["denial_reason"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "recommended": {"type": "boolean"},
                "physician": {"type": "string"},
                "talking_points": {"type": "array", "items": {"type": "string"}},
                "optimal_timing": {"type": "string"}
            }
        }
    },
    "DEN-007": {
        "id": "DEN-007",
        "name": "queue_wait_time",
        "display_name": "Queue Wait Time Agent",
        "description": "Estimates queue wait times and optimizes workflow prioritization.",
        "category": "denial",
        "model": "gpt-4.1-nano",
        "input_schema": {
            "type": "object",
            "properties": {
                "queue_size": {"type": "number"},
                "staff_available": {"type": "number"},
                "priority_level": {"type": "string"}
            },
            "required": []
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "estimated_wait_minutes": {"type": "number"},
                "queue_position": {"type": "number"},
                "optimization_suggestions": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    "DEN-008": {
        "id": "DEN-008",
        "name": "pa_risk_predictor",
        "display_name": "PA Risk Predictor Agent",
        "description": "Predicts prior authorization denial risk before submission.",
        "category": "denial",
        "model": "gpt-4.1-mini",
        "input_schema": {
            "type": "object",
            "properties": {
                "procedure_code": {"type": "string"},
                "diagnosis_code": {"type": "string"},
                "payer_name": {"type": "string"},
                "patient_history": {"type": "string"}
            },
            "required": ["procedure_code", "payer_name"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "denial_risk": {"type": "number"},
                "risk_factors": {"type": "array", "items": {"type": "string"}},
                "mitigation_steps": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    "DEN-009": {
        "id": "DEN-009",
        "name": "doc_completeness",
        "display_name": "Documentation Completeness Agent",
        "description": "Checks documentation completeness and identifies missing required documents.",
        "category": "denial",
        "model": "gpt-4.1-mini",
        "input_schema": {
            "type": "object",
            "properties": {
                "procedure_code": {"type": "string"},
                "payer_name": {"type": "string"},
                "submitted_documents": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["procedure_code"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "completeness_score": {"type": "number"},
                "missing_docs": {"type": "array", "items": {"type": "string"}},
                "recommendations": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    "DEN-010": {
        "id": "DEN-010",
        "name": "policy_monitor",
        "display_name": "Policy Monitor Agent",
        "description": "Monitors payer policy changes and alerts on relevant updates.",
        "category": "denial",
        "model": "gpt-4.1-nano",
        "input_schema": {
            "type": "object",
            "properties": {
                "payer_name": {"type": "string"},
                "procedure_codes": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["payer_name"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "policy_changes": {"type": "array", "items": {"type": "object"}},
                "impact_assessment": {"type": "string"},
                "action_required": {"type": "boolean"}
            }
        }
    },
    "DEN-011": {
        "id": "DEN-011",
        "name": "root_cause_analyzer",
        "display_name": "Root Cause Analyzer Agent",
        "description": "Analyzes root causes of denials using advanced reasoning patterns.",
        "category": "denial",
        "model": "o3",
        "input_schema": {
            "type": "object",
            "properties": {
                "denial_reason": {"type": "string"},
                "denial_code": {"type": "string"},
                "historical_denials": {"type": "array", "items": {"type": "object"}}
            },
            "required": ["denial_reason"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "root_causes": {"type": "array", "items": {"type": "string"}},
                "systemic_issues": {"type": "array", "items": {"type": "string"}},
                "prevention_recommendations": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    "DEN-012": {
        "id": "DEN-012",
        "name": "staff_feedback_processor",
        "display_name": "Staff Feedback Processor Agent",
        "description": "Processes staff feedback for reinforcement learning model improvement.",
        "category": "denial",
        "model": "deepseek",
        "input_schema": {
            "type": "object",
            "properties": {
                "feedback_text": {"type": "string"},
                "agent_recommendation": {"type": "string"},
                "actual_outcome": {"type": "string"},
                "staff_rating": {"type": "number"}
            },
            "required": ["feedback_text"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "processed_feedback": {"type": "object"},
                "model_adjustment": {"type": "string"},
                "confidence_delta": {"type": "number"}
            }
        }
    },
    
    # ==================== VALIDATION AGENTS (VAL-001 to VAL-006) ====================
    "VAL-001": {
        "id": "VAL-001",
        "name": "safety_validator",
        "display_name": "Safety Validator Agent",
        "description": "Validates safety-critical decisions using o1 reasoning model for cross-verification.",
        "category": "validation",
        "model": "o1",
        "input_schema": {
            "type": "object",
            "properties": {
                "recommendation": {"type": "string"},
                "patient_data": {"type": "object"},
                "clinical_context": {"type": "string"}
            },
            "required": ["recommendation"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "safety_status": {"type": "string", "enum": ["SAFE", "CAUTION", "BLOCKED"]},
                "human_review_required": {"type": "boolean"},
                "safety_concerns": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    "VAL-002": {
        "id": "VAL-002",
        "name": "consensus_checker",
        "display_name": "Consensus Checker Agent",
        "description": "Checks consensus across multiple agent outputs for contradiction detection.",
        "category": "validation",
        "model": "gpt-4.1",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_outputs": {"type": "object"},
                "decision_context": {"type": "string"}
            },
            "required": ["agent_outputs"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "consensus_score": {"type": "number"},
                "contradictions": {"type": "array", "items": {"type": "object"}},
                "resolution": {"type": "string"}
            }
        }
    },
    "VAL-003": {
        "id": "VAL-003",
        "name": "policy_match_grader",
        "display_name": "Policy Match Grader Agent",
        "description": "Grades policy compliance using DeepSeek for detailed policy analysis.",
        "category": "validation",
        "model": "deepseek",
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_data": {"type": "object"},
                "policy_requirements": {"type": "array", "items": {"type": "string"}},
                "payer_name": {"type": "string"}
            },
            "required": ["claim_data"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "policy_match_grade": {"type": "number"},
                "compliance_details": {"type": "array", "items": {"type": "object"}},
                "gaps": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    "VAL-004": {
        "id": "VAL-004",
        "name": "viability_scorer",
        "display_name": "Viability Scorer Agent",
        "description": "Scores appeal viability using o3 reasoning for complex assessment.",
        "category": "validation",
        "model": "o3",
        "input_schema": {
            "type": "object",
            "properties": {
                "denial_data": {"type": "object"},
                "available_evidence": {"type": "array", "items": {"type": "string"}},
                "payer_history": {"type": "object"}
            },
            "required": ["denial_data"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "viability_grade": {"type": "number"},
                "success_factors": {"type": "array", "items": {"type": "string"}},
                "risk_factors": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    "VAL-005": {
        "id": "VAL-005",
        "name": "eligibility_verifier",
        "display_name": "Eligibility Verifier Agent",
        "description": "Verifies patient eligibility in real-time for claims processing.",
        "category": "validation",
        "model": "gpt-4.1-mini",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "payer_name": {"type": "string"},
                "service_date": {"type": "string"},
                "procedure_code": {"type": "string"}
            },
            "required": ["patient_id", "payer_name"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "eligible": {"type": "boolean"},
                "coverage_details": {"type": "object"},
                "limitations": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    "VAL-006": {
        "id": "VAL-006",
        "name": "followup_scheduler",
        "display_name": "Followup Scheduler Agent",
        "description": "Schedules automated follow-up actions based on case status.",
        "category": "validation",
        "model": "gpt-4.1-nano",
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string"},
                "current_status": {"type": "string"},
                "deadline": {"type": "string"}
            },
            "required": ["case_id"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "scheduled_actions": {"type": "array", "items": {"type": "object"}},
                "next_followup_date": {"type": "string"},
                "priority": {"type": "string"}
            }
        }
    },
    
    # ==================== CFO AGENTS (CFO-001 to CFO-012) ====================
    "CFO-001": {
        "id": "CFO-001",
        "name": "submission_churn_predictor",
        "display_name": "Submission Churn Predictor Agent",
        "description": "Predicts submission churn at 837 claim submission using o3 reasoning.",
        "category": "cfo",
        "model": "o3",
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_data": {"type": "object"},
                "payer_name": {"type": "string"},
                "procedure_code": {"type": "string"},
                "billed_amount": {"type": "number"}
            },
            "required": ["claim_data"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "predicted_paid": {"type": "number"},
                "churn_amount": {"type": "number"},
                "churn_rate": {"type": "number"},
                "risk_level": {"type": "string"},
                "confidence": {"type": "number"}
            }
        }
    },
    "CFO-002": {
        "id": "CFO-002",
        "name": "payer_behavior_modeler",
        "display_name": "Payer Behavior Modeler Agent",
        "description": "Models payer behavior patterns for prediction improvement.",
        "category": "cfo",
        "model": "gpt-4.1",
        "input_schema": {
            "type": "object",
            "properties": {
                "payer_name": {"type": "string"},
                "historical_data": {"type": "array", "items": {"type": "object"}}
            },
            "required": ["payer_name"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "behavior_patterns": {"type": "array", "items": {"type": "object"}},
                "prediction_adjustments": {"type": "object"},
                "confidence": {"type": "number"}
            }
        }
    },
    "CFO-003": {
        "id": "CFO-003",
        "name": "procedure_risk_scorer",
        "display_name": "Procedure Risk Scorer Agent",
        "description": "Scores procedure-specific denial risk based on historical data.",
        "category": "cfo",
        "model": "gpt-4.1",
        "input_schema": {
            "type": "object",
            "properties": {
                "procedure_code": {"type": "string"},
                "payer_name": {"type": "string"},
                "diagnosis_code": {"type": "string"}
            },
            "required": ["procedure_code"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "risk_score": {"type": "number"},
                "historical_denial_rate": {"type": "number"},
                "risk_factors": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    "CFO-004": {
        "id": "CFO-004",
        "name": "documentation_gap_predictor",
        "display_name": "Documentation Gap Predictor Agent",
        "description": "Predicts documentation gaps before submission.",
        "category": "cfo",
        "model": "gpt-4.1-mini",
        "input_schema": {
            "type": "object",
            "properties": {
                "procedure_code": {"type": "string"},
                "payer_name": {"type": "string"},
                "current_docs": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["procedure_code"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "predicted_gaps": {"type": "array", "items": {"type": "string"}},
                "gap_probability": {"type": "number"},
                "recommendations": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    "CFO-005": {
        "id": "CFO-005",
        "name": "contractual_estimator",
        "display_name": "Contractual Estimator Agent",
        "description": "Estimates contractual amounts based on payer contracts.",
        "category": "cfo",
        "model": "gpt-4.1",
        "input_schema": {
            "type": "object",
            "properties": {
                "procedure_code": {"type": "string"},
                "payer_name": {"type": "string"},
                "billed_amount": {"type": "number"}
            },
            "required": ["procedure_code", "payer_name"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "estimated_payment": {"type": "number"},
                "contractual_adjustment": {"type": "number"},
                "confidence": {"type": "number"}
            }
        }
    },
    "CFO-006": {
        "id": "CFO-006",
        "name": "collection_timeline_predictor",
        "display_name": "Collection Timeline Predictor Agent",
        "description": "Predicts collection timelines for cash flow forecasting.",
        "category": "cfo",
        "model": "gpt-4.1-mini",
        "input_schema": {
            "type": "object",
            "properties": {
                "payer_name": {"type": "string"},
                "claim_type": {"type": "string"},
                "billed_amount": {"type": "number"}
            },
            "required": ["payer_name"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "expected_days_to_payment": {"type": "number"},
                "confidence_interval": {"type": "object"},
                "risk_factors": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    "CFO-007": {
        "id": "CFO-007",
        "name": "variance_analyzer",
        "display_name": "Variance Analyzer Agent",
        "description": "Analyzes payment variances between expected and actual.",
        "category": "cfo",
        "model": "gpt-4.1",
        "input_schema": {
            "type": "object",
            "properties": {
                "expected_payment": {"type": "number"},
                "actual_payment": {"type": "number"},
                "payer_name": {"type": "string"},
                "procedure_code": {"type": "string"}
            },
            "required": ["expected_payment", "actual_payment"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "variance_amount": {"type": "number"},
                "variance_reasons": {"type": "array", "items": {"type": "string"}},
                "action_required": {"type": "boolean"}
            }
        }
    },
    "CFO-008": {
        "id": "CFO-008",
        "name": "denial_categorizer",
        "display_name": "Denial Categorizer Agent",
        "description": "Categorizes denial types for reporting and analysis.",
        "category": "cfo",
        "model": "gpt-4.1-mini",
        "input_schema": {
            "type": "object",
            "properties": {
                "carc_code": {"type": "string"},
                "rarc_code": {"type": "string"},
                "group_code": {"type": "string"},
                "adjustment_amount": {"type": "number"}
            },
            "required": ["carc_code"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "subcategory": {"type": "string"},
                "actionability": {"type": "string"},
                "appeal_success_rate": {"type": "number"}
            }
        }
    },
    "CFO-009": {
        "id": "CFO-009",
        "name": "reconciliation_scorer",
        "display_name": "Reconciliation Scorer Agent",
        "description": "Scores reconciliation accuracy for model improvement.",
        "category": "cfo",
        "model": "gpt-4.1-mini",
        "input_schema": {
            "type": "object",
            "properties": {
                "batch_id": {"type": "string"},
                "predictions": {"type": "array", "items": {"type": "object"}},
                "actuals": {"type": "array", "items": {"type": "object"}}
            },
            "required": ["predictions", "actuals"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "accuracy_score": {"type": "number"},
                "model_drift_detected": {"type": "boolean"},
                "improvement_suggestions": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    "CFO-010": {
        "id": "CFO-010",
        "name": "cash_flow_forecaster",
        "display_name": "Cash Flow Forecaster Agent",
        "description": "Generates 90-day cash flow forecasts for CFO dashboard.",
        "category": "cfo",
        "model": "gpt-4.1",
        "input_schema": {
            "type": "object",
            "properties": {
                "pipeline_value": {"type": "number"},
                "historical_yield": {"type": "number"},
                "current_ar": {"type": "number"}
            },
            "required": ["pipeline_value"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "forecast_90_day": {"type": "object"},
                "weekly_projections": {"type": "array", "items": {"type": "object"}},
                "risk_factors": {"type": "array", "items": {"type": "object"}}
            }
        }
    },
    "CFO-011": {
        "id": "CFO-011",
        "name": "budget_scenario_modeler",
        "display_name": "Budget Scenario Modeler Agent",
        "description": "Models budget scenarios for what-if analysis.",
        "category": "cfo",
        "model": "o3",
        "input_schema": {
            "type": "object",
            "properties": {
                "scenario_name": {"type": "string"},
                "current_denial_rate": {"type": "number"},
                "target_denial_rate": {"type": "number"},
                "annual_submissions": {"type": "number"}
            },
            "required": ["scenario_name"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "projected_impact": {"type": "object"},
                "investment_analysis": {"type": "object"},
                "implementation_roadmap": {"type": "array", "items": {"type": "object"}}
            }
        }
    },
    "CFO-012": {
        "id": "CFO-012",
        "name": "executive_narrative_generator",
        "display_name": "Executive Narrative Generator Agent",
        "description": "Generates plain-English executive summaries for CFO reporting.",
        "category": "cfo",
        "model": "gpt-4.1",
        "input_schema": {
            "type": "object",
            "properties": {
                "metrics": {"type": "object"},
                "period": {"type": "string"},
                "highlights": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["metrics"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "headline": {"type": "string"},
                "narrative": {"type": "string"},
                "key_metrics": {"type": "array", "items": {"type": "object"}},
                "action_items": {"type": "array", "items": {"type": "object"}}
            }
        }
    },
    
    # ==================== STATUS INTELLIGENCE AGENTS (STS-001 to STS-008) ====================
    "STS-001": {
        "id": "STS-001",
        "name": "front_end_rejection_analyzer",
        "display_name": "Front End Rejection Analyzer Agent",
        "description": "Analyzes 277CA front-end rejections to identify patterns and prevent future failures.",
        "category": "status",
        "model": "o3",
        "input_schema": {
            "type": "object",
            "properties": {
                "rejection_data": {"type": "object"},
                "historical_patterns": {"type": "array", "items": {"type": "object"}},
                "clearinghouse": {"type": "string"}
            },
            "required": ["rejection_data"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "rejection_category": {"type": "string"},
                "root_cause": {"type": "string"},
                "pattern_detected": {"type": "boolean"},
                "fix_recommendation": {"type": "string"}
            }
        }
    },
    "STS-002": {
        "id": "STS-002",
        "name": "appeal_deadline_risk_assessor",
        "display_name": "Appeal Deadline Risk Assessor Agent",
        "description": "Prioritizes appeals by combining deadline urgency, financial value, and success probability.",
        "category": "status",
        "model": "o3",
        "input_schema": {
            "type": "object",
            "properties": {
                "denial_summary": {"type": "string"},
                "amount": {"type": "number"},
                "days_remaining": {"type": "number"},
                "payer_name": {"type": "string"},
                "success_probability": {"type": "number"}
            },
            "required": ["days_remaining"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "priority_score": {"type": "number"},
                "risk_level": {"type": "string"},
                "recommended_action": {"type": "string"},
                "deadline_alert": {"type": "boolean"}
            }
        }
    },
    "STS-003": {
        "id": "STS-003",
        "name": "pending_claim_risk_scorer",
        "display_name": "Pending Claim Risk Scorer Agent",
        "description": "Scores risk for pending claims based on aging and payer patterns.",
        "category": "status",
        "model": "gpt-4.1",
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_summary": {"type": "string"},
                "days_pending": {"type": "number"},
                "payer_name": {"type": "string"},
                "status_history": {"type": "array", "items": {"type": "object"}}
            },
            "required": ["days_pending"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "risk_score": {"type": "number"},
                "predicted_outcome": {"type": "string"},
                "intervention_recommended": {"type": "boolean"}
            }
        }
    },
    "STS-004": {
        "id": "STS-004",
        "name": "aging_trend_forecaster",
        "display_name": "Aging Trend Forecaster Agent",
        "description": "Forecasts A/R aging trends and cash flow impact from pending claims.",
        "category": "status",
        "model": "gpt-4.1",
        "input_schema": {
            "type": "object",
            "properties": {
                "current_aging": {"type": "object"},
                "historical_aging": {"type": "array", "items": {"type": "object"}},
                "pending_resolution": {"type": "array", "items": {"type": "object"}}
            },
            "required": ["current_aging"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "aging_forecast": {"type": "array", "items": {"type": "object"}},
                "cash_conversion_forecast": {"type": "number"},
                "concerning_trends": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    "STS-005": {
        "id": "STS-005",
        "name": "payer_sla_monitor",
        "display_name": "Payer SLA Monitor Agent",
        "description": "Monitors payer SLA compliance and identifies breaches.",
        "category": "status",
        "model": "gpt-4.1-mini",
        "input_schema": {
            "type": "object",
            "properties": {
                "payer_name": {"type": "string"},
                "contracted_sla_days": {"type": "number"},
                "claims_submitted": {"type": "number"},
                "claims_adjudicated": {"type": "number"}
            },
            "required": ["payer_name"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "sla_compliance_rate": {"type": "number"},
                "claims_breaching_sla": {"type": "number"},
                "escalation_recommended": {"type": "boolean"}
            }
        }
    },
    "STS-006": {
        "id": "STS-006",
        "name": "cob_coordination_analyzer",
        "display_name": "COB Coordination Analyzer Agent",
        "description": "Analyzes Coordination of Benefits holds and identifies resolution paths.",
        "category": "status",
        "model": "gpt-4.1-mini",
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_summary": {"type": "string"},
                "primary_payer": {"type": "string"},
                "secondary_payer": {"type": "string"},
                "cob_status": {"type": "string"}
            },
            "required": ["primary_payer"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "cob_issue_identified": {"type": "boolean"},
                "issue_type": {"type": "string"},
                "resolution_path": {"type": "string"}
            }
        }
    },
    "STS-007": {
        "id": "STS-007",
        "name": "status_pattern_detector",
        "display_name": "Status Pattern Detector Agent",
        "description": "Detects anomalies and patterns in claim status flows using batch analysis.",
        "category": "status",
        "model": "deepseek",
        "input_schema": {
            "type": "object",
            "properties": {
                "status_flow_data": {"type": "array", "items": {"type": "object"}},
                "baseline_days": {"type": "number"},
                "baseline_stuck_rate": {"type": "number"}
            },
            "required": ["status_flow_data"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "anomalies_detected": {"type": "array", "items": {"type": "object"}},
                "emerging_patterns": {"type": "array", "items": {"type": "object"}},
                "recommended_investigations": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    "STS-008": {
        "id": "STS-008",
        "name": "status_intelligence_summarizer",
        "display_name": "Status Intelligence Summarizer Agent",
        "description": "Summarizes all status intelligence for dashboards and alerts.",
        "category": "status",
        "model": "gpt-4.1-nano",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_outputs": {"type": "object"}
            },
            "required": ["agent_outputs"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "headline": {"type": "string"},
                "alert_level": {"type": "string"},
                "key_metrics": {"type": "object"},
                "top_issues": {"type": "array", "items": {"type": "object"}}
            }
        }
    },
    
    # ==================== SYSTEM AGENTS (SYS-001 to SYS-003) ====================
    "SYS-001": {
        "id": "SYS-001",
        "name": "audit_agent",
        "display_name": "Audit Agent",
        "description": "Out-of-band audit agent that validates consistency across all agents.",
        "category": "system",
        "model": "o3",
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_data": {"type": "object"},
                "all_outputs": {"type": "object"},
                "historical_accuracy": {"type": "object"}
            },
            "required": ["all_outputs"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "audit_passed": {"type": "boolean"},
                "overall_confidence": {"type": "number"},
                "consistency_check": {"type": "object"},
                "human_review_required": {"type": "boolean"}
            }
        }
    },
    "SYS-002": {
        "id": "SYS-002",
        "name": "health_check_agent",
        "display_name": "Health Check Agent",
        "description": "Monitors health and performance of all 42 agents.",
        "category": "system",
        "model": "gpt-4.1-mini",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_metrics": {"type": "object"},
                "baseline": {"type": "object"}
            },
            "required": []
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "overall_health": {"type": "string"},
                "agents_checked": {"type": "number"},
                "degraded_agents": {"type": "array", "items": {"type": "object"}},
                "recommendations": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    "SYS-003": {
        "id": "SYS-003",
        "name": "policy_scraper_agent",
        "display_name": "Policy Scraper Agent",
        "description": "Weekly automated scraping of FL payer policy portals.",
        "category": "system",
        "model": "gpt-4.1",
        "input_schema": {
            "type": "object",
            "properties": {
                "payer_id": {"type": "string"},
                "scrape_type": {"type": "string", "enum": ["full", "incremental"]}
            },
            "required": ["payer_id"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "policies_scraped": {"type": "number"},
                "policies_updated": {"type": "number"},
                "policies_new": {"type": "number"},
                "errors": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    
    # ==================== RAG AGENT (RAG-001) ====================
    "RAG-001": {
        "id": "RAG-001",
        "name": "policy_rag_agent",
        "display_name": "Policy RAG Agent",
        "description": "Retrieves and validates claims against payer policies using Azure AI Search.",
        "category": "rag",
        "model": "gpt-4.1",
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_data": {"type": "object"},
                "payer_name": {"type": "string"},
                "procedure_code": {"type": "string"},
                "procedure_description": {"type": "string"}
            },
            "required": ["payer_name", "procedure_code"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "policy_compliance": {"type": "boolean"},
                "compliance_score": {"type": "number"},
                "matching_policies": {"type": "array", "items": {"type": "object"}},
                "prior_auth_required": {"type": "boolean"},
                "recommendations": {"type": "array", "items": {"type": "string"}}
            }
        }
    }
}


class AgentToolRegistry:
    """Registry for all MCP agent tools."""
    
    def __init__(self):
        self.agents = AGENT_DEFINITIONS
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all tools in MCP format."""
        tools = []
        for agent_id, agent in self.agents.items():
            tools.append({
                "name": agent["name"],
                "description": agent["description"],
                "inputSchema": agent["input_schema"]
            })
        return tools
    
    def get_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific tool by name."""
        for agent_id, agent in self.agents.items():
            if agent["name"] == tool_name:
                return {
                    "id": agent_id,
                    "name": agent["name"],
                    "display_name": agent["display_name"],
                    "description": agent["description"],
                    "category": agent["category"],
                    "model": agent["model"],
                    "inputSchema": agent["input_schema"],
                    "outputSchema": agent["output_schema"]
                }
        return None
    
    def tool_exists(self, tool_name: str) -> bool:
        """Check if a tool exists."""
        return any(agent["name"] == tool_name for agent in self.agents.values())
    
    def get_categories(self) -> List[str]:
        """Get all unique categories."""
        return list(set(agent["category"] for agent in self.agents.values()))
    
    def get_tools_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all tools in a specific category."""
        tools = []
        for agent_id, agent in self.agents.items():
            if agent["category"] == category:
                tools.append({
                    "id": agent_id,
                    "name": agent["name"],
                    "display_name": agent["display_name"],
                    "description": agent["description"],
                    "model": agent["model"]
                })
        return tools
    
    def get_agent_by_id(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent definition by ID."""
        return self.agents.get(agent_id)


async def execute_agent_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute an agent tool with the provided arguments.
    This connects to the backend agent service for actual execution.
    """
    try:
        # Import backend agents
        from app.services.ai_agents import (
            SDOHScorerAgent, CareGapDetectorAgent, ClinicalUrgencyAgent,
            FinancialValueAgent, RecoveryPredictorAgent, P2POptimizerAgent,
            QueueWaitTimeAgent, PARiskPredictorAgent, DocCompletenessAgent,
            PolicyMonitorAgent, RootCauseAnalyzerAgent, StaffFeedbackProcessorAgent,
            SafetyValidatorAgent, ConsensusCheckerAgent, PolicyMatchGraderAgent,
            ViabilityScorerAgent, EligibilityVerifierAgent, FollowupSchedulerAgent,
            SubmissionChurnPredictorAgent, PayerBehaviorModelerAgent,
            ProcedureRiskScorerAgent, DocumentationGapPredictorAgent,
            ContractualEstimatorAgent, CollectionTimelinePredictorAgent,
            VarianceAnalyzerAgent, DenialCategorizerAgent, ReconciliationScorerAgent,
            CashFlowForecasterAgent, BudgetScenarioModelerAgent,
            ExecutiveNarrativeGeneratorAgent, FrontEndRejectionAnalyzerAgent,
            AppealDeadlineRiskAssessorAgent, PendingClaimRiskScorerAgent,
            AgingTrendForecasterAgent, PayerSLAMonitorAgent, COBCoordinationAnalyzerAgent,
            StatusPatternDetectorAgent, StatusIntelligenceSummarizerAgent,
            AuditAgent, HealthCheckAgent, PolicyScraperAgent, PolicyRAGAgent
        )
        
        # Agent name to class mapping
        AGENT_CLASSES = {
            "sdoh_scorer": SDOHScorerAgent,
            "care_gap_detector": CareGapDetectorAgent,
            "clinical_urgency": ClinicalUrgencyAgent,
            "financial_value": FinancialValueAgent,
            "recovery_predictor": RecoveryPredictorAgent,
            "p2p_optimizer": P2POptimizerAgent,
            "queue_wait_time": QueueWaitTimeAgent,
            "pa_risk_predictor": PARiskPredictorAgent,
            "doc_completeness": DocCompletenessAgent,
            "policy_monitor": PolicyMonitorAgent,
            "root_cause_analyzer": RootCauseAnalyzerAgent,
            "staff_feedback_processor": StaffFeedbackProcessorAgent,
            "safety_validator": SafetyValidatorAgent,
            "consensus_checker": ConsensusCheckerAgent,
            "policy_match_grader": PolicyMatchGraderAgent,
            "viability_scorer": ViabilityScorerAgent,
            "eligibility_verifier": EligibilityVerifierAgent,
            "followup_scheduler": FollowupSchedulerAgent,
            "submission_churn_predictor": SubmissionChurnPredictorAgent,
            "payer_behavior_modeler": PayerBehaviorModelerAgent,
            "procedure_risk_scorer": ProcedureRiskScorerAgent,
            "documentation_gap_predictor": DocumentationGapPredictorAgent,
            "contractual_estimator": ContractualEstimatorAgent,
            "collection_timeline_predictor": CollectionTimelinePredictorAgent,
            "variance_analyzer": VarianceAnalyzerAgent,
            "denial_categorizer": DenialCategorizerAgent,
            "reconciliation_scorer": ReconciliationScorerAgent,
            "cash_flow_forecaster": CashFlowForecasterAgent,
            "budget_scenario_modeler": BudgetScenarioModelerAgent,
            "executive_narrative_generator": ExecutiveNarrativeGeneratorAgent,
            "front_end_rejection_analyzer": FrontEndRejectionAnalyzerAgent,
            "appeal_deadline_risk_assessor": AppealDeadlineRiskAssessorAgent,
            "pending_claim_risk_scorer": PendingClaimRiskScorerAgent,
            "aging_trend_forecaster": AgingTrendForecasterAgent,
            "payer_sla_monitor": PayerSLAMonitorAgent,
            "cob_coordination_analyzer": COBCoordinationAnalyzerAgent,
            "status_pattern_detector": StatusPatternDetectorAgent,
            "status_intelligence_summarizer": StatusIntelligenceSummarizerAgent,
            "audit_agent": AuditAgent,
            "health_check_agent": HealthCheckAgent,
            "policy_scraper_agent": PolicyScraperAgent,
            "policy_rag_agent": PolicyRAGAgent,
        }
        
        if tool_name not in AGENT_CLASSES:
            return {"error": f"Unknown agent: {tool_name}", "status": "failed"}
        
        # Instantiate and run the agent
        agent_class = AGENT_CLASSES[tool_name]
        agent = agent_class()
        result = await agent.analyze(arguments)
        
        return {
            "status": "success",
            "agent": tool_name,
            "result": result
        }
        
    except ImportError as e:
        # Fallback response when backend is not available
        return {
            "status": "fallback",
            "agent": tool_name,
            "message": "Agent execution requires backend service connection",
            "arguments_received": arguments,
            "error": str(e)
        }
    except Exception as e:
        return {
            "status": "error",
            "agent": tool_name,
            "error": str(e)
        }
