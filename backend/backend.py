import io
import csv
import re
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
from loguru import logger
import asyncio
import os
from datetime import datetime

# Initialize Loguru logger
logger.add("log_file.log", rotation="10 MB", level="INFO")

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
    Summarize the key insights and critical errors from the following log chunk:
    {log_content}
    Focus on unique patterns, frequent errors, and actionable items.
    """
)
final_summarize_prompt = PromptTemplate.from_template(
    """
    The following are summaries of log file chunks:
    {log_content}
    Create a concise, high-level summary focusing on recurring patterns, critical issues, and actionable insights with detailed steps to resolve it.
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
final_summarize_chain = final_summarize_prompt | llm
query_chain = query_prompt | llm


# Utility function to validate and read the uploaded file
async def validate_and_read_file(file: UploadFile) -> str:
    """
    Validates the uploaded file and reads its content.
    Args:
        file (UploadFile): The uploaded file.
    Returns:
        str: The content of the file as a string.
    Raises:
        HTTPException: If the file type is invalid or content is empty.
    """
    logger.info("Validating file: {}", file.filename)
    if file.filename.split(".")[-1] not in ["txt", "log"]:
        logger.error("Invalid file type.")
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .txt or .log file.")
    try:
        log_content = (await file.read()).decode("utf-8").strip()
        if not log_content:
            logger.error("Empty or invalid file content.")
            raise HTTPException(status_code=400, detail="File is empty or contains no valid content.")
        return log_content
    except Exception as e:
        logger.error("Error reading file: {}", str(e))
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")


# Utility function to split log content into manageable chunks
def split_log_content_with_metadata(log_content: str, chunk_size=3500):
    """
    Splits log content into manageable chunks with metadata.
    Args:
        log_content (str): The full log content.
        chunk_size (int): The maximum size of each chunk in characters.
    Returns:
        tuple: A list of chunks and metadata for each chunk.
    """
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        model_name="gpt-4o",
        chunk_size=chunk_size,
        chunk_overlap=0,
        separators=["\n"],
    )

    chunks = text_splitter.split_text(log_content)
    metadata = [{"chunk_id": i, "length": len(chunk), "error_count": chunk.count("ERROR")}
                for i, chunk in enumerate(chunks)]

    logger.info("Split log into {} chunks with metadata.", len(chunks))
    return chunks, metadata


# Utility function to pre-summarize log content
def regex_logs(log_content: str, as_dict=False) -> str:
    """
    Extracts key error details from the log content using regex.
    Args:
        log_content (str): The full log content.
        as_dict (bool): Whether to return the result as a dictionary.
    Returns:
        str or dict: A pre-summarized log content or dictionary of errors.
    """
    logger.info("Pre-summarizing logs.")
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
        return {"Error Summary": [{"Type & Description": k, "Count": v} for k, v in error_summary.items()]}
    return "\n".join([f"{key} - Count: {count}" for key, count in error_summary.items()])

def extract_metadata_with_timestamps(log_content: str):
    """
    Extracts metadata including error occurrence, timestamps, and time concentration.
    Args:
        log_content (str): The content of the log file.
    Returns:
        dict: Metadata about errors in the log.
    """
    metadata = {"total_errors": 0, "error_timestamps": {}, "time_concentration": {}}
    lines = log_content.splitlines()

    for line in lines:
        timestamp_match = re.search(r"\[(.*?)\]", line)  # Extract timestamps
        error_match = re.search(r"ERROR\s+(\d{3})?",line)#"ERROR\\s+(\\d{3})", line)
        #"ERROR\s+(\d{3})?:?\s*(.+)"
        #print(timestamp_match)
        #rint(error_match)

        if error_match and timestamp_match:
            timestamp = timestamp_match.group(1)
            error_code = error_match.group(1)
            metadata["total_errors"] += 1
            # Update timestamp-based metadata
            dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            metadata["error_timestamps"].setdefault(error_code, []).append(dt)

            # Aggregate errors by hour
            hour = dt.strftime("%Y-%m-%d %H:00:00")
            metadata["time_concentration"][hour] = metadata["time_concentration"].get(hour, 0) + 1
    #print (metadata)
    return metadata

# Asynchronous chunk processing
async def process_chunk_async(chunk, chain):
    """
    Processes a single chunk asynchronously.
    Args:
        chunk (str): The chunk of log content.
        chain: The LLM chain to process the chunk.
    Returns:
        str: The processed chunk summary.
    """
    return await asyncio.to_thread(chain.invoke, {"log_content": chunk})


async def summarize_chunks_async(chunks, chain):
    """
    Processes all chunks asynchronously.
    Args:
        chunks (list): The list of log content chunks.
        chain: The LLM chain to process the chunks.
    Returns:
        list: A list of chunk summaries.
    """
    tasks = [process_chunk_async(chunk, chain) for chunk in chunks]
    return await asyncio.gather(*tasks)


# Endpoint for basic analysis
@app.post("/basic-analysis/")
async def basic_analysis(file: UploadFile = File(...)):
    """
    Uploads a log file for basic analysis and returns a JSON response.
    Args:
        file (UploadFile): The uploaded log file.
    Returns:
        JSONResponse: The error summary.
    """
    log_content = await validate_and_read_file(file)
    logger.info("Analyzing log file.")
    error_summary = regex_logs(log_content, as_dict=True)
    #print(error_summary)
    # Extract timestamp metadata
    metadata = extract_metadata_with_timestamps(log_content)

    # Format timestamp metadata for JSON response
    time_insights = {
        "total_errors": metadata["total_errors"],
        "peak_time": max(metadata["time_concentration"], key=metadata["time_concentration"].get),
        "peak_errors": max(metadata["time_concentration"].values()),
        "time_concentration": metadata["time_concentration"]
    }

    if error_summary:
        return JSONResponse(content={
            "Error Summary": error_summary["Error Summary"],
            "Timestamp Insights": time_insights
        })

    #if error_summary:
    #    return JSONResponse(content=error_summary)
    return {"message": "No errors found in the log file."}


# Endpoint for summarizing logs using GenAI
@app.post("/summary-raw-log/")
async def summary_raw_log(file: UploadFile = File(...)):
    """
    Summarizes the content of a log file using GenAI.
    Args:
        file (UploadFile): The uploaded log file.
    Returns:
        dict: A dictionary containing the summarized log.
    """
    log_content = await validate_and_read_file(file)
    chunks, metadata = split_log_content_with_metadata(log_content)
    summaries = await summarize_chunks_async(chunks[:10], summarize_chain)

    try:
        combined_summary = final_summarize_chain.invoke({"log_content": "\n".join(summaries)})
        return {"summary": combined_summary}
    except Exception as e:
        logger.error("Error generating final summary: {}", str(e))
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")

# Endpoint for summarizing logs using GenAI
@app.post("/summary-log/")
async def summary_log(file: UploadFile = File(...)):
    """
    Summarizes the content of a log file using GenAI.
    Args:
        file (UploadFile): The uploaded log file.
    Returns:
        dict: A dictionary containing the summarized log.
    """
    log_content = await validate_and_read_file(file)
    logger.info("Analyzing log file.")
    error_summary = regex_logs(log_content, as_dict=True)
    print(error_summary)
    # Extract timestamp metadata
    metadata = extract_metadata_with_timestamps(log_content)

    # Format timestamp metadata and error summary for JSON response
    processed_error_insight= {
        "Error Summary": error_summary["Error Summary"],
        "Timestamp Insights": {
        "total_errors": metadata["total_errors"],
        "peak_time": max(metadata["time_concentration"], key=metadata["time_concentration"].get),
        "peak_errors": max(metadata["time_concentration"].values()),
        "time_concentration": metadata["time_concentration"]
    }
    }

    try:
        combined_summary = final_summarize_chain.invoke({"log_content": processed_error_insight})
        return {"summary": combined_summary}
    except Exception as e:
        logger.error("Error generating final summary: {}", str(e))
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")

# Endpoint for querying logs using GenAI
@app.post("/query-log/")
async def query_log(file: UploadFile = File(...), query: str = Query(..., description="Query about the log file")):
    """
    Processes a query about a log file using GenAI.
    Args:
        file (UploadFile): The uploaded log file.
        query (str): The user query about the log.
    Returns:
        dict: The query response.
    """
    log_content = await validate_and_read_file(file)
    chunks, _ = split_log_content_with_metadata(log_content)
    response = await summarize_chunks_async(chunks, query_chain)
    return {"query": query, "response": "\n".join(response)}


# Endpoint to download error summary as CSV
@app.post("/download-error-summary/")
async def download_error_summary(file: UploadFile = File(...)):
    """
    Analyzes the log file and returns the error summary as a CSV file.
    Args:
        file (UploadFile): The uploaded log file.
    Returns:
        StreamingResponse: The CSV file containing the error summary.
    """
    log_content = await validate_and_read_file(file)
    error_summary, metadata = split_log_content_with_metadata(log_content)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Type & Description", "Count", "Chunk ID", "Chunk Length"])

    for entry in error_summary["Error Summary"]:
        writer.writerow([
            entry["Type & Description"],
            entry["Count"],
            metadata[entry["chunk_id"]]["length"] if "chunk_id" in entry else "N/A"
        ])

    output.seek(0)
    return StreamingResponse(output, media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=error_summary.csv"})
