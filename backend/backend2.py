import io
import csv
import re
import logging
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import os

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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

# Combine prompt and LLM for GenAI tasks
summarize_chain = summarize_prompt | llm
query_chain = query_prompt | llm


# Utility function to validate and read the uploaded file
async def validate_and_read_file(file: UploadFile) -> str:
    """
    Validates the uploaded file and reads its content.
    """
    logging.info(f"Validating file: {file.filename}")
    if file.filename.split(".")[-1] not in ["txt", "log"]:
        logging.error("Invalid file type.")
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .txt or .log file.")
    try:
        log_content = (await file.read()).decode("utf-8").strip()
        if not log_content:
            logging.error("Empty or invalid file content.")
            raise HTTPException(status_code=400, detail="File is empty or contains no valid content.")
        return log_content
    except Exception as e:
        logging.error(f"Error reading file: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")


# Utility function to pre-summarize log content
def pre_summarize_logs(log_content: str, as_dict=False) -> str:
    """
    Pre-summarizes the log content to extract key error details.
    """
    logging.info("Pre-summarizing logs.")
    error_summary = {}
    lines = log_content.splitlines()
    for line in lines:
        match = re.search(error_pattern, line.replace(":", " ").strip())
        if match:
            error_code = match.group(1) or "N/A"
            error_desc = match.group(2)
            key = f"Error {error_code}: {error_desc}"
            error_summary[key] = error_summary.get(key, 0) + 1

    if as_dict:
        return {"Error Summary": [{"Type & Description": k, "Count": v} for k, v in error_summary.items()]
        }
    return "\n".join([f"{key} - Count: {count}" for key, count in error_summary.items()])


# Endpoint for basic analysis
@app.post("/basic-analysis/")
async def basic_analysis(file: UploadFile = File(...)):
    """
    Uploads a log file for basic analysis and returns a JSON response.
    """
    log_content = await validate_and_read_file(file)
    logging.info("Analyzing log file.")
    error_summary = pre_summarize_logs(log_content, as_dict=True)
    if error_summary:
        return JSONResponse(content=error_summary)
    return {"message": "No errors found in the log file."}


# Endpoint for summarizing logs using GenAI
@app.post("/summarize-log/")
async def summarize_log(file: UploadFile = File(...)):
    """
    Summarizes the content of a log file using GenAI.
    """
    log_content = await validate_and_read_file(file)
    pre_summary = pre_summarize_logs(log_content)
    try:
        logging.info("Generating log summary with GenAI.")
        summary = summarize_chain.invoke({"log_content": pre_summary})
        return {"summary": summary}
    except Exception as e:
        logging.error(f"Error generating summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")


# Endpoint for querying logs using GenAI
@app.post("/query-log/")
async def query_log(file: UploadFile = File(...), query: str = Query(..., description="Query about the log file")):
    """
    Processes a query about a log file using GenAI.
    """
    log_content = await validate_and_read_file(file)
    pre_summary = pre_summarize_logs(log_content)
    try:
        logging.info("Processing query with GenAI.")
        response = query_chain.invoke({"log_content": pre_summary, "query": query})
        return {"query": query, "response": response}
    except Exception as e:
        logging.error(f"Error generating query response: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")


# Endpoint to download error summary as CSV
@app.post("/download-error-summary/")
async def download_error_summary(file: UploadFile = File(...)):
    """
    Analyzes the log file and returns the error summary as a CSV file.
    """
    log_content = await validate_and_read_file(file)
    error_summary = pre_summarize_logs(log_content)
    if not error_summary:
        raise HTTPException(status_code=400, detail="No errors found in the log file.")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Type & Description", "Count"])

    for line in error_summary.split("\n"):
        key, count = line.split(" - Count: ")
        writer.writerow([key, count])
    
    #for entry in error_summary["Error Summary"]:
    #    writer.writerow([entry["Type & Description"], entry["Count"]])

    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=error_summary.csv"})
