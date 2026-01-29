import streamlit as st
import json
import datetime
import os
import tempfile
import atexit
from llm_interface import get_forensic_narrative

# Cleanup temporary PDF files on exit
def cleanup_temp_files():
    for file_path in st.session_state.get("temp_pdf_files", []):
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except:
            pass

atexit.register(cleanup_temp_files)

# App Configuration
PROJECT_TITLE = "AudiTrailGPT: Neuro-Symbolic Forensic Analysis"
USER_NAME = "Group 2"

st.set_page_config(layout="wide", page_title=PROJECT_TITLE, page_icon="🕵️")
st.title(PROJECT_TITLE)
st.markdown(f"**Developed by:** {USER_NAME}")
st.markdown("---")

# Initialize session state
if "results" not in st.session_state:
    st.session_state.results = None
if "temp_pdf_files" not in st.session_state:
    st.session_state.temp_pdf_files = []
if "last_file" not in st.session_state:
    st.session_state.last_file = None

# Upload Section
st.header("1. Upload Audit Log File (.txt)")

uploaded_file = st.file_uploader(
    "Choose a .txt file with financial crime alert logs",
    type=["txt"],
    help="Supported format: Line | Date | CaseID | Alert Type ... | Amount: $xxxxx"
)

if uploaded_file is not None:
    if st.session_state.last_file != uploaded_file.name:
        st.session_state.results = None
        st.session_state.temp_pdf_files = []
        st.session_state.last_file = uploaded_file.name

    raw_logs = uploaded_file.read().decode("utf-8", errors="ignore")
    st.success(f"Loaded: **{uploaded_file.name}** — {len(raw_logs.splitlines())} lines")

    if st.button("🔍 Analyze Logs & Generate Forensic Report", type="primary", use_container_width=True):
        with st.spinner("Running Llama-3.3-70B (OpenRouter Free) + Symbolic Engine…"):
            try:
                results = get_forensic_narrative(raw_logs)
                st.session_state.results = results
                st.success("✅ Analysis Complete! Report Ready.")
                st.balloons()
            except Exception as e:
                st.error("❌ Analysis failed. Check internet or API status.")
                st.exception(e)

else:
    st.info("👆 Please upload a .txt audit log file to begin analysis.")
    st.stop()

# Results Display
if st.session_state.results:
    st.markdown("---")
    st.header("2. Forensic Analysis Results")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🧾 Symbolic Output (Parsed Causal Chain)")
        try:
            parsed = json.loads(st.session_state.results["causal_chain"])
            st.json(parsed, expanded=False)
        except:
            st.code(st.session_state.results["causal_chain"], language="json")

    with col2:
        st.subheader("📜 Neuro Output (Llama-3.3 Forensic Narrative)")
        st.markdown(st.session_state.results["narrative"])

    # PDF Generation
    st.markdown("---")
    st.subheader("📄 Download Professional Forensic Report (PDF)")

    from report_generator import generate_coverity_style_pdf

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"AudiTrailGPT_Forensic_Report_{timestamp}.pdf"

    if st.button("🎯 Generate & Download PDF Report", type="primary", use_container_width=True):
        with st.spinner("Generating professional PDF report…"):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    generate_coverity_style_pdf(
                        report_data=st.session_state.results,
                        filename=tmp.name,
                        source_file=uploaded_file.name
                    )
                    temp_path = tmp.name

                st.session_state.temp_pdf_files.append(temp_path)

                with open(temp_path, "rb") as pdf_file:
                    st.download_button(
                        label="⬇️ Download Full Forensic Report (PDF)",
                        data=pdf_file.read(),
                        file_name=pdf_filename,
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )
                st.success("✅ PDF report ready!")
            except Exception as e:
                st.error("❌ PDF generation failed.")
                st.code(str(e))

# Sidebar
with st.sidebar:
    st.header("🛠 AudiTrailGPT")
    st.markdown("**Neuro-Symbolic Forensic Engine**")
    st.markdown("Powered by **Llama-3.3-70B Instruct** (OpenRouter **Free Tier**)")
    st.markdown("---")
    st.markdown("### How It Works")
    st.markdown("""
    1. Upload audit log (.txt)  
    2. Symbolic parser extracts facts  
    3. LLM generates detailed narrative  
    4. Export professional PDF report
    """)
    st.markdown("---")
    st.markdown("**Status:** ✅ Fully free • No rate limits • Stable")
    st.markdown("© 2025 Group 2")
    st.caption("Powered by OpenRouter • Reliable & Unlimited")
