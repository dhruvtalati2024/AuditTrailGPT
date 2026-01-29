# llm_interface.py - FINAL FIXED VERSION (No Syntax Errors)
import json
from openai import OpenAI
from forensics_engine import extract_causal_chain

# YOUR OPENROUTER API KEY
OPENROUTER_API_KEY = " "

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

# Primary model (tool-capable when possible)
MODEL_PRIMARY = "meta-llama/llama-3.3-70b-instruct:free"

# Reliable fallback models (no tool issues)
MODEL_FALLBACKS = [
    "qwen/qwen-2.5-72b-instruct:free",
    "google/gemma-2-27b-it:free",
    "microsoft/phi-3-medium-128k-instruct:free"
]

def get_forensic_narrative(raw_logs: str):
    # Run symbolic parser first (always works)
    structured_json = extract_causal_chain(raw_logs=raw_logs)
    
    try:
        chain_data = json.loads(structured_json)
        summary = chain_data.get('summary', {})
        total_alerts = summary.get('total_alerts', 0)
        total_amount = summary.get('total_amount_at_risk', 0)
        format_detected = summary.get('detected_format', 'UNKNOWN')
        
        typologies = list(set(
            e['details'].get('alert_type', 'N/A')
            for e in chain_data.get('causal_chain', [])
            if e['event_type'] == 'FINANCIAL_CRIME_ALERT'
        ))
        
        chain_summary = (
            f"**{total_alerts} alerts parsed** | "
            f"**${total_amount:,} at risk** | "
            f"Format: {format_detected}\n"
            f"Detected typologies: {', '.join(typologies) if typologies else 'None'}"
        )
    except Exception:
        chain_summary = "**Symbolic parsing completed with minor issues.**"

    # Try tool-calling first
    narrative = try_tool_calling(raw_logs, structured_json)
    
    # Fallback if tool calling fails
    if "Error" in narrative or "failed" in narrative.lower() or "TOOL_CALL_FAILED" in narrative:
        narrative = try_fallback_analysis(raw_logs, structured_json, chain_summary)

    return {
        "narrative": narrative,
        "causal_chain": structured_json
    }

def try_tool_calling(raw_logs: str, structured_json: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a senior Anti-Money Laundering (AML) forensic investigator. "
                "Your goal is to produce an EXHAUSTIVE, highly detailed, and insightful forensic report. "
                "The report must be a VERY LONG, comprehensive document (at least 2000 words if data permits) in clean, professional markdown format. "
                "You MUST use ONLY the structured causal chain provided by the tool to generate the narrative. "
                "The report MUST include these mandatory sections with granular detail:\n\n"
                "## 1. Executive Summary and Key Findings\n"
                "   - Provide a high-level overview of the entire investigation.\n"
                "   - Highlight the most critical risks and immediate concerns.\n"
                "## 2. Comprehensive Event Timeline\n"
                "   - Present a detailed table of all detected events.\n"
                "   - Include timestamps, event types, and specific financial details.\n"
                "## 3. Threat Assessment and Risk Indicators\n"
                "   - Perform a deep dive into specific risk indicators found in the data.\n"
                "   - Use data-driven metrics to justify risk levels.\n"
                "## 4. In-Depth Pattern and Trend Analysis\n"
                "   - Identify recurring behaviors, structural anomalies, and suspicious sequences.\n"
                "   - Explain the 'how' and 'why' behind the detected patterns.\n"
                "## 5. Financial Impact and Exposure Assessment\n"
                "   - Quantify the total exposure and potential loss.\n"
                "   - Analyze the flow of funds and identify primary beneficiaries or sinks.\n"
                "## 6. Money Laundering Typologies and Red Flags\n"
                "   - Map findings to known AML typologies (e.g., structuring, layering, smurfing).\n"
                "   - List specific red flags triggered by the observed activities.\n"
                "## 7. Granular Investigation Recommendations\n"
                "   - Provide actionable, step-by-step next steps for the investigation team.\n"
                "   - Suggest specific entities or accounts for further scrutiny.\n\n"
                "Use **bold text** for emphasis, extensive tables, and multi-level bulleted lists. "
                "Maintain a formal, investigative tone. DO NOT fabricate information, but be exhaustive in your analysis of the provided data."
            )
        },
        {"role": "user", "content": f"Analyze these financial crime alerts and provide an exhaustive forensic report:\n\n---\n{raw_logs[:4000]}...\n---"}
    ]

    TOOL_SCHEMA = {
        "type": "function",
        "function": {
            "name": "extract_causal_chain",
            "description": "Extract structured facts from financial crime logs.",
            "parameters": {
                "type": "object",
                "properties": {"raw_logs": {"type": "string"}},
                "required": ["raw_logs"]
            }
        }
    }

    try:
        response = client.chat.completions.create(
            model=MODEL_PRIMARY,
            messages=messages,
            tools=[TOOL_SCHEMA],
            tool_choice={"type": "function", "function": {"name": "extract_causal_chain"}},
            temperature=0.3,
            stream=False,
            max_tokens=8000
        )
        
        msg = response.choices[0].message
        if msg.tool_calls:
            messages.append(msg)
            messages.append({
                "role": "tool",
                "tool_call_id": msg.tool_calls[0].id,
                "name": "extract_causal_chain",
                "content": structured_json
            })
            
            final = client.chat.completions.create(
                model=MODEL_PRIMARY,
                messages=messages,
                temperature=0.4,
                stream=False,
                max_tokens=8000
            )
            return final.choices[0].message.content.strip()
            
    except Exception as e:
        print(f"Tool calling failed: {str(e)}")
    
    return "TOOL_CALL_FAILED"

def try_fallback_analysis(raw_logs: str, structured_json: str, chain_summary: str) -> str:
    # Use .format() to safely embed variables — avoids f-string triple-quote conflict
    prompt_template = """You are a senior Anti-Money Laundering (AML) forensic investigator.

**STRUCTURED CAUSAL CHAIN ALREADY EXTRACTED** (use ONLY this data):
{chain_summary}

**FULL JSON CAUSAL CHAIN**:
```json
{structured_json}
```

**YOUR TASK**:
Produce an EXHAUSTIVE, highly detailed, and insightful forensic report.
The report must be a VERY LONG, comprehensive document (at least 2000 words if data permits) in clean, professional markdown format.
The report MUST include these mandatory sections with granular detail:

## 1. Executive Summary and Key Findings
   - Provide a high-level overview of the entire investigation.
   - Highlight the most critical risks and immediate concerns.
## 2. Comprehensive Event Timeline
   - Present a detailed table of all detected events.
   - Include timestamps, event types, and specific financial details.
## 3. Threat Assessment and Risk Indicators
   - Perform a deep dive into specific risk indicators found in the data.
   - Use data-driven metrics to justify risk levels.
## 4. In-Depth Pattern and Trend Analysis
   - Identify recurring behaviors, structural anomalies, and suspicious sequences.
   - Explain the 'how' and 'why' behind the detected patterns.
## 5. Financial Impact and Exposure Assessment
   - Quantify the total exposure and potential loss.
   - Analyze the flow of funds and identify primary beneficiaries or sinks.
## 6. Money Laundering Typologies and Red Flags
   - Map findings to known AML typologies (e.g., structuring, layering, smurfing).
   - List specific red flags triggered by the observed activities.
## 7. Granular Investigation Recommendations
   - Provide actionable, step-by-step next steps for the investigation team.
   - Suggest specific entities or accounts for further scrutiny.

Use **bold text** for emphasis, extensive tables, and multi-level bulleted lists.
Maintain a formal, investigative tone. DO NOT fabricate information, but be exhaustive in your analysis of the provided data.

**RAW LOGS FOR CONTEXT ONLY**:
{raw_logs}
"""

    for model in MODEL_FALLBACKS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt_template.format(
                        chain_summary=chain_summary,
                        structured_json=structured_json,
                        raw_logs=raw_logs[:3000]
                    )}
                ],
                temperature=0.4,
                max_tokens=8000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Fallback model {model} failed: {str(e)}")
            continue

    return "Error: All models failed to generate a narrative."