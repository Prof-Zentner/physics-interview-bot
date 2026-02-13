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
    
    # Create table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            date TEXT NOT NULL,
            score INTEGER NOT NULL,
            status TEXT NOT NULL,
            transcript TEXT NOT NULL,
            topic_index INTEGER DEFAULT 0
        )
    ''')
    
    # Check if topic_index column exists, add it if it doesn't
    cursor.execute("PRAGMA table_info(interviews)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'topic_index' not in columns:
        cursor.execute('ALTER TABLE interviews ADD COLUMN topic_index INTEGER DEFAULT 0')
        conn.commit()
    
    conn.commit()
    conn.close()

def save_interview(student_id, score, status, transcript, topic_index):
    """Save interview results to database"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO interviews (student_id, date, score, status, transcript, topic_index)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (student_id, date, score, status, transcript, topic_index))
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

def get_student_topic_progress(student_id):
    """Get the next topic index for a student (where they should continue from)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT topic_index FROM interviews 
        WHERE student_id = ? 
        ORDER BY date DESC 
        LIMIT 1
    ''', (student_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        # Return the next topic index (the one after the last completed session)
        return result[0]
    return 0  # Start from beginning if no history

def grade_transcript(transcript):
    """Use Gemini AI to grade the interview transcript"""
    import time
    
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    grading_prompt = f"""
You are a physics teacher grading an AP Physics interview about Waves and Modern Physics.

Below is the complete transcript of a student interview session:

{transcript}

IMPORTANT GRADING INSTRUCTIONS:
- If the transcript contains "[Student hasn't learned: X - Not yet covered in class]", DO NOT penalize the student for those topics
- Only grade the student on topics they actually answered
- Topics they haven't learned yet should be treated neutrally and NOT count against their score
- The student should only be evaluated on material they have been taught

Please analyze the student's responses and provide:
1. A Score from 0-100 based on:
   - Correctness of answers (50%)
   - Understanding of concepts (30%)
   - Depth of explanations (20%)
   - ONLY for topics they answered (not topics they haven't learned)
2. A Status: "Pass" if score >= 60, otherwise "Fail"

Respond in this exact format:
Score: [number]
Status: [Pass/Fail]
Feedback: [2-3 sentences explaining the grade, acknowledging any topics not yet covered]
"""
    
    # Try grading with retry on rate limit
    max_retries = 3
    for attempt in range(max_retries):
        try:
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
            
        except Exception as e:
            if "ResourceExhausted" in str(e) or "429" in str(e):
                if attempt < max_retries - 1:
                    time.sleep(5)  # Wait 5 seconds before retry
                    continue
                else:
                    # Return default passing grade if can't grade
                    return 75, "Pass", "Unable to grade due to API limits. Session saved with default passing grade. Your instructor can review the transcript."
            else:
                # Other error - return default
                return 75, "Pass", f"Grading error: {str(e)[:100]}. Session saved with default passing grade."
    
    return 75, "Pass", "Unable to grade after multiple attempts. Session saved with default passing grade."

def analyze_failure_reasons(transcript, score):
    """Use Gemini AI to analyze why a student failed"""
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    analysis_prompt = f"""
You are an AP Physics teacher analyzing why a student did not pass their interview (Score: {score}/100).

Below is the complete interview transcript:

{transcript}

Please provide a detailed analysis covering:

1. **Main Weaknesses** - What were the 2-3 biggest gaps in understanding?
2. **Specific Misconceptions** - What incorrect concepts did the student demonstrate?
3. **Missing Fundamentals** - What foundational knowledge appears to be lacking?
4. **Recommendations** - What specific topics should the student review before retrying?

Keep your analysis constructive and specific. Focus on learning opportunities.

Format your response clearly with headers.
"""
    
    try:
        response = model.generate_content(analysis_prompt)
        return response.text
    except Exception as e:
        return f"Unable to generate analysis: {str(e)[:200]}"

def admin_panel():
    """Display admin panel with all results"""
    st.title("📊 Admin Panel - Interview Results")
    
    df = get_all_interviews()
    
    if df.empty:
        st.info("No interview records found.")
    else:
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Interviews", len(df))
        with col2:
            pass_count = len(df[df['status'] == 'Pass'])
            st.metric("Passed", pass_count)
        with col3:
            fail_count = len(df[df['status'] == 'Fail'])
            st.metric("Failed", fail_count)
        with col4:
            avg_score = df['score'].mean()
            st.metric("Avg Score", f"{avg_score:.1f}")
        
        st.divider()
        
        # Display dataframe
        st.subheader("All Interview Results")
        st.dataframe(df[['id', 'student_id', 'date', 'score', 'status', 'topic_index']], use_container_width=True)
        
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
        
        st.divider()
        
        # Detailed review section - expandable for each failed interview
        st.subheader("📋 Detailed Review - Failed Interviews")
        
        failed_interviews = df[df['status'] == 'Fail']
        
        if failed_interviews.empty:
            st.success("✅ No failed interviews to review!")
        else:
            for idx, row in failed_interviews.iterrows():
                with st.expander(f"🔍 Student {row['student_id']} - Score: {row['score']}/100 - Date: {row['date']}"):
                    st.write(f"**Interview ID:** {row['id']}")
                    st.write(f"**Topics Completed:** {row['topic_index']}/17")
                    
                    # Show transcript
                    with st.expander("📄 View Full Transcript"):
                        st.text_area("Transcript", row['transcript'], height=300, key=f"transcript_{row['id']}")
                    
                    # AI Analysis button
                    if st.button(f"🤖 Generate AI Failure Analysis", key=f"analyze_{row['id']}"):
                        with st.spinner("Analyzing interview with AI..."):
                            analysis = analyze_failure_reasons(row['transcript'], row['score'])
                            st.markdown("### 📊 AI Analysis Results")
                            st.markdown(analysis)
                            
                    st.divider()
        
        # Optional: Review passed interviews
        st.divider()
        st.subheader("✅ Review Passed Interviews (Optional)")
        
        if st.checkbox("Show passed interviews for review"):
            passed_interviews = df[df['status'] == 'Pass']
            
            if passed_interviews.empty:
                st.info("No passed interviews yet.")
            else:
                for idx, row in passed_interviews.iterrows():
                    with st.expander(f"✅ Student {row['student_id']} - Score: {row['score']}/100 - Date: {row['date']}"):
                        st.write(f"**Interview ID:** {row['id']}")
                        st.write(f"**Topics Completed:** {row['topic_index']}/17")
                        
                        # Show transcript
                        with st.expander("📄 View Full Transcript"):
                            st.text_area("Transcript", row['transcript'], height=300, key=f"transcript_pass_{row['id']}")
                        
                        st.divider()

def chat_interface(student_id):
    """Main chat interface for student interviews"""
    
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
    
    # Sidebar with progress and info (collapsible on mobile)
    with st.sidebar:
        st.title("📊 Session Info")
        st.write(f"**Student:** {student_id}")
        st.write("**Topic:** Waves & Modern Physics")
        st.divider()
        
        # Show current progress if session started
        if 'current_topic_index' in st.session_state:
            progress = st.session_state.current_topic_index / len(TOPICS)
            st.progress(progress)
            st.caption(f"Overall: {st.session_state.current_topic_index}/{len(TOPICS)} topics")
            st.divider()
        
        # Expandable topic list
        with st.expander("📚 All Topics (17)", expanded=False):
            for i, topic in enumerate(TOPICS, 1):
                # Highlight completed topics
                if 'current_topic_index' in st.session_state and i <= st.session_state.current_topic_index:
                    st.markdown(f"✅ {i}. {topic}")
                else:
                    st.caption(f"{i}. {topic}")
        
        st.divider()
        
        # Logout button in sidebar
        if st.button("👋 Logout", use_container_width=True, type="secondary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Main content
    st.title("🎓 AP Physics Interview")
    
    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []
        st.session_state.turn_count = 0
        st.session_state.interview_complete = False
        
        # Get where student left off
        starting_topic_index = get_student_topic_progress(student_id)
        st.session_state.starting_topic_index = starting_topic_index
        st.session_state.current_topic_index = starting_topic_index
        
        # Check if all topics are completed
        if starting_topic_index >= len(TOPICS):
            st.success("🎉 Congratulations! You've completed all topics!")
            st.info("All 17 topics have been covered. Great work!")
            if st.button("Start Over from Beginning"):
                # Reset their progress
                st.session_state.starting_topic_index = 0
                st.session_state.current_topic_index = 0
                st.rerun()
            return
        
        # Initialize AI conversation
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            st.session_state.chat = model.start_chat(history=[])
            
            # Determine which topics for this session
            session_topics = TOPICS[starting_topic_index:starting_topic_index + 5]
            
            # Send initial system message with topic progression
            initial_prompt = f"""You are an AP Physics teacher interviewing a grade 12 student about Waves and Modern Physics. 

CRITICAL INSTRUCTIONS - THIS SESSION'S TOPICS:
This is a 5-question session. You MUST ask questions following this exact order for THIS session:
{chr(10).join([f"{i+1}. {topic}" for i, topic in enumerate(session_topics)])}

The student has already completed topics 1-{starting_topic_index} in previous sessions.

RULES:
- Start with topic: {session_topics[0]}
- Ask ONE clear, focused question about each topic in order
- After the student answers, move to the NEXT topic in the session list
- Do NOT skip topics or go out of order
- Be encouraging but test their understanding thoroughly
- Each question should probe their conceptual understanding of that specific topic
- This session will cover {len(session_topics)} topics

Start the interview with your first question about {session_topics[0]}."""
            
            response = st.session_state.chat.send_message(initial_prompt)
            first_question = st.session_state.chat.send_message(f"Ask your first question about {session_topics[0]}.")
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": first_question.text
            })
        except Exception as e:
            st.error("⚠️ API Error: Unable to start the interview. This might be due to rate limits.")
            st.info("Please wait a few minutes and try again, or contact your instructor.")
            if "ResourceExhausted" in str(e) or "429" in str(e):
                st.warning("🕐 The API has reached its rate limit. Please wait 1-2 minutes before starting a new session.")
            return
    
    # Get session info
    starting_index = st.session_state.starting_topic_index
    current_index = st.session_state.current_topic_index
    session_topics = TOPICS[starting_index:min(starting_index + 5, len(TOPICS))]
    
    # Display session progress (compact for mobile)
    session_question_num = st.session_state.turn_count + 1
    total_session_questions = len(session_topics)
    
    st.info(f"📝 Question {session_question_num}/{total_session_questions} • {current_index}/{len(TOPICS)} topics done")
    
    # Show current topic
    if st.session_state.turn_count < len(session_topics):
        current_topic = session_topics[st.session_state.turn_count]
        st.success(f"**Current:** {current_topic}")
        st.caption("💡 Not there yet in class? Click 'Haven't Learned This Yet'")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Check if interview is complete
    if st.session_state.interview_complete:
        st.success("✅ Session completed and graded!")
        if st.button("Start New Session"):
            for key in ['messages', 'turn_count', 'interview_complete', 'chat', 'starting_topic_index', 'current_topic_index']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        return
    
    # Show finish button and skip topic option
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("📚 Haven't Learned Yet", use_container_width=True):
            # Skip the current topic without penalty
            if st.session_state.turn_count < len(session_topics):
                skipped_topic = session_topics[st.session_state.turn_count]
                
                # Add a message indicating the skip
                skip_message = f"[Student hasn't learned: {skipped_topic} - Not yet covered in class]"
                st.session_state.messages.append({
                    "role": "user", 
                    "content": skip_message
                })
                
                # Increment counters
                st.session_state.turn_count += 1
                st.session_state.current_topic_index += 1
                
                # Check if session is complete
                if st.session_state.turn_count >= len(session_topics):
                    complete_interview()
                    return
                
                # Move to next topic
                next_topic = session_topics[st.session_state.turn_count]
                try:
                    instruction = f"The student has not covered {skipped_topic} yet in class. Move to the next topic: {next_topic}. Ask a question about {next_topic}."
                    response = st.session_state.chat.send_message(instruction)
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response.text
                    })
                    
                    st.rerun()
                except Exception as e:
                    st.error("⚠️ API Error: Unable to skip to next topic.")
                    if "ResourceExhausted" in str(e) or "429" in str(e):
                        st.warning("🕐 Rate limit reached. Please wait 1-2 minutes and try again.")
                    st.info("You can click 'Finish Session' to save your progress.")
    with col2:
        if st.button("🏁 Finish Session", use_container_width=True, type="primary"):
            complete_interview()
            return
    
    # Chat input
    if prompt := st.chat_input("Type your answer here..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        # Increment turn counter and topic index
        st.session_state.turn_count += 1
        st.session_state.current_topic_index += 1
        
        # Check if we've completed this session (5 questions or all remaining topics)
        if st.session_state.turn_count >= len(session_topics):
            complete_interview()
            return
        
        # Get next topic in this session
        next_topic = session_topics[st.session_state.turn_count]
        
        # Get AI response with instruction to move to next topic
        try:
            follow_up_instruction = f"Good. Now move to the next topic in this session: {next_topic}. Ask ONE clear question about {next_topic}."
            response = st.session_state.chat.send_message(f"{prompt}\n\n[INSTRUCTION TO AI: {follow_up_instruction}]")
            assistant_message = response.text
            
            st.session_state.messages.append({"role": "assistant", "content": assistant_message})
            with st.chat_message("assistant"):
                st.write(assistant_message)
            
            st.rerun()
        except Exception as e:
            st.error("⚠️ API Error: Unable to get next question.")
            if "ResourceExhausted" in str(e) or "429" in str(e):
                st.warning("🕐 Rate limit reached. Please wait 1-2 minutes and click 'Finish Session' to save your progress.")
            else:
                st.info("Please try clicking 'Finish Session' to save your progress so far.")

def complete_interview():
    """Complete the interview and grade it"""
    st.session_state.interview_complete = True
    
    # Build transcript
    transcript = "\n\n".join([
        f"{'AI Interviewer' if msg['role'] == 'assistant' else 'Student'}: {msg['content']}"
        for msg in st.session_state.messages
    ])
    
    # Grade the transcript
    with st.spinner("Grading your session..."):
        score, status, feedback = grade_transcript(transcript)
    
    # Save to database with updated topic index
    save_interview(
        st.session_state.student_id, 
        score, 
        status, 
        transcript, 
        st.session_state.current_topic_index
    )
    
    # Display results
    st.balloons() if status == "Pass" else None
    st.subheader("📋 Session Results")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Score", f"{score}/100")
    with col2:
        status_color = "🟢" if status == "Pass" else "🔴"
        st.metric("Status", f"{status_color} {status}")
    
    st.text_area("Detailed Feedback", feedback, height=150)
    
    # Show progress info
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
    
    remaining = len(TOPICS) - st.session_state.current_topic_index
    if remaining > 0:
        st.info(f"📚 Progress: {st.session_state.current_topic_index}/{len(TOPICS)} topics completed. {remaining} topics remaining.")
        st.write("Come back for your next session to continue!")
    else:
        st.success("🎉 Congratulations! You've completed all 17 topics!")
    
    st.rerun()

def main():
    """Main application logic"""
    st.set_page_config(
        page_title="AP Physics Interview Bot", 
        page_icon="🎓", 
        layout="wide",
        initial_sidebar_state="auto"  # Auto-collapse on mobile
    )
    
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
            topic_progress = get_student_topic_progress(st.session_state.student_id)
            
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
            
            if last_interview:
                st.write(f"**Student ID:** {st.session_state.student_id}")
                st.write(f"**Last Session:** {last_interview[2]}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Last Session Score", f"{last_interview[3]}/100")
                with col2:
                    status_color = "🟢" if last_interview[4] == "Pass" else "🔴"
                    st.metric("Last Session Status", f"{status_color} {last_interview[4]}")
                
                # Show progress
                st.progress(topic_progress / len(TOPICS))
                st.info(f"📚 Progress: {topic_progress}/{len(TOPICS)} topics completed")
                
                if topic_progress < len(TOPICS):
                    remaining = min(5, len(TOPICS) - topic_progress)
                    next_topics = TOPICS[topic_progress:topic_progress + remaining]
                    st.success(f"**Next Session Topics ({remaining} questions):**")
                    for i, topic in enumerate(next_topics, 1):
                        st.write(f"{i}. {topic}")
                else:
                    st.success("🎉 You've completed all topics!")
                
                st.divider()
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📝 Continue to Next Session", use_container_width=True):
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
