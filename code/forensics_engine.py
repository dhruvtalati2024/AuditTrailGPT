# forensics_engine.py
import re
import json
from typing import List, Dict, Any
from collections import Counter
from datetime import datetime

# 1. Original Kaggle-style alert pattern
KAGGLE_PATTERN = re.compile(
    r"^\s*\d+\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*"
    r"Case\s*ID\s+(FC\d{6})\s*\|\s*"
    r"(.*?)\s+detected\s+involving\s+cross-border\s+entities,\s*"
    r"automated\s+alert\s+triggered\.\s*\|\s*"
    r"Amount:\s*\$([\d,]+)",
    re.IGNORECASE
)

# 2. AMLSim-style block detection
BEGIN_PATTERN = re.compile(r"^BEGIN LAUNDERING ATTEMPT - (\w+(?:-\w+)*)", re.IGNORECASE)
END_PATTERN = re.compile(r"^END LAUNDERING ATTEMPT", re.IGNORECASE)

# Transaction line pattern (simplified – we only need date and amount)
TX_PATTERN = re.compile(
    r"^(\d{4}/\d{2}/\d{2})\s+\d{2}:\d{2},.*?,\d+,\w+,([\d.]+),\w+",
    re.IGNORECASE
)

def parse_kaggle_format(lines: List[str]) -> List[Dict[str, Any]]:
    events = []
    for line_num, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line:
            continue
        match = KAGGLE_PATTERN.search(raw_line)
        if match:
            date, case_id, alert_type, amount_str = match.groups()
            amount = int(amount_str.replace(',', ''))
            events.append({
                "timestamp": f"{date} 00:00:00",
                "event_type": "FINANCIAL_CRIME_ALERT",
                "raw_log": raw_line.rstrip(),
                "details": {
                    "date": date,
                    "case_id": case_id,
                    "alert_type": alert_type.strip(),
                    "amount": amount
                }
            })
        else:
            events.append({
                "timestamp": "N/A",
                "event_type": "UNKNOWN",
                "raw_log": raw_line.rstrip(),
                "details": {"error": f"Unmatched line {line_num}"}
            })
    return events

def parse_amlsim_format(lines: List[str]) -> List[Dict[str, Any]]:
    events = []
    current_typology = None
    current_txs = []
    line_num = 0

    while line_num < len(lines):
        raw_line = lines[line_num].strip()
        line_num += 1

        begin_match = BEGIN_PATTERN.match(raw_line)
        if begin_match:
            if current_typology and current_txs:  # Save previous block
                events.extend(summarize_block(current_typology, current_txs))
            current_typology = begin_match.group(1).upper().replace("-", "_")
            current_txs = []
            continue

        end_match = END_PATTERN.match(raw_line)
        if end_match and current_typology:
            events.extend(summarize_block(current_typology, current_txs))
            current_typology = None
            current_txs = []
            continue

        if current_typology:
            tx_match = TX_PATTERN.match(raw_line)
            if tx_match:
                date_str, amount_str = tx_match.groups()
                try:
                    amount = float(amount_str)
                    # Convert date format 2022/09/01 → 2022-09-01
                    date = datetime.strptime(date_str, "%Y/%m/%d").strftime("%Y-%m-%d")
                    current_txs.append({"date": date, "amount": amount})
                except:
                    pass  # Skip malformed lines

    # Final block if file ends without END
    if current_typology and current_txs:
        events.extend(summarize_block(current_typology, current_txs))

    return events

def summarize_block(typology: str, txs: List[Dict]) -> List[Dict[str, Any]]:
    if not txs:
        return []
    total_amount = sum(tx["amount"] for tx in txs)
    dates = sorted(set(tx["date"] for tx in txs))
    start_date = dates[0]
    end_date = dates[-1]
    case_id = f"SYN{typology[:2]}{len(txs):04d}"  # Synthetic case ID

    return [{
        "timestamp": f"{start_date} 00:00:00",
        "event_type": "FINANCIAL_CRIME_ALERT",
        "raw_log": f"Synthetic alert from {typology} block ({len(txs)} transactions)",
        "details": {
            "date": start_date,
            "case_id": case_id,
            "alert_type": typology.replace("_", "-"),
            "amount": int(total_amount),  # Convert to int for consistency
            "transaction_count": len(txs),
            "period": f"{start_date} to {end_date}"
        }
    }]

def extract_causal_chain(raw_logs: str) -> str:
    lines = raw_logs.strip().split('\n')

    # Detect format
    has_kaggle = any(KAGGLE_PATTERN.search(line) for line in lines[:50])  # Check first 50 lines
    has_amlsim = any(BEGIN_PATTERN.search(line) for line in lines)

    if has_kaggle:
        parsed_events = parse_kaggle_format(lines)
    elif has_amlsim:
        parsed_events = parse_amlsim_format(lines)
    else:
        # Fallback: treat as unknown
        parsed_events = [{
            "timestamp": "N/A",
            "event_type": "UNKNOWN",
            "raw_log": line.rstrip(),
            "details": {"error": "Unsupported log format"}
        } for line in lines if line.strip()]

    # Sort by timestamp
    parsed_events.sort(key=lambda x: x["timestamp"] if x["timestamp"] != "N/A" else "9999-99-99")

    valid = [e for e in parsed_events if e["event_type"] == "FINANCIAL_CRIME_ALERT"]
    total_alerts = len(valid)
    total_amount = sum(e["details"]["amount"] for e in valid if isinstance(e["details"].get("amount"), (int, float)))

    return json.dumps({
        "causal_chain": parsed_events,
        "summary": {
            "total_alerts": total_alerts,
            "total_amount_at_risk": int(total_amount),
            "total_lines": len(lines),
            "unmatched_lines": len(lines) - total_alerts,
            "detected_format": "KAGGLE" if has_kaggle else "AMLSIM" if has_amlsim else "UNKNOWN"
        }
    }, indent=2)
