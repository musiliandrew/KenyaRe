# app.py
import streamlit as st
import pandas as pd
from main import Manager


import time
from io import BytesIO
from fpdf import FPDF

# Use session state to persist manager and extracted data
if 'manager' not in st.session_state:
    st.session_state.manager = Manager()
if 'extracted_results' not in st.session_state:
    st.session_state.extracted_results = None
if 'attachment_names' not in st.session_state:
    st.session_state.attachment_names = None


st.set_page_config(page_title="Reinsurance Claims Processing Dashboard", layout="wide")

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", [
    "📥 Document Ingestion",
    "🚨 Exception Management",
    "📊 Reporting & SICS Integration"
])

# ---- Page 1: Document Ingestion ----
if page == "📥 Document Ingestion":
    st.title("📥 Document Ingestion Agent")
    st.write("Upload and classify documents (Bordereaux, Account Statements, Cash Calls, Treaty Slips).")

    uploaded_file = st.file_uploader("Upload Documents", type=["msg"])
    if uploaded_file:
        st.success(f"Received: {uploaded_file.name}")
        placeholder = st.empty()
        placeholder.text("Processing file")
        time.sleep(1)
        placeholder.text("Extracting files and info from msg files")
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".msg") as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name
        response = st.session_state.manager.ingest_file(tmp_path)
        placeholder.text(f"Extracting data from {response['attachment_count']} marine pdf(s)")
        if response['attachment_count'] == 0:
            st.warning("No marine attachments found in the uploaded .msg file.")
            st.session_state.extracted_results = None
            st.session_state.attachment_names = None
        else:
            try:
                results = st.session_state.manager.process_using_model()
                st.session_state.extracted_results = results
                st.session_state.attachment_names = response['attachment_names']
            except Exception as e:
                st.error(f"Error during model processing: {e}")
                st.session_state.extracted_results = None
                st.session_state.attachment_names = None

    # Display extracted data if available
    if st.session_state.extracted_results and st.session_state.attachment_names:
        st.subheader("Extracted Data")
        for idx, data in enumerate(st.session_state.extracted_results):
            # Convert Output object to dict if needed
            if hasattr(data, 'model_dump'):
                data_dict = data.model_dump()
            elif isinstance(data, dict):
                data_dict = data
            else:
                data_dict = dict(data)
            st.markdown(f"---\n#### Attachment {idx+1}: {st.session_state.attachment_names[idx]}")
            st.markdown(f"**Insurance Company:** {data_dict.get('insurance_company', '')}")
            st.markdown(f"**Quarter:** {data_dict.get('quarter', '')}")
            st.markdown(f"**Total Income:** {data_dict.get('total_income', '')}")
            st.markdown(f"**Commission:** {data_dict.get('commision', '')}")
            st.markdown(f"**Premium Tax:** {data_dict.get('premium_tax', '')}")
            st.markdown("**Borderaux Table:**")
            if data_dict.get('borderaux'):
                st.table(pd.DataFrame(data_dict['borderaux']))
            else:
                st.info("No borderaux table found.")
            st.markdown("**Issues:**")
            if data_dict.get('issues'):
                for issue in data_dict['issues']:
                    st.warning(issue)
            else:
                st.success("No issues found.")



# ---- Page 3: Exception Management ----
elif page == "🚨 Exception Management":
    st.title("🚨 Exception Management Agent")
    st.write("All issues detected during document ingestion are listed below.")

    # Gather all issues from extracted results
    issues_list = []
    if st.session_state.extracted_results and st.session_state.attachment_names:
        for idx, data in enumerate(st.session_state.extracted_results):
            # Convert Output object to dict if needed
            if hasattr(data, 'model_dump'):
                data_dict = data.model_dump()
            elif isinstance(data, dict):
                data_dict = data
            else:
                data_dict = dict(data)
            if data_dict.get('issues'):
                for issue in data_dict['issues']:
                    issues_list.append({
                        "Attachment": st.session_state.attachment_names[idx],
                        "Issue": issue
                    })
    if issues_list:
        st.subheader("Exception Queue")
        st.table(pd.DataFrame(issues_list))
    else:
        st.success("No issues detected in the ingested documents.")



# ---- Page 3: Reporting & SICS Integration ----
elif page == "📊 Reporting & SICS Integration":
    st.title("📊 Reporting & SICS Integration Agent")
    st.write("Generate exception reports and booking-ready summaries.")

    # Agent to generate a summary report
    def report_agent(extracted_results, attachment_names):
        summary = []
        issues = []
        if extracted_results and attachment_names:
            for idx, data in enumerate(extracted_results):
                if hasattr(data, 'model_dump'):
                    data_dict = data.model_dump()
                elif isinstance(data, dict):
                    data_dict = data
                else:
                    data_dict = dict(data)
                summary.append({
                    "Attachment": attachment_names[idx],
                    "Insurance Company": data_dict.get('insurance_company', ''),
                    "Quarter": data_dict.get('quarter', ''),
                    "Total Income": data_dict.get('total_income', ''),
                    "Commission": data_dict.get('commision', ''),
                    "Premium Tax": data_dict.get('premium_tax', '')
                })
                if data_dict.get('issues'):
                    for issue in data_dict['issues']:
                        issues.append({
                            "Attachment": attachment_names[idx],
                            "Issue": issue
                        })
        return summary, issues

    summary, issues_list = report_agent(st.session_state.extracted_results, st.session_state.attachment_names)

    # Show summary table
    if summary:
        st.subheader("Summary Data")
        st.table(pd.DataFrame(summary))
    else:
        st.info("No extracted data available.")

    # Show issues table
    if issues_list:
        st.subheader("Exception Queue")
        st.table(pd.DataFrame(issues_list))
    else:
        st.success("No issues detected in the ingested documents.")

    # Generate PDF report
    def generate_pdf_report():
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=14)
        pdf.cell(0, 10, "Exception & Summary Report", ln=True, align="C")
        pdf.ln(10)
        if issues_list:
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, "Issues Detected:", ln=True)
            for item in issues_list:
                pdf.multi_cell(0, 10, f"Attachment: {item['Attachment']}\nIssue: {item['Issue']}", border=0)
                pdf.ln(2)
        else:
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, "No issues detected in the ingested documents.", ln=True)
        pdf.ln(10)
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, "Summary Data:", ln=True)
        if summary:
            for item in summary:
                pdf.cell(0, 10, f"Attachment: {item['Attachment']}", ln=True)
                pdf.cell(0, 10, f"Insurance Company: {item['Insurance Company']}", ln=True)
                pdf.cell(0, 10, f"Quarter: {item['Quarter']}", ln=True)
                pdf.cell(0, 10, f"Total Income: {item['Total Income']}", ln=True)
                pdf.cell(0, 10, f"Commission: {item['Commission']}", ln=True)
                pdf.cell(0, 10, f"Premium Tax: {item['Premium Tax']}", ln=True)
                pdf.ln(5)
        else:
            pdf.cell(0, 10, "No extracted data available.", ln=True)
        pdf_bytes = pdf.output(dest='S').encode('latin1')
        pdf_output = BytesIO(pdf_bytes)
        return pdf_output

    pdf_bytes = generate_pdf_report()
    st.download_button(
        label="⬇️ Download Exception & Summary Report (PDF)",
        data=pdf_bytes,
        file_name="exception_summary_report.pdf",
        mime="application/pdf"
    )

    st.download_button("⬇️ Download Booking Ready Report (Excel)", "Excel content here", file_name="booking_report.xlsx")
