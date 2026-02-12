import streamlit as st
import google.generativeai as genai
import os
import sqlite3
from datetime import datetime
import pandas as pd
import io

# Configure Gemini API
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    st.error("⚠️ API Key not found! Please contact the administrator.")
    st.stop()

genai.configure(api_key=API_KEY)

# Database setup
DB_NAME = "interview_results.db"

def init_db():
    """Initialize the SQLite database"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            date TEXT NOT NULL,
            score INTEGER NOT NULL,
            status TEXT NOT NULL,
            transcript TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def save_interview(student_id, score, status, transcript):
    """Save interview results to database"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO interviews (student_id, date, score, status, transcript)
        VALUES (?, ?, ?, ?, ?)
    ''', (student_id, date, score, status, transcript))
    conn.commit()
    conn.close()

def get_all_interviews():
    """Retrieve all interview records"""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM interviews", conn)
    conn.close()
    return df

def get_student_last_interview(student_id):
    """Get the most recent interview for a student"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM interviews 
        WHERE student_id = ? 
        ORDER BY date DESC 
        LIMIT 1
    ''', (student_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def grade_transcript(transcript):
    """Use Gemini AI to grade the interview transcript"""
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    grading_prompt = f"""
You are a physics teacher grading an AP Physics interview about Waves and Modern Physics.

Below is the complete transcript of a student interview session:

{transcript}

Please analyze the student's responses and provide:
1. A Score from 0-100 based on:
   - Correctness of answers (50%)
   - Understanding of concepts (30%)
   - Depth of explanations (20%)
2. A Status: "Pass" if score >= 60, otherwise "Fail"

Respond in this exact format:
Score: [number]
Status: [Pass/Fail]
Feedback: [2-3 sentences explaining the grade]
"""
    
    response = model.generate_content(grading_prompt)
    result_text = response.text
    
    # Parse the response
    score = 0
    status = "Fail"
    
    for line in result_text.split('\n'):
        if line.startswith('Score:'):
            score = int(''.join(filter(str.isdigit, line)))
        elif line.startswith('Status:'):
            status = line.split(':')[1].strip()
    
    return score, status, result_text

def admin_panel():
    """Display admin panel with all results"""
    st.title("📊 Admin Panel - Interview Results")
    
    df = get_all_interviews()
    
    if df.empty:
        st.info("No interview records found.")
    else:
        st.dataframe(df, use_container_width=True)
        
        # Download CSV button
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        
        st.download_button(
            label="📥 Download Results as CSV",
            data=csv_data,
            file_name=f"interview_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

def chat_interface(student_id):
    """Main chat interface for student interviews"""
    st.title("🎓 AP Physics Interview Bot")
    st.write(f"**Student ID:** {student_id}")
    st.write("**Topic:** Waves and Modern Physics")
    st.divider()
    
    # Define the topic progression
    TOPICS = [
        "Simple Harmonic Motion",
        "Pendulum and Mass Spring",
        "Wave form",
        "Damped oscillation Damped Pendulum",
        "Waves on a string",
        "Standing Waves",
        "Sound Waves",
        "Doppler effect",
        "Musical instruments",
        "Light as a wave",
        "Angular Resolution",
        "Thin film",
        "Polarization",
        "Thermal Physics Black body",
        "Light as a particle",
        "Radioactivity",
        "Relativity"
    ]
    
    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []
        st.session_state.turn_count = 0
        st.session_state.interview_complete = False
        st.session_state.current_topic_index = 0
        
        # Initialize AI conversation
        model = genai.GenerativeModel('gemini-2.5-flash')
        st.session_state.chat = model.start_chat(history=[])
        
        # Send initial system message with topic progression
        initial_prompt = f"""You are an AP Physics teacher interviewing a grade 12 student about Waves and Modern Physics. 

CRITICAL INSTRUCTIONS - TOPIC PROGRESSION:
You MUST ask questions following this exact order of topics, one topic at a time:
1. Simple Harmonic Motion
2. Pendulum and Mass Spring
3. Wave form
4. Damped oscillation Damped Pendulum
5. Waves on a string
6. Standing Waves
7. Sound Waves
8. Doppler effect
9. Musical instruments
10. Light as a wave
11. Angular Resolution
12. Thin film
13. Polarization
14. Thermal Physics Black body
15. Light as a particle
16. Radioactivity
17. Relativity

RULES:
- Start with topic 1: Simple Harmonic Motion
- Ask ONE clear, focused question about the current topic
- After the student answers, move to the NEXT topic in the list
- Do NOT skip topics or go out of order
- Be encouraging but test their understanding thoroughly
- Each question should probe their conceptual understanding of that specific topic

Start the interview with your first question about Simple Harmonic Motion."""
        
        response = st.session_state.chat.send_message(initial_prompt)
        first_question = st.session_state.chat.send_message("Ask your first question about Simple Harmonic Motion.")
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": first_question.text
        })
    
    # Display current topic progress
    if st.session_state.turn_count < len(TOPICS):
        current_topic = TOPICS[st.session_state.turn_count]
        st.info(f"📚 Current Topic ({st.session_state.turn_count + 1}/{len(TOPICS)}): **{current_topic}**")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Check if interview is complete
    if st.session_state.interview_complete:
        st.success("✅ Interview completed and graded!")
        if st.button("Start New Interview"):
            for key in ['messages', 'turn_count', 'interview_complete', 'chat', 'student_id', 'current_topic_index']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        return
    
    # Show turn counter and finish button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(f"Question {st.session_state.turn_count + 1}/{len(TOPICS)}")
    with col2:
        if st.button("🏁 Finish Interview"):
            complete_interview()
            return
    
    # Chat input
    if prompt := st.chat_input("Type your answer here..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        # Increment turn counter
        st.session_state.turn_count += 1
        
        # Check if we've covered all topics
        if st.session_state.turn_count >= len(TOPICS):
            complete_interview()
            return
        
        # Get next topic
        next_topic = TOPICS[st.session_state.turn_count]
        
        # Get AI response with instruction to move to next topic
        follow_up_instruction = f"Good. Now move to the next topic: {next_topic}. Ask ONE clear question about {next_topic}."
        response = st.session_state.chat.send_message(f"{prompt}\n\n[INSTRUCTION TO AI: {follow_up_instruction}]")
        assistant_message = response.text
        
        st.session_state.messages.append({"role": "assistant", "content": assistant_message})
        with st.chat_message("assistant"):
            st.write(assistant_message)
        
        st.rerun()

def complete_interview():
    """Complete the interview and grade it"""
    st.session_state.interview_complete = True
    
    # Build transcript
    transcript = "\n\n".join([
        f"{'AI Interviewer' if msg['role'] == 'assistant' else 'Student'}: {msg['content']}"
        for msg in st.session_state.messages
    ])
    
    # Grade the transcript
    with st.spinner("Grading your interview..."):
        score, status, feedback = grade_transcript(transcript)
    
    # Save to database
    save_interview(st.session_state.student_id, score, status, transcript)
    
    # Display results
    st.balloons() if status == "Pass" else None
    st.subheader("📋 Interview Results")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Score", f"{score}/100")
    with col2:
        status_color = "🟢" if status == "Pass" else "🔴"
        st.metric("Status", f"{status_color} {status}")
    
    st.text_area("Detailed Feedback", feedback, height=150)
    
    st.rerun()

def main():
    """Main application logic"""
    st.set_page_config(page_title="AP Physics Interview Bot", page_icon="🎓", layout="wide")
    
    # Initialize database
    init_db()
    
    # Check if student ID is in session
    if 'student_id' not in st.session_state:
        st.title("🎓 AP Physics Interview Bot")
        st.write("Welcome! Please enter your Student ID to begin.")
        
        student_id = st.text_input("Student ID:", placeholder="Enter your Student ID")
        
        if st.button("Start Interview"):
            if student_id:
                # Check if admin
                if student_id == "ADMIN123":
                    st.session_state.student_id = student_id
                    st.rerun()
                else:
                    # Check for previous interview
                    last_interview = get_student_last_interview(student_id)
                    
                    if last_interview:
                        st.session_state.student_id = student_id
                        st.session_state.show_previous_results = True
                        st.rerun()
                    else:
                        # New student - start interview
                        st.session_state.student_id = student_id
                        st.rerun()
            else:
                st.error("Please enter a Student ID")
    else:
        # Check if we need to show previous results
        if hasattr(st.session_state, 'show_previous_results') and st.session_state.show_previous_results:
            st.title("🎓 Welcome Back!")
            
            last_interview = get_student_last_interview(st.session_state.student_id)
            
            if last_interview:
                st.write(f"**Student ID:** {st.session_state.student_id}")
                st.write(f"**Last Interview:** {last_interview[2]}")  # date
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Previous Score", f"{last_interview[3]}/100")
                with col2:
                    status_color = "🟢" if last_interview[4] == "Pass" else "🔴"
                    st.metric("Previous Status", f"{status_color} {last_interview[4]}")
                
                st.divider()
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📝 Start New Interview", use_container_width=True):
                        del st.session_state.show_previous_results
                        st.rerun()
                with col2:
                    if st.button("👋 Logout", use_container_width=True):
                        for key in list(st.session_state.keys()):
                            del st.session_state[key]
                        st.rerun()
            else:
                del st.session_state.show_previous_results
                st.rerun()
        # Check if admin
        elif st.session_state.student_id == "ADMIN123":
            admin_panel()
        else:
            chat_interface(st.session_state.student_id)

if __name__ == "__main__":
    main()
