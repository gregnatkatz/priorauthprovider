"""
EDI Parser Service for 837/835 files
Enhancement Spec v2 Phase 2: EDI Parser

Parses X12 837P/837I (claim submissions) and 835 (remittance advice) files
to extract claims, payments, and CARC/RARC denial codes.
"""

import re
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from dataclasses import dataclass


@dataclass
class ParsedClaim:
    """Parsed claim from 837 file"""
    patient_control_number: str
    claim_amount: float
    service_date: Optional[date]
    diagnosis_codes: List[str]
    procedure_codes: List[str]
    subscriber_id: str
    payer_id: str
    provider_npi: str
    facility_npi: Optional[str]
    claim_type: str  # '837P' or '837I'


@dataclass
class ParsedPayment:
    """Parsed payment from 835 file"""
    claim_number: str
    payer_claim_number: str
    billed_amount: float
    paid_amount: float
    patient_responsibility: float
    claim_status_code: str
    check_number: Optional[str]
    payment_date: Optional[date]
    adjustments: List['ParsedAdjustment']


@dataclass
class ParsedAdjustment:
    """Parsed adjustment from 835 CAS segment"""
    group_code: str  # CO, PR, OA, PI, CR
    reason_code: str  # CARC code
    amount: float
    quantity: Optional[int]
    remark_codes: List[str]  # RARC codes


# CARC code to denial category mapping (from Clearinghouse Addendum)
CARC_CATEGORY_MAP = {
    # Prior Authorization denials (28%)
    "197": "prior_auth",
    "198": "prior_auth", 
    "39": "prior_auth",
    
    # Medical Necessity denials (24%)
    "50": "medical_necessity",
    "55": "medical_necessity",
    "96": "medical_necessity",
    
    # Coding/Billing errors (18%)
    "4": "coding_billing",
    "5": "coding_billing",
    "236": "coding_billing",
    
    # Eligibility issues (12%)
    "27": "eligibility",
    "31": "eligibility",
    "32": "eligibility",
    
    # Duplicate claims (8%)
    "18": "duplicate",
    
    # Timely filing (5%)
    "29": "timely_filing",
    
    # Bundling issues (5%)
    "97": "bundling",
    "234": "bundling",
    
    # Contractual adjustments (not denials)
    "45": "contractual",
    "253": "contractual",
}


class EDIParser:
    """Parser for X12 837 and 835 EDI files"""
    
    def __init__(self):
        self.segment_terminator = "~"
        self.element_separator = "*"
        self.subelement_separator = ":"
    
    def parse_file(self, content: str, file_type: str) -> Dict[str, Any]:
        """
        Parse an EDI file and return structured data
        
        Args:
            content: Raw EDI file content
            file_type: '837P', '837I', or '835'
            
        Returns:
            Dictionary with parsed data
        """
        # Detect delimiters from ISA segment
        self._detect_delimiters(content)
        
        # Split into segments
        segments = self._split_segments(content)
        
        if file_type in ('837P', '837I'):
            return self._parse_837(segments, file_type)
        elif file_type == '835':
            return self._parse_835(segments)
        else:
            raise ValueError(f"Unknown file type: {file_type}")
    
    def _detect_delimiters(self, content: str):
        """Detect EDI delimiters from ISA segment"""
        if content.startswith("ISA"):
            # ISA segment is fixed length, element separator is at position 3
            self.element_separator = content[3]
            # Subelement separator is at position 104
            if len(content) > 104:
                self.subelement_separator = content[104]
            # Segment terminator is at position 105
            if len(content) > 105:
                self.segment_terminator = content[105]
    
    def _split_segments(self, content: str) -> List[List[str]]:
        """Split EDI content into segments and elements"""
        # Remove newlines and split by segment terminator
        content = content.replace("\n", "").replace("\r", "")
        raw_segments = content.split(self.segment_terminator)
        
        segments = []
        for seg in raw_segments:
            if seg.strip():
                elements = seg.split(self.element_separator)
                segments.append(elements)
        
        return segments
    
    def _parse_837(self, segments: List[List[str]], file_type: str) -> Dict[str, Any]:
        """Parse 837P or 837I claim submission"""
        result = {
            "file_type": file_type,
            "interchange_control_number": None,
            "sender_id": None,
            "receiver_id": None,
            "claims": [],
            "total_claims": 0,
            "total_billed": 0.0,
        }
        
        current_claim = None
        current_subscriber_id = None
        current_payer_id = None
        current_provider_npi = None
        
        for seg in segments:
            seg_id = seg[0] if seg else ""
            
            if seg_id == "ISA":
                result["interchange_control_number"] = seg[13] if len(seg) > 13 else None
                result["sender_id"] = seg[6].strip() if len(seg) > 6 else None
                result["receiver_id"] = seg[8].strip() if len(seg) > 8 else None
            
            elif seg_id == "NM1":
                # Subscriber/Patient
                if len(seg) > 1 and seg[1] == "IL":
                    current_subscriber_id = seg[9] if len(seg) > 9 else None
                # Payer
                elif len(seg) > 1 and seg[1] == "PR":
                    current_payer_id = seg[9] if len(seg) > 9 else None
                # Billing Provider
                elif len(seg) > 1 and seg[1] == "85":
                    current_provider_npi = seg[9] if len(seg) > 9 else None
            
            elif seg_id == "CLM":
                # Start of a new claim
                if current_claim:
                    result["claims"].append(current_claim)
                
                current_claim = ParsedClaim(
                    patient_control_number=seg[1] if len(seg) > 1 else "",
                    claim_amount=float(seg[2]) if len(seg) > 2 and seg[2] else 0.0,
                    service_date=None,
                    diagnosis_codes=[],
                    procedure_codes=[],
                    subscriber_id=current_subscriber_id or "",
                    payer_id=current_payer_id or "",
                    provider_npi=current_provider_npi or "",
                    facility_npi=None,
                    claim_type=file_type
                )
                result["total_billed"] += current_claim.claim_amount
            
            elif seg_id == "DTP" and current_claim:
                # Date/Time Period
                if len(seg) > 3 and seg[1] == "472":  # Service date
                    date_str = seg[3]
                    if len(date_str) == 8:
                        current_claim.service_date = datetime.strptime(date_str, "%Y%m%d").date()
            
            elif seg_id == "HI" and current_claim:
                # Health Care Information Codes (diagnosis)
                for i in range(1, len(seg)):
                    if seg[i]:
                        parts = seg[i].split(self.subelement_separator)
                        if len(parts) >= 2:
                            current_claim.diagnosis_codes.append(parts[1])
            
            elif seg_id == "SV1" and current_claim:
                # Professional Service (837P)
                if len(seg) > 1:
                    parts = seg[1].split(self.subelement_separator)
                    if len(parts) >= 2:
                        current_claim.procedure_codes.append(parts[1])
            
            elif seg_id == "SV2" and current_claim:
                # Institutional Service (837I)
                if len(seg) > 2:
                    current_claim.procedure_codes.append(seg[2])
        
        # Don't forget the last claim
        if current_claim:
            result["claims"].append(current_claim)
        
        result["total_claims"] = len(result["claims"])
        
        return result
    
    def _parse_835(self, segments: List[List[str]]) -> Dict[str, Any]:
        """Parse 835 remittance advice"""
        result = {
            "file_type": "835",
            "interchange_control_number": None,
            "payer_id": None,
            "payer_name": None,
            "check_number": None,
            "payment_date": None,
            "payments": [],
            "total_claims": 0,
            "total_billed": 0.0,
            "total_paid": 0.0,
            "total_adjustments": 0.0,
            "denials_found": 0,
        }
        
        current_payment = None
        current_adjustments = []
        
        for seg in segments:
            seg_id = seg[0] if seg else ""
            
            if seg_id == "ISA":
                result["interchange_control_number"] = seg[13] if len(seg) > 13 else None
            
            elif seg_id == "N1":
                # Payer identification
                if len(seg) > 1 and seg[1] == "PR":
                    result["payer_name"] = seg[2] if len(seg) > 2 else None
                    result["payer_id"] = seg[4] if len(seg) > 4 else None
            
            elif seg_id == "BPR":
                # Financial Information
                if len(seg) > 16:
                    result["check_number"] = seg[16] if seg[16] else None
                if len(seg) > 16:
                    date_str = seg[16] if len(seg) > 16 else None
                    # Payment date is often in DTM segment instead
            
            elif seg_id == "DTM":
                # Date/Time Reference
                if len(seg) > 2 and seg[1] == "405":  # Production date
                    date_str = seg[2]
                    if len(date_str) == 8:
                        result["payment_date"] = datetime.strptime(date_str, "%Y%m%d").date()
            
            elif seg_id == "TRN":
                # Check/EFT Trace Number
                if len(seg) > 2:
                    result["check_number"] = seg[2]
            
            elif seg_id == "CLP":
                # Claim Payment Information - start of new claim
                if current_payment:
                    current_payment.adjustments = current_adjustments
                    result["payments"].append(current_payment)
                    current_adjustments = []
                
                claim_status = seg[2] if len(seg) > 2 else "1"
                billed = float(seg[3]) if len(seg) > 3 and seg[3] else 0.0
                paid = float(seg[4]) if len(seg) > 4 and seg[4] else 0.0
                patient_resp = float(seg[5]) if len(seg) > 5 and seg[5] else 0.0
                
                current_payment = ParsedPayment(
                    claim_number=seg[1] if len(seg) > 1 else "",
                    payer_claim_number=seg[7] if len(seg) > 7 else "",
                    billed_amount=billed,
                    paid_amount=paid,
                    patient_responsibility=patient_resp,
                    claim_status_code=claim_status,
                    check_number=result["check_number"],
                    payment_date=result["payment_date"],
                    adjustments=[]
                )
                
                result["total_billed"] += billed
                result["total_paid"] += paid
                
                # Status code 2 = Denied, 4 = Denied (duplicate)
                if claim_status in ("2", "4"):
                    result["denials_found"] += 1
            
            elif seg_id == "CAS" and current_payment:
                # Claim Adjustment Segment
                group_code = seg[1] if len(seg) > 1 else ""
                
                # CAS can have multiple adjustments: CAS*CO*45*100*1*253*50~
                i = 2
                while i < len(seg) and seg[i]:
                    reason_code = seg[i]
                    amount = float(seg[i+1]) if i+1 < len(seg) and seg[i+1] else 0.0
                    quantity = int(seg[i+2]) if i+2 < len(seg) and seg[i+2] else None
                    
                    adjustment = ParsedAdjustment(
                        group_code=group_code,
                        reason_code=reason_code,
                        amount=amount,
                        quantity=quantity,
                        remark_codes=[]
                    )
                    current_adjustments.append(adjustment)
                    result["total_adjustments"] += amount
                    
                    # Check if this is a denial (not contractual)
                    if group_code != "CO" or reason_code not in ("45", "253"):
                        if reason_code in CARC_CATEGORY_MAP:
                            category = CARC_CATEGORY_MAP[reason_code]
                            if category != "contractual":
                                result["denials_found"] += 1
                    
                    i += 3
            
            elif seg_id == "LQ" and current_adjustments:
                # Remark codes
                if len(seg) > 2 and seg[1] == "HE":
                    current_adjustments[-1].remark_codes.append(seg[2])
        
        # Don't forget the last payment
        if current_payment:
            current_payment.adjustments = current_adjustments
            result["payments"].append(current_payment)
        
        result["total_claims"] = len(result["payments"])
        
        return result
    
    def get_denial_category(self, carc_code: str) -> str:
        """Map CARC code to denial category"""
        return CARC_CATEGORY_MAP.get(carc_code, "other")
    
    def extract_denials(self, parsed_835: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract denial information from parsed 835"""
        denials = []
        
        for payment in parsed_835.get("payments", []):
            for adj in payment.adjustments:
                # Skip contractual adjustments
                if adj.group_code == "CO" and adj.reason_code in ("45", "253"):
                    continue
                
                category = self.get_denial_category(adj.reason_code)
                if category != "contractual":
                    denials.append({
                        "claim_number": payment.claim_number,
                        "payer_claim_number": payment.payer_claim_number,
                        "carc_code": adj.reason_code,
                        "rarc_codes": adj.remark_codes,
                        "group_code": adj.group_code,
                        "adjustment_amount": adj.amount,
                        "denial_category": category,
                        "billed_amount": payment.billed_amount,
                        "paid_amount": payment.paid_amount,
                    })
        
        return denials


# Singleton instance
edi_parser = EDIParser()


def parse_edi_file(content: str, file_type: str) -> Dict[str, Any]:
    """Convenience function to parse EDI file"""
    return edi_parser.parse_file(content, file_type)


def extract_denials_from_835(content: str) -> List[Dict[str, Any]]:
    """Convenience function to extract denials from 835 content"""
    parsed = edi_parser.parse_file(content, "835")
    return edi_parser.extract_denials(parsed)
