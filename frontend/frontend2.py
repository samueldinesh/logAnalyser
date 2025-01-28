import streamlit as st
import requests
import pandas as pd

# Backend API URL
API_URL = "http://127.0.0.1:8000"

# Streamlit app title
st.title("Log File Analysis Bot with GenAI")

# File Upload
uploaded_file = st.file_uploader("Upload your log file (max size: 5MB)", type=["txt", "log"])

if uploaded_file is not None:
    # Show preview of the file content
    log_content = uploaded_file.read().decode("utf-8")
    st.subheader("Log File Content Preview")
    st.text_area("Preview", log_content, height=150)

    # Error Analysis
    if st.button("Analyze Errors"):
        with st.spinner("Analyzing errors..."):
            try:
                # Prepare file for upload
                files = {"file": (uploaded_file.name, log_content)}#, "text/plain")}
                response = requests.post(f"{API_URL}/basic-analysis/", files=files)

                if response.status_code == 200:
                    error_summary = response.json().get("Error Summary", [])
                    print("200 & len:", len(error_summary))
                    if error_summary:
                        st.write("### Error Summary")
                        error_df = pd.DataFrame(error_summary)
                        st.dataframe(error_df)
                        st.download_button(
                            label="Download Error Summary as CSV",
                            data=error_df.to_csv(index=False),
                            file_name="error_summary.csv",
                            mime="text/csv",
                        )
                    else:
                        st.info("No errors found in the log file.")
                else:
                    st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
            except Exception as e:
                st.error(f"An error occurred during analysis: {e}")

    # Log Summarization
    if st.button("Summarize Log"):
        with st.spinner("Generating summary..."):
            try:
                files = {"file": (uploaded_file.name, log_content)}
                response = requests.post(f"{API_URL}/summarize-log/", files=files)

                if response.status_code == 200:
                    summary = response.json().get("summary", "")
                    st.write("### Log Summary")
                    st.text_area("Summary", summary, height=200)
                else:
                    st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
            except Exception as e:
                st.error(f"An error occurred during summarization: {e}")

    # Query Logs
    query = st.text_input("Ask a question about the log file", placeholder="Enter your query here...")
    if query and st.button("Get AI Response"):
        with st.spinner("Processing query..."):
            try:
                files = {"file": (uploaded_file.name, log_content)}
                params = {"query": query}
                response = requests.post(f"{API_URL}/query-log/", files=files, params=params)

                if response.status_code == 200:
                    ai_response = response.json().get("response", "")
                    st.write("### AI Response")
                    st.text_area("Response", ai_response, height=150)
                else:
                    st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
            except Exception as e:
                st.error(f"An error occurred while processing the query: {e}")
