"""
Payer Policy RAG System with Azure AI Search

This module provides a comprehensive RAG (Retrieval-Augmented Generation) system
for FL payer policies using Azure AI Search as the vector store.

Supported Payers:
- Florida Blue (BCBS FL)
- Humana FL
- Florida Medicaid (AHCA)
- Aetna FL

Features:
- Semantic search across payer policy documents
- Version tracking and change detection
- Weekly automated updates via PolicyScraperAgent
- Integration with PolicyMatchGraderAgent and SafetyValidatorAgent
"""

import os
import json
import hashlib
import re
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

# Azure AI Search imports
try:
    from azure.search.documents import SearchClient
    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.indexes.models import (
        SearchIndex,
        SearchField,
        SearchFieldDataType,
        SimpleField,
        SearchableField,
        SemanticConfiguration,
        SemanticField,
        SemanticPrioritizedFields,
        SemanticSearch
    )
    from azure.core.credentials import AzureKeyCredential
    AZURE_SEARCH_AVAILABLE = True
except ImportError:
    AZURE_SEARCH_AVAILABLE = False
    SearchClient = None

# Azure AI Search configuration from environment variables
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "https://vectorstore25.search.windows.net")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY", "")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX", "payerpolicy25")


@dataclass
class PolicyDocument:
    """Represents a payer policy document."""
    payer_id: str
    payer_name: str
    policy_type: str
    policy_title: str
    policy_number: str
    effective_date: str
    content: str
    source_url: str
    last_updated: str
    version: str
    content_hash: str = ""
    
    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hashlib.md5(self.content.encode()).hexdigest()


@dataclass
class PolicySearchResult:
    """Result from policy search."""
    document: PolicyDocument
    relevance_score: float
    matched_section: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class PayerPolicyRAG:
    """
    RAG system for payer policy retrieval using Azure AI Search.
    
    Provides semantic search across comprehensive FL payer policies
    with version tracking and change detection.
    """
    
    INDEX_NAME = AZURE_SEARCH_INDEX
    
    PAYER_CONFIG = {
        "florida_blue": {
            "id": "FL_BLUE",
            "name": "Florida Blue (BCBS FL)",
            "portal_url": "https://www.floridablue.com/providers",
            "policy_types": [
                "medical_policy",
                "prior_auth",
                "clinical_guidelines",
                "coverage_determination",
                "appeal_procedures"
            ]
        },
        "humana": {
            "id": "HUMANA_FL",
            "name": "Humana Florida",
            "portal_url": "https://www.humana.com/provider",
            "policy_types": [
                "medical_policy",
                "prior_auth",
                "formulary",
                "step_therapy",
                "utilization_management"
            ]
        },
        "florida_medicaid": {
            "id": "FL_MEDICAID",
            "name": "Florida Medicaid (AHCA)",
            "portal_url": "https://ahca.myflorida.com/medicaid",
            "policy_types": [
                "coverage_policy",
                "fee_schedule",
                "prior_auth",
                "medical_necessity",
                "provider_handbook"
            ]
        },
        "aetna": {
            "id": "AETNA_FL",
            "name": "Aetna Florida",
            "portal_url": "https://www.aetna.com/health-care-professionals",
            "policy_types": [
                "clinical_policy_bulletin",
                "prior_auth",
                "medical_necessity",
                "utilization_review",
                "appeal_guidelines"
            ]
        },
        "medicare": {
            "id": "MEDICARE",
            "name": "Medicare (CMS)",
            "portal_url": "https://www.cms.gov/medicare",
            "policy_types": [
                "national_coverage_determination",
                "local_coverage_determination",
                "medicare_benefit_policy",
                "claims_processing_manual",
                "appeals_process"
            ]
        },
        "united_healthcare": {
            "id": "UNITED",
            "name": "United Healthcare",
            "portal_url": "https://www.uhcprovider.com",
            "policy_types": [
                "medical_policy",
                "prior_auth",
                "clinical_guidelines",
                "coverage_determination",
                "appeal_procedures"
            ]
        },
        "cigna": {
            "id": "CIGNA",
            "name": "Cigna Healthcare",
            "portal_url": "https://www.cigna.com/health-care-providers",
            "policy_types": [
                "coverage_policy",
                "prior_auth",
                "medical_necessity",
                "utilization_management",
                "appeal_guidelines"
            ]
        },
        "tricare": {
            "id": "TRICARE",
            "name": "TRICARE (Military Health)",
            "portal_url": "https://www.tricare.mil/providers",
            "policy_types": [
                "tricare_policy_manual",
                "prior_auth",
                "medical_necessity",
                "appeals_process",
                "reimbursement_manual"
            ]
        },
        "anthem": {
            "id": "ANTHEM",
            "name": "Anthem Blue Cross Blue Shield",
            "portal_url": "https://www.anthem.com/provider",
            "policy_types": [
                "medical_policy",
                "prior_auth",
                "clinical_guidelines",
                "coverage_determination",
                "appeal_procedures"
            ]
        }
    }
    
    def __init__(self, endpoint: str = None, api_key: str = None, index_name: str = None):
        """Initialize the RAG system with Azure AI Search."""
        self.endpoint = endpoint or AZURE_SEARCH_ENDPOINT
        self.api_key = api_key or AZURE_SEARCH_KEY
        self.index_name = index_name or AZURE_SEARCH_INDEX
        self.search_client = None
        self.collection = None  # For backward compatibility
        self._initialize_azure_search()
    
    def _initialize_azure_search(self):
        """Initialize Azure AI Search client."""
        if not AZURE_SEARCH_AVAILABLE:
            print("Warning: Azure AI Search SDK not available. RAG features disabled.")
            return
        
        if not self.api_key:
            print("Warning: Azure AI Search API key not configured. RAG features disabled.")
            return
        
        try:
            self.search_client = SearchClient(
                endpoint=self.endpoint,
                index_name=self.index_name,
                credential=AzureKeyCredential(self.api_key)
            )
            self.collection = True  # For backward compatibility checks
            print(f"Connected to Azure AI Search: {self.index_name}")
        except Exception as e:
            print(f"Error connecting to Azure AI Search: {e}")
            self.search_client = None
            self.collection = None
    
    def _sanitize_key(self, key: str) -> str:
        """Sanitize document key to only contain valid characters for Azure AI Search."""
        return re.sub(r'[^a-zA-Z0-9_\-=]', '_', key)
    
    def add_policy(self, policy: PolicyDocument) -> str:
        """Add a policy document to the vector store."""
        if not self.search_client:
            return ""
        
        raw_id = f"{policy.payer_id}_{policy.policy_number}_{policy.version}"
        doc_id = self._sanitize_key(raw_id)
        
        document = {
            "id": doc_id,
            "payer_id": policy.payer_id,
            "payer_name": policy.payer_name,
            "policy_type": policy.policy_type,
            "policy_title": policy.policy_title,
            "policy_number": policy.policy_number,
            "effective_date": policy.effective_date,
            "content": policy.content,
            "source_url": policy.source_url,
            "last_updated": policy.last_updated,
            "version": policy.version,
            "content_hash": policy.content_hash
        }
        
        try:
            self.search_client.upload_documents(documents=[document])
            return doc_id
        except Exception as e:
            print(f"Error adding policy: {e}")
            return ""
    
    def search_policies(
        self,
        query: str,
        payer_id: Optional[str] = None,
        policy_type: Optional[str] = None,
        n_results: int = 5
    ) -> List[PolicySearchResult]:
        """
        Search for relevant policy documents using Azure AI Search.
        
        Args:
            query: Search query (e.g., "prior authorization for knee replacement")
            payer_id: Filter by specific payer
            policy_type: Filter by policy type
            n_results: Number of results to return
            
        Returns:
            List of PolicySearchResult with relevance scores
        """
        if not self.search_client:
            return []
        
        # Build filter string for Azure AI Search
        filters = []
        if payer_id:
            filters.append(f"payer_id eq '{payer_id}'")
        if policy_type:
            filters.append(f"policy_type eq '{policy_type}'")
        filter_str = " and ".join(filters) if filters else None
        
        try:
            results = self.search_client.search(
                search_text=query,
                filter=filter_str,
                top=n_results,
                include_total_count=True
            )
            
            search_results = []
            for result in results:
                # Azure AI Search returns @search.score for relevance
                score = result.get("@search.score", 0)
                # Normalize score to 0-1 range (Azure scores can be > 1)
                relevance_score = min(score / 10.0, 1.0) if score else 0.0
                
                content = result.get("content", "")
                
                policy = PolicyDocument(
                    payer_id=result.get("payer_id", ""),
                    payer_name=result.get("payer_name", ""),
                    policy_type=result.get("policy_type", ""),
                    policy_title=result.get("policy_title", ""),
                    policy_number=result.get("policy_number", ""),
                    effective_date=result.get("effective_date", ""),
                    content=content,
                    source_url=result.get("source_url", ""),
                    last_updated=result.get("last_updated", ""),
                    version=result.get("version", ""),
                    content_hash=result.get("content_hash", "")
                )
                
                search_results.append(PolicySearchResult(
                    document=policy,
                    relevance_score=relevance_score,
                    matched_section=content[:500] + "..." if len(content) > 500 else content,
                    metadata=dict(result)
                ))
            
            return search_results
        except Exception as e:
            print(f"Error searching policies: {e}")
            return []
    
    def get_policy_by_id(self, payer_id: str, policy_number: str) -> Optional[PolicyDocument]:
        """Get a specific policy by payer and policy number."""
        if not self.search_client:
            return None
        
        try:
            filter_str = f"payer_id eq '{payer_id}' and policy_number eq '{policy_number}'"
            results = self.search_client.search(
                search_text="*",
                filter=filter_str,
                top=1
            )
            
            for result in results:
                return PolicyDocument(
                    payer_id=result.get("payer_id", ""),
                    payer_name=result.get("payer_name", ""),
                    policy_type=result.get("policy_type", ""),
                    policy_title=result.get("policy_title", ""),
                    policy_number=result.get("policy_number", ""),
                    effective_date=result.get("effective_date", ""),
                    content=result.get("content", ""),
                    source_url=result.get("source_url", ""),
                    last_updated=result.get("last_updated", ""),
                    version=result.get("version", ""),
                    content_hash=result.get("content_hash", "")
                )
        except Exception as e:
            print(f"Error getting policy by id: {e}")
        
        return None
    
    def check_policy_changes(self, policy: PolicyDocument) -> Dict[str, Any]:
        """
        Check if a policy has changed since last update.
        
        Returns:
            Dict with change detection results
        """
        existing = self.get_policy_by_id(policy.payer_id, policy.policy_number)
        
        if not existing:
            return {
                "is_new": True,
                "has_changed": False,
                "previous_version": None,
                "previous_hash": None
            }
        
        has_changed = existing.content_hash != policy.content_hash
        
        return {
            "is_new": False,
            "has_changed": has_changed,
            "previous_version": existing.version,
            "previous_hash": existing.content_hash,
            "current_hash": policy.content_hash
        }
    
    def get_all_policies_for_payer(self, payer_id: str) -> List[PolicyDocument]:
        """Get all policies for a specific payer."""
        if not self.search_client:
            return []
        
        try:
            filter_str = f"payer_id eq '{payer_id}'"
            results = self.search_client.search(
                search_text="*",
                filter=filter_str,
                top=1000
            )
            
            policies = []
            for result in results:
                policies.append(PolicyDocument(
                    payer_id=result.get("payer_id", ""),
                    payer_name=result.get("payer_name", ""),
                    policy_type=result.get("policy_type", ""),
                    policy_title=result.get("policy_title", ""),
                    policy_number=result.get("policy_number", ""),
                    effective_date=result.get("effective_date", ""),
                    content=result.get("content", ""),
                    source_url=result.get("source_url", ""),
                    last_updated=result.get("last_updated", ""),
                    version=result.get("version", ""),
                    content_hash=result.get("content_hash", "")
                ))
            
            return policies
        except Exception as e:
            print(f"Error getting policies for payer: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the policy database."""
        if not self.search_client:
            return {"error": "Azure AI Search not available"}
        
        try:
            # Count total documents
            results = self.search_client.search(search_text="*", top=0, include_total_count=True)
            total_count = results.get_count() or 0
        except Exception:
            total_count = 0
        
        stats = {
            "total_policies": total_count,
            "payers": {},
            "policy_types": {},
            "last_updated": datetime.utcnow().isoformat()
        }
        
        for payer_key, payer_config in self.PAYER_CONFIG.items():
            payer_id = payer_config["id"]
            payer_policies = self.get_all_policies_for_payer(payer_id)
            stats["payers"][payer_id] = {
                "name": payer_config["name"],
                "policy_count": len(payer_policies),
                "policy_types": list(set(p.policy_type for p in payer_policies))
            }
        
        return stats
    
    def get_policy_stats(self) -> Dict[str, Any]:
        """Get policy statistics in the format expected by API endpoints."""
        if not self.search_client:
            return {
                "total_policies": 0,
                "by_payer": {},
                "by_type": {},
                "last_updated": None
            }
        
        try:
            # Count total documents
            results = self.search_client.search(search_text="*", top=0, include_total_count=True)
            total_count = results.get_count() or 0
        except Exception:
            total_count = 0
        
        by_payer = {}
        by_type = {}
        
        for payer_key, payer_config in self.PAYER_CONFIG.items():
            payer_id = payer_config["id"]
            payer_policies = self.get_all_policies_for_payer(payer_id)
            by_payer[payer_id] = len(payer_policies)
            
            for policy in payer_policies:
                policy_type = policy.policy_type
                by_type[policy_type] = by_type.get(policy_type, 0) + 1
        
        return {
            "total_policies": total_count,
            "by_payer": by_payer,
            "by_type": by_type,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def get_policy_by_number(self, policy_number: str) -> Optional[PolicyDocument]:
        """Get a policy by its policy number."""
        if not self.search_client:
            return None
        
        try:
            filter_str = f"policy_number eq '{policy_number}'"
            results = self.search_client.search(
                search_text="*",
                filter=filter_str,
                top=1
            )
            
            for result in results:
                return PolicyDocument(
                    payer_id=result.get("payer_id", ""),
                    payer_name=result.get("payer_name", ""),
                    policy_type=result.get("policy_type", ""),
                    policy_title=result.get("policy_title", ""),
                    policy_number=result.get("policy_number", ""),
                    effective_date=result.get("effective_date", ""),
                    content=result.get("content", ""),
                    source_url=result.get("source_url", ""),
                    last_updated=result.get("last_updated", ""),
                    version=result.get("version", "1.0"),
                    content_hash=result.get("content_hash", "")
                )
        except Exception as e:
            print(f"Error getting policy by number: {e}")
        
        return None


def get_comprehensive_payer_policies() -> List[PolicyDocument]:
    """
    Returns comprehensive payer policy documents for all major payers.
    
    Supported Payers (8 total):
    - Florida Blue (BCBS FL)
    - Humana Florida
    - Florida Medicaid (AHCA)
    - Aetna Florida
    - Medicare (CMS)
    - United Healthcare
    - Cigna Healthcare
    - TRICARE (Military Health)
    
    These are detailed policy documents covering:
    - Prior authorization requirements
    - Medical necessity criteria
    - Coverage determinations
    - Appeal procedures
    - Documentation requirements
    - National and local coverage determinations
    """
    
    policies = []
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    policies.extend([
        PolicyDocument(
            payer_id="FL_BLUE",
            payer_name="Florida Blue (BCBS FL)",
            policy_type="prior_auth",
            policy_title="Prior Authorization Requirements - Orthopedic Procedures",
            policy_number="PA-ORTHO-2024-001",
            effective_date="2024-01-01",
            content="""FLORIDA BLUE PRIOR AUTHORIZATION POLICY
Policy Number: PA-ORTHO-2024-001
Effective Date: January 1, 2024
Last Reviewed: December 1, 2024

ORTHOPEDIC PROCEDURES REQUIRING PRIOR AUTHORIZATION

1. TOTAL KNEE REPLACEMENT (CPT 27447)
   Prior Authorization: REQUIRED
   
   Medical Necessity Criteria:
   - Patient must have documented osteoarthritis with Kellgren-Lawrence Grade 3 or 4
   - Conservative treatment failure for minimum 3 months including:
     * Physical therapy (minimum 6 weeks)
     * NSAIDs or other anti-inflammatory medications
     * Intra-articular injections (corticosteroid or hyaluronic acid)
   - Functional limitation documented by validated outcome measure (WOMAC, KOOS, or equivalent)
   - BMI < 40 (or documented weight management program enrollment if BMI 40-45)
   - No active infection at surgical site
   - Cardiac clearance if patient has cardiovascular disease history
   
   Required Documentation:
   - Recent X-rays (within 6 months) showing joint space narrowing
   - Physical therapy notes documenting treatment and outcomes
   - Medication history showing conservative treatment attempts
   - Functional assessment scores
   - Surgical plan and expected outcomes
   
   Turnaround Time: 5 business days for standard requests, 72 hours for urgent
   
   Appeal Process:
   - First-level appeal: Peer-to-peer review within 30 days of denial
   - Second-level appeal: External review within 60 days
   - Expedited appeal available for urgent cases (24-48 hours)

2. TOTAL HIP REPLACEMENT (CPT 27130)
   Prior Authorization: REQUIRED
   
   Medical Necessity Criteria:
   - Documented hip osteoarthritis, avascular necrosis, or hip fracture
   - Conservative treatment failure for minimum 3 months (unless acute fracture)
   - Functional limitation affecting activities of daily living
   - Pain not adequately controlled with conservative measures
   
   Required Documentation:
   - Hip X-rays or MRI within 6 months
   - Documentation of conservative treatment attempts
   - Functional assessment
   - Surgical plan

3. ARTHROSCOPIC KNEE SURGERY (CPT 29881)
   Prior Authorization: REQUIRED for non-traumatic indications
   
   Medical Necessity Criteria:
   - Mechanical symptoms (locking, catching) suggesting meniscal tear
   - MRI confirmation of meniscal pathology
   - Failed conservative treatment for 6 weeks minimum
   - Age consideration: For patients over 50, must demonstrate mechanical symptoms
   
   Note: Arthroscopic debridement for osteoarthritis alone is NOT covered per clinical evidence guidelines.

4. SPINAL FUSION (CPT 22612, 22630, 22633)
   Prior Authorization: REQUIRED
   
   Medical Necessity Criteria:
   - Documented spinal instability, spondylolisthesis, or degenerative disc disease
   - Failed conservative treatment for minimum 6 months including:
     * Physical therapy
     * Pain management interventions
     * Epidural steroid injections (if appropriate)
   - Imaging correlation with clinical symptoms
   - Psychological evaluation for chronic pain patients
   
   Required Documentation:
   - MRI or CT within 6 months
   - Physical therapy records
   - Pain management records
   - Psychological evaluation (if applicable)
   - Surgical plan with expected outcomes

GENERAL PRIOR AUTHORIZATION GUIDELINES:
- All requests must be submitted via Availity or the Florida Blue provider portal
- Incomplete requests will be returned; ensure all required documentation is attached
- Urgent/emergent procedures may be performed with retrospective authorization within 48 hours
- Peer-to-peer reviews available Monday-Friday 8am-5pm EST

CONTACT INFORMATION:
Prior Authorization Department: 1-800-727-2227
Provider Portal: https://www.floridablue.com/providers
Fax for PA requests: 1-800-955-6281""",
            source_url="https://www.floridablue.com/providers/prior-auth",
            last_updated=today,
            version="2024.12.1"
        ),
        
        PolicyDocument(
            payer_id="FL_BLUE",
            payer_name="Florida Blue (BCBS FL)",
            policy_type="medical_policy",
            policy_title="Medical Policy - Diagnostic Imaging",
            policy_number="MP-IMG-2024-001",
            effective_date="2024-01-01",
            content="""FLORIDA BLUE MEDICAL POLICY
Policy Number: MP-IMG-2024-001
Effective Date: January 1, 2024

DIAGNOSTIC IMAGING COVERAGE POLICY

1. MRI (Magnetic Resonance Imaging)
   
   A. BRAIN MRI (CPT 70551-70553)
      Coverage: Covered when medically necessary
      
      Indications:
      - Suspected brain tumor or metastatic disease
      - Multiple sclerosis evaluation or monitoring
      - Stroke evaluation (acute or follow-up)
      - Seizure disorder evaluation
      - Headache with red flag symptoms:
        * New onset severe headache
        * Headache with neurological deficits
        * Headache with papilledema
        * Thunderclap headache
      - Dementia evaluation
      - Pituitary disorders
      
      Prior Authorization: NOT required for initial diagnostic MRI
      Prior Authorization: REQUIRED for repeat MRI within 12 months
      
   B. SPINE MRI (CPT 72141-72158)
      Coverage: Covered when medically necessary
      
      Indications:
      - Radiculopathy with failed conservative treatment (4-6 weeks)
      - Red flag symptoms:
        * Cauda equina syndrome
        * Progressive neurological deficit
        * Suspected infection or malignancy
        * Trauma with neurological symptoms
      - Pre-surgical planning
      - Post-surgical evaluation with new symptoms
      
      Prior Authorization: REQUIRED except for red flag indications
      
   C. MUSCULOSKELETAL MRI (CPT 73221-73723)
      Coverage: Covered when medically necessary
      
      Indications:
      - Suspected internal derangement after failed conservative treatment
      - Tumor evaluation
      - Infection evaluation
      - Pre-surgical planning
      
      Prior Authorization: REQUIRED
      
      Note: X-ray should be obtained first for most musculoskeletal complaints

2. CT SCAN (Computed Tomography)
   
   A. HEAD CT (CPT 70450-70470)
      Coverage: Covered when medically necessary
      
      Indications:
      - Acute head trauma
      - Acute stroke evaluation
      - Acute severe headache
      - Altered mental status
      - Suspected intracranial hemorrhage
      
      Prior Authorization: NOT required for emergency indications
      
   B. CHEST CT (CPT 71250-71275)
      Coverage: Covered when medically necessary
      
      Indications:
      - Lung cancer screening (per USPSTF guidelines)
      - Pulmonary embolism evaluation
      - Lung nodule follow-up
      - Staging for known malignancy
      - Interstitial lung disease evaluation
      
      Prior Authorization: REQUIRED for non-emergent indications
      
   C. ABDOMINAL/PELVIC CT (CPT 74150-74178)
      Coverage: Covered when medically necessary
      
      Indications:
      - Acute abdominal pain with concerning features
      - Suspected appendicitis, diverticulitis, or bowel obstruction
      - Trauma evaluation
      - Cancer staging or surveillance
      - Kidney stone evaluation
      
      Prior Authorization: REQUIRED for non-emergent indications

3. PET SCAN (Positron Emission Tomography)
   
   Prior Authorization: ALWAYS REQUIRED
   
   Covered Indications:
   - Initial staging of known malignancy
   - Restaging after treatment
   - Evaluation of treatment response
   - Detection of recurrence when other imaging inconclusive
   
   Not Covered:
   - Screening in asymptomatic patients
   - Routine surveillance without clinical indication
   - Conditions where PET has not demonstrated clinical utility

IMAGING APPROPRIATENESS CRITERIA:
Florida Blue follows ACR Appropriateness Criteria and Choosing Wisely guidelines.
Requests not meeting these criteria may be denied or require peer-to-peer review.

RADIOLOGY BENEFIT MANAGER:
Advanced imaging requests are managed through eviCore Healthcare.
Provider Portal: https://www.evicore.com
Phone: 1-888-693-3211""",
            source_url="https://www.floridablue.com/providers/medical-policies",
            last_updated=today,
            version="2024.12.1"
        ),
        
        PolicyDocument(
            payer_id="FL_BLUE",
            payer_name="Florida Blue (BCBS FL)",
            policy_type="appeal_procedures",
            policy_title="Appeals and Grievances Process",
            policy_number="AP-GEN-2024-001",
            effective_date="2024-01-01",
            content="""FLORIDA BLUE APPEALS AND GRIEVANCES PROCESS
Policy Number: AP-GEN-2024-001
Effective Date: January 1, 2024

PROVIDER APPEAL RIGHTS AND PROCEDURES

1. FIRST-LEVEL APPEAL (Internal Review)
   
   Timeframe to File: 180 days from date of adverse determination
   
   How to Submit:
   - Online: Florida Blue Provider Portal
   - Fax: 1-800-955-6282
   - Mail: Florida Blue Appeals Department, P.O. Box 1798, Jacksonville, FL 32231
   
   Required Information:
   - Member ID and date of birth
   - Claim number or prior authorization reference number
   - Date(s) of service
   - Detailed explanation of why the decision should be overturned
   - Supporting clinical documentation
   - Peer-reviewed literature (if applicable)
   
   Decision Timeframe:
   - Pre-service appeals: 30 calendar days
   - Post-service appeals: 60 calendar days
   - Urgent appeals: 72 hours
   
   Peer-to-Peer Review:
   - Available for medical necessity denials
   - Request within 10 business days of denial
   - Schedule via Provider Services: 1-800-727-2227
   - Must be conducted by physician of same or similar specialty

2. SECOND-LEVEL APPEAL (External Review)
   
   Eligibility: Available after exhausting first-level appeal
   
   Timeframe to File: 4 months from final internal appeal decision
   
   External Review Organization: Independent Review Organization (IRO)
   
   How to Request:
   - Submit written request to Florida Blue
   - Florida Blue will forward to IRO within 5 business days
   
   Decision Timeframe:
   - Standard: 45 calendar days
   - Expedited: 72 hours for urgent situations
   
   IRO Decision: Final and binding on Florida Blue

3. EXPEDITED/URGENT APPEALS
   
   Criteria for Expedited Review:
   - Imminent and serious threat to patient's health
   - Continued stay in acute care facility
   - Time-sensitive treatment
   
   How to Request:
   - Call Provider Services: 1-800-727-2227
   - Clearly state "urgent appeal" and clinical justification
   
   Decision Timeframe: 72 hours or less

4. CLAIM PAYMENT DISPUTES
   
   For payment amount disputes (not medical necessity):
   - Submit corrected claim with documentation
   - Or file formal payment dispute within 365 days
   
   Required Documentation:
   - Original claim information
   - Explanation of correct payment calculation
   - Supporting documentation (contracts, fee schedules)

5. APPEAL TIPS FOR SUCCESS
   
   DO:
   - Include all relevant clinical documentation
   - Reference specific policy criteria and how patient meets them
   - Cite peer-reviewed literature supporting medical necessity
   - Request peer-to-peer review for complex cases
   - Meet all filing deadlines
   
   DON'T:
   - Submit duplicate appeals for same service
   - Miss filing deadlines
   - Submit without complete documentation
   - Ignore requests for additional information

CONTACT INFORMATION:
Appeals Department: 1-800-727-2227
Appeals Fax: 1-800-955-6282
Provider Portal: https://www.floridablue.com/providers

REGULATORY COMPLIANCE:
This appeals process complies with Florida Insurance Code Chapter 641
and applicable federal regulations including the Affordable Care Act.""",
            source_url="https://www.floridablue.com/providers/appeals",
            last_updated=today,
            version="2024.12.1"
        ),
    ])
    
    policies.extend([
        PolicyDocument(
            payer_id="HUMANA_FL",
            payer_name="Humana Florida",
            policy_type="prior_auth",
            policy_title="Prior Authorization Requirements - Comprehensive Guide",
            policy_number="PA-COMP-2024-001",
            effective_date="2024-01-01",
            content="""HUMANA FLORIDA PRIOR AUTHORIZATION GUIDE
Policy Number: PA-COMP-2024-001
Effective Date: January 1, 2024

SERVICES REQUIRING PRIOR AUTHORIZATION

1. INPATIENT ADMISSIONS
   - All elective admissions require prior authorization
   - Emergency admissions: Notify within 24 hours or next business day
   - Observation to inpatient conversion: Notify within 24 hours
   
   Required Information:
   - Admitting diagnosis and ICD-10 codes
   - Expected length of stay
   - Treatment plan
   - Supporting clinical documentation

2. OUTPATIENT PROCEDURES
   
   A. Surgical Procedures Requiring PA:
      - All joint replacements (hip, knee, shoulder)
      - Spinal surgeries (fusion, laminectomy, discectomy)
      - Bariatric surgery
      - Cardiac procedures (CABG, valve replacement, PCI)
      - Oncologic surgeries
      
   B. Non-Surgical Procedures Requiring PA:
      - Advanced imaging (MRI, CT, PET)
      - Sleep studies
      - Genetic testing
      - Cardiac testing (stress tests, echocardiograms)
      - Pain management procedures

3. DURABLE MEDICAL EQUIPMENT (DME)
   
   PA Required for:
   - CPAP/BiPAP machines
   - Power wheelchairs and scooters
   - Hospital beds
   - Oxygen equipment
   - Prosthetics and orthotics over $500
   
   Documentation Requirements:
   - Physician prescription
   - Medical necessity documentation
   - Face-to-face encounter notes
   - Mobility assessment (for wheelchairs)

4. HOME HEALTH SERVICES
   
   PA Required for:
   - Skilled nursing visits
   - Physical therapy
   - Occupational therapy
   - Speech therapy
   - Home health aide services
   
   Required Documentation:
   - Plan of care signed by physician
   - Homebound status certification
   - Skilled need documentation
   - Functional assessment

5. SPECIALTY MEDICATIONS
   
   PA Required for:
   - Biologics (Humira, Enbrel, Remicade, etc.)
   - Oncology medications
   - Multiple sclerosis medications
   - Hepatitis C medications
   - Growth hormones
   - Specialty injectables
   
   Step Therapy Requirements:
   - Many specialty medications require trial of first-line agents
   - Documentation of treatment failure or contraindication required
   - See formulary for specific step therapy protocols

PRIOR AUTHORIZATION SUBMISSION

How to Submit:
- Online: Availity Portal (preferred)
- Phone: 1-800-448-6262
- Fax: 1-800-949-2961

Turnaround Times:
- Urgent requests: 24-72 hours
- Standard requests: 5-7 business days
- Retrospective requests: 30 calendar days

MEDICAL NECESSITY CRITERIA

Humana uses the following clinical criteria:
- MCG (Milliman Care Guidelines) for inpatient and procedures
- InterQual for select services
- Humana Clinical Policies for specific conditions

Appeals:
- First-level appeal within 180 days of denial
- Peer-to-peer review available
- External review available after internal appeal exhausted

CONTACT INFORMATION:
Prior Authorization: 1-800-448-6262
Provider Services: 1-800-626-2741
Availity Portal: https://www.availity.com""",
            source_url="https://www.humana.com/provider/prior-auth",
            last_updated=today,
            version="2024.12.1"
        ),
        
        PolicyDocument(
            payer_id="HUMANA_FL",
            payer_name="Humana Florida",
            policy_type="step_therapy",
            policy_title="Step Therapy and Formulary Requirements",
            policy_number="ST-FORM-2024-001",
            effective_date="2024-01-01",
            content="""HUMANA FLORIDA STEP THERAPY REQUIREMENTS
Policy Number: ST-FORM-2024-001
Effective Date: January 1, 2024

STEP THERAPY OVERVIEW

Step therapy requires trial of preferred, cost-effective medications before
coverage of more expensive alternatives. This ensures appropriate utilization
while maintaining quality care.

1. RHEUMATOID ARTHRITIS / INFLAMMATORY CONDITIONS

   Step 1 (Required First):
   - Methotrexate (oral or injectable)
   - Trial period: 12 weeks at therapeutic dose
   
   Step 2 (After Step 1 Failure):
   - Preferred biologics: Humira, Enbrel
   - Trial period: 12 weeks
   
   Step 3 (After Step 2 Failure):
   - Non-preferred biologics: Remicade, Orencia, Actemra
   - JAK inhibitors: Xeljanz, Rinvoq
   
   Exception Criteria:
   - Documented contraindication to methotrexate
   - Severe disease requiring immediate biologic therapy
   - Prior biologic use with documented response

2. DIABETES MEDICATIONS

   Step 1 (Required First):
   - Metformin (unless contraindicated)
   - Trial period: 3 months at maximum tolerated dose
   
   Step 2 (After Step 1 Failure or Add-On):
   - Sulfonylureas (glipizide, glimepiride)
   - SGLT2 inhibitors (for patients with cardiovascular disease or CKD)
   
   Step 3:
   - GLP-1 agonists (Ozempic, Trulicity, Victoza)
   - DPP-4 inhibitors (Januvia, Tradjenta)
   
   Exception Criteria:
   - Metformin contraindication (renal impairment, lactic acidosis risk)
   - Established cardiovascular disease (SGLT2 or GLP-1 preferred)
   - A1C > 10% at diagnosis (may start combination therapy)

3. HYPERTENSION

   Step 1 (Required First):
   - ACE inhibitors (lisinopril, enalapril) OR
   - ARBs (losartan, valsartan) OR
   - Calcium channel blockers (amlodipine) OR
   - Thiazide diuretics (HCTZ, chlorthalidone)
   
   Step 2 (Combination Therapy):
   - Add second agent from different class
   
   Step 3:
   - Brand-name combination products
   - Newer agents (Entresto for heart failure)

4. DEPRESSION / ANXIETY

   Step 1 (Required First):
   - Generic SSRIs: sertraline, escitalopram, fluoxetine
   - Trial period: 6-8 weeks at therapeutic dose
   
   Step 2 (After Step 1 Failure):
   - SNRIs: venlafaxine, duloxetine
   - Other SSRIs: paroxetine, citalopram
   
   Step 3:
   - Atypical antidepressants: bupropion, mirtazapine
   - Brand-name medications

5. MIGRAINE PREVENTION

   Step 1 (Required First):
   - Beta-blockers (propranolol, metoprolol)
   - Antidepressants (amitriptyline, venlafaxine)
   - Anticonvulsants (topiramate, valproate)
   - Trial period: 2-3 months each
   
   Step 2 (After 2+ Step 1 Failures):
   - CGRP inhibitors: Aimovig, Ajovy, Emgality
   
   Exception Criteria:
   - Contraindication to all Step 1 agents
   - Chronic migraine (15+ headache days/month)
   - Prior CGRP use with documented response

STEP THERAPY EXCEPTION PROCESS

To request an exception:
1. Submit exception request via Availity or fax
2. Include documentation of:
   - Prior medication trials and outcomes
   - Contraindications to required steps
   - Clinical rationale for exception
3. Decision within 72 hours for urgent requests

FORMULARY TIERS:
Tier 1: Generic medications (lowest copay)
Tier 2: Preferred brand medications
Tier 3: Non-preferred brand medications
Tier 4: Specialty medications (highest copay)

CONTACT:
Pharmacy Prior Authorization: 1-800-555-2546
Formulary Questions: 1-800-448-6262""",
            source_url="https://www.humana.com/provider/formulary",
            last_updated=today,
            version="2024.12.1"
        ),
    ])
    
    policies.extend([
        PolicyDocument(
            payer_id="FL_MEDICAID",
            payer_name="Florida Medicaid (AHCA)",
            policy_type="coverage_policy",
            policy_title="Florida Medicaid Coverage and Limitations Handbook",
            policy_number="CLH-2024-001",
            effective_date="2024-01-01",
            content="""FLORIDA MEDICAID COVERAGE AND LIMITATIONS HANDBOOK
Agency for Health Care Administration (AHCA)
Policy Number: CLH-2024-001
Effective Date: January 1, 2024

GENERAL COVERAGE PRINCIPLES

Florida Medicaid covers medically necessary services for eligible recipients.
Services must be:
- Medically necessary
- Provided by enrolled providers
- Within coverage limitations
- Properly documented

1. PHYSICIAN SERVICES

   Covered Services:
   - Office visits (evaluation and management)
   - Consultations
   - Preventive care
   - Immunizations
   - Minor surgical procedures
   
   Limitations:
   - Maximum 4 office visits per month (exceptions for chronic conditions)
   - Specialist referrals required for non-emergency specialty care
   - Prior authorization required for certain procedures
   
   Reimbursement:
   - Fee-for-service rates per AHCA fee schedule
   - Managed care plans may have different rates

2. HOSPITAL SERVICES

   Inpatient Services:
   - Acute care hospitalization
   - Surgical services
   - Intensive care
   - Rehabilitation (limited)
   
   Prior Authorization Required:
   - All elective admissions
   - Admissions exceeding 3 days
   - Transfers to higher level of care
   
   Outpatient Services:
   - Emergency department visits
   - Outpatient surgery
   - Diagnostic services
   - Therapy services
   
   Limitations:
   - Non-emergency ED visits may be subject to copay
   - Outpatient surgery preferred over inpatient when appropriate

3. PRESCRIPTION DRUGS

   Covered Medications:
   - FDA-approved medications on Preferred Drug List (PDL)
   - Generic medications preferred
   - Brand medications with prior authorization
   
   Prior Authorization Required:
   - Non-PDL medications
   - Quantity limits exceeded
   - Age restrictions
   - Specialty medications
   
   Excluded Medications:
   - Cosmetic medications
   - Fertility medications
   - Experimental medications
   - OTC medications (with exceptions)

4. DURABLE MEDICAL EQUIPMENT

   Covered Equipment:
   - Wheelchairs (manual and power)
   - Hospital beds
   - Oxygen equipment
   - Diabetic supplies
   - Prosthetics and orthotics
   
   Prior Authorization Required:
   - All DME over $500
   - Power wheelchairs
   - Custom equipment
   
   Documentation Requirements:
   - Physician prescription
   - Medical necessity documentation
   - Face-to-face encounter (for certain items)

5. HOME HEALTH SERVICES

   Covered Services:
   - Skilled nursing
   - Physical therapy
   - Occupational therapy
   - Speech therapy
   - Home health aide
   
   Eligibility:
   - Homebound status
   - Skilled need
   - Physician-ordered plan of care
   
   Limitations:
   - Maximum visits per authorization period
   - Recertification required every 60 days

6. BEHAVIORAL HEALTH SERVICES

   Covered Services:
   - Outpatient mental health
   - Substance abuse treatment
   - Crisis intervention
   - Psychiatric hospitalization
   - Community mental health services
   
   Prior Authorization:
   - Inpatient psychiatric admissions
   - Residential treatment
   - Intensive outpatient programs

PRIOR AUTHORIZATION PROCESS

Submit via:
- Florida Medicaid Portal
- Managed Care Plan portal (for managed care enrollees)
- Phone: 1-877-254-1055

Turnaround Times:
- Urgent: 24 hours
- Standard: 7 calendar days
- Retrospective: 30 calendar days

APPEALS PROCESS

Provider Appeals:
- File within 120 days of adverse determination
- Submit to AHCA or managed care plan
- Include supporting documentation

Fair Hearing:
- Recipients may request fair hearing
- File within 90 days of adverse action
- Hearing conducted by AHCA

CONTACT INFORMATION:
Provider Enrollment: 1-800-289-7799
Prior Authorization: 1-877-254-1055
Provider Portal: https://portal.flmmis.com""",
            source_url="https://ahca.myflorida.com/medicaid",
            last_updated=today,
            version="2024.12.1"
        ),
        
        PolicyDocument(
            payer_id="FL_MEDICAID",
            payer_name="Florida Medicaid (AHCA)",
            policy_type="fee_schedule",
            policy_title="Florida Medicaid Fee Schedule Guidelines",
            policy_number="FS-2024-001",
            effective_date="2024-01-01",
            content="""FLORIDA MEDICAID FEE SCHEDULE GUIDELINES
Policy Number: FS-2024-001
Effective Date: January 1, 2024

REIMBURSEMENT METHODOLOGY

Florida Medicaid reimburses providers based on:
- Resource-Based Relative Value Scale (RBRVS) for physician services
- Diagnosis-Related Groups (DRG) for inpatient hospital
- Ambulatory Payment Classifications (APC) for outpatient hospital
- Fee schedules for other services

1. PHYSICIAN SERVICES

   Calculation: RBRVS methodology
   Formula: (Work RVU + Practice Expense RVU + Malpractice RVU) × Conversion Factor × GPCI
   
   Current Conversion Factor: $28.50 (effective 1/1/2024)
   
   Common Procedure Rates (examples):
   - 99213 (Office visit, established, level 3): $52.00
   - 99214 (Office visit, established, level 4): $78.00
   - 99215 (Office visit, established, level 5): $105.00
   - 99203 (Office visit, new, level 3): $85.00
   - 99204 (Office visit, new, level 4): $130.00
   
   Modifiers Affecting Payment:
   - -25: Significant, separately identifiable E/M (100% of fee)
   - -59: Distinct procedural service (100% of fee)
   - -51: Multiple procedures (50% of secondary procedures)
   - -80: Assistant surgeon (16% of primary surgeon fee)

2. HOSPITAL INPATIENT

   Methodology: All Patient Refined DRG (APR-DRG)
   
   Payment Calculation:
   Base Rate × DRG Weight × Policy Adjusters = Payment
   
   Current Base Rates (varies by hospital):
   - Teaching hospitals: Higher base rate
   - Rural hospitals: Rural adjustment
   - Children's hospitals: Specialized rates
   
   Outlier Payments:
   - Available for exceptionally high-cost cases
   - Threshold: Cost exceeds payment by fixed dollar amount + percentage

3. HOSPITAL OUTPATIENT

   Methodology: Enhanced Ambulatory Patient Groups (EAPG)
   
   Payment Calculation:
   APC Weight × Conversion Factor × Adjusters = Payment
   
   Packaging:
   - Minor ancillary services packaged into primary service
   - Drugs and supplies may be packaged

4. AMBULATORY SURGICAL CENTERS

   Methodology: ASC fee schedule
   
   Payment: Lesser of:
   - Billed charges
   - ASC fee schedule amount
   
   Facility fees separate from professional fees

5. LABORATORY SERVICES

   Methodology: Clinical Laboratory Fee Schedule
   
   Payment: Lesser of:
   - Billed charges
   - Fee schedule amount
   
   Common Tests:
   - 80053 (Comprehensive metabolic panel): $11.00
   - 85025 (CBC with differential): $8.00
   - 81001 (Urinalysis): $3.50

6. RADIOLOGY SERVICES

   Professional Component: RBRVS methodology
   Technical Component: Fee schedule
   Global: Combined professional + technical
   
   Common Procedures:
   - 71046 (Chest X-ray, 2 views): $25.00 global
   - 73030 (Shoulder X-ray): $22.00 global
   - 72148 (MRI lumbar spine): $285.00 global

BILLING REQUIREMENTS

- Use current CPT/HCPCS codes
- Include all required modifiers
- Submit within 365 days of service
- Include valid diagnosis codes (ICD-10)

TIMELY FILING:
- Clean claims: 365 days from date of service
- Corrected claims: 365 days from original remittance
- Appeals: 120 days from denial

FEE SCHEDULE ACCESS:
Current fee schedules available at:
https://ahca.myflorida.com/medicaid/fee_schedules""",
            source_url="https://ahca.myflorida.com/medicaid/fee_schedules",
            last_updated=today,
            version="2024.12.1"
        ),
    ])
    
    policies.extend([
        PolicyDocument(
            payer_id="AETNA_FL",
            payer_name="Aetna Florida",
            policy_type="clinical_policy_bulletin",
            policy_title="Clinical Policy Bulletin - Surgical Procedures",
            policy_number="CPB-SURG-2024-001",
            effective_date="2024-01-01",
            content="""AETNA CLINICAL POLICY BULLETIN
Policy Number: CPB-SURG-2024-001
Effective Date: January 1, 2024
Last Reviewed: December 1, 2024

SURGICAL PROCEDURES - MEDICAL NECESSITY CRITERIA

1. BARIATRIC SURGERY

   Covered Procedures:
   - Roux-en-Y gastric bypass (CPT 43644, 43645)
   - Sleeve gastrectomy (CPT 43775)
   - Adjustable gastric banding (CPT 43770)
   - Biliopancreatic diversion (CPT 43846, 43847)
   
   Medical Necessity Criteria:
   
   A. BMI Requirements:
      - BMI ≥ 40 kg/m², OR
      - BMI ≥ 35 kg/m² with obesity-related comorbidities:
        * Type 2 diabetes
        * Hypertension
        * Obstructive sleep apnea
        * Obesity hypoventilation syndrome
        * Nonalcoholic steatohepatitis (NASH)
        * Pseudotumor cerebri
        * GERD
        * Venous stasis disease
        * Severe urinary incontinence
   
   B. Documentation Requirements:
      - Weight history showing obesity for ≥ 5 years
      - Documentation of failed supervised weight loss attempts:
        * Physician-supervised program for ≥ 6 months within past 2 years
        * Must include dietary, exercise, and behavioral components
      - Psychological evaluation within 6 months
      - Nutritional evaluation
      - Medical clearance from PCP
      - Commitment to lifelong follow-up
   
   C. Exclusions:
      - Active substance abuse
      - Uncontrolled psychiatric disorder
      - Unable to comprehend risks/benefits
      - Pregnancy or planned pregnancy within 12-18 months
   
   Prior Authorization: REQUIRED
   
   Center of Excellence Requirement:
   - Surgery must be performed at MBSAQIP-accredited facility
   - Surgeon must meet volume and outcome requirements

2. SPINAL SURGERY

   A. Lumbar Fusion (CPT 22612, 22630, 22633)
   
   Covered Indications:
   - Spondylolisthesis (Grade II or higher, or Grade I with instability)
   - Spinal stenosis with instability
   - Degenerative disc disease with:
     * Instability on flexion/extension films
     * Failed conservative treatment ≥ 6 months
     * Concordant discography (if performed)
   - Recurrent disc herniation at same level
   - Adjacent segment disease after prior fusion
   
   Medical Necessity Criteria:
   - Failed conservative treatment including:
     * Physical therapy (≥ 6 weeks)
     * NSAIDs or other medications
     * Epidural steroid injections (if appropriate)
   - Imaging correlation with symptoms
   - Functional impairment documented
   - Psychological evaluation for chronic pain patients
   
   Not Covered:
   - Prophylactic fusion
   - Fusion for uncomplicated disc herniation
   - Multi-level fusion without clear indication for each level
   
   B. Cervical Fusion (CPT 22551, 22552, 22554)
   
   Covered Indications:
   - Cervical radiculopathy with:
     * Imaging-confirmed nerve root compression
     * Failed conservative treatment ≥ 6 weeks
   - Cervical myelopathy
   - Cervical instability
   - Trauma with instability
   
   C. Artificial Disc Replacement (CPT 22856, 22857, 22861, 22862)
   
   Covered for:
   - Single-level cervical or lumbar disease
   - Skeletally mature patients
   - No significant facet arthropathy
   - No osteoporosis
   - No prior fusion at adjacent level

3. JOINT REPLACEMENT

   A. Total Knee Replacement (CPT 27447)
   
   Medical Necessity Criteria:
   - Kellgren-Lawrence Grade 3 or 4 osteoarthritis
   - Failed conservative treatment ≥ 3 months:
     * Physical therapy
     * Weight management (if applicable)
     * NSAIDs or analgesics
     * Intra-articular injections
   - Significant functional limitation
   - Pain not controlled with conservative measures
   
   B. Total Hip Replacement (CPT 27130)
   
   Medical Necessity Criteria:
   - Documented hip pathology (OA, AVN, fracture)
   - Failed conservative treatment (unless acute fracture)
   - Functional limitation
   - Pain affecting quality of life
   
   C. Shoulder Replacement (CPT 23472, 23473, 23474)
   
   Medical Necessity Criteria:
   - Severe glenohumeral arthritis
   - Failed conservative treatment
   - Significant pain and functional limitation
   - Reverse total shoulder: Rotator cuff arthropathy or massive irreparable cuff tear

PRIOR AUTHORIZATION SUBMISSION

Submit via:
- Availity (preferred)
- Aetna Provider Portal
- Fax: 1-860-754-5844

Required Documentation:
- Clinical notes supporting medical necessity
- Imaging reports
- Conservative treatment records
- Specialist consultations
- Psychological evaluation (when required)

Turnaround Times:
- Urgent: 72 hours
- Standard: 15 calendar days

APPEALS:
First-level appeal within 180 days
Peer-to-peer review available
External review after internal appeal exhausted

CONTACT:
Prior Authorization: 1-800-624-0756
Provider Services: 1-800-624-0756
Clinical Policy Bulletins: https://www.aetna.com/cpb""",
            source_url="https://www.aetna.com/cpb",
            last_updated=today,
            version="2024.12.1"
        ),
        
        PolicyDocument(
            payer_id="AETNA_FL",
            payer_name="Aetna Florida",
            policy_type="utilization_review",
            policy_title="Utilization Management Program Guidelines",
            policy_number="UM-2024-001",
            effective_date="2024-01-01",
            content="""AETNA UTILIZATION MANAGEMENT PROGRAM
Policy Number: UM-2024-001
Effective Date: January 1, 2024

UTILIZATION MANAGEMENT OVERVIEW

Aetna's Utilization Management (UM) program ensures members receive
medically necessary, appropriate care in the most cost-effective setting.

1. PRECERTIFICATION (PRIOR AUTHORIZATION)

   Services Requiring Precertification:
   
   A. Inpatient Services:
      - All elective admissions
      - Skilled nursing facility admissions
      - Inpatient rehabilitation
      - Long-term acute care
      - Behavioral health admissions
   
   B. Outpatient Services:
      - Advanced imaging (MRI, CT, PET)
      - Outpatient surgery (select procedures)
      - Radiation therapy
      - Infusion therapy
      - Sleep studies
      - Genetic testing
   
   C. Specialty Services:
      - Transplant evaluations and procedures
      - Bariatric surgery
      - Spinal surgery
      - Joint replacement
      - Cardiac procedures
   
   D. Durable Medical Equipment:
      - Power wheelchairs
      - CPAP/BiPAP
      - Home oxygen
      - Prosthetics over $1,000
   
   E. Medications:
      - Specialty medications
      - Medications requiring step therapy
      - High-cost medications

2. CONCURRENT REVIEW

   Purpose: Monitor ongoing inpatient stays for continued medical necessity
   
   Process:
   - Initial authorization for estimated length of stay
   - Concurrent review at defined intervals
   - Extension requests as needed
   - Discharge planning coordination
   
   Review Criteria:
   - InterQual or MCG criteria
   - Aetna clinical policies
   - Physician reviewer judgment
   
   Notification Requirements:
   - Facility must notify Aetna of admission within 24 hours
   - Updates required for significant clinical changes
   - Discharge notification required

3. RETROSPECTIVE REVIEW

   When Performed:
   - Emergency admissions
   - Services provided without prior authorization
   - Claims review
   
   Timeframe:
   - Submit within 90 days of discharge/service
   - Decision within 30 calendar days
   
   Documentation Required:
   - Complete medical records
   - Explanation for lack of prior authorization
   - Clinical justification

4. CASE MANAGEMENT

   Eligibility:
   - Complex medical conditions
   - Multiple comorbidities
   - High-cost cases
   - Transplant patients
   - Catastrophic injuries
   
   Services Provided:
   - Care coordination
   - Discharge planning
   - Resource identification
   - Patient education
   - Provider communication

5. CLINICAL CRITERIA

   Aetna uses the following criteria sources:
   
   A. InterQual:
      - Acute care
      - Subacute care
      - Rehabilitation
      - Behavioral health
   
   B. MCG (Milliman Care Guidelines):
      - Select services
      - Ambulatory care
   
   C. Aetna Clinical Policy Bulletins:
      - Procedure-specific criteria
      - Technology assessments
      - Experimental/investigational determinations
   
   D. Hayes Medical Technology Directory:
      - Emerging technology review

6. APPEAL RIGHTS

   First-Level Appeal:
   - File within 180 days of adverse determination
   - Submit additional clinical information
   - Peer-to-peer review available
   - Decision within 30 days (post-service) or 15 days (pre-service)
   
   Second-Level Appeal:
   - File within 60 days of first-level decision
   - Reviewed by physician not involved in original decision
   - Decision within 30 days
   
   External Review:
   - Available after exhausting internal appeals
   - Independent Review Organization (IRO)
   - Decision binding on Aetna
   
   Expedited Appeals:
   - Available for urgent situations
   - Decision within 72 hours
   - Concurrent with external review if needed

CONTACT INFORMATION:
Precertification: 1-800-624-0756
Case Management: 1-800-624-0756
Appeals: 1-800-624-0756
Provider Portal: https://www.aetna.com/providers""",
            source_url="https://www.aetna.com/providers/um",
            last_updated=today,
            version="2024.12.1"
        ),
        
        PolicyDocument(
            payer_id="AETNA_FL",
            payer_name="Aetna Florida",
            policy_type="appeal_guidelines",
            policy_title="Provider Appeals Process and Guidelines",
            policy_number="APP-2024-001",
            effective_date="2024-01-01",
            content="""AETNA PROVIDER APPEALS PROCESS
Policy Number: APP-2024-001
Effective Date: January 1, 2024

APPEAL RIGHTS AND PROCEDURES

1. TYPES OF APPEALS

   A. Medical Necessity Appeals:
      - Challenge denial based on medical necessity criteria
      - Requires clinical documentation supporting necessity
      - Peer-to-peer review available
   
   B. Administrative Appeals:
      - Challenge denial based on administrative reasons
      - Examples: timely filing, authorization issues, coding
      - May not require clinical documentation
   
   C. Payment Appeals:
      - Challenge payment amount or methodology
      - Requires documentation of correct payment
      - Contract reference may be needed

2. FIRST-LEVEL APPEAL PROCESS

   Timeframe to File: 180 calendar days from date of denial
   
   How to Submit:
   - Availity Portal (preferred)
   - Aetna Provider Portal
   - Fax: 1-860-754-5844
   - Mail: Aetna Appeals, P.O. Box 14079, Lexington, KY 40512
   
   Required Information:
   - Member ID and date of birth
   - Claim number or authorization reference
   - Date(s) of service
   - Provider NPI and Tax ID
   - Detailed explanation of appeal
   - Supporting clinical documentation
   - Relevant medical literature (if applicable)
   
   Decision Timeframe:
   - Pre-service: 15 calendar days
   - Post-service: 30 calendar days
   - Urgent: 72 hours

3. PEER-TO-PEER REVIEW

   Availability:
   - Medical necessity denials
   - Must request within 10 business days of denial
   
   How to Request:
   - Call Provider Services: 1-800-624-0756
   - Request peer-to-peer review
   - Schedule with Aetna Medical Director
   
   Preparation:
   - Have complete medical records available
   - Be prepared to discuss clinical rationale
   - Reference specific criteria not met
   - Provide additional information if available
   
   Outcome:
   - Immediate decision in some cases
   - Written determination within 5 business days

4. SECOND-LEVEL APPEAL

   Eligibility: After first-level appeal denial
   
   Timeframe to File: 60 calendar days from first-level decision
   
   Process:
   - Submit written request for second-level review
   - Include new information if available
   - Reviewed by physician not involved in prior decisions
   
   Decision Timeframe:
   - Pre-service: 15 calendar days
   - Post-service: 30 calendar days

5. EXTERNAL REVIEW (INDEPENDENT REVIEW)

   Eligibility:
   - After exhausting internal appeals
   - Medical necessity or experimental/investigational denials
   - Not available for administrative or payment disputes
   
   How to Request:
   - Submit written request to Aetna
   - Aetna forwards to Independent Review Organization (IRO)
   
   Timeframe:
   - Standard: 45 calendar days
   - Expedited: 72 hours (for urgent cases)
   
   IRO Decision:
   - Final and binding on Aetna
   - Member may have additional rights under state law

6. EXPEDITED APPEALS

   Criteria:
   - Imminent and serious threat to health
   - Continued hospital stay
   - Time-sensitive treatment
   
   How to Request:
   - Call Provider Services: 1-800-624-0756
   - State "urgent appeal" and clinical justification
   - Fax supporting documentation immediately
   
   Decision: Within 72 hours

7. APPEAL TIPS FOR SUCCESS

   DO:
   - Submit complete documentation with initial appeal
   - Reference specific denial reason and criteria
   - Include peer-reviewed literature if applicable
   - Request peer-to-peer for complex cases
   - Meet all filing deadlines
   - Follow up on pending appeals
   
   DON'T:
   - Submit duplicate appeals
   - Miss filing deadlines
   - Submit without addressing denial reason
   - Ignore requests for additional information

8. COMMON DENIAL REASONS AND RESPONSES

   A. "Not Medically Necessary"
      Response: Provide documentation showing patient meets criteria
      Include: Clinical notes, test results, treatment history
   
   B. "Experimental/Investigational"
      Response: Provide peer-reviewed literature supporting efficacy
      Include: Clinical trials, FDA approvals, specialty society guidelines
   
   C. "Alternative Treatment Available"
      Response: Document why alternatives are not appropriate
      Include: Prior treatment failures, contraindications
   
   D. "Documentation Insufficient"
      Response: Provide complete medical records
      Include: All relevant clinical documentation

CONTACT INFORMATION:
Appeals Department: 1-800-624-0756
Appeals Fax: 1-860-754-5844
Provider Portal: https://www.aetna.com/providers
Appeals Status: Check via provider portal or call""",
            source_url="https://www.aetna.com/providers/appeals",
            last_updated=today,
            version="2024.12.1"
        ),
        
        PolicyDocument(
            payer_id="MEDICARE",
            payer_name="Medicare (CMS)",
            policy_type="national_coverage_determination",
            policy_title="National Coverage Determination - Total Knee Arthroplasty",
            policy_number="NCD-150.8",
            effective_date="2024-01-01",
            content="""MEDICARE NATIONAL COVERAGE DETERMINATION
Policy Number: NCD-150.8
Effective Date: January 1, 2024
CMS Manual Section: Medicare National Coverage Determinations Manual, Chapter 1, Part 2

TOTAL KNEE ARTHROPLASTY (TKA) - CPT 27447

1. COVERAGE INDICATIONS
   Medicare covers total knee arthroplasty when performed for the following indications:
   
   A. Primary Indications:
      - Severe osteoarthritis with joint space narrowing
      - Rheumatoid arthritis with joint destruction
      - Post-traumatic arthritis
      - Avascular necrosis of the knee
      - Failed previous knee surgery (revision TKA)
   
   B. Clinical Criteria:
      - Significant pain limiting activities of daily living
      - Radiographic evidence of joint destruction (Kellgren-Lawrence Grade 3-4)
      - Failed conservative treatment for minimum 3 months:
        * Physical therapy
        * Anti-inflammatory medications
        * Intra-articular injections
      - Functional limitation documented by validated outcome measure

2. LIMITATIONS AND EXCLUSIONS
   
   A. Not Covered:
      - Prophylactic knee replacement without documented pathology
      - Cosmetic indications
      - Patients who cannot participate in rehabilitation
   
   B. Conditional Coverage:
      - BMI > 40: Requires documentation of weight management program
      - Active infection: Must be resolved prior to surgery
      - Uncontrolled diabetes: HbA1c must be < 8.0%

3. DOCUMENTATION REQUIREMENTS
   
   Required for all TKA claims:
   - History and physical examination
   - Radiographic imaging (X-ray within 6 months)
   - Documentation of conservative treatment failure
   - Functional assessment scores (WOMAC, KOOS, or equivalent)
   - Surgical operative report
   - Anesthesia records
   
4. BILLING AND CODING
   
   Primary CPT Codes:
   - 27447: Total knee arthroplasty
   - 27486: Revision of total knee arthroplasty, one component
   - 27487: Revision of total knee arthroplasty, all components
   
   Required ICD-10 Codes:
   - M17.11/M17.12: Primary osteoarthritis, right/left knee
   - M05.x: Rheumatoid arthritis
   - M87.x: Osteonecrosis
   
5. APPEALS PROCESS
   
   Level 1 - Redetermination:
   - File within 120 days of initial determination
   - Submit to Medicare Administrative Contractor (MAC)
   - Decision within 60 days
   
   Level 2 - Reconsideration:
   - File within 180 days of redetermination
   - Submit to Qualified Independent Contractor (QIC)
   - Decision within 60 days
   
   Level 3 - Administrative Law Judge (ALJ):
   - File within 60 days of reconsideration
   - Amount in controversy must meet threshold ($180 for 2024)
   - Hearing scheduled within 90 days
   
   Level 4 - Medicare Appeals Council:
   - File within 60 days of ALJ decision
   - Review of ALJ decision
   
   Level 5 - Federal District Court:
   - File within 60 days of Appeals Council decision
   - Amount in controversy must meet threshold ($1,840 for 2024)

CONTACT INFORMATION:
Medicare Administrative Contractor: Check cms.gov for your region
Medicare Appeals: 1-800-MEDICARE (1-800-633-4227)
CMS Website: https://www.cms.gov/medicare-coverage-database""",
            source_url="https://www.cms.gov/medicare-coverage-database/details/ncd-details.aspx",
            last_updated=today,
            version="2024.12.1"
        ),
        
        PolicyDocument(
            payer_id="MEDICARE",
            payer_name="Medicare (CMS)",
            policy_type="local_coverage_determination",
            policy_title="Local Coverage Determination - Advanced Diagnostic Imaging",
            policy_number="LCD-L35074",
            effective_date="2024-01-01",
            content="""MEDICARE LOCAL COVERAGE DETERMINATION
Policy Number: LCD-L35074
Effective Date: January 1, 2024
Contractor: First Coast Service Options (Florida MAC)

ADVANCED DIAGNOSTIC IMAGING - MRI, CT, PET

1. MRI COVERAGE CRITERIA

   A. BRAIN MRI (CPT 70551-70553)
      
      Covered Indications:
      - Suspected intracranial neoplasm
      - Multiple sclerosis diagnosis or monitoring
      - Stroke evaluation (acute or follow-up)
      - Seizure disorder evaluation
      - Headache with neurological deficits
      - Dementia evaluation
      - Pituitary disorders
      - Acoustic neuroma evaluation
      
      Documentation Required:
      - Clinical indication and symptoms
      - Relevant neurological examination findings
      - Prior imaging results if applicable
      
   B. SPINE MRI (CPT 72141-72158)
      
      Covered Indications:
      - Radiculopathy with failed conservative treatment (6 weeks)
      - Suspected spinal cord compression
      - Cauda equina syndrome (emergent)
      - Post-operative evaluation
      - Suspected infection or tumor
      - Trauma with neurological deficit
      
      Not Covered:
      - Routine low back pain without red flags
      - Screening without clinical indication
      
   C. EXTREMITY MRI (CPT 73218-73223, 73718-73723)
      
      Covered Indications:
      - Suspected ligament or tendon tear
      - Bone tumor evaluation
      - Osteomyelitis
      - Avascular necrosis
      - Joint effusion with suspected internal derangement

2. CT SCAN COVERAGE CRITERIA

   A. HEAD CT (CPT 70450-70470)
      
      Covered Indications:
      - Acute head trauma
      - Acute stroke evaluation
      - Suspected intracranial hemorrhage
      - Altered mental status
      - New onset seizure
      
   B. CHEST CT (CPT 71250-71275)
      
      Covered Indications:
      - Lung cancer screening (per USPSTF guidelines)
      - Pulmonary embolism evaluation
      - Lung nodule follow-up
      - Staging of known malignancy
      - Interstitial lung disease evaluation
      
   C. ABDOMINAL CT (CPT 74150-74178)
      
      Covered Indications:
      - Acute abdominal pain
      - Suspected appendicitis
      - Kidney stone evaluation
      - Staging of malignancy
      - Abscess or infection evaluation

3. PET SCAN COVERAGE CRITERIA (CPT 78811-78816)

   Covered Indications:
   - Oncologic staging and restaging
   - Solitary pulmonary nodule evaluation
   - Myocardial viability assessment
   - Refractory seizure evaluation
   - Dementia differential diagnosis (FDG-PET)
   
   Prior Authorization: REQUIRED for all PET scans
   
   Documentation Required:
   - Pathology report (for oncologic indications)
   - Prior imaging results
   - Clinical staging information
   - Treatment plan

4. FREQUENCY LIMITATIONS

   - Repeat imaging within 12 months requires documentation of:
     * Change in clinical status
     * New symptoms
     * Treatment response evaluation
     * Surveillance per established guidelines

APPEALS PROCESS:
Follow standard Medicare appeals process (5 levels)
LCD-specific appeals should reference this LCD number

CONTACT INFORMATION:
First Coast Service Options: 1-888-664-4112
Provider Portal: https://medicare.fcso.com
LCD Questions: MedicalPolicy@fcso.com""",
            source_url="https://www.cms.gov/medicare-coverage-database/details/lcd-details.aspx",
            last_updated=today,
            version="2024.12.1"
        ),
        
        PolicyDocument(
            payer_id="MEDICARE",
            payer_name="Medicare (CMS)",
            policy_type="medicare_benefit_policy",
            policy_title="Medicare Benefit Policy Manual - Inpatient Hospital Services",
            policy_number="MBP-CH1-2024",
            effective_date="2024-01-01",
            content="""MEDICARE BENEFIT POLICY MANUAL
Chapter 1: Inpatient Hospital Services
Effective Date: January 1, 2024

1. INPATIENT ADMISSION CRITERIA

   A. Two-Midnight Rule:
      Medicare Part A covers inpatient hospital services when:
      - Physician expects patient to require hospital care spanning at least 2 midnights
      - Admission is based on complex medical factors
      - Documentation supports medical necessity
      
   B. Exceptions to Two-Midnight Rule:
      - Inpatient-only procedures (per CMS list)
      - Death or transfer before 2 midnights
      - Unforeseen circumstances
      - Clinical judgment with documentation
      
   C. Observation vs. Inpatient:
      - Observation: Outpatient status, typically < 24 hours
      - Inpatient: Requires formal admission order
      - Patient status affects Part A vs. Part B billing

2. COVERED INPATIENT SERVICES

   A. Room and Board:
      - Semi-private room (2-4 beds)
      - Private room if medically necessary
      - Meals and special diets
      
   B. Nursing Services:
      - General nursing care
      - Skilled nursing services
      - Intensive care nursing
      
   C. Ancillary Services:
      - Laboratory tests
      - Diagnostic imaging
      - Operating room
      - Recovery room
      - Drugs and biologicals
      - Medical supplies
      - Appliances and equipment
      
   D. Other Services:
      - Physical therapy
      - Occupational therapy
      - Speech-language pathology
      - Social services
      - Respiratory therapy

3. MEDICAL NECESSITY DOCUMENTATION

   Required Elements:
   - Admitting diagnosis with ICD-10 code
   - History of present illness
   - Physical examination findings
   - Diagnostic test results
   - Treatment plan
   - Expected length of stay
   - Physician certification of medical necessity
   
   Physician Certification:
   - Required for all admissions
   - Must be completed within 1 working day of admission
   - Recertification required at intervals per condition

4. UTILIZATION REVIEW

   A. Admission Review:
      - Concurrent review by UR committee
      - Criteria-based screening
      - Physician advisor review for questionable cases
      
   B. Continued Stay Review:
      - Periodic review of ongoing necessity
      - Documentation of continued medical need
      - Discharge planning assessment
      
   C. Discharge Review:
      - Appropriate discharge disposition
      - Post-acute care needs assessment
      - Patient/family education

5. BILLING AND REIMBURSEMENT

   A. DRG Payment System:
      - Prospective payment based on diagnosis
      - Includes all covered services
      - Outlier payments for exceptionally costly cases
      
   B. Cost Sharing:
      - Part A deductible: $1,632 (2024)
      - Days 1-60: $0 coinsurance
      - Days 61-90: $408/day coinsurance
      - Lifetime reserve days: $816/day coinsurance

APPEALS:
Follow standard Medicare appeals process
Admission denials may be appealed through QIO

CONTACT INFORMATION:
Medicare: 1-800-MEDICARE
QIO for Florida: KEPRO 1-888-317-0751
CMS Manual: https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals""",
            source_url="https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals/Downloads/bp102c01.pdf",
            last_updated=today,
            version="2024.12.1"
        ),
        
        PolicyDocument(
            payer_id="UNITED",
            payer_name="United Healthcare",
            policy_type="medical_policy",
            policy_title="Medical Policy - Orthopedic Surgery Prior Authorization",
            policy_number="UHC-ORTHO-2024-001",
            effective_date="2024-01-01",
            content="""UNITED HEALTHCARE MEDICAL POLICY
Policy Number: UHC-ORTHO-2024-001
Effective Date: January 1, 2024
Last Reviewed: December 1, 2024

ORTHOPEDIC SURGERY PRIOR AUTHORIZATION REQUIREMENTS

1. TOTAL JOINT REPLACEMENT

   A. Total Knee Arthroplasty (CPT 27447)
      Prior Authorization: REQUIRED
      
      Medical Necessity Criteria:
      - Documented osteoarthritis with Kellgren-Lawrence Grade 3 or 4
      - Significant functional limitation (WOMAC score > 39)
      - Failed conservative treatment for minimum 3 months:
        * Physical therapy (minimum 6 weeks, 12 sessions)
        * NSAIDs or other anti-inflammatory medications (minimum 6 weeks)
        * At least one intra-articular injection (corticosteroid or viscosupplementation)
      - BMI < 40 (or documented weight management if BMI 40-45)
      - No active infection
      - Medically optimized for surgery (cardiac clearance if indicated)
      
      Required Documentation:
      - Weight-bearing X-rays within 6 months
      - Physical therapy notes with functional outcomes
      - Medication history
      - WOMAC or KOOS functional assessment
      - Surgical plan
      
      Turnaround Time: 5 business days standard, 72 hours urgent
      
   B. Total Hip Arthroplasty (CPT 27130)
      Prior Authorization: REQUIRED
      
      Medical Necessity Criteria:
      - Documented hip osteoarthritis, avascular necrosis, or fracture
      - Failed conservative treatment for minimum 3 months (unless acute fracture)
      - Significant pain and functional limitation
      - Harris Hip Score < 70
      
      Required Documentation:
      - Hip X-rays or MRI within 6 months
      - Conservative treatment documentation
      - Harris Hip Score or equivalent functional assessment
      - Surgical plan

2. SPINE SURGERY

   A. Lumbar Fusion (CPT 22612, 22630, 22633)
      Prior Authorization: REQUIRED
      
      Medical Necessity Criteria:
      - Documented spinal instability, spondylolisthesis (Grade 2+), or degenerative disc disease
      - Failed conservative treatment for minimum 6 months:
        * Physical therapy (minimum 12 weeks)
        * Pain management (medications, injections)
        * At least 2 epidural steroid injections (if appropriate)
      - Imaging correlation with clinical symptoms
      - Psychological evaluation for chronic pain patients
      - No secondary gain issues
      
      Required Documentation:
      - MRI or CT within 6 months
      - Physical therapy records
      - Pain management records
      - Psychological evaluation
      - Surgical plan with expected outcomes
      
   B. Cervical Fusion (CPT 22551, 22552)
      Prior Authorization: REQUIRED
      
      Medical Necessity Criteria:
      - Documented cervical radiculopathy or myelopathy
      - Imaging correlation (MRI showing nerve compression)
      - Failed conservative treatment for 6-12 weeks (unless myelopathy)
      - Progressive neurological deficit requires urgent evaluation

3. ARTHROSCOPIC PROCEDURES

   A. Knee Arthroscopy (CPT 29881)
      Prior Authorization: REQUIRED for non-traumatic indications
      
      Medical Necessity Criteria:
      - Mechanical symptoms (locking, catching, giving way)
      - MRI confirmation of meniscal pathology
      - Failed conservative treatment for 6 weeks
      - Age consideration: Patients > 50 must have mechanical symptoms
      
      NOT COVERED:
      - Arthroscopic debridement for osteoarthritis alone
      - Lavage without specific pathology
      
   B. Shoulder Arthroscopy (CPT 29827)
      Prior Authorization: REQUIRED
      
      Medical Necessity Criteria:
      - Documented rotator cuff tear (MRI confirmed)
      - Failed conservative treatment for 6 weeks
      - Functional limitation affecting work or ADLs

4. APPEAL PROCESS

   First Level Appeal:
   - Submit within 180 days of denial
   - Include additional clinical documentation
   - Peer-to-peer review available
   - Decision within 30 days (15 days urgent)
   
   Second Level Appeal:
   - Submit within 60 days of first level decision
   - External review by independent organization
   - Decision within 45 days
   
   Expedited Appeal:
   - Available for urgent/emergent situations
   - Decision within 72 hours

CONTACT INFORMATION:
Prior Authorization: 1-866-889-8054
Provider Portal: https://www.uhcprovider.com
Fax for PA: 1-866-889-8054
Peer-to-Peer: 1-866-889-8054 (option 2)""",
            source_url="https://www.uhcprovider.com/medical-policies",
            last_updated=today,
            version="2024.12.1"
        ),
        
        PolicyDocument(
            payer_id="UNITED",
            payer_name="United Healthcare",
            policy_type="prior_auth",
            policy_title="Prior Authorization List - High-Cost Drugs and Biologics",
            policy_number="UHC-DRUG-PA-2024",
            effective_date="2024-01-01",
            content="""UNITED HEALTHCARE PRIOR AUTHORIZATION
Policy Number: UHC-DRUG-PA-2024
Effective Date: January 1, 2024

HIGH-COST DRUGS AND BIOLOGICS REQUIRING PRIOR AUTHORIZATION

1. ONCOLOGY DRUGS

   A. Pembrolizumab (Keytruda) - J9271
      Prior Authorization: REQUIRED
      
      Covered Indications:
      - Non-small cell lung cancer (NSCLC) with PD-L1 expression ≥ 1%
      - Melanoma (unresectable or metastatic)
      - Head and neck squamous cell carcinoma
      - Classical Hodgkin lymphoma
      - Urothelial carcinoma
      - Microsatellite instability-high (MSI-H) cancers
      - Other FDA-approved indications
      
      Required Documentation:
      - Pathology report confirming diagnosis
      - PD-L1 testing results (where applicable)
      - Prior treatment history
      - ECOG performance status
      - Treatment plan from oncologist
      
      Quantity Limits: Per FDA-approved dosing
      
   B. Bevacizumab (Avastin) - J9035
      Prior Authorization: REQUIRED
      
      Covered Indications:
      - Metastatic colorectal cancer
      - Non-squamous NSCLC
      - Glioblastoma
      - Metastatic renal cell carcinoma
      - Cervical cancer
      - Ovarian, fallopian tube, or primary peritoneal cancer
      
      Required Documentation:
      - Pathology report
      - Staging information
      - Prior treatment history
      - Treatment plan
      
   C. Trastuzumab (Herceptin) - J9355
      Prior Authorization: REQUIRED
      
      Covered Indications:
      - HER2-positive breast cancer
      - HER2-positive metastatic gastric cancer
      
      Required Documentation:
      - HER2 testing results (IHC 3+ or FISH positive)
      - Pathology report
      - Treatment plan

2. AUTOIMMUNE/INFLAMMATORY DRUGS

   A. Adalimumab (Humira) - J0135
      Prior Authorization: REQUIRED
      
      Covered Indications:
      - Rheumatoid arthritis (after DMARD failure)
      - Psoriatic arthritis
      - Ankylosing spondylitis
      - Crohn's disease
      - Ulcerative colitis
      - Plaque psoriasis
      - Hidradenitis suppurativa
      - Uveitis
      - Juvenile idiopathic arthritis
      
      Step Therapy Required:
      - Must fail conventional DMARDs before biologics
      - Methotrexate trial required for RA (unless contraindicated)
      
      Required Documentation:
      - Diagnosis confirmation
      - Prior DMARD treatment history
      - Disease activity scores
      - TB screening results
      - Hepatitis B/C screening
      
   B. Infliximab (Remicade) - J1745
      Prior Authorization: REQUIRED
      
      Similar criteria to adalimumab
      Biosimilar preferred when available

3. SPECIALTY DRUGS - OTHER

   A. Eculizumab (Soliris) - J1300
      Prior Authorization: REQUIRED
      
      Covered Indications:
      - Paroxysmal nocturnal hemoglobinuria (PNH)
      - Atypical hemolytic uremic syndrome (aHUS)
      - Generalized myasthenia gravis
      - Neuromyelitis optica spectrum disorder
      
      Required Documentation:
      - Specialist confirmation of diagnosis
      - Laboratory confirmation
      - Meningococcal vaccination documentation
      - Treatment plan
      
   B. Ocrelizumab (Ocrevus) - J2350
      Prior Authorization: REQUIRED
      
      Covered Indications:
      - Relapsing forms of multiple sclerosis
      - Primary progressive multiple sclerosis
      
      Required Documentation:
      - MS diagnosis by neurologist
      - MRI results
      - Prior MS treatment history
      - JC virus antibody status

4. APPEAL PROCESS FOR DRUG DENIALS

   Expedited Review:
   - Available for urgent clinical situations
   - Decision within 24-72 hours
   
   Standard Appeal:
   - Submit within 180 days
   - Include peer-reviewed literature if off-label use
   - Peer-to-peer with medical director available
   
   External Review:
   - Available after internal appeals exhausted
   - Independent review organization

CONTACT INFORMATION:
Specialty Pharmacy PA: 1-800-711-4555
Provider Portal: https://www.uhcprovider.com
Fax for PA: 1-800-711-4560
Clinical Pharmacist Consultation: 1-800-711-4555 (option 3)""",
            source_url="https://www.uhcprovider.com/prior-auth-drugs",
            last_updated=today,
            version="2024.12.1"
        ),
        
        PolicyDocument(
            payer_id="UNITED",
            payer_name="United Healthcare",
            policy_type="appeal_procedures",
            policy_title="Provider Appeals and Grievances Guide",
            policy_number="UHC-APPEALS-2024",
            effective_date="2024-01-01",
            content="""UNITED HEALTHCARE APPEALS AND GRIEVANCES GUIDE
Policy Number: UHC-APPEALS-2024
Effective Date: January 1, 2024

1. TYPES OF APPEALS

   A. Pre-Service Appeals (Prior Authorization Denials):
      - Appeal before service is rendered
      - Standard: Decision within 30 days
      - Expedited: Decision within 72 hours
      
   B. Post-Service Appeals (Claim Denials):
      - Appeal after service is rendered
      - Standard: Decision within 30 days
      - Retrospective review of medical necessity
      
   C. Concurrent Appeals (Continued Stay):
      - Appeal during ongoing treatment
      - Expedited review required
      - Decision within 24 hours for urgent cases

2. APPEAL FILING REQUIREMENTS

   A. Timeframes:
      - Pre-service: Within 180 days of denial
      - Post-service: Within 180 days of denial
      - Expedited: Immediate for urgent situations
      
   B. Required Information:
      - Member ID and date of birth
      - Provider NPI and contact information
      - Date(s) of service
      - Procedure/diagnosis codes
      - Original denial reference number
      - Reason for appeal
      - Supporting clinical documentation
      
   C. Submission Methods:
      - Online: UHC Provider Portal
      - Fax: 1-866-889-8054
      - Mail: UHC Appeals, PO Box 30432, Salt Lake City, UT 84130

3. APPEAL LEVELS

   Level 1 - Internal Appeal:
   - Reviewed by clinical staff not involved in original decision
   - Peer-to-peer review available upon request
   - Decision within 30 days (standard) or 72 hours (expedited)
   
   Level 2 - Internal Appeal:
   - Reviewed by medical director
   - Additional documentation may be submitted
   - Decision within 30 days
   
   External Review:
   - Available after internal appeals exhausted
   - Independent Review Organization (IRO)
   - Binding decision
   - Decision within 45 days (standard) or 72 hours (expedited)

4. PEER-TO-PEER REVIEW

   Availability:
   - Available for all clinical denials
   - Must be requested within 10 business days of denial
   - Scheduled within 5 business days of request
   
   Process:
   - Treating physician speaks with UHC medical director
   - Opportunity to present additional clinical information
   - Decision communicated within 24 hours of call
   
   How to Request:
   - Call: 1-866-889-8054 (option 2)
   - Online: UHC Provider Portal
   - Include: Member ID, denial reference, preferred callback times

5. EXPEDITED APPEALS

   Criteria for Expedited Review:
   - Imminent and serious threat to health
   - Continued hospital stay at risk
   - Time-sensitive treatment
   - Potential for significant harm if delayed
   
   Process:
   - Call Provider Services: 1-866-889-8054
   - State "expedited appeal" and clinical justification
   - Fax supporting documentation immediately
   - Decision within 72 hours (24 hours for concurrent review)

6. COMMON DENIAL REASONS AND RESPONSES

   A. "Not Medically Necessary"
      Response Strategy:
      - Provide clinical documentation showing patient meets criteria
      - Include relevant clinical guidelines
      - Request peer-to-peer review
      
   B. "Experimental/Investigational"
      Response Strategy:
      - Provide peer-reviewed literature
      - Include FDA approvals or clearances
      - Reference specialty society guidelines
      
   C. "Out of Network"
      Response Strategy:
      - Document network inadequacy if applicable
      - Show no in-network provider available
      - Request single case agreement
      
   D. "Prior Authorization Not Obtained"
      Response Strategy:
      - Document emergency circumstances
      - Show timely notification attempt
      - Request retrospective authorization

7. APPEAL TIPS FOR SUCCESS

   DO:
   - Submit complete documentation with initial appeal
   - Reference specific denial reason and policy criteria
   - Include peer-reviewed literature for complex cases
   - Request peer-to-peer for clinical denials
   - Meet all filing deadlines
   - Follow up on pending appeals
   
   DON'T:
   - Submit duplicate appeals
   - Miss filing deadlines
   - Submit without addressing specific denial reason
   - Ignore requests for additional information

CONTACT INFORMATION:
Appeals Department: 1-866-889-8054
Appeals Fax: 1-866-889-8054
Provider Portal: https://www.uhcprovider.com
Appeals Status: Check via provider portal""",
            source_url="https://www.uhcprovider.com/appeals",
            last_updated=today,
            version="2024.12.1"
        ),
        
        PolicyDocument(
            payer_id="CIGNA",
            payer_name="Cigna Healthcare",
            policy_type="coverage_policy",
            policy_title="Coverage Policy - Advanced Imaging Services",
            policy_number="CGN-IMG-2024-001",
            effective_date="2024-01-01",
            content="""CIGNA HEALTHCARE COVERAGE POLICY
Policy Number: CGN-IMG-2024-001
Effective Date: January 1, 2024
Last Reviewed: December 1, 2024

ADVANCED IMAGING SERVICES - MRI, CT, PET

1. PRIOR AUTHORIZATION REQUIREMENTS

   Prior Authorization REQUIRED for:
   - All MRI studies
   - All CT studies (except emergency)
   - All PET/PET-CT studies
   - All nuclear medicine studies
   
   Prior Authorization NOT Required for:
   - Emergency/urgent imaging
   - Inpatient imaging
   - X-rays
   - Ultrasound
   - Mammography

2. MRI COVERAGE CRITERIA

   A. BRAIN MRI (CPT 70551-70553)
      
      Covered Indications:
      - Suspected brain tumor or metastatic disease
      - Multiple sclerosis (diagnosis or monitoring)
      - Stroke evaluation
      - Seizure disorder (new onset or refractory)
      - Headache with red flag symptoms
      - Dementia evaluation
      - Pituitary disorders
      - Acoustic neuroma
      - Trigeminal neuralgia
      
      Frequency Limits:
      - Initial diagnostic: No limit
      - Follow-up: Per clinical guidelines (typically 3-12 months)
      - MS monitoring: Per McDonald criteria
      
   B. SPINE MRI (CPT 72141-72158)
      
      Covered Indications:
      - Radiculopathy with failed conservative treatment (6 weeks)
      - Suspected spinal cord compression
      - Cauda equina syndrome (emergent)
      - Myelopathy
      - Post-operative evaluation
      - Suspected infection or tumor
      - Trauma with neurological deficit
      
      NOT Covered:
      - Routine low back pain without red flags
      - Screening without clinical indication
      - Repeat imaging without clinical change
      
   C. JOINT MRI (CPT 73221-73223, 73721-73723)
      
      Covered Indications:
      - Suspected ligament or tendon tear
      - Internal derangement with mechanical symptoms
      - Bone tumor evaluation
      - Osteomyelitis
      - Avascular necrosis
      - Pre-operative planning

3. CT SCAN COVERAGE CRITERIA

   A. HEAD CT (CPT 70450-70470)
      
      Covered Indications:
      - Acute head trauma
      - Acute stroke (initial evaluation)
      - Suspected intracranial hemorrhage
      - Altered mental status
      - New onset seizure
      - Sinusitis (after failed medical treatment)
      
   B. CHEST CT (CPT 71250-71275)
      
      Covered Indications:
      - Lung cancer screening (per USPSTF criteria)
      - Pulmonary embolism evaluation
      - Lung nodule follow-up (per Fleischner guidelines)
      - Staging of known malignancy
      - Interstitial lung disease
      - Mediastinal mass evaluation
      
   C. ABDOMINAL/PELVIC CT (CPT 74150-74178)
      
      Covered Indications:
      - Acute abdominal pain
      - Suspected appendicitis
      - Kidney stone evaluation
      - Staging of malignancy
      - Abscess or infection
      - Trauma evaluation

4. PET SCAN COVERAGE CRITERIA

   Prior Authorization: REQUIRED for all PET scans
   
   Covered Indications:
   - Oncologic staging and restaging (most solid tumors)
   - Solitary pulmonary nodule (> 8mm)
   - Lymphoma staging and response assessment
   - Melanoma staging (Stage III+)
   - Myocardial viability (after other testing)
   - Refractory seizure localization
   
   NOT Covered:
   - Screening without known or suspected malignancy
   - Routine surveillance without clinical indication
   - Prostate cancer (except PSMA PET for specific indications)

5. DOCUMENTATION REQUIREMENTS

   All imaging requests must include:
   - Clinical indication and symptoms
   - Relevant physical examination findings
   - Prior imaging results (if applicable)
   - Conservative treatment history (for musculoskeletal)
   - Ordering physician specialty
   
6. APPEAL PROCESS

   First Level Appeal:
   - Submit within 180 days of denial
   - Include additional clinical documentation
   - Peer-to-peer available
   - Decision within 30 days
   
   Second Level Appeal:
   - Submit within 60 days of first level decision
   - Medical director review
   - Decision within 30 days
   
   External Review:
   - Available after internal appeals exhausted
   - Independent review organization
   - Decision within 45 days

CONTACT INFORMATION:
Prior Authorization (eviCore): 1-888-693-3211
Provider Portal: https://www.cigna.com/providers
Fax for PA: 1-888-693-3210
Peer-to-Peer: 1-888-693-3211 (option 2)""",
            source_url="https://www.cigna.com/providers/coverage-policies",
            last_updated=today,
            version="2024.12.1"
        ),
        
        PolicyDocument(
            payer_id="CIGNA",
            payer_name="Cigna Healthcare",
            policy_type="prior_auth",
            policy_title="Prior Authorization Requirements - Surgical Procedures",
            policy_number="CGN-SURG-PA-2024",
            effective_date="2024-01-01",
            content="""CIGNA HEALTHCARE PRIOR AUTHORIZATION
Policy Number: CGN-SURG-PA-2024
Effective Date: January 1, 2024

SURGICAL PROCEDURES REQUIRING PRIOR AUTHORIZATION

1. ORTHOPEDIC SURGERY

   A. Total Joint Replacement
      
      Total Knee Arthroplasty (CPT 27447):
      Prior Authorization: REQUIRED
      
      Criteria:
      - Kellgren-Lawrence Grade 3-4 osteoarthritis
      - Failed conservative treatment ≥ 3 months:
        * Physical therapy (6+ weeks)
        * NSAIDs (6+ weeks)
        * At least one injection (steroid or viscosupplementation)
      - Functional limitation (WOMAC > 39 or equivalent)
      - BMI < 40 (or weight management program if 40-45)
      - Medically optimized
      
      Total Hip Arthroplasty (CPT 27130):
      Prior Authorization: REQUIRED
      
      Criteria:
      - Documented hip pathology (OA, AVN, fracture)
      - Failed conservative treatment ≥ 3 months
      - Significant functional limitation
      - Harris Hip Score < 70
      
   B. Spine Surgery
      
      Lumbar Fusion (CPT 22612, 22630, 22633):
      Prior Authorization: REQUIRED
      
      Criteria:
      - Documented instability, spondylolisthesis, or DDD
      - Failed conservative treatment ≥ 6 months
      - Physical therapy ≥ 12 weeks
      - At least 2 epidural injections (if appropriate)
      - Imaging correlation
      - Psychological evaluation (chronic pain)
      
      Cervical Fusion (CPT 22551, 22552):
      Prior Authorization: REQUIRED
      
      Criteria:
      - Documented radiculopathy or myelopathy
      - MRI showing nerve compression
      - Failed conservative treatment 6-12 weeks
      - Progressive deficit = urgent review
      
   C. Arthroscopy
      
      Knee Arthroscopy (CPT 29881):
      Prior Authorization: REQUIRED (non-traumatic)
      
      Criteria:
      - Mechanical symptoms (locking, catching)
      - MRI confirmation of pathology
      - Failed conservative treatment 6 weeks
      - NOT covered: OA debridement alone

2. BARIATRIC SURGERY

   Gastric Bypass (CPT 43644) / Sleeve Gastrectomy (CPT 43775):
   Prior Authorization: REQUIRED
   
   Criteria:
   - BMI ≥ 40, or BMI ≥ 35 with comorbidities
   - Documented obesity ≥ 5 years
   - Failed supervised weight loss program (6-12 months)
   - Psychological evaluation
   - Nutritional evaluation
   - No active substance abuse
   - Letter of medical necessity from surgeon
   
   Required Documentation:
   - Weight history (5+ years)
   - Diet program records
   - Psychological evaluation
   - Nutritional assessment
   - Medical clearances
   - Surgeon's letter

3. CARDIAC SURGERY

   CABG (CPT 33533-33536):
   Prior Authorization: REQUIRED (elective)
   
   Criteria:
   - Significant coronary artery disease on angiography
   - Failed or not candidate for PCI
   - Symptoms despite optimal medical therapy
   - Cardiac surgery evaluation
   
   TAVR (CPT 33361-33369):
   Prior Authorization: REQUIRED
   
   Criteria:
   - Severe aortic stenosis
   - High or prohibitive surgical risk
   - Heart team evaluation
   - Appropriate anatomy per imaging

4. COSMETIC VS. RECONSTRUCTIVE

   Reconstructive Surgery (Covered):
   - Post-mastectomy breast reconstruction
   - Functional rhinoplasty (breathing obstruction)
   - Panniculectomy (functional impairment)
   - Blepharoplasty (visual field obstruction)
   
   Cosmetic Surgery (NOT Covered):
   - Aesthetic procedures without functional indication
   - Elective body contouring
   - Cosmetic rhinoplasty

5. APPEAL PROCESS

   Standard Appeal:
   - File within 180 days
   - Include clinical documentation
   - Peer-to-peer available
   - Decision within 30 days
   
   Expedited Appeal:
   - Urgent clinical situations
   - Decision within 72 hours
   
   External Review:
   - After internal appeals exhausted
   - Independent organization
   - Binding decision

CONTACT INFORMATION:
Prior Authorization: 1-800-244-6224
Provider Portal: https://www.cigna.com/providers
Fax for PA: 1-859-410-3414
Peer-to-Peer: 1-800-244-6224 (option 3)""",
            source_url="https://www.cigna.com/providers/prior-auth",
            last_updated=today,
            version="2024.12.1"
        ),
        
        PolicyDocument(
            payer_id="CIGNA",
            payer_name="Cigna Healthcare",
            policy_type="appeal_guidelines",
            policy_title="Provider Appeals Process Guide",
            policy_number="CGN-APPEALS-2024",
            effective_date="2024-01-01",
            content="""CIGNA HEALTHCARE PROVIDER APPEALS GUIDE
Policy Number: CGN-APPEALS-2024
Effective Date: January 1, 2024

1. APPEAL TYPES

   A. Utilization Management Appeals:
      - Prior authorization denials
      - Concurrent review denials
      - Retrospective review denials
      
   B. Claims Appeals:
      - Payment disputes
      - Coding denials
      - Timely filing denials
      
   C. Administrative Appeals:
      - Credentialing issues
      - Contract disputes

2. FILING REQUIREMENTS

   Timeframes:
   - UM Appeals: 180 days from denial
   - Claims Appeals: 365 days from remittance
   - Expedited: Immediate for urgent situations
   
   Required Information:
   - Member ID and demographics
   - Provider NPI and contact info
   - Date(s) of service
   - Procedure and diagnosis codes
   - Denial reference number
   - Detailed reason for appeal
   - Supporting documentation
   
   Submission Methods:
   - Online: Cigna Provider Portal (preferred)
   - Fax: 1-859-410-3414
   - Mail: Cigna Appeals, PO Box 188011, Chattanooga, TN 37422

3. APPEAL LEVELS

   Level 1 - Initial Appeal:
   - Clinical review by qualified reviewer
   - Not involved in original decision
   - Decision within 30 days (standard)
   - Decision within 72 hours (expedited)
   
   Level 2 - Secondary Appeal:
   - Medical director review
   - Additional documentation accepted
   - Decision within 30 days
   
   External Review:
   - Independent Review Organization
   - Available after internal appeals
   - Binding decision
   - Decision within 45 days

4. PEER-TO-PEER REVIEW

   Availability:
   - All clinical denials eligible
   - Request within 10 business days of denial
   - Scheduled within 5 business days
   
   Process:
   - Treating physician speaks with Cigna medical director
   - Present additional clinical information
   - Real-time decision when possible
   - Written decision within 24 hours
   
   How to Request:
   - Call: 1-800-244-6224 (option 3)
   - Online: Provider Portal
   - Fax request with preferred times

5. EXPEDITED APPEALS

   Criteria:
   - Serious threat to life or health
   - Continued hospitalization
   - Time-sensitive treatment
   - Significant pain or functional impairment
   
   Process:
   - Call Provider Services immediately
   - State "expedited appeal"
   - Provide clinical justification
   - Fax documentation immediately
   - Decision within 72 hours (24 hours for concurrent)

6. DOCUMENTATION TIPS

   For Medical Necessity Appeals:
   - Complete medical records
   - Clinical notes supporting indication
   - Test results and imaging
   - Treatment history
   - Peer-reviewed literature (if applicable)
   
   For Coding Appeals:
   - Operative reports
   - Documentation supporting code selection
   - Modifier justification
   - Medical record excerpts

7. COMMON DENIAL REASONS

   A. "Not Medically Necessary"
      - Provide documentation meeting criteria
      - Include clinical guidelines
      - Request peer-to-peer
      
   B. "Experimental/Investigational"
      - Peer-reviewed literature
      - FDA approvals
      - Specialty society guidelines
      
   C. "Prior Authorization Required"
      - Document emergency circumstances
      - Show notification attempt
      - Request retrospective auth
      
   D. "Out of Network"
      - Document network inadequacy
      - Request single case agreement
      - Show no in-network option

CONTACT INFORMATION:
Appeals: 1-800-244-6224
Appeals Fax: 1-859-410-3414
Provider Portal: https://www.cigna.com/providers
Appeals Status: Check via portal or call""",
            source_url="https://www.cigna.com/providers/appeals",
            last_updated=today,
            version="2024.12.1"
        ),
        
        PolicyDocument(
            payer_id="TRICARE",
            payer_name="TRICARE (Military Health)",
            policy_type="tricare_policy_manual",
            policy_title="TRICARE Policy Manual - Covered Services",
            policy_number="TPM-2024-001",
            effective_date="2024-01-01",
            content="""TRICARE POLICY MANUAL
Chapter: Covered Services
Effective Date: January 1, 2024
Authority: 32 CFR 199

1. TRICARE PROGRAM OVERVIEW

   TRICARE Options:
   - TRICARE Prime: HMO-style managed care
   - TRICARE Select: PPO-style fee-for-service
   - TRICARE For Life: Medicare wraparound for retirees
   - TRICARE Reserve Select: For Selected Reserve members
   - TRICARE Young Adult: For adult children up to age 26
   
   Eligibility:
   - Active duty service members
   - Active duty family members
   - Retirees and their families
   - Survivors
   - Medal of Honor recipients

2. COVERED SERVICES

   A. Inpatient Hospital Services:
      - Room and board (semi-private)
      - Nursing services
      - Operating room
      - Anesthesia
      - Drugs and biologicals
      - Laboratory and radiology
      - Medical supplies
      - Rehabilitation services
      
   B. Outpatient Services:
      - Physician visits
      - Preventive care
      - Diagnostic testing
      - Outpatient surgery
      - Physical therapy
      - Mental health services
      - Durable medical equipment
      
   C. Prescription Drugs:
      - TRICARE Pharmacy Program
      - Military pharmacy (no cost)
      - Retail pharmacy (copay)
      - Mail order (preferred)
      - Specialty pharmacy

3. PRIOR AUTHORIZATION REQUIREMENTS

   Services Requiring Prior Authorization:
   - Inpatient admissions (non-emergency)
   - Skilled nursing facility
   - Inpatient rehabilitation
   - Home health care
   - Hospice care
   - Organ transplants
   - Certain surgical procedures
   - High-cost drugs
   - Durable medical equipment (> $3,000)
   
   How to Obtain Authorization:
   - Contact regional contractor
   - Submit clinical documentation
   - Decision within 5 business days (routine)
   - Decision within 24 hours (urgent)
   
   Emergency Admissions:
   - Notification within 24 hours
   - Retrospective review
   - No penalty for true emergencies

4. MEDICAL NECESSITY CRITERIA

   TRICARE uses evidence-based criteria:
   - InterQual criteria for admissions
   - MCG guidelines for procedures
   - TRICARE Policy Manual for specific services
   
   Documentation Requirements:
   - History and physical
   - Diagnostic test results
   - Treatment plan
   - Expected outcomes
   - Physician certification

5. REFERRAL REQUIREMENTS

   TRICARE Prime:
   - PCM referral required for specialty care
   - Self-referral allowed for:
     * Emergency care
     * Urgent care
     * Preventive care
     * Mental health (first 8 visits)
     * OB/GYN care
   
   TRICARE Select:
   - No referral required
   - Network providers preferred
   - Point-of-service option available

6. COST SHARING

   TRICARE Prime:
   - Active duty: No cost
   - Active duty family: Minimal copays
   - Retirees: Annual enrollment fee + copays
   
   TRICARE Select:
   - Annual deductible
   - Cost shares (percentage of allowed amount)
   - Catastrophic cap protection
   
   TRICARE For Life:
   - Medicare pays first
   - TRICARE pays Medicare cost sharing
   - No enrollment fee

7. APPEALS PROCESS

   Initial Determination:
   - Review by regional contractor
   - Decision within 60 days
   
   Reconsideration:
   - File within 90 days of initial decision
   - Additional documentation accepted
   - Decision within 60 days
   
   Formal Review:
   - File within 90 days of reconsideration
   - Hearing officer review
   - Decision within 90 days
   
   TRICARE Board of Appeals:
   - Final administrative appeal
   - File within 60 days of formal review
   - Board review and decision

CONTACT INFORMATION:
TRICARE East: Humana Military 1-800-444-5445
TRICARE West: Health Net Federal Services 1-844-866-9378
TRICARE Overseas: International SOS 1-877-678-1207
TRICARE Website: https://www.tricare.mil""",
            source_url="https://www.tricare.mil/CoveredServices",
            last_updated=today,
            version="2024.12.1"
        ),
        
        PolicyDocument(
            payer_id="TRICARE",
            payer_name="TRICARE (Military Health)",
            policy_type="prior_auth",
            policy_title="Prior Authorization Guide for Providers",
            policy_number="TPM-PA-2024",
            effective_date="2024-01-01",
            content="""TRICARE PRIOR AUTHORIZATION GUIDE
Policy Number: TPM-PA-2024
Effective Date: January 1, 2024

1. SERVICES REQUIRING PRIOR AUTHORIZATION

   A. Inpatient Services:
      - All non-emergency admissions
      - Skilled nursing facility
      - Inpatient rehabilitation facility
      - Long-term acute care hospital
      - Inpatient mental health (after initial days)
      - Substance abuse treatment (residential)
      
   B. Outpatient Services:
      - Advanced imaging (MRI, CT, PET)
      - Outpatient surgery (select procedures)
      - Radiation therapy
      - Dialysis (initial authorization)
      - Home health care
      - Hospice care
      
   C. Surgical Procedures:
      - Bariatric surgery
      - Cosmetic/reconstructive surgery
      - Organ transplants
      - Joint replacement (select cases)
      - Spine surgery
      
   D. Durable Medical Equipment:
      - Items > $3,000
      - Power wheelchairs
      - CPAP/BiPAP
      - Prosthetics
      - Custom orthotics
      
   E. Prescription Drugs:
      - Non-formulary medications
      - Specialty drugs
      - Compound medications
      - Growth hormone
      - Oncology drugs

2. AUTHORIZATION PROCESS

   A. How to Request:
      - Online: Provider portal (preferred)
      - Phone: Regional contractor
      - Fax: Authorization request form
      
   B. Required Information:
      - Beneficiary information (SSN, DOB)
      - Provider information (NPI, contact)
      - Service requested (CPT, ICD-10)
      - Clinical documentation
      - Medical necessity justification
      
   C. Turnaround Times:
      - Routine: 5 business days
      - Urgent: 24 hours
      - Emergency: Retrospective (notify within 24 hours)

3. MEDICAL NECESSITY CRITERIA

   TRICARE uses nationally recognized criteria:
   - InterQual for inpatient admissions
   - MCG for outpatient procedures
   - TRICARE Policy Manual for specific services
   
   Key Elements:
   - Diagnosis supports service
   - Service is appropriate treatment
   - Less intensive alternatives considered
   - Expected to improve condition
   - Provided at appropriate level of care

4. SPECIFIC PROCEDURE REQUIREMENTS

   A. Joint Replacement:
      - Documented arthritis (imaging)
      - Failed conservative treatment (3 months)
      - Functional limitation documented
      - Medical optimization
      
   B. Spine Surgery:
      - Imaging correlation with symptoms
      - Failed conservative treatment (6 months)
      - Physical therapy completed
      - Pain management attempted
      
   C. Bariatric Surgery:
      - BMI ≥ 40 or ≥ 35 with comorbidities
      - Failed weight loss program (6 months)
      - Psychological evaluation
      - Nutritional evaluation
      - No contraindications
      
   D. Advanced Imaging:
      - Clinical indication documented
      - Prior imaging reviewed
      - Conservative treatment (if applicable)
      - Appropriate for diagnosis

5. EMERGENCY AND URGENT CARE

   Emergency Care:
   - No prior authorization required
   - Notify contractor within 24 hours of admission
   - Retrospective review for medical necessity
   - True emergencies always covered
   
   Urgent Care:
   - Expedited authorization (24 hours)
   - Clinical justification required
   - May proceed pending authorization

6. APPEALS PROCESS

   Reconsideration:
   - File within 90 days of denial
   - Submit additional documentation
   - Peer-to-peer available
   - Decision within 30 days
   
   Formal Appeal:
   - File within 90 days of reconsideration
   - Hearing officer review
   - Written decision
   
   Board Appeal:
   - Final administrative level
   - File within 60 days
   - Board review

7. PROVIDER TIPS

   DO:
   - Submit complete documentation initially
   - Use correct codes and modifiers
   - Include clinical notes supporting necessity
   - Follow up on pending authorizations
   - Request peer-to-peer for denials
   
   DON'T:
   - Perform services without authorization
   - Submit incomplete requests
   - Miss appeal deadlines
   - Ignore denial reasons

CONTACT INFORMATION:
TRICARE East (Humana Military):
- Prior Auth: 1-800-444-5445
- Fax: 1-800-357-3498
- Portal: https://www.humanamilitary.com

TRICARE West (Health Net):
- Prior Auth: 1-844-866-9378
- Fax: 1-844-722-0443
- Portal: https://www.tricare-west.com""",
            source_url="https://www.tricare.mil/providers/prior-auth",
            last_updated=today,
            version="2024.12.1"
        ),
        
        PolicyDocument(
            payer_id="TRICARE",
            payer_name="TRICARE (Military Health)",
            policy_type="appeals_process",
            policy_title="TRICARE Appeals and Grievances Process",
            policy_number="TPM-APPEALS-2024",
            effective_date="2024-01-01",
            content="""TRICARE APPEALS AND GRIEVANCES PROCESS
Policy Number: TPM-APPEALS-2024
Effective Date: January 1, 2024
Authority: 32 CFR 199.10

1. TYPES OF APPEALS

   A. Initial Determination Appeal:
      - Coverage decisions
      - Medical necessity denials
      - Prior authorization denials
      - Claims payment disputes
      
   B. Grievances:
      - Quality of care concerns
      - Access to care issues
      - Provider behavior
      - Administrative issues

2. APPEAL LEVELS

   Level 1 - Reconsideration:
   - First level of appeal
   - File within 90 days of initial determination
   - Reviewed by contractor (different reviewer)
   - Decision within 60 days
   - Additional documentation accepted
   
   Level 2 - Formal Review:
   - File within 90 days of reconsideration
   - Independent hearing officer
   - May request in-person or telephonic hearing
   - Decision within 90 days
   - Written findings of fact
   
   Level 3 - TRICARE Board of Appeals:
   - Final administrative appeal
   - File within 60 days of formal review
   - Board review of record
   - Decision is final for TRICARE

3. FILING REQUIREMENTS

   Required Information:
   - Beneficiary name and SSN
   - Sponsor information
   - Date(s) of service
   - Provider information
   - Denial reference number
   - Specific reason for appeal
   - Supporting documentation
   
   Submission Methods:
   - Online: Regional contractor portal
   - Mail: Address on denial letter
   - Fax: Number on denial letter
   
   Timeframes:
   - Reconsideration: 90 days from denial
   - Formal Review: 90 days from reconsideration
   - Board Appeal: 60 days from formal review

4. EXPEDITED APPEALS

   Criteria:
   - Serious threat to life or health
   - Continued hospitalization at risk
   - Time-sensitive treatment
   - Significant pain or impairment
   
   Process:
   - Contact contractor immediately
   - State "expedited appeal"
   - Provide clinical justification
   - Decision within 72 hours
   
   For Concurrent Review:
   - Decision within 24 hours
   - Services continue pending decision

5. PEER-TO-PEER REVIEW

   Availability:
   - All clinical denials
   - Request within 14 days of denial
   
   Process:
   - Treating physician contacts contractor
   - Speaks with medical director
   - Present additional clinical information
   - Decision communicated promptly
   
   How to Request:
   - Call contractor medical management
   - Reference denial and request P2P
   - Schedule convenient time

6. DOCUMENTATION FOR APPEALS

   Medical Necessity Appeals:
   - Complete medical records
   - Clinical notes supporting service
   - Test results and imaging
   - Treatment history
   - Peer-reviewed literature (if applicable)
   - Letter from treating physician
   
   Claims Appeals:
   - Itemized bill
   - Medical records
   - Explanation of charges
   - Corrected claim (if applicable)

7. COMMON DENIAL REASONS

   A. "Not Medically Necessary"
      Response:
      - Provide documentation meeting criteria
      - Reference TRICARE policy
      - Include clinical guidelines
      - Request peer-to-peer
      
   B. "Experimental/Investigational"
      Response:
      - Peer-reviewed literature
      - FDA approvals
      - Clinical trial data
      - Specialty society guidelines
      
   C. "Prior Authorization Not Obtained"
      Response:
      - Document emergency circumstances
      - Show notification attempt
      - Request retrospective review
      
   D. "Not a TRICARE Benefit"
      Response:
      - Review TRICARE Policy Manual
      - Identify applicable coverage provision
      - Request clarification

8. BENEFICIARY RIGHTS

   - Right to appeal any adverse determination
   - Right to representation
   - Right to review case file
   - Right to present evidence
   - Right to hearing (formal review)
   - Right to written decision with rationale

CONTACT INFORMATION:
TRICARE East Appeals:
Humana Military
PO Box 740062
Louisville, KY 40201
Phone: 1-800-444-5445

TRICARE West Appeals:
Health Net Federal Services
PO Box 202010
Florence, SC 29502
Phone: 1-844-866-9378

TRICARE Overseas Appeals:
International SOS
Phone: 1-877-678-1207

TRICARE Website: https://www.tricare.mil/appeals""",
            source_url="https://www.tricare.mil/appeals",
            last_updated=today,
            version="2024.12.1"
        ),
    ])
    
    # ==================== ANTHEM BLUE CROSS BLUE SHIELD POLICIES ====================
    policies.extend([
        PolicyDocument(
            payer_id="ANTHEM",
            payer_name="Anthem Blue Cross Blue Shield",
            policy_type="medical_policy",
            policy_title="Medical Policy - Orthopedic Surgery Guidelines",
            policy_number="ANT-ORTHO-2024-001",
            effective_date="2024-01-01",
            content="""ANTHEM BLUE CROSS BLUE SHIELD
MEDICAL POLICY: ORTHOPEDIC SURGERY GUIDELINES
Policy Number: ANT-ORTHO-2024-001
Effective Date: January 1, 2024
Last Review: December 1, 2024

1. POLICY OVERVIEW

This policy outlines coverage criteria for orthopedic surgical procedures
including joint replacement, arthroscopy, and spine surgery.

2. TOTAL KNEE ARTHROPLASTY (TKA) - CPT 27447

Coverage Criteria:
- Diagnosis of severe osteoarthritis (ICD-10: M17.11, M17.12)
- Kellgren-Lawrence Grade III or IV on radiographic imaging
- Failed conservative treatment for minimum 3 months:
  * Physical therapy (minimum 6 weeks)
  * NSAIDs or analgesics
  * Intra-articular injections (corticosteroid or hyaluronic acid)
- Functional impairment documented by validated outcome measure:
  * WOMAC score ≥ 39
  * KOOS Pain subscale ≤ 50
  * Oxford Knee Score ≤ 27
- BMI < 45 (relative contraindication if > 40)
- Medical clearance for surgery

Prior Authorization Required: YES
Authorization Valid: 90 days from approval

3. TOTAL HIP ARTHROPLASTY (THA) - CPT 27130

Coverage Criteria:
- Diagnosis of severe hip osteoarthritis (ICD-10: M16.11, M16.12)
- Radiographic evidence of joint space narrowing
- Failed conservative treatment for minimum 3 months
- Harris Hip Score < 70
- Significant functional limitation

Prior Authorization Required: YES
Authorization Valid: 90 days from approval

4. KNEE ARTHROSCOPY - CPT 29881

Coverage Criteria:
- Mechanical symptoms (locking, catching)
- MRI evidence of meniscal tear
- Failed conservative treatment for 6 weeks
- Age consideration: Limited coverage for degenerative tears in patients > 50

Prior Authorization Required: NO (for simple meniscectomy)
Prior Authorization Required: YES (for complex repairs)

5. SPINE SURGERY

Lumbar Fusion (CPT 22612, 22630):
- Documented instability or spondylolisthesis
- Failed conservative treatment for 6 months
- Concordant pain on provocative discography (if applicable)
- Psychological clearance for chronic pain patients

Cervical Fusion (CPT 22551):
- Documented radiculopathy or myelopathy
- MRI correlation with clinical findings
- Failed conservative treatment for 6-12 weeks

Prior Authorization Required: YES for all spine fusion procedures

6. DOCUMENTATION REQUIREMENTS

Required for All Orthopedic Surgery Requests:
- Complete history and physical
- Imaging reports (X-ray, MRI, CT as applicable)
- Conservative treatment documentation
- Functional assessment scores
- Operative plan
- Medical clearance (if applicable)

7. EXCLUSIONS

Not Covered:
- Experimental or investigational procedures
- Cosmetic procedures
- Procedures not meeting medical necessity criteria
- Services from non-participating providers without authorization

8. APPEAL PROCESS

If authorization is denied:
- Level 1: Reconsideration (30 days)
- Level 2: Internal Appeal (60 days)
- Level 3: External Review (if applicable)

CONTACT INFORMATION:
Prior Authorization: 1-800-274-7767
Provider Services: 1-800-676-2583
Website: https://www.anthem.com/provider""",
            source_url="https://www.anthem.com/provider/policies/orthopedic",
            last_updated=today,
            version="2024.12.1"
        ),
        
        PolicyDocument(
            payer_id="ANTHEM",
            payer_name="Anthem Blue Cross Blue Shield",
            policy_type="prior_auth",
            policy_title="Prior Authorization Requirements - Comprehensive Guide",
            policy_number="ANT-PA-2024-001",
            effective_date="2024-01-01",
            content="""ANTHEM BLUE CROSS BLUE SHIELD
PRIOR AUTHORIZATION REQUIREMENTS
Policy Number: ANT-PA-2024-001
Effective Date: January 1, 2024
Last Review: December 1, 2024

1. OVERVIEW

This document outlines services requiring prior authorization for
Anthem Blue Cross Blue Shield members. Authorization ensures medical
necessity and appropriate utilization of healthcare resources.

2. SERVICES REQUIRING PRIOR AUTHORIZATION

A. INPATIENT SERVICES
   - All elective hospital admissions
   - Skilled nursing facility admissions
   - Inpatient rehabilitation
   - Long-term acute care (LTAC)
   - Transplant services

B. OUTPATIENT SURGICAL PROCEDURES
   - Joint replacement (hip, knee, shoulder)
   - Spine surgery (fusion, decompression)
   - Bariatric surgery
   - Cardiac procedures (non-emergent)
   - Oncology surgery (select procedures)

C. ADVANCED IMAGING
   - MRI (all body parts)
   - CT scan (non-emergent)
   - PET scan
   - Nuclear medicine studies
   
   CPT Codes Requiring Authorization:
   - 70551-70553 (Brain MRI)
   - 72141-72158 (Spine MRI)
   - 73721-73723 (Lower extremity MRI)
   - 73221-73223 (Upper extremity MRI)
   - 71250-71275 (Chest CT)
   - 74176-74178 (Abdomen/Pelvis CT)

D. HIGH-COST DRUGS AND BIOLOGICS
   - Specialty medications > $1,000/month
   - Infusion therapies
   - Oncology drugs
   - Immunomodulators
   - Gene therapies

E. DURABLE MEDICAL EQUIPMENT (DME)
   - Power wheelchairs
   - Hospital beds
   - Oxygen equipment
   - CPAP/BiPAP devices
   - Prosthetics > $1,000

3. AUTHORIZATION PROCESS

Submission Methods:
- Online: Availity Portal (preferred)
- Phone: 1-800-274-7767
- Fax: 1-800-249-9949

Required Information:
- Member ID and demographics
- Provider NPI and contact information
- Diagnosis codes (ICD-10)
- Procedure codes (CPT/HCPCS)
- Clinical documentation supporting medical necessity
- Facility information (if applicable)

4. TURNAROUND TIMES

Standard Requests:
- Urgent: 24-72 hours
- Non-urgent: 5-15 business days
- Retrospective: 30 business days

Expedited Review:
Available when standard timeframe could seriously jeopardize
member's life, health, or ability to regain maximum function.

5. AUTHORIZATION VALIDITY

- Outpatient procedures: 60 days
- Inpatient admissions: 30 days
- Imaging: 60 days
- DME: 90 days
- Medications: Varies by drug (30-365 days)

6. EMERGENCY SERVICES

Prior authorization is NOT required for:
- Emergency room visits
- Emergency admissions
- Urgent care visits
- Ambulance services for emergencies

Notification Required:
- Within 24 hours of emergency admission
- Within 48 hours for weekend/holiday admissions

7. PEER-TO-PEER REVIEW

If initial request is denied:
- Request peer-to-peer within 10 business days
- Schedule through Provider Services: 1-800-676-2583
- Have clinical documentation ready
- Discuss case with Anthem Medical Director

8. COMMON DENIAL REASONS

- Incomplete clinical documentation
- Service not meeting medical necessity criteria
- Alternative treatments not attempted
- Out-of-network provider without authorization
- Experimental/investigational service

CONTACT INFORMATION:
Prior Authorization Line: 1-800-274-7767
Provider Services: 1-800-676-2583
Availity Portal: https://www.availity.com
Anthem Provider Portal: https://www.anthem.com/provider""",
            source_url="https://www.anthem.com/provider/prior-authorization",
            last_updated=today,
            version="2024.12.1"
        ),
        
        PolicyDocument(
            payer_id="ANTHEM",
            payer_name="Anthem Blue Cross Blue Shield",
            policy_type="appeal_procedures",
            policy_title="Appeals and Grievances Process",
            policy_number="ANT-APPEALS-2024-001",
            effective_date="2024-01-01",
            content="""ANTHEM BLUE CROSS BLUE SHIELD
APPEALS AND GRIEVANCES PROCESS
Policy Number: ANT-APPEALS-2024-001
Effective Date: January 1, 2024
Last Review: December 1, 2024

1. OVERVIEW

This document outlines the appeals and grievances process for
providers and members when a claim is denied or a service is
not authorized by Anthem Blue Cross Blue Shield.

2. TYPES OF APPEALS

A. PRE-SERVICE APPEALS
   For denied prior authorization requests before service is rendered.
   
   Timeframe to File: 180 days from denial notice
   Decision Timeframe:
   - Urgent: 72 hours
   - Standard: 30 calendar days

B. POST-SERVICE APPEALS
   For denied claims after service has been rendered.
   
   Timeframe to File: 180 days from denial notice
   Decision Timeframe: 60 calendar days

C. EXPEDITED APPEALS
   For urgent situations where standard timeframe could seriously
   jeopardize member's life, health, or ability to regain maximum function.
   
   Decision Timeframe: 72 hours

3. APPEAL LEVELS

LEVEL 1: INTERNAL APPEAL (RECONSIDERATION)
- First level of review
- Reviewed by clinical staff not involved in original decision
- Submit additional documentation
- Decision within 30 days (pre-service) or 60 days (post-service)

LEVEL 2: INTERNAL APPEAL (SECOND LEVEL)
- If Level 1 upholds denial
- Reviewed by Medical Director
- Peer-to-peer available
- Decision within 30 days

LEVEL 3: EXTERNAL REVIEW
- For fully-insured members (state-regulated plans)
- Independent Review Organization (IRO)
- Binding decision
- Available after exhausting internal appeals

4. HOW TO FILE AN APPEAL

Written Appeals:
Anthem Blue Cross Blue Shield
Appeals Department
P.O. Box 105568
Atlanta, GA 30348

Fax: 1-800-249-9949

Online: Availity Portal or Anthem Provider Portal

Required Information:
- Member name and ID number
- Provider name and NPI
- Date of service
- Claim number (if applicable)
- Authorization number (if applicable)
- Reason for appeal
- Supporting clinical documentation

5. SUPPORTING DOCUMENTATION

Medical Necessity Appeals:
- Complete medical records
- Clinical notes from treating physician
- Test results and imaging reports
- Treatment history
- Peer-reviewed literature (if applicable)
- Letter of medical necessity

Claims Appeals:
- Itemized bill
- Medical records
- Explanation of charges
- Corrected claim form (if applicable)

6. PEER-TO-PEER REVIEW

Available for:
- Prior authorization denials
- Medical necessity denials
- Concurrent review denials

How to Request:
- Call Provider Services: 1-800-676-2583
- Request within 10 business days of denial
- Schedule convenient time with Medical Director
- Have all clinical documentation ready

7. COMMON APPEAL SCENARIOS

A. "Not Medically Necessary" Denial
   Response Strategy:
   - Provide additional clinical documentation
   - Reference Anthem medical policy
   - Include clinical guidelines supporting service
   - Request peer-to-peer review

B. "Experimental/Investigational" Denial
   Response Strategy:
   - Provide peer-reviewed literature
   - Include FDA approvals
   - Reference clinical trial data
   - Cite specialty society guidelines

C. "Prior Authorization Not Obtained" Denial
   Response Strategy:
   - Document emergency circumstances
   - Show notification attempt
   - Request retrospective authorization
   - Provide clinical justification

D. "Out-of-Network" Denial
   Response Strategy:
   - Document network inadequacy
   - Show no in-network provider available
   - Request single case agreement
   - Provide member consent documentation

8. APPEAL RIGHTS

Providers and members have the right to:
- Appeal any adverse benefit determination
- Receive written explanation of denial
- Review case file and relevant documents
- Submit additional information
- Request expedited review when appropriate
- External review (for eligible plans)

9. GRIEVANCES

For complaints about:
- Quality of care
- Access to services
- Provider behavior
- Administrative issues

Submit to:
Anthem Member Services
P.O. Box 105187
Atlanta, GA 30348
Phone: 1-800-274-7767

CONTACT INFORMATION:
Appeals Department: 1-800-274-7767
Provider Services: 1-800-676-2583
Fax: 1-800-249-9949
Website: https://www.anthem.com/provider/appeals""",
            source_url="https://www.anthem.com/provider/appeals",
            last_updated=today,
            version="2024.12.1"
        ),
    ])
    
    return policies


def initialize_policy_database(rag: PayerPolicyRAG) -> Dict[str, Any]:
    """
    Initialize the policy database with comprehensive payer policies for all major payers.
    
    Loads policies for 9 payers: Florida Blue, Humana FL, Florida Medicaid, Aetna FL,
    Medicare (CMS), United Healthcare, Cigna, TRICARE, and Anthem/BCBS.
    
    Returns statistics about the initialization.
    """
    policies = get_comprehensive_payer_policies()
    
    results = {
        "total_policies": len(policies),
        "added": 0,
        "updated": 0,
        "errors": 0,
        "by_payer": {}
    }
    
    for policy in policies:
        try:
            change_info = rag.check_policy_changes(policy)
            doc_id = rag.add_policy(policy)
            
            if change_info["is_new"]:
                results["added"] += 1
            elif change_info["has_changed"]:
                results["updated"] += 1
            
            if policy.payer_id not in results["by_payer"]:
                results["by_payer"][policy.payer_id] = {"added": 0, "updated": 0}
            
            if change_info["is_new"]:
                results["by_payer"][policy.payer_id]["added"] += 1
            elif change_info["has_changed"]:
                results["by_payer"][policy.payer_id]["updated"] += 1
                
        except Exception as e:
            results["errors"] += 1
            print(f"Error adding policy {policy.policy_number}: {e}")
    
    return results
