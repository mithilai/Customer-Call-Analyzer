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

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Function to ensure the correct database schema
def update_database_schema():
    conn = sqlite3.connect("call_analysis.db")
    cursor = conn.cursor()

    # Get the existing columns
    cursor.execute("PRAGMA table_info(call_reports);")
    existing_columns = [column[1] for column in cursor.fetchall()]

    # Add missing columns if needed
    if "company_improvements" not in existing_columns:
        cursor.execute("ALTER TABLE call_reports ADD COLUMN company_improvements TEXT;")
        conn.commit()

    conn.close()

# Create or update the database schema
def create_database():
    conn = sqlite3.connect("call_analysis.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS call_reports (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      customer_name TEXT DEFAULT 'Unknown',
                      agent_name TEXT DEFAULT 'Unknown',
                      customer_satisfied TEXT CHECK(customer_satisfied IN ('Yes', 'No')),
                      company_improvements TEXT)''')
    conn.commit()
    conn.close()

# Run database setup
create_database()
update_database_schema()

# Streamlit UI
st.title("📞 Customer Call Analyzer")

page = st.sidebar.radio("Navigation", ["Home", "Reports"])

if page == "Home":
    st.write("Upload an audio file (.wav or .mp3) to analyze the conversation.")
    uploaded_file = st.file_uploader("Choose an audio file", type=["wav", "mp3"])

    if uploaded_file is not None:
        filename = os.path.join("temp_audio", uploaded_file.name)
        os.makedirs("temp_audio", exist_ok=True)

        with open(filename, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.success("✅ File uploaded successfully!")

        # Load Whisper model
        model = whisper.load_model("base")

        # Transcribe audio
        with st.spinner("🔄 Transcribing audio..."):
            result = model.transcribe(filename)
            transcription = result["text"]

        st.subheader("📝 Transcription")
        st.text_area("", transcription, height=200)

        # Use LLaMA via Groq API for analysis
        llm = ChatGroq(api_key=GROQ_API_KEY, model_name="llama3-8b-8192", temperature=0.2)

        # Summarization
        with st.spinner("🔄 Summarizing conversation..."):
            summary_prompt = f"""
            Summarize the following customer support conversation:
            keep it without preamble
            {transcription}
            """
            messages = [HumanMessage(content=summary_prompt)]
            summary = llm(messages)

        st.subheader("📑 Summary")
        st.write(summary.content if hasattr(summary, 'content') else summary)

        # Extract Agent and Customer Names
        with st.spinner("🔄 Extracting names from the conversation..."):
            name_prompt = f"""
            Extract only the names of the agent and customer from this conversation. 
            Respond strictly in JSON format:
            
            {{
              "agent_name": "<agent_name>", 
              "customer_name": "<customer_name>"
            }}

            If unknown, use "Unknown" instead of leaving fields blank.

            Conversation:
            {transcription}
            """
            name_result = llm([HumanMessage(content=name_prompt)])

            agent_name, customer_name = "Unknown", "Unknown"
            if name_result and hasattr(name_result, 'content'):
                try:
                    # Extract JSON part using regex
                    match = re.search(r'\{.*?\}', name_result.content, re.DOTALL)
                    if match:
                        name_data = json.loads(match.group(0))  # Extract JSON block
                        agent_name = name_data.get("agent_name", "Unknown").strip()
                        customer_name = name_data.get("customer_name", "Unknown").strip()
                except json.JSONDecodeError:
                    st.warning("⚠️ Failed to extract names correctly. Raw response:")
                    st.code(name_result.content)

        # Extract Satisfaction
        with st.spinner("🔄 Checking customer satisfaction..."):
            satisfaction_prompt = f"""
            Was the customer satisfied at the end of the call? Answer only Yes or No.
            {transcription}
            """
            satisfaction_result = llm([HumanMessage(content=satisfaction_prompt)])
            customer_satisfied = satisfaction_result.content.strip()

        # Extract Company Improvements
        with st.spinner("🔄 Identifying areas for company improvement..."):
            improvements_prompt = f"""
            No preamble.
            Identify issues the customer faced that the company needs to improve. 
            Return only a short list of issues separated by commas also without any preamble.
            Example: "Website not user-friendly, Customer didn't receive email"
            If nothing needs improvement, return "No issues reported."
            {transcription}
            """
            improvements_result = llm([HumanMessage(content=improvements_prompt)])
            company_improvements = improvements_result.content.strip()

        # Store in SQLite database
        conn = sqlite3.connect("call_analysis.db")
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO call_reports (customer_name, agent_name, customer_satisfied, company_improvements)
                          VALUES (?, ?, ?, ?)''',
                       (customer_name, agent_name, customer_satisfied, company_improvements))
        conn.commit()
        conn.close()

        # Generate alternative responses for agent
        with st.spinner("🔄 Generating alternative response suggestions..."):
            response_prompt = f"""
            - no preamble
            Extract all responses given by the agent from the following conversation. Identify responses that may not have effectively addressed the customer’s concerns. 

            Format the output as follows and do not put any markdown syntax or bulletpoint in the response:
            - Old Response: "<original agent response>"
            - Upgraded Response: "<better alternative>"
            - Reason for improvement: "<explanation>"

            for example
            - Old Response: "I am sorry for problem you faced i will look in to it but it will take some time"
            - Upgraded Response: "I am sorry for the inconvience you faced, I will look in to it and soon i will be resolved"
            - Reason for improvement: "The Response before was little informal and will take some time will make customer that they have to wait more while the new response will feel like it will be finish soon"


            ### Make a line after one comeplete response to differentiate between others.
            for example
            - old response
            - upgraded response
            - reason for improvement
            ----------------------------
            - old response 
            - upgraded response
            - reason for improvement

            Ensure the upgraded response is clear, empathetic, and directly addresses customer concerns. Do not include customer statements in the output.

            Conversation:
            {transcription}
            """
            messages = [HumanMessage(content=response_prompt)]
            alternative_response = llm(messages)

        st.subheader("🗣️ Alternative Response Suggestions")
        st.write(alternative_response.content if hasattr(alternative_response, 'content') else alternative_response)

        # Clean up
        os.remove(filename)

elif page == "Reports":
    st.title("📊 Call Reports")

    # Fetch data from database
    conn = sqlite3.connect("call_analysis.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, customer_name, agent_name, customer_satisfied, company_improvements FROM call_reports")
    data = cursor.fetchall()
    conn.close()

    if data:
        # Convert to DataFrame for better styling
        df = pd.DataFrame(data, columns=["ID", "Customer Name", "Agent Name", "Satisfied", "Company Improvements"])

        # Apply custom CSS for better readability
        st.markdown("""
        <style>
            .stDataFrame { overflow-x: auto; }
            table { width: 100% !important; }
            th { background-color: #4CAF50; color: white; text-align: left; }
            td, th { padding: 10px; border-bottom: 1px solid #ddd; }
        </style>
        """, unsafe_allow_html=True)

        # Display as a styled dataframe
        st.dataframe(df, width=1500, height=500)  # Adjust width & height as needed
    else:
        st.write("❌ No records found.")
