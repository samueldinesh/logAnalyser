import streamlit as st
import requests
import pandas as pd

# Backend API URL
API_URL = "http://127.0.0.1:8000"

st.title("Log File Analysis Bot with GenAI")

# File Upload
uploaded_file = st.file_uploader("Upload your log file (max size: 5MB)", type=["txt", "log"])


if uploaded_file is not None:
    # Show preview of the file content
    log_content = uploaded_file.read().decode("utf-8")
    st.subheader("Log File Content Preview")
    st.text_area("Preview", log_content, height=150)

    # Error Classification
    if st.button("Analyze Errors"):
        with st.spinner("Analyzing errors..."):
            files = {"file": (uploaded_file.name,log_content)}
            #print(files,"\n",log_content)
            response = requests.post(f"{API_URL}/basic-analysis/", 
                                     files=files)
            if response.status_code == 200:
                
                error_data = response.json().get("Error Summary", [])
                print("200 & len:", len(error_data))

                if error_data:
                    st.write("### Error Summary")
                    error_dict={'Type & Description':[],'Count':[]} 

                    for item in error_data:
                        error_dict['Type & Description'].append(item['Type & Description'])
                        error_dict['Count'].append(item['Count'])

                    error_df = pd.DataFrame(error_data)
                    st.dataframe(error_df)
                else:
                    st.write("No errors found in the log file.")
            else:
                st.error(f"Error: {response.json().get('detail', 'Unknown error')}")

    # Log Summarization
    if st.button("Summarize Log"):
        with st.spinner("Generating summary..."):
            files = {"file": (uploaded_file.name,log_content)}
            response = requests.post(f"{API_URL}/summarize-log/", files=files)
            if response.status_code == 200:
                summary = response.json().get("summary", "")
                st.write("### Log Summary")
                st.write(summary)
            else:
                st.error(f"Error: {response.json().get('detail', 'Unknown error')}")

    # Query Logs
    query = st.text_input("Ask a question about the log file")
    if query and st.button("Get AI Response"):
        with st.spinner("Processing query..."):
            files = {"file": (uploaded_file.name,log_content)}
            params = {"query": query}
            print(files,"\n",params)
            response = requests.post(f"{API_URL}/query-log/", files=files, params=params)
            if response.status_code == 200:
                ai_response = response.json().get("response", "")
                st.write("### AI Response")
                st.write(ai_response)
            else:
                st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
