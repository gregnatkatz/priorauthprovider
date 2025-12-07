# Data Mapping: POC to Production Integration

This document maps the POC database tables to production data sources for ContosoHealth's phased integration approach. The POC uses a star schema designed for easy migration to Fabric HDS when production integration begins.

## Overview

The Denial Intelligence Platform POC is structured around three integration phases, each with different data sources and complexity levels:

| Phase | Focus | Data Source | Complexity | Timeline |
|-------|-------|-------------|------------|----------|
| Phase 1 | 835 Denial Management | Clearinghouse ERA feeds | LOW | 60-90 days |
| Phase 2 | Clinical Context | Epic FHIR R4 APIs | MEDIUM | 90-180 days |
| Phase 3 | Prior Auth Intelligence | Payer portals, Epic PA module | HIGH | 6+ months |

## Phase 1: 835 Denial Management (PRIMARY FOCUS)

Phase 1 represents approximately 80% of the value in revenue cycle optimization. The 835 ERA (Electronic Remittance Advice) is a standardized EDI format that payers use to communicate claim adjudication results, including denials with CARC/RARC codes.

### Data Source
- **Primary:** Clearinghouse ERA feeds (Availity, Change Healthcare)
- **Format:** ANSI X12 835 EDI transactions
- **Frequency:** Daily batch processing
- **Complexity:** LOW - Standardized format across all payers

### Entity Mappings

#### fact_denial

The core denial fact table maps directly to the 835 CAS (Claim Adjustment Segment).

| POC Field | Production Source | 835 Segment | Notes |
|-----------|------------------|-------------|-------|
| denial_id | Generated | N/A | Surrogate key |
| claim_id | FK to fact_claim | CLP01 | Patient control number |
| denial_reason_id | FK to dim_denial_reason | CAS02 | CARC code lookup |
| denial_date | 835 transaction date | BPR16 or DTM | Check/EFT date |
| denial_amount | CAS03 | CAS03 | Monetary amount |
| carc_code | CAS02 | CAS02 | Claim Adjustment Reason Code |
| rarc_code | CAS segment qualifier | CAS05+ | Remittance Advice Remark Code |
| group_code | CAS01 | CAS01 | CO, PR, OA, PI, CR |
| status | Derived | N/A | New, In Review, Appealed, etc. |
| ai_appeal_probability | AI-generated | N/A | From Recovery Predictor agent |
| ai_recommended_action | AI-generated | N/A | From Root Cause Analyzer |
| clinical_urgency_score | AI-generated | N/A | From Clinical Urgency agent |
| sdoh_risk_score | AI-generated | N/A | From SDOH Scorer agent |

**835 CAS Segment Structure:**
```
CAS*CO*45*500.00*1~
    |  |  |      |
    |  |  |      +-- Quantity (optional)
    |  |  +--------- Adjustment Amount
    |  +------------ CARC Code (reason)
    +--------------- Group Code (CO=Contractual Obligation)
```

#### fact_claim

Claims data combines 835 CLP segment with original 837 submission context.

| POC Field | Production Source | 835 Segment | Notes |
|-----------|------------------|-------------|-------|
| claim_id | Generated | N/A | Surrogate key |
| claim_number | CLP01 | CLP01 | Patient control number |
| payer_claim_number | CLP07 | CLP07 | Payer's claim control number |
| patient_id | FK to dim_patient | N/A | From 837 or patient matching |
| payer_id | FK to dim_payer | N1 loop | Payer identification |
| facility_id | FK to dim_facility | N/A | From 837 billing provider |
| physician_id | FK to dim_physician | N/A | From 837 rendering provider |
| procedure_id | FK to dim_procedure | SVC01 | Service line procedure code |
| service_date | SVC segment | DTM | Date of service |
| billed_amount | CLP03 | CLP03 | Total claim charge amount |
| allowed_amount | CLP04 | CLP04 | Payer allowed amount |
| paid_amount | CLP04 | CLP04 | Amount paid |
| patient_responsibility | Derived | CAS (PR group) | Sum of PR adjustments |
| claim_status | CLP02 | CLP02 | 1=Processed, 2=Denied, etc. |

**835 CLP Segment Structure:**
```
CLP*12345*1*1500.00*1200.00**12*ABC123~
    |     |  |       |      |  |  |
    |     |  |       |      |  |  +-- Payer claim number
    |     |  |       |      |  +----- Claim filing indicator
    |     |  |       |      +-------- Facility code (optional)
    |     |  |       +--------------- Paid amount
    |     |  +----------------------- Charge amount
    |     +-------------------------- Status code
    +-------------------------------- Patient control number
```

#### dim_denial_reason

Maps to standard CARC/RARC reference tables maintained by X12.

| POC Field | Production Source | Notes |
|-----------|------------------|-------|
| denial_reason_id | Generated | Surrogate key |
| carc_code | CARC reference | Claim Adjustment Reason Code |
| rarc_code | RARC reference | Remittance Advice Remark Code |
| category | Derived | Medical Necessity, Coding, Eligibility, etc. |
| description | CARC/RARC reference | Standard description text |
| appeal_guidance | AI-generated | Recommended appeal approach |

**Common CARC Codes:**
| Code | Category | Description |
|------|----------|-------------|
| 4 | Coding | Procedure code inconsistent with modifier |
| 16 | Information | Claim lacks information needed for adjudication |
| 18 | Duplicate | Exact duplicate claim |
| 29 | Timely Filing | Time limit for filing has expired |
| 50 | Medical Necessity | Not deemed a medical necessity |
| 96 | Non-Covered | Non-covered charge(s) |
| 197 | Prior Auth | Precertification/authorization absent |

#### dim_payer

Maps to clearinghouse payer identification and routing.

| POC Field | Production Source | 835 Segment | Notes |
|-----------|------------------|-------------|-------|
| payer_id | Generated | N/A | Surrogate key |
| payer_name | N1 loop | N102 | Payer organization name |
| payer_identifier | N1 loop | N104 | Payer ID (NPI or proprietary) |
| era_payer_id | ISA/GS | ISA06 | Clearinghouse payer routing ID |
| denial_rate | Calculated | N/A | Historical denial rate |
| avg_resolution_days | Calculated | N/A | Average time to resolution |
| appeal_success_rate | Calculated | N/A | Historical appeal success |

### 835 Transaction Flow

```
ISA/GS (Interchange/Functional Group Headers)
  |
  +-- ST (Transaction Set Header - 835)
        |
        +-- BPR (Financial Information - payment details)
        |
        +-- TRN (Reassociation Trace Number)
        |
        +-- N1 Loop (Payer/Payee Identification)
        |
        +-- LX Loop (Header Number)
              |
              +-- CLP Loop (Claim Payment Information)
                    |
                    +-- CAS (Claim Adjustment Segment) --> fact_denial
                    |
                    +-- NM1 (Patient/Subscriber Name)
                    |
                    +-- SVC Loop (Service Line)
                          |
                          +-- CAS (Service Line Adjustments)
                          |
                          +-- DTM (Service Dates)
```

## Phase 2: Clinical Context Integration

Phase 2 adds clinical context from Epic to enhance denial analysis and appeal documentation.

### Data Source
- **Primary:** Epic FHIR R4 APIs
- **Secondary:** Epic Bridges (HL7v2 ADT, ORU)
- **Frequency:** Real-time or near-real-time
- **Complexity:** MEDIUM - Requires Epic integration and data governance

### Entity Mappings

#### dim_patient

| POC Field | Production Source | FHIR Resource | Notes |
|-----------|------------------|---------------|-------|
| patient_id | Generated | N/A | Surrogate key |
| mrn | Patient.identifier | identifier[mrn] | Medical record number |
| first_name | Patient.name | name.given | Patient first name |
| last_name | Patient.name | name.family | Patient last name |
| date_of_birth | Patient.birthDate | birthDate | DOB |
| gender | Patient.gender | gender | male, female, other, unknown |
| address | Patient.address | address | Full address |
| sdoh_score | Derived | N/A | Calculated from Z-codes, social history |
| insurance_type | Coverage.type | type.coding | Medicare, Medicaid, Commercial |

**FHIR Patient Resource Example:**
```json
{
  "resourceType": "Patient",
  "id": "12345",
  "identifier": [
    {
      "type": {"coding": [{"code": "MR"}]},
      "value": "MRN123456"
    }
  ],
  "name": [{"family": "Smith", "given": ["John"]}],
  "birthDate": "1965-04-15",
  "gender": "male"
}
```

#### dim_procedure

| POC Field | Production Source | FHIR Resource | Notes |
|-----------|------------------|---------------|-------|
| procedure_id | Generated | N/A | Surrogate key |
| cpt_code | Procedure.code | code.coding[CPT] | CPT/HCPCS code |
| description | Procedure.code | code.text | Procedure description |
| category | Derived | N/A | Surgical, Diagnostic, etc. |
| avg_cost | ChargeItem | ChargeItem.priceOverride | Average charge amount |
| denial_risk | AI-generated | N/A | Historical denial probability |

#### dim_physician

| POC Field | Production Source | FHIR Resource | Notes |
|-----------|------------------|---------------|-------|
| physician_id | Generated | N/A | Surrogate key |
| npi | Practitioner.identifier | identifier[NPI] | National Provider Identifier |
| first_name | Practitioner.name | name.given | First name |
| last_name | Practitioner.name | name.family | Last name |
| specialty | PractitionerRole.specialty | specialty.coding | Medical specialty |
| facility_id | FK to dim_facility | N/A | Primary facility |

### SDOH Score Calculation

The SDOH (Social Determinants of Health) score is derived from multiple Epic data sources:

| Data Source | FHIR Resource | Indicators |
|-------------|---------------|------------|
| Z-codes | Condition | Z55-Z65 (socioeconomic factors) |
| Social History | Observation | Housing, food security, transportation |
| ADT Events | Encounter | ED visits, readmissions |
| Insurance | Coverage | Medicaid, uninsured status |

## Phase 3: Prior Authorization Intelligence (FUTURE)

Phase 3 is NOT implemented in this POC. It is documented here for future roadmap planning only.

### Data Source Challenges
- **Fragmented:** Each payer has different portal/API
- **Non-standardized:** No universal PA status format
- **Real-time requirements:** Status changes frequently
- **Integration complexity:** HIGH

### Potential Data Sources
| Source | Coverage | Complexity |
|--------|----------|------------|
| Availity API | Multi-payer | Medium |
| Direct payer APIs | Single payer each | High |
| Epic PA module | Internal tracking | Medium |
| RPA/screen scraping | Fallback | Very High |

### Future Entity Mappings (Not Implemented)

#### fact_prior_auth (Future)

| Field | Source | Notes |
|-------|--------|-------|
| pa_id | Generated | Surrogate key |
| patient_id | FK to dim_patient | Patient reference |
| procedure_id | FK to dim_procedure | Requested procedure |
| payer_id | FK to dim_payer | Authorizing payer |
| status | Payer portal | Pending, Approved, Denied |
| request_date | Internal | Date PA submitted |
| decision_date | Payer portal | Date of payer decision |
| expiration_date | Payer portal | Authorization expiry |
| auth_number | Payer portal | Authorization reference |

## AI Agent Data Requirements

The 18 AI agents require specific data inputs from the mapped sources:

### Patient-Centric Agents
| Agent | Required Data | Source Phase |
|-------|--------------|--------------|
| SDOH Scorer | Patient demographics, Z-codes, social history | Phase 2 |
| Care Gap Detector | Clinical history, preventive care records | Phase 2 |
| Clinical Urgency | Diagnosis codes, vitals, lab results | Phase 2 |
| Financial Value | Claim amounts, patient responsibility | Phase 1 |

### Revenue Intelligence Agents
| Agent | Required Data | Source Phase |
|-------|--------------|--------------|
| Recovery Predictor | Historical appeals, denial reasons, payer patterns | Phase 1 |
| P2P Optimizer | Physician specialty, payer P2P history | Phase 1 + 2 |
| Queue Wait Time | Payer response times, submission volumes | Phase 1 |

### Denial Prevention Agents
| Agent | Required Data | Source Phase |
|-------|--------------|--------------|
| Denial Risk Predictor | Procedure codes, payer rules, historical denials | Phase 1 |
| Doc Completeness | Required documentation checklist, submitted docs | Phase 1 + 2 |
| Policy Monitor | Payer policy updates, LCD/NCD changes | Phase 1 |

### Learning Agents
| Agent | Required Data | Source Phase |
|-------|--------------|--------------|
| Root Cause Analyzer | Denial reasons, claim details, resolution outcomes | Phase 1 |
| Staff Feedback Processor | User actions, outcome tracking, feedback | Phase 1 |

### Validation Agents
| Agent | Required Data | Source Phase |
|-------|--------------|--------------|
| Safety Validator | Clinical data, medication history | Phase 2 |
| Consensus Checker | All agent outputs | Phase 1 |
| Policy Match Grader | Payer policies, claim details | Phase 1 |
| Viability Scorer | All agent scores, historical success rates | Phase 1 |
| Eligibility Verifier | Coverage data, eligibility responses | Phase 1 + 2 |
| Follow-up Scheduler | Deadlines, payer response patterns | Phase 1 |

## Data Quality Requirements

### Phase 1 (835) Data Quality
- **Completeness:** All CAS segments must be captured
- **Timeliness:** ERA files processed within 24 hours of receipt
- **Accuracy:** CARC/RARC codes validated against X12 reference
- **Consistency:** Claim matching between 835 and 837

### Phase 2 (Epic) Data Quality
- **Patient Matching:** MRN-based matching with fallback to demographics
- **Code Mapping:** ICD-10, CPT codes validated and current
- **SDOH Completeness:** Z-codes and social history captured when available

## Migration Path to Fabric HDS

The POC star schema is designed for direct migration to Microsoft Fabric Health Data Solutions:

| POC Table | Fabric HDS Table | Notes |
|-----------|-----------------|-------|
| fact_denial | ClaimDenial | Add Fabric-specific metadata |
| fact_claim | Claim | Map to FHIR Claim resource |
| dim_patient | Patient | Map to FHIR Patient resource |
| dim_payer | Organization | Map to FHIR Organization (payer) |
| dim_procedure | Procedure | Map to FHIR Procedure resource |
| dim_physician | Practitioner | Map to FHIR Practitioner resource |
| dim_denial_reason | CodeSystem | CARC/RARC as CodeSystem |

The schema supports both the current SQLite POC and future Fabric deployment without structural changes.
