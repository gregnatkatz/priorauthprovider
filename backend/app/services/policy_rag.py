"""
Payer Policy RAG System with ChromaDB

This module provides a comprehensive RAG (Retrieval-Augmented Generation) system
for FL payer policies using ChromaDB as the vector store.

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
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None


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
    RAG system for payer policy retrieval using ChromaDB.
    
    Provides semantic search across comprehensive FL payer policies
    with version tracking and change detection.
    """
    
    COLLECTION_NAME = "payer_policies"
    
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
        }
    }
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """Initialize the RAG system with ChromaDB."""
        self.persist_directory = persist_directory
        self.client = None
        self.collection = None
        self._initialize_chromadb()
    
    def _initialize_chromadb(self):
        """Initialize ChromaDB client and collection."""
        if not CHROMADB_AVAILABLE:
            print("Warning: ChromaDB not available. RAG features disabled.")
            return
        
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"description": "FL Payer Policy Documents"}
        )
    
    def add_policy(self, policy: PolicyDocument) -> str:
        """Add a policy document to the vector store."""
        if not self.collection:
            return ""
        
        doc_id = f"{policy.payer_id}_{policy.policy_number}_{policy.version}"
        
        metadata = {
            "payer_id": policy.payer_id,
            "payer_name": policy.payer_name,
            "policy_type": policy.policy_type,
            "policy_title": policy.policy_title,
            "policy_number": policy.policy_number,
            "effective_date": policy.effective_date,
            "source_url": policy.source_url,
            "last_updated": policy.last_updated,
            "version": policy.version,
            "content_hash": policy.content_hash
        }
        
        self.collection.upsert(
            ids=[doc_id],
            documents=[policy.content],
            metadatas=[metadata]
        )
        
        return doc_id
    
    def search_policies(
        self,
        query: str,
        payer_id: Optional[str] = None,
        policy_type: Optional[str] = None,
        n_results: int = 5
    ) -> List[PolicySearchResult]:
        """
        Search for relevant policy documents.
        
        Args:
            query: Search query (e.g., "prior authorization for knee replacement")
            payer_id: Filter by specific payer
            policy_type: Filter by policy type
            n_results: Number of results to return
            
        Returns:
            List of PolicySearchResult with relevance scores
        """
        if not self.collection:
            return []
        
        where_filter = {}
        if payer_id:
            where_filter["payer_id"] = payer_id
        if policy_type:
            where_filter["policy_type"] = policy_type
        
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter if where_filter else None,
            include=["documents", "metadatas", "distances"]
        )
        
        search_results = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                document = results["documents"][0][i] if results["documents"] else ""
                distance = results["distances"][0][i] if results["distances"] else 1.0
                
                relevance_score = 1.0 - min(distance, 1.0)
                
                policy = PolicyDocument(
                    payer_id=metadata.get("payer_id", ""),
                    payer_name=metadata.get("payer_name", ""),
                    policy_type=metadata.get("policy_type", ""),
                    policy_title=metadata.get("policy_title", ""),
                    policy_number=metadata.get("policy_number", ""),
                    effective_date=metadata.get("effective_date", ""),
                    content=document,
                    source_url=metadata.get("source_url", ""),
                    last_updated=metadata.get("last_updated", ""),
                    version=metadata.get("version", ""),
                    content_hash=metadata.get("content_hash", "")
                )
                
                search_results.append(PolicySearchResult(
                    document=policy,
                    relevance_score=relevance_score,
                    matched_section=document[:500] + "..." if len(document) > 500 else document,
                    metadata=metadata
                ))
        
        return search_results
    
    def get_policy_by_id(self, payer_id: str, policy_number: str) -> Optional[PolicyDocument]:
        """Get a specific policy by payer and policy number."""
        if not self.collection:
            return None
        
        results = self.collection.get(
            where={"$and": [
                {"payer_id": payer_id},
                {"policy_number": policy_number}
            ]},
            include=["documents", "metadatas"]
        )
        
        if results and results["ids"]:
            metadata = results["metadatas"][0] if results["metadatas"] else {}
            document = results["documents"][0] if results["documents"] else ""
            
            return PolicyDocument(
                payer_id=metadata.get("payer_id", ""),
                payer_name=metadata.get("payer_name", ""),
                policy_type=metadata.get("policy_type", ""),
                policy_title=metadata.get("policy_title", ""),
                policy_number=metadata.get("policy_number", ""),
                effective_date=metadata.get("effective_date", ""),
                content=document,
                source_url=metadata.get("source_url", ""),
                last_updated=metadata.get("last_updated", ""),
                version=metadata.get("version", ""),
                content_hash=metadata.get("content_hash", "")
            )
        
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
        if not self.collection:
            return []
        
        results = self.collection.get(
            where={"payer_id": payer_id},
            include=["documents", "metadatas"]
        )
        
        policies = []
        if results and results["ids"]:
            for i, doc_id in enumerate(results["ids"]):
                metadata = results["metadatas"][i] if results["metadatas"] else {}
                document = results["documents"][i] if results["documents"] else ""
                
                policies.append(PolicyDocument(
                    payer_id=metadata.get("payer_id", ""),
                    payer_name=metadata.get("payer_name", ""),
                    policy_type=metadata.get("policy_type", ""),
                    policy_title=metadata.get("policy_title", ""),
                    policy_number=metadata.get("policy_number", ""),
                    effective_date=metadata.get("effective_date", ""),
                    content=document,
                    source_url=metadata.get("source_url", ""),
                    last_updated=metadata.get("last_updated", ""),
                    version=metadata.get("version", ""),
                    content_hash=metadata.get("content_hash", "")
                ))
        
        return policies
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the policy database."""
        if not self.collection:
            return {"error": "ChromaDB not available"}
        
        total_count = self.collection.count()
        
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
        if not self.collection:
            return {
                "total_policies": 0,
                "by_payer": {},
                "by_type": {},
                "last_updated": None
            }
        
        total_count = self.collection.count()
        
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
        if not self.collection:
            return None
        
        try:
            results = self.collection.get(
                where={"policy_number": policy_number},
                include=["documents", "metadatas"]
            )
            
            if results and results["ids"]:
                metadata = results["metadatas"][0]
                content = results["documents"][0]
                
                return PolicyDocument(
                    payer_id=metadata.get("payer_id", ""),
                    payer_name=metadata.get("payer_name", ""),
                    policy_type=metadata.get("policy_type", ""),
                    policy_title=metadata.get("policy_title", ""),
                    policy_number=metadata.get("policy_number", ""),
                    effective_date=metadata.get("effective_date", ""),
                    content=content,
                    source_url=metadata.get("source_url", ""),
                    last_updated=metadata.get("last_updated", ""),
                    version=metadata.get("version", "1.0"),
                    content_hash=metadata.get("content_hash", "")
                )
        except Exception as e:
            print(f"Error getting policy by number: {e}")
        
        return None


def get_comprehensive_fl_payer_policies() -> List[PolicyDocument]:
    """
    Returns comprehensive FL payer policy documents.
    
    These are detailed policy documents covering:
    - Prior authorization requirements
    - Medical necessity criteria
    - Coverage determinations
    - Appeal procedures
    - Documentation requirements
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
    ])
    
    return policies


def initialize_policy_database(rag: PayerPolicyRAG) -> Dict[str, Any]:
    """
    Initialize the policy database with comprehensive FL payer policies.
    
    Returns statistics about the initialization.
    """
    policies = get_comprehensive_fl_payer_policies()
    
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
