from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class Claim277CAStatus:
    """Individual claim status from 277CA."""
    claim_id: str
    status_code: str
    status_description: str
    rejection_reason_code: Optional[str]
    rejection_reason_description: Optional[str]
    original_claim_amount: float
    received_date: datetime


@dataclass
class Parsed277CA:
    """Parsed 277CA Claim Acknowledgment."""
    transaction_id: str
    sender_id: str
    receiver_id: str
    transaction_date: datetime
    total_claims: int
    accepted_count: int
    rejected_count: int
    claims: List[Claim277CAStatus]
    raw_edi: str


class Parser277CA:
    """
    Parser for X12 277CA Claim Acknowledgment transactions.
    
    277CA is sent by clearinghouse/payer within 24-48 hours of 837 receipt
    to confirm whether claims were accepted for processing or rejected.
    
    Key Status Codes:
    - A1: Accepted for processing
    - A2: Accepted with errors (warnings, will process)
    - A3: Rejected (will not process, must fix and resubmit)
    - A4: Rejected - Not found
    - A5: Rejected - Split
    - A6: Rejected - Terminated
    - A7: Pending adjudication
    - A8: Finalized - payment or denial issued
    """
    
    STATUS_CODES = {
        "A1": "Accepted - Claim/encounter has been received",
        "A2": "Accepted with errors - Claim/encounter has been accepted but has errors",
        "A3": "Rejected - Claim/encounter has been rejected",
        "A4": "Not Found - Claim/encounter could not be found",
        "A5": "Split - Claim/encounter has been split",
        "A6": "Terminated - Claim/encounter has been terminated",
        "A7": "Pending - Claim/encounter is pending adjudication",
        "A8": "Finalized - Claim/encounter processing complete"
    }
    
    REJECTION_CODES = {
        "T1": "Invalid/missing member ID",
        "T2": "Invalid/missing member name",
        "T3": "Invalid/missing member DOB",
        "T4": "Invalid/missing provider ID",
        "T5": "Invalid/missing service date",
        "T6": "Invalid/missing diagnosis code",
        "T7": "Invalid/missing procedure code",
        "T8": "Duplicate claim",
        "T9": "Invalid payer ID",
        "T10": "Claim not found for adjustment",
        "T11": "Invalid claim frequency code",
        "T12": "Invalid claim total charge",
        "T13": "Invalid service line charge",
        "T14": "Invalid units of service",
        "T15": "Missing/invalid prior authorization"
    }
    
    def parse(self, edi_content: str) -> Parsed277CA:
        """Parse 277CA EDI content into structured data."""
        
        segments = self._split_segments(edi_content)
        
        isa = self._find_segment(segments, "ISA")
        gs = self._find_segment(segments, "GS")
        
        transaction_id = self._extract_element(isa, 13) if isa else ""
        sender_id = self._extract_element(gs, 2) if gs else ""
        receiver_id = self._extract_element(gs, 3) if gs else ""
        transaction_date = self._parse_date(self._extract_element(gs, 4)) if gs else datetime.now()
        
        claims = []
        stc_segments = [s for s in segments if s.startswith("STC")]
        
        for stc in stc_segments:
            claim = self._parse_stc_segment(stc, segments)
            if claim:
                claims.append(claim)
        
        accepted = sum(1 for c in claims if c.status_code in ["A1", "A2", "A7", "A8"])
        rejected = sum(1 for c in claims if c.status_code in ["A3", "A4", "A6"])
        
        return Parsed277CA(
            transaction_id=transaction_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            transaction_date=transaction_date,
            total_claims=len(claims),
            accepted_count=accepted,
            rejected_count=rejected,
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
            if seg.startswith(segment_id + "*") or seg.startswith(segment_id + ":"):
                return seg
        return None
    
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
    
    def _parse_stc_segment(self, stc: str, all_segments: List[str]) -> Optional[Claim277CAStatus]:
        """Parse STC segment into claim status."""
        elements = stc.split("*")
        if len(elements) < 2:
            return None
        
        status_info = elements[1].split(":") if len(elements) > 1 else []
        status_code = status_info[0] if status_info else "A1"
        
        rejection_code = status_info[1] if len(status_info) > 1 and status_code == "A3" else None
        
        claim_id = self._extract_claim_id(all_segments, stc)
        
        amount = self._extract_amount(all_segments, stc)
        
        return Claim277CAStatus(
            claim_id=claim_id,
            status_code=status_code,
            status_description=self.STATUS_CODES.get(status_code, "Unknown"),
            rejection_reason_code=rejection_code,
            rejection_reason_description=self.REJECTION_CODES.get(rejection_code, "") if rejection_code else None,
            original_claim_amount=amount,
            received_date=datetime.now()
        )
    
    def _extract_claim_id(self, segments: List[str], stc_segment: str) -> str:
        """Extract claim ID from surrounding TRN segment."""
        stc_idx = segments.index(stc_segment) if stc_segment in segments else 0
        for i in range(stc_idx - 1, max(0, stc_idx - 5), -1):
            if segments[i].startswith("TRN"):
                elements = segments[i].split("*")
                return elements[2] if len(elements) > 2 else ""
        return f"CLM-{stc_idx}"
    
    def _extract_amount(self, segments: List[str], stc_segment: str) -> float:
        """Extract claim amount from AMT segment."""
        stc_idx = segments.index(stc_segment) if stc_segment in segments else 0
        for i in range(stc_idx + 1, min(len(segments), stc_idx + 5)):
            if segments[i].startswith("AMT"):
                elements = segments[i].split("*")
                try:
                    return float(elements[2]) if len(elements) > 2 else 0.0
                except Exception:
                    return 0.0
        return 0.0
