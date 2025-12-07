from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class ClaimStatusDetail:
    """Detailed claim status from 277."""
    claim_id: str
    patient_name: str
    patient_dob: Optional[str]
    payer_name: str
    payer_claim_control_number: str
    service_date: datetime
    billed_amount: float
    status_category_code: str
    status_category_description: str
    status_code: str
    status_description: str
    effective_date: datetime
    adjudication_finalized: bool
    paid_amount: Optional[float]
    check_number: Optional[str]
    remittance_date: Optional[datetime]


@dataclass
class Parsed277:
    """Parsed 277 Claim Status Response."""
    transaction_id: str
    sender_id: str
    receiver_id: str
    transaction_date: datetime
    payer_name: str
    claims: List[ClaimStatusDetail]
    raw_edi: str
    
    @property
    def is_finalized(self) -> bool:
        """Check if any claim in this response is finalized (A8 status)."""
        return any(c.adjudication_finalized for c in self.claims)


class Parser277:
    """
    Parser for X12 277 Claim Status Response transactions.
    
    277 provides detailed status updates on claims during adjudication.
    Typically received in response to 276 inquiries or proactively from payers.
    
    Status Category Codes (STC01):
    - A0: Forwarded - forwarded to another entity
    - A1: Received - claim has been received
    - A2: Pending - claim is pending
    - A3: Rejected - claim is rejected
    - A4: Not Found - claim not found
    - A5: Split - claim has been split
    - A6: Terminated - claim processing terminated
    - A7: Pending Review - awaiting additional information
    - A8: Finalized - adjudication complete
    
    Status Codes (STC01-2, more specific):
    - 0: Cannot provide status
    - 1: Rejected for missing information
    - 2: Pending review
    - 3: Payment issued
    - 4: Payment denied
    - 15: Entity's coverage suspended
    - 20: Claim/service lacks required information
    - 21: Missing/invalid patient ID
    - 22: Invalid payer ID
    - 33: Input errors
    - 35: Claim/service denied
    """
    
    STATUS_CATEGORY_CODES = {
        "A0": "Forwarded",
        "A1": "Received",
        "A2": "Pending",
        "A3": "Rejected",
        "A4": "Not Found",
        "A5": "Split",
        "A6": "Terminated",
        "A7": "Pending Review",
        "A8": "Finalized"
    }
    
    STATUS_CODES = {
        "0": "Cannot provide status",
        "1": "Rejected - missing information",
        "2": "Pending review",
        "3": "Payment issued",
        "4": "Payment denied",
        "15": "Coverage suspended",
        "20": "Lacks required information",
        "21": "Missing/invalid patient ID",
        "22": "Invalid payer ID",
        "33": "Input errors",
        "35": "Claim denied",
        "65": "Awaiting additional information",
        "85": "Authorization required",
        "100": "In process",
        "101": "Pending payer review",
        "102": "Pending provider information"
    }
    
    def parse(self, edi_content: str) -> Parsed277:
        """Parse 277 EDI content into structured data."""
        
        segments = self._split_segments(edi_content)
        
        isa = self._find_segment(segments, "ISA")
        gs = self._find_segment(segments, "GS")
        
        transaction_id = self._extract_element(isa, 13) if isa else ""
        sender_id = self._extract_element(gs, 2) if gs else ""
        receiver_id = self._extract_element(gs, 3) if gs else ""
        transaction_date = self._parse_date(self._extract_element(gs, 4)) if gs else datetime.now()
        
        payer_name = self._extract_payer_name(segments)
        
        claims = self._parse_all_claims(segments)
        
        return Parsed277(
            transaction_id=transaction_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            transaction_date=transaction_date,
            payer_name=payer_name,
            claims=claims,
            raw_edi=edi_content
        )
    
    def _split_segments(self, edi: str) -> List[str]:
        """Split EDI into segments."""
        edi = edi.replace("\n", "").replace("\r", "")
        if "~" in edi:
            return [s.strip() for s in edi.split("~") if s.strip()]
        return [s.strip() for s in edi.split("\n") if s.strip()]
    
    def _find_segment(self, segments: List[str], segment_id: str) -> Optional[str]:
        """Find first segment matching ID."""
        for seg in segments:
            if seg.startswith(segment_id + "*"):
                return seg
        return None
    
    def _find_all_segments(self, segments: List[str], segment_id: str) -> List[str]:
        """Find all segments matching ID."""
        return [s for s in segments if s.startswith(segment_id + "*")]
    
    def _extract_element(self, segment: str, position: int) -> str:
        """Extract element at position from segment."""
        if not segment:
            return ""
        elements = segment.split("*")
        return elements[position] if position < len(elements) else ""
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date from YYYYMMDD format."""
        try:
            return datetime.strptime(date_str[:8], "%Y%m%d")
        except Exception:
            return datetime.now()
    
    def _extract_payer_name(self, segments: List[str]) -> str:
        """Extract payer name from NM1*PR segment."""
        for seg in segments:
            if seg.startswith("NM1*PR"):
                elements = seg.split("*")
                return elements[3] if len(elements) > 3 else "Unknown Payer"
        return "Unknown Payer"
    
    def _parse_all_claims(self, segments: List[str]) -> List[ClaimStatusDetail]:
        """Parse all claim status details from 277."""
        claims = []
        
        current_claim_data: dict = {}
        
        for i, seg in enumerate(segments):
            if seg.startswith("TRN*"):
                if current_claim_data:
                    claim = self._build_claim_status(current_claim_data)
                    if claim:
                        claims.append(claim)
                current_claim_data = {"trn": seg}
            
            elif seg.startswith("STC*"):
                current_claim_data["stc"] = seg
            
            elif seg.startswith("REF*"):
                current_claim_data["ref"] = seg
            
            elif seg.startswith("DTP*"):
                current_claim_data.setdefault("dtp", []).append(seg)
            
            elif seg.startswith("AMT*"):
                current_claim_data["amt"] = seg
            
            elif seg.startswith("NM1*QC"):
                current_claim_data["patient"] = seg
        
        if current_claim_data:
            claim = self._build_claim_status(current_claim_data)
            if claim:
                claims.append(claim)
        
        return claims
    
    def _build_claim_status(self, data: dict) -> Optional[ClaimStatusDetail]:
        """Build ClaimStatusDetail from parsed segments."""
        if "stc" not in data:
            return None
        
        stc = data["stc"].split("*")
        trn = data.get("trn", "").split("*")
        patient = data.get("patient", "").split("*")
        amt = data.get("amt", "").split("*")
        
        status_info = stc[1].split(":") if len(stc) > 1 else ["A1"]
        category_code = status_info[0] if status_info else "A1"
        status_code = status_info[1] if len(status_info) > 1 else "0"
        
        finalized = category_code == "A8"
        paid = status_code == "3"
        
        try:
            billed_amount = float(amt[2]) if len(amt) > 2 else 0.0
        except Exception:
            billed_amount = 0.0
        
        try:
            paid_amount = float(stc[4]) if len(stc) > 4 and paid else None
        except Exception:
            paid_amount = None
        
        return ClaimStatusDetail(
            claim_id=trn[2] if len(trn) > 2 else "",
            patient_name=f"{patient[3]} {patient[4]}" if len(patient) > 4 else "Unknown",
            patient_dob=None,
            payer_name="",
            payer_claim_control_number=trn[2] if len(trn) > 2 else "",
            service_date=self._parse_date(stc[2]) if len(stc) > 2 else datetime.now(),
            billed_amount=billed_amount,
            status_category_code=category_code,
            status_category_description=self.STATUS_CATEGORY_CODES.get(category_code, "Unknown"),
            status_code=status_code,
            status_description=self.STATUS_CODES.get(status_code, "Unknown status"),
            effective_date=datetime.now(),
            adjudication_finalized=finalized,
            paid_amount=paid_amount,
            check_number=None,
            remittance_date=None
        )
