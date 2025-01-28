import io
import csv
from fastapi.responses import StreamingResponse

from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
import pandas as pd
import re
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fetch the OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OpenAI API key not set. Ensure OPENAI_API_KEY is defined in the .env file.")

# Initialize OpenAI LLM
llm = OpenAI(temperature=0.7, openai_api_key=api_key)

# Initialize FastAPI app
app = FastAPI()

# Regex for error pattern
error_pattern = r"ERROR\s+(\d{3})?:?\s*(.+)"

# Prompt templates for GenAI
summarize_prompt = PromptTemplate.from_template(
    """
    The following is a log file with various error codes and descriptions:
    {log_content}
    Please provide a summary of the errors, categorize them by type, and suggest possible causes for the most frequent ones.
    """
)

query_prompt = PromptTemplate.from_template(
    """
    Analyze the following log file:
    {log_content}
    Respond to the user's query: {query}
    Include any relevant details and actionable suggestions in your response.
    """
)

#summarize_chain = LLMChain(llm=llm, prompt=summarize_prompt)
summarize_chain = summarize_prompt | llm
query_chain = query_prompt | llm #
#query_chain = LLMChain(llm=llm, prompt=query_prompt) #


def pre_summarize_logs(log_content: str) -> str:
    """
    Pre-summarize the log file to extract key details and create a compact summary.
    """
    error_summary = {}
    lines = log_content.splitlines()

    for line in lines:
        match = re.search(error_pattern, line.replace(":", " ").strip())
        if match:
            error_code = match.group(1) or "N/A"
            error_desc = match.group(2)
            key = f"Error {error_code}: {error_desc}"
            error_summary[key] = error_summary.get(key, 0) + 1

    # Create a compact summary of errors
    summary = []
    for key, count in error_summary.items():
        summary.append(f"{key} - Count: {count}")

    return "\n".join(summary)

async def validate_file(file: UploadFile) -> str:
    
    print("file:", file.filename,"|||" ,file.size ,"|||" ,file.content_type,"|||" ,file.headers)
   
    # Validate file type
    if file.filename.split(".")[-1] not in ["txt", "log"]:
        logging.error("status_code=400, detail=Invalid file type. Please upload a .txt or .log file.")
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .txt or .log file.")
    
    # Read and decode the log file content
    try:
        log_content = (await file.read()).decode("utf-8").strip()
        if not log_content:
            logging.error("status_code=400, detail=File is empty or contains no valid content.")
            raise HTTPException(status_code=400, detail="File is empty or contains no valid content.")
    except Exception as e:
        logging.error(f"status_code=400, detail= Error reading file: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

    return log_content

@app.post("/basic-analysis/")
async def basic_analysis(file: UploadFile = File(...)):
    logging.info(f"Received file: {file.filename}")
    """
    Uploads a log file for analysis. 
    - **Input**: `.txt` or `.log` file with log records.
    - **Output**: JSON response with error summary.
    """
    # Validate file and read content
    log_content = await validate_file(file)
    # Parse log file for errors
    error_summary = {}
    lines = log_content.splitlines()

    for line in lines:
        match = re.search(error_pattern, line.replace(":", " ").strip())
        if match:
            error_code = match.group(1) or "N/A"
            error_desc = match.group(2)
            key = f"Error {error_code}: {error_desc}"
            error_summary[key] = error_summary.get(key, 0) + 1

    # Convert summary to a DataFrame and JSON response
    if error_summary:
        error_data = {
            "Error Summary": [{"Type & Description": k, "Count": v} for k, v in error_summary.items()]
        }

        return JSONResponse(content=error_data)
    else:
        return {"message": "No errors found in the log file."}

@app.post("/summarize-log/")
async def summarize_log(file: UploadFile = File(...)):
    """
    Summarizes the content of a log file using GenAI.
    """
    # Validate file and read content
    log_content = await validate_file(file)
    # Pre-summarize logs
    pre_summary = pre_summarize_logs(log_content)
    #print("Pre-summary:",pre_summary)

    # Generate a summary using GenAI
    try:
        #summary = summarize_chain.run(log_content=log_content)
        summary = summarize_chain.invoke({"log_content":pre_summary})
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")

@app.post("/query-log/")
async def query_log(file: UploadFile = File(...), query: str = Query(None)):
    """
    Processes a query about a log file using GenAI.
    """
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # Validate file and read content
    log_content = await validate_file(file)

    # Pre-summarize logs
    pre_summary = pre_summarize_logs(log_content)
    #print("Pre-summary:",pre_summary)

    # Generate a response using GenAI
    try:
        #response = query_chain.run(log_content=log_content, query=query)
        response = query_chain.invoke({"log_content": pre_summary, "query": query})
        
        return {"query": query, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")


@app.post("/download-error-summary/")
async def download_error_summary(file: UploadFile = File(...)):
    """
    Analyze the log file and return the error summary as a CSV file.
    """
    # Validate file and read content
    log_content = await validate_file(file)

    error_summary = pre_summarize_logs(log_content)

    if not error_summary:
        raise HTTPException(status_code=400, detail="No errors found in the log file.")

    # Prepare CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Type & Description", "Count"])
    for key, count in error_summary.items():
        writer.writerow([key, count])
    output.seek(0)

    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=error_summary.csv"})
