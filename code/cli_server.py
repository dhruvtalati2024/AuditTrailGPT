import argparse
import os
import datetime
from llm_interface import get_forensic_narrative
from report_generator import generate_coverity_style_pdf

def main():
    parser = argparse.ArgumentParser(description="AudiTrailGPT CLI: Generate AML forensic report")
    parser.add_argument("input_file", help="Path to .txt log file")
    parser.add_argument("-o", "--output", default=None, help="Output PDF path (optional)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"Error: File '{args.input_file}' not found.")
        return
    
    with open(args.input_file, "r", encoding="utf-8", errors="ignore") as f:
        raw_logs = f.read()
    
    print("Analyzing...")
    results = get_forensic_narrative(raw_logs)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_name = args.output or f"AudiTrailGPT_Report_{timestamp}.pdf"
    
    print("Generating PDF...")
    generate_coverity_style_pdf(results, pdf_name, os.path.basename(args.input_file))
    
    print(f"Report saved: {pdf_name}")

if __name__ == "__main__":
    main()