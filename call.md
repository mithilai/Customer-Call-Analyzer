---

# 📞 Customer Call Analyzer

A Streamlit-based web application that uses **OpenAI Whisper** for transcribing audio calls and **LLaMA via Groq API** for analyzing the content. The tool is designed to help businesses better understand customer interactions by automatically summarizing calls, identifying customer sentiment, and suggesting improvements.

---

## 🚀 Features

**Audio Transcription**  
Upload `.wav` or `.mp3` files to get accurate transcriptions using Whisper.

**LLM-Based Analysis (LLaMA via Groq)**  
- Summarizes conversations  
- Extracts agent and customer names  
- Detects customer satisfaction (Yes/No)  
- Identifies company improvement areas  
- Suggests improved agent responses with rationale  

**Report Dashboard**  
All call analyses are stored in an SQLite database and can be viewed in a tabular format under the "Reports" section.

---

## 🛠 Technologies Used

- Streamlit – for the web interface  
- Whisper – for audio transcription  
- LangChain + Groq – to connect with LLaMA  
- SQLite3 – for storing call reports  
- Python – for the backend logic  

---

## 📦 Installation Guide

1. **Clone the repository**  
   `git clone https://github.com/your-username/customer-call-analyzer.git`  
   `cd customer-call-analyzer`

2. **Install the required packages**  
   `pip install -r requirements.txt`

3. **Set up your environment variables**  
   Create a `.env` file in the root directory and add your Groq API key:  
   `GROQ_API_KEY=your_groq_api_key_here`

4. **Run the application**  
   `streamlit run app.py`

---

## 📁 File Overview

- `app.py`: Main application logic  
- `call_analysis.db`: SQLite database to store reports (auto-created)  
- `temp_audio/`: Temporary storage for uploaded audio  
- `.env`: Your environment variables (should be kept private)  
- `requirements.txt`: All required Python packages  
- `README.md`: Project documentation

---

## 🧪 How to Use

1. Go to the **Home** tab to upload your audio file.
2. The system will transcribe and analyze the call.
3. Review the transcription, summary, satisfaction result, improvement suggestions, and enhanced agent responses.
4. Head to the **Reports** tab to view or search past call analyses.

---

## 🔒 Privacy Note

All uploaded audio is processed locally and temporarily saved. After transcription and analysis, the file is deleted automatically.

---

## 💡 Future Improvements

- Add authentication for secure usage  
- Enable audio playback in the UI  
- Export reports as PDF  
- Support multi-language transcription and analysis  

---

## 📬 Contact

Developed with ❤️ by Mithil Maske 
For bugs, suggestions, or collaboration, open an issue or contact directly.

---
