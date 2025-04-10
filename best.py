# -------------------------------
# 📦 Imports
# -------------------------------
import streamlit as st
import torch
import whisper
import os
import sqlite3
import json
import pandas as pd
import re
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

# -------------------------------
# 🔐 Load Environment Variables
# -------------------------------
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# -------------------------------
# 🧰 Database Setup and Schema Update
# -------------------------------

# Ensures the call_reports table has the right columns
def update_database_schema():
    conn = sqlite3.connect("call_analysis.db")
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(call_reports);")
    existing_columns = [column[1] for column in cursor.fetchall()]

    # Add missing column if it's not already there
    if "company_improvements" not in existing_columns:
        cursor.execute("ALTER TABLE call_reports ADD COLUMN company_improvements TEXT;")
        conn.commit()
    conn.close()

# Creates the database table if it doesn't exist
def create_database():
    conn = sqlite3.connect("call_analysis.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS call_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT DEFAULT 'Unknown',
            agent_name TEXT DEFAULT 'Unknown',
            customer_satisfied TEXT CHECK(customer_satisfied IN ('Yes', 'No')),
            company_improvements TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Call database setup functions
create_database()
update_database_schema()

# -------------------------------
# 🎛️ Streamlit UI Setup
# -------------------------------
st.title("📞 Customer Call Analyzer")
page = st.sidebar.radio("Navigation", ["Home", "Reports"])

# -------------------------------
# 🏠 Home Page: Upload & Analyze Call
# -------------------------------
if page == "Home":
    st.write("Upload an audio file (.wav or .mp3) to analyze the conversation.")
    uploaded_file = st.file_uploader("Choose an audio file", type=["wav", "mp3"])

    if uploaded_file:
        # Save uploaded audio
        filename = os.path.join("temp_audio", uploaded_file.name)
        os.makedirs("temp_audio", exist_ok=True)
        with open(filename, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success("✅ File uploaded successfully!")

        # Load Whisper model for transcription
        model = whisper.load_model("base")

        # Transcribe audio
        with st.spinner("🔄 Transcribing audio..."):
            result = model.transcribe(filename)
            transcription = result["text"]

        st.subheader("📝 Transcription")
        st.text_area("", transcription, height=200)

        # Initialize LLaMA model via Groq API
        llm = ChatGroq(api_key=GROQ_API_KEY, model_name="llama3-8b-8192", temperature=0.2)

        # -------------------------------
        # 🧠 Summarize the conversation
        # -------------------------------
        with st.spinner("🔄 Summarizing conversation..."):
            summary_prompt = f"""Summarize the following customer support conversation:
            keep it without preamble
            {transcription}"""
            summary = llm([HumanMessage(content=summary_prompt)])

        st.subheader("📑 Summary")
        st.write(summary.content if hasattr(summary, 'content') else summary)

        # -------------------------------
        # 🕵️ Extract Names
        # -------------------------------
        with st.spinner("🔄 Extracting names from the conversation..."):
            name_prompt = f"""
            Extract only the names of the agent and customer from this conversation. 
            Respond strictly in JSON format:
            {{
              "agent_name": "<agent_name>", 
              "customer_name": "<customer_name>"
            }}
            If unknown, use "Unknown".
            Conversation:
            {transcription}
            """
            name_result = llm([HumanMessage(content=name_prompt)])

            agent_name, customer_name = "Unknown", "Unknown"
            if name_result and hasattr(name_result, 'content'):
                try:
                    match = re.search(r'\{.*?\}', name_result.content, re.DOTALL)
                    if match:
                        name_data = json.loads(match.group(0))
                        agent_name = name_data.get("agent_name", "Unknown").strip()
                        customer_name = name_data.get("customer_name", "Unknown").strip()
                except json.JSONDecodeError:
                    st.warning("⚠️ Failed to extract names correctly.")
                    st.code(name_result.content)

        # -------------------------------
        # 😊 Extract Customer Satisfaction
        # -------------------------------
        with st.spinner("🔄 Checking customer satisfaction..."):
            satisfaction_prompt = f"""
            Was the customer satisfied at the end of the call? Answer only Yes or No.
            {transcription}
            """
            satisfaction_result = llm([HumanMessage(content=satisfaction_prompt)])
            customer_satisfied = satisfaction_result.content.strip()

        # -------------------------------
        # 🏢 Company Improvement Suggestions
        # -------------------------------
        with st.spinner("🔄 Identifying areas for company improvement..."):
            improvements_prompt = f"""
            Identify issues the customer faced that the company needs to improve. 
            Return a short comma-separated list. No preamble.
            If nothing needs improvement, return "No issues reported."
            {transcription}
            """
            improvements_result = llm([HumanMessage(content=improvements_prompt)])
            company_improvements = improvements_result.content.strip()

        # -------------------------------
        # 💾 Save Analyzed Data to SQLite
        # -------------------------------
        conn = sqlite3.connect("call_analysis.db")
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO call_reports 
            (customer_name, agent_name, customer_satisfied, company_improvements)
            VALUES (?, ?, ?, ?)''',
            (customer_name, agent_name, customer_satisfied, company_improvements))
        conn.commit()
        conn.close()

        # -------------------------------
        # 🧠 Generate Improved Agent Responses
        # -------------------------------
        with st.spinner("🔄 Generating alternative response suggestions..."):
            response_prompt = f"""
            - no preamble
            Extract all agent responses and identify weak ones. Provide better alternatives and explain why.

            Format:
            - Old Response: "<original>"
            - Upgraded Response: "<better version>"
            - Reason for improvement: "<why it's better>"

            Use "----------------------------" to separate entries.

            Conversation:
            {transcription}
            """
            alternative_response = llm([HumanMessage(content=response_prompt)])

        st.subheader("🗣️ Alternative Response Suggestions")
        st.write(alternative_response.content if hasattr(alternative_response, 'content') else alternative_response)

        # Cleanup uploaded file
        os.remove(filename)

# -------------------------------
# 📊 Reports Page: View Past Calls
# -------------------------------
elif page == "Reports":
    st.title("📊 Call Reports")

    # Fetch records from DB
    conn = sqlite3.connect("call_analysis.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, customer_name, agent_name, customer_satisfied, company_improvements FROM call_reports")
    data = cursor.fetchall()
    conn.close()

    if data:
        df = pd.DataFrame(data, columns=["ID", "Customer Name", "Agent Name", "Satisfied", "Company Improvements"])

        # Improve table visuals using HTML/CSS
        st.markdown("""
        <style>
            .stDataFrame { overflow-x: auto; }
            table { width: 100% !important; }
            th { background-color: #4CAF50; color: white; text-align: left; }
            td, th { padding: 10px; border-bottom: 1px solid #ddd; }
        </style>
        """, unsafe_allow_html=True)

        st.dataframe(df, width=1500, height=500)
    else:
        st.write("❌ No records found.")
