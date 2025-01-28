import streamlit as st
import requests
import pandas as pd
import os

# Backend API URL
API_URL = "http://127.0.0.1:8000"

# Streamlit app title
st.title("Log Investigation Bot")

# File Upload (always at the top)
uploaded_file = st.file_uploader("Upload your log file (max size: 5MB)", type=["txt", "log"])
file_path = st.text_input("Or, enter the file location path", placeholder="e.g., /path/to/logfile.log")

agree = None  # Placeholder for the checkbox state
log_content = None  # Placeholder for the log content

# Handle file input (either upload or path)
if uploaded_file:
    #print("File size:", uploaded_file.size, "bytes")
    if uploaded_file.size > 5 * 1024 * 1024:
        st.error("File size exceeds the maximum limit of 5MB.")
    else:
        log_content = uploaded_file.read().decode("utf-8")
elif file_path:
    try:
        with open(file_path, "r") as f:
            #print("Size of file is :", os.path.getsize(file_path), "bytes")
            if os.path.getsize(file_path) > 5 * 1024 * 1024:
                st.error("File size exceeds the maximum limit of 5MB.")
            else:
                log_content = f.read()
            
    except Exception as e:
        st.error(f"Could not read file at path: {file_path}. Error: {e}")

# Layout using st.columns
if log_content is not None:

    # Create a two-column layout
    col1, col2 = st.columns([1, 2])  # Left column (1 unit) and right column (2 units)

    with col1:
        st.subheader("Actions")
        # Left-side buttons
        analyze_errors = st.button("Basic Analyze")
        summarize_log = st.button("AI Summary")
        agree = st.checkbox("Enable Query")
        if agree:
            query = st.text_input("Ask a question about the log file", placeholder="Enter your query here...")
            get_ai_response = st.button("Query AI")
            if st.button("Clear Results"):
                st.session_state.clear()

    with col2:
        # Right-side response area
        st.subheader("Results")
        # Show log preview
        st.text_area("Log File Content Preview", log_content, height=150, key="log_preview")

        # Handle "Analyze Errors"
        if analyze_errors:
            with st.spinner("Analyzing errors..."):
                try:
                    files = {"file": ("logfile.log", log_content)}
                    response = requests.post(f"{API_URL}/basic-analysis/", files=files)

                    if response.status_code == 200:
                        error_summary = response.json().get("Error Summary", [])
                        #print(response.json())
                        st.success("Analysis completed successfully!")
                        if error_summary:

                            st.write("### Error Type Analysis")
                            error_df1 = pd.DataFrame(error_summary)
                            st.dataframe(error_df1)
                            st.download_button(
                                label="Download (CSV)",
                                data=error_df1.to_csv(index=False),
                                file_name="error_summary.csv",
                                mime="text/csv",
                            )
                        else:
                            st.info("No errors found in the log file.")
                    else:
                        st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"An error occurred during analysis: {e}")

        # Handle "Summarize Log"
        if summarize_log:
            with st.spinner("Generating summary..."):
                try:
                    files = {"file": ("logfile.log", log_content)}
                    response = requests.post(f"{API_URL}/summary-log/", files=files)

                    if response.status_code == 200:
                        summary = response.json().get("summary", "")
                        st.write("### Log Summary")
                        st.text_area("Summary", summary, height=200, key="log_summary")
                    else:
                        st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"An error occurred during summarization: {e}")

        if agree:
            # Handle "Get AI Response"
            if get_ai_response and query:
                with st.spinner("Processing query..."):
                    try:
                        files = {"file": ("logfile.log", log_content)}
                        params = {"query": query}
                        response = requests.post(f"{API_URL}/query-log/", files=files, params=params)

                        if response.status_code == 200:
                            ai_response = response.json().get("response", "")
                            st.write("### AI Response")
                            st.text_area("Response", ai_response, height=150, key="ai_response")
                        else:
                            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"An error occurred while processing the query: {e}")
