import streamlit as st
import torch
import whisper
import os
import sqlite3
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def create_database():
    conn = sqlite3.connect("call_analysis.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS call_reports (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      customer_service_department TEXT,
                      agent_name TEXT DEFAULT 'Unknown',
                      customer_name TEXT DEFAULT 'Unknown',
                      summary TEXT,
                      overall_sentiment TEXT CHECK(overall_sentiment IN ('Positive', 'Negative', 'Neutral')),
                      customer_satisfied TEXT CHECK(customer_satisfied IN ('Yes', 'No')),
                      main_attention_areas TEXT)''')
    conn.commit()
    conn.close()

create_database()

# Streamlit UI
st.title("Customer Call Analyzer")

page = st.sidebar.radio("Navigation", ["Home", "Reports"])

if page == "Home":
    st.write("Upload an audio file (.wav or .mp3) to analyze the conversation.")
    uploaded_file = st.file_uploader("Choose an audio file", type=["wav", "mp3"])
    
    if uploaded_file is not None:
        filename = os.path.join("temp_audio", uploaded_file.name)
        os.makedirs("temp_audio", exist_ok=True)
        
        with open(filename, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.success("File uploaded successfully!")
        
        # Load Whisper model
        model = whisper.load_model("base")
        
        # Transcribe audio
        with st.spinner("Transcribing..."):
            result = model.transcribe(filename)
            transcription = result["text"]
        
        st.subheader("Transcription")
        st.text_area("", transcription, height=200)
        
        # Use LLaMA via Groq API for analysis
        llm = ChatGroq(api_key=GROQ_API_KEY, model_name="llama3-8b-8192")
        
        # Summarization
        summary_prompt = f"""
        Summarize the following customer support conversation:
        {transcription}
        """
        messages = [HumanMessage(content=summary_prompt)]
        summary = llm(messages)
        st.subheader("Summary")
        st.write(summary.content if hasattr(summary, 'content') else summary)
        
        # Extract key details for database storage
        name_prompt = f"""
        Extract only the names of the agent and customer from this conversation in JSON format:
        {{"agent_name": "<agent_name>", "customer_name": "<customer_name>"}}
        If unknown, use "Unknown".
        {transcription}
        """
        name_result = llm([HumanMessage(content=name_prompt)])
        agent_name, customer_name = "Unknown", "Unknown"
        
        if name_result and hasattr(name_result, 'content'):
            import json
            try:
                name_data = json.loads(name_result.content)
                agent_name = name_data.get("agent_name", "Unknown").strip()
                customer_name = name_data.get("customer_name", "Unknown").strip()
            except json.JSONDecodeError:
                pass
        
        sentiment_prompt = f"""
        Classify the overall sentiment of the customer's conversation strictly as Positive, Negative, or Neutral.
        Only return one of these three words without any explanation:
        {transcription}
        """
        sentiment_result = llm([HumanMessage(content=sentiment_prompt)])
        overall_sentiment = sentiment_result.content.strip()
        
        satisfaction_prompt = f"""
        Was the customer satisfied at the end of the call? Answer only Yes or No.
        {transcription}
        """
        satisfaction_result = llm([HumanMessage(content=satisfaction_prompt)])
        customer_satisfied = satisfaction_result.content.strip()
        
        attention_prompt = f"""
        Identify key topics or main areas of attention in short comma-separated keywords only (e.g., billing, technical issue, refund):
        {transcription}
        """
        attention_result = llm([HumanMessage(content=attention_prompt)])
        main_attention_areas = attention_result.content.strip()
        
        # Store in SQLite database
        conn = sqlite3.connect("call_analysis.db")
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO call_reports (customer_service_department, agent_name, customer_name, summary, overall_sentiment, customer_satisfied, main_attention_areas)
                          VALUES (?, ?, ?, ?, ?, ?, ?)''',
                       ("Unknown", agent_name, customer_name, summary.content, overall_sentiment, customer_satisfied, main_attention_areas))
        conn.commit()
        conn.close()
        
        # Generate alternative responses
        response_prompt = f"""
        Extract all responses given by the agent from the following conversation. Identify responses that may not have effectively addressed the customer’s concerns. 
        
        Format the output as follows:
        - Old Response: "<original agent response>"
        - Upgraded Response: "<better alternative>"
        - Reason for improvement: "<explanation>"
        
        Ensure the upgraded response is clear, empathetic, and directly addresses customer concerns. Do not include customer statements in the output.
        
        Conversation:
        {transcription}
        """
        messages = [HumanMessage(content=response_prompt)]
        alternative_response = llm(messages)
        
        st.subheader("Alternative Response Suggestions")
        st.write(alternative_response.content if hasattr(alternative_response, 'content') else alternative_response)
        
        # Clean up
        os.remove(filename)

elif page == "Reports":
    st.title("Call Reports")
    conn = sqlite3.connect("call_analysis.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, agent_name, customer_name, overall_sentiment, customer_satisfied, main_attention_areas FROM call_reports")
    data = cursor.fetchall()
    conn.close()
    
    if data:
        st.table([{ "ID": row[0], "Agent Name": row[1], "Customer Name": row[2], "Sentiment": row[3], "Satisfied": row[4], "Attention Areas": row[5] } for row in data])
    else:
        st.write("No records found.")
