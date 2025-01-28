# Log Investigation Bot

## **Overview**
The Log Investigation Bot is a GenAI-powered tool designed to analyze log files, classify errors, and generate AI-driven insights. It provides users with an intuitive interface to upload log files, perform analysis, summarize logs, query AI for insights, and download error summaries as CSV files.

---

## **Features**

### **Core Features**
- **File Upload**: Supports `.txt` and `.log` files up to 5MB.
- **Error Classification**: Parses log files to identify and count error types.
- **AI Summarization**: Generates a natural language summary of the log content.
- **Query AI**: Answers user questions about the log content using GenAI.
- **CSV Export**: Allows users to download error summaries as CSV files.

### **Frontend**
- Built using **Streamlit**.
- Interactive UI with left-side menu for actions and right-side panel for results.

### **Backend**
- Developed with **FastAPI**.
- Integrates with **LangChain** and **OpenAI** APIs for AI capabilities.

---

## **System Requirements**

### **Frontend Requirements**
- **Python**: 3.9+
- **Dependencies**: Streamlit, Requests

### **Backend Requirements**
- **Python**: 3.9+
- **Dependencies**: FastAPI, LangChain, OpenAI, Python-dotenv

---

## **Setup Instructions**

### **Step 1: Clone the Repository**
```bash
git clone <repository_url>
cd log-investigation-bot
```

### **Step 2: Install Dependencies**

#### **Backend**
```bash
cd backend
pip install -r requirements.txt
```

#### **Frontend**
```bash
cd frontend
pip install -r requirements.txt
```

### **Step 3: Configure Environment Variables**
- Create a `.env` file in the `backend` directory with the following content:
  ```env
  OPENAI_API_KEY=your_openai_api_key
  ```

### **Step 4: Run the Application**

#### **Backend**
```bash
cd backend
uvicorn main:app --reload
```

#### **Frontend**
```bash
cd frontend
streamlit run app.py
```

### **Step 5: Access the Application**
- Open your browser and navigate to: `http://localhost:8501`

---

## **Usage**

### **1. Upload Log File**
- Use the file uploader to select a `.log` or `.txt` file.
- Alternatively, provide a file path.

### **2. Analyze Errors**
- Click "Basic Analyze" to classify errors and download a summary as CSV.

### **3. Summarize Log Content**
- Click "AI Summary" to generate an AI-driven summary of the log content.

### **4. Query AI**
- Enter a question in the "Ask a Question" field and click "Query AI" to receive detailed insights.

---

## **Testing**

### **Run Automated Tests**
- **Backend Tests**:
  ```bash
  cd backend
  pytest test_backend.py
  ```

- **Frontend Tests**:
  ```bash
  cd frontend
  python -m unittest test_frontend.py
  ```

---

## **Deployment**

### **Backend Deployment**
- Use Docker for containerized deployment:
  ```dockerfile
  FROM python:3.9
  WORKDIR /app
  COPY . .
  RUN pip install -r requirements.txt
  CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
  ```

- Deploy on AWS, Azure, or Heroku.

### **Frontend Deployment**
- Use [Streamlit Cloud](https://streamlit.io/cloud) for quick hosting.

---

## **Known Issues**
- Query AI may timeout for files larger than 4MB.
- Summarization of large logs can exceed 15 seconds.

---

## **Future Enhancements**
- Add pagination for large error summaries.
- Improve performance for AI queries and summarization.
- Add real-time log monitoring.

---

## **License**
This project is licensed under the MIT License. See the LICENSE file for details.

