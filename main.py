import streamlit as st
import google.generativeai as genai
import os
import sqlite3
from datetime import datetime
import pandas as pd
import io

# Configure API Keys
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

if not GEMINI_API_KEY:
    st.error("⚠️ Gemini API Key not found! Please set the GEMINI_API_KEY environment variable.")
    st.stop()

if not ANTHROPIC_API_KEY:
    st.warning("ℹ️ Anthropic (Claude) API Key not set. Set ANTHROPIC_API_KEY environment variable if needed.")

# Configure Gemini for chat and grading
genai.configure(api_key=GEMINI_API_KEY)

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
            transcript TEXT NOT NULL,
            topic_index INTEGER DEFAULT 0
        )
    ''')
    
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
        return result[0]
    return 0

def grade_transcript(transcript):
    """Use Gemini AI to grade the interview transcript"""
    import time
    
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    grading_prompt = f"""
You are a physics teacher grading a SINGLE reflection chat session about Waves and Modern Physics.

Below is the transcript from THIS SESSION ONLY:

{transcript}

CRITICAL GRADING INSTRUCTIONS:
- Grade ONLY what happened in THIS session — do not consider any previous sessions or overall progress
- If the student only answered 1 or 2 questions in this session, grade them ONLY on those 1 or 2 answers
- If the transcript contains "[Student hasn't learned: X - Not yet covered in class]", IGNORE those topics entirely — they do not count for or against the student
- A student who answers 1 question brilliantly should score just as high as someone who answers 5 questions brilliantly
- Do NOT penalize for fewer questions answered — quality matters, not quantity
- Base the grade purely on the quality of the responses given in this session

Score from 0-100 based on:
- Correctness of the student's answers in this session (40%)
- Depth of understanding shown in this session (40%)
- Quality of explanations given in this session (20%)

Status: "Pass" if score >= 60, otherwise "Fail"

Respond in this exact format:
Score: [number]
Status: [Pass/Fail]
Feedback: [2-3 sentences about how the student did in THIS session specifically]
"""
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(grading_prompt)
            result_text = response.text
            
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
                    time.sleep(5)
                    continue
                else:
                    return 75, "Pass", "Unable to grade due to API limits. Session saved with default passing grade. Your instructor can review the transcript."
            else:
                return 75, "Pass", f"Grading error: {str(e)[:100]}. Session saved with default passing grade."
    
    return 75, "Pass", "Unable to grade after multiple attempts. Session saved with default passing grade."

def admin_panel():
    """Display admin panel with student summaries and transcript access"""
    st.title("📊 Admin Panel")
    
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
    
    df = get_all_interviews()
    
    if df.empty:
        st.info("No session records found.")
        return
    
    # Check if we're viewing a specific student's transcripts
    if 'admin_view_student' in st.session_state:
        student_id = st.session_state.admin_view_student
        st.subheader(f"📝 Conversations for: {student_id}")
        
        if st.button("← Back to Student List"):
            del st.session_state.admin_view_student
            st.rerun()
        
        student_df = df[df['student_id'] == student_id].sort_values('date', ascending=False)
        
        for _, row in student_df.iterrows():
            with st.expander(f"Session: {row['date']} — Score: {row['score']}/100 ({row['status']}) — Topics up to #{row.get('topic_index', 'N/A')}"):
                st.text_area(
                    "Transcript",
                    row['transcript'],
                    height=400,
                    key=f"transcript_{row['id']}",
                    disabled=True
                )
        return
    
    # Build student summary table
    st.subheader("Student Overview")
    
    summary_rows = []
    for student_id in df['student_id'].unique():
        if student_id.upper() == "ADMIN123":
            continue
        
        student_data = df[df['student_id'] == student_id].sort_values('date', ascending=False)
        latest = student_data.iloc[0]
        
        topic_index = int(latest.get('topic_index', 0))
        total_sessions = len(student_data)
        latest_score = int(latest['score'])
        latest_status = latest['status']
        last_date = latest['date']
        
        # Determine learning status
        if topic_index >= len(TOPICS):
            learning_status = "✅ Completed All Topics"
        elif topic_index == 0:
            learning_status = f"🔵 Just Started (0/{len(TOPICS)})"
        else:
            learning_status = f"🟡 In Progress ({topic_index}/{len(TOPICS)})"
        
        avg_score = round(student_data['score'].mean(), 1)
        
        summary_rows.append({
            "Student ID": student_id,
            "Learning Status": learning_status,
            "Topics Completed": f"{topic_index}/{len(TOPICS)}",
            "Total Sessions": total_sessions,
            "Latest Score": f"{latest_score}/100",
            "Avg Score": f"{avg_score}/100",
            "Latest Status": latest_status,
            "Last Active": last_date,
        })
    
    if not summary_rows:
        st.info("No student records found.")
        return
    
    summary_df = pd.DataFrame(summary_rows)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
    
    # CSV download
    csv_buffer = io.StringIO()
    summary_df.to_csv(csv_buffer, index=False)
    st.download_button(
        label="📥 Download Summary as CSV",
        data=csv_buffer.getvalue(),
        file_name=f"student_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
    
    st.divider()
    
    # View conversations buttons
    st.subheader("📝 View Student Conversations")
    
    student_ids = [s for s in df['student_id'].unique() if s.upper() != "ADMIN123"]
    cols = st.columns(min(3, len(student_ids)))
    
    for i, sid in enumerate(student_ids):
        with cols[i % 3]:
            if st.button(f"🔍 {sid}", key=f"view_{sid}", use_container_width=True):
                st.session_state.admin_view_student = sid
                st.rerun()
    
    st.divider()
    
    # Full data download
    csv_buffer_full = io.StringIO()
    df.to_csv(csv_buffer_full, index=False)
    st.download_button(
        label="📥 Download Full Data (all transcripts) as CSV",
        data=csv_buffer_full.getvalue(),
        file_name=f"full_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

def get_topic_keywords(topic):
    """Return key physics terms for each topic"""
    keywords = {
        "Simple Harmonic Motion": ["oscillation", "restoring force", "equilibrium", "amplitude", "frequency", "period", "angular frequency", "displacement", "Hooke's law"],
        "Pendulum and Mass Spring": ["pendulum", "mass-spring system", "spring constant", "period", "gravitational acceleration", "simple pendulum", "elastic potential energy", "natural frequency"],
        "Wave form": ["wavelength", "amplitude", "frequency", "period", "crest", "trough", "transverse wave", "longitudinal wave", "wave speed"],
        "Damped oscillation Damped Pendulum": ["damping", "damped oscillation", "underdamped", "overdamped", "critical damping", "energy dissipation", "exponential decay", "damping coefficient"],
        "Waves on a string": ["tension", "linear density", "wave speed", "pulse", "reflection", "transmission", "superposition", "boundary conditions"],
        "Standing Waves": ["nodes", "antinodes", "harmonics", "fundamental frequency", "resonance", "overtones", "standing wave pattern", "fixed end", "open end"],
        "Sound Waves": ["compression", "rarefaction", "longitudinal wave", "speed of sound", "intensity", "decibels", "pitch", "frequency", "medium"],
        "Doppler effect": ["frequency shift", "source velocity", "observer velocity", "red shift", "blue shift", "approaching", "receding", "apparent frequency"],
        "Musical instruments": ["harmonics", "overtones", "resonance", "open pipe", "closed pipe", "standing waves", "fundamental", "timbre", "vibrating string"],
        "Light as a wave": ["electromagnetic wave", "wavelength", "frequency", "speed of light", "diffraction", "interference", "double-slit experiment", "wave-particle duality"],
        "Angular Resolution": ["Rayleigh criterion", "diffraction limit", "aperture", "resolution", "angular separation", "single slit", "circular aperture"],
        "Thin film": ["constructive interference", "destructive interference", "path difference", "refractive index", "phase change", "oil film", "soap bubble", "optical thickness"],
        "Polarization": ["polarized light", "unpolarized light", "Malus's law", "polarizer", "analyzer", "Brewster's angle", "plane of polarization", "polarization by reflection"],
        "Thermal Physics Black body": ["blackbody radiation", "Stefan-Boltzmann law", "Wien's law", "Planck's law", "thermal equilibrium", "emissivity", "peak wavelength", "ultraviolet catastrophe"],
        "Light as a particle": ["photon", "photoelectric effect", "work function", "threshold frequency", "Planck's constant", "photon energy", "wave-particle duality", "Einstein"],
        "Radioactivity": ["alpha decay", "beta decay", "gamma radiation", "half-life", "nuclear decay", "isotopes", "radioactive decay", "binding energy", "mass defect"],
        "Relativity": ["time dilation", "length contraction", "speed of light", "Lorentz factor", "mass-energy equivalence", "E=mc²", "reference frame", "special relativity"],
    }
    return keywords.get(topic, [])

def chat_interface(student_id):
    """Main chat interface for student reflection sessions"""
    st.title("🎓 Reflections on Waves and Modern Physics")
    st.write(f"**Student ID:** {student_id}")
    st.divider()
    
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
        
        starting_topic_index = get_student_topic_progress(student_id)
        st.session_state.starting_topic_index = starting_topic_index
        st.session_state.current_topic_index = starting_topic_index
        
        if starting_topic_index >= len(TOPICS):
            # Silently restart from beginning
            starting_topic_index = 0
            st.session_state.starting_topic_index = 0
            st.session_state.current_topic_index = 0
        
        try:
            with st.spinner("Getting things ready for you... 😊"):
                model = genai.GenerativeModel('gemini-2.5-flash')
                st.session_state.chat = model.start_chat(history=[])
                
                session_topics = TOPICS[starting_topic_index:starting_topic_index + 5]
                
                initial_prompt = f"""You are a warm, friendly, and encouraging physics learning companion having a reflective conversation with a grade 12 student about Waves and Modern Physics.

YOUR PERSONALITY & STYLE:
- You are NOT a strict interviewer or examiner. You are a supportive friend who loves physics and wants to help the student think deeply.
- Use a warm, conversational tone — like a friendly tutor chatting over coffee.
- Celebrate what the student knows! Say things like "That's a great way to think about it!" or "I love how you connected those ideas!"
- When a student struggles, gently guide them with hints rather than just moving on. Say things like "You're on the right track! What if you think about it this way..." or "No worries — let's explore this together."
- Use real-world examples and analogies to make physics feel alive and relatable.
- Ask follow-up reflection questions like "What surprised you about that?" or "How does that connect to what you already know?"
- Keep it light and fun — sprinkle in enthusiasm! Physics is amazing and you want the student to feel that.
- Use emojis occasionally to keep things friendly 😊🌊✨
- NEVER tell the student which topic number they are on, how many topics are left, or mention any progress tracking. Just have a natural conversation.

CRITICAL INSTRUCTIONS - THIS SESSION'S TOPICS:
This is a 5-question session. You MUST cover these topics in order for THIS session:
{chr(10).join([f"{i+1}. {topic}" for i, topic in enumerate(session_topics)])}

RULES:
- Start with topic: {session_topics[0]}
- Ask ONE warm, thought-provoking question about each topic in order
- After the student answers, briefly acknowledge their response with encouragement, then transition naturally to the NEXT topic
- Do NOT skip topics or go out of order
- Do NOT mention topic numbers, progress, or how many questions remain
- Frame questions as reflections: "What do you think happens when..." or "How would you explain ... to a friend?"
- Make each question feel like a natural part of a conversation, not a test
- This session will cover {len(session_topics)} topics

Now greet the student warmly and ask your first friendly reflection question about {session_topics[0]}. Be conversational and encouraging!"""
                
                response = st.session_state.chat.send_message(initial_prompt)
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response.text
            })
        except Exception as e:
            st.error("⚠️ API Error: Unable to start the session. This might be due to rate limits.")
            st.info("Please wait a few minutes and try again, or contact your instructor.")
            if "ResourceExhausted" in str(e) or "429" in str(e):
                st.warning("🕐 The API has reached its rate limit. Please wait 1-2 minutes before starting a new session.")
            return
    
    # Get session info
    starting_index = st.session_state.starting_topic_index
    session_topics = TOPICS[starting_index:min(starting_index + 5, len(TOPICS))]
    
    # Two-column layout: chat on left, keywords on right
    chat_col, keyword_col = st.columns([3, 1])
    
    with keyword_col:
        st.markdown("### 🔑 Key Terms")
        # Show keywords for current topic and previously covered topics in this session
        topics_so_far = session_topics[:st.session_state.turn_count + 1]
        for topic in topics_so_far:
            keywords = get_topic_keywords(topic)
            if keywords:
                st.markdown(f"**{topic}**")
                st.markdown(", ".join(f"`{kw}`" for kw in keywords))
                st.write("")
        
        if not topics_so_far:
            st.caption("Keywords will appear here as you chat!")
    
    with chat_col:
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
    
        if st.session_state.interview_complete:
            # Show helpful learning resources for topics covered in this session
            TOPIC_RESOURCES = {
                "Simple Harmonic Motion": ("https://www.khanacademy.org/science/physics/mechanical-waves-and-sound/harmonic-motion/v/introduction-to-harmonic-motion", "Khan Academy — Intro to Harmonic Motion"),
                "Pendulum and Mass Spring": ("https://www.khanacademy.org/science/physics/mechanical-waves-and-sound/harmonic-motion/v/pendulum", "Khan Academy — Pendulums & Springs"),
                "Wave form": ("https://www.physicsclassroom.com/class/waves/Lesson-2/The-Anatomy-of-a-Wave", "The Physics Classroom — Anatomy of a Wave"),
                "Damped oscillation Damped Pendulum": ("https://www.khanacademy.org/science/physics/mechanical-waves-and-sound/harmonic-motion/a/what-is-damped-harmonic-motion", "Khan Academy — Damped Harmonic Motion"),
                "Waves on a string": ("https://phet.colorado.edu/en/simulations/wave-on-a-string", "PhET Simulation — Wave on a String"),
                "Standing Waves": ("https://www.physicsclassroom.com/class/sound/Lesson-4/Standing-Wave-Patterns", "The Physics Classroom — Standing Waves"),
                "Sound Waves": ("https://www.khanacademy.org/science/physics/mechanical-waves-and-sound/sound-topic/v/introduction-to-sound", "Khan Academy — Introduction to Sound"),
                "Doppler effect": ("https://www.khanacademy.org/science/physics/mechanical-waves-and-sound/doppler-effect/v/doppler-effect-introduction", "Khan Academy — Doppler Effect"),
                "Musical instruments": ("https://www.physicsclassroom.com/class/sound/Lesson-5/Musical-Instruments", "The Physics Classroom — Musical Instruments"),
                "Light as a wave": ("https://www.khanacademy.org/science/physics/light-waves/introduction-to-light-waves/v/introduction-to-light", "Khan Academy — Light as a Wave"),
                "Angular Resolution": ("https://www.khanacademy.org/science/physics/light-waves/interference-of-light-waves/v/single-slit-interference", "Khan Academy — Diffraction & Resolution"),
                "Thin film": ("https://www.khanacademy.org/science/physics/light-waves/interference-of-light-waves/v/thin-film-interference", "Khan Academy — Thin Film Interference"),
                "Polarization": ("https://www.physicsclassroom.com/class/light/Lesson-1/Polarization", "The Physics Classroom — Polarization"),
                "Thermal Physics Black body": ("https://www.khanacademy.org/science/physics/quantum-physics/photons/v/blackbody-radiation", "Khan Academy — Blackbody Radiation"),
                "Light as a particle": ("https://www.khanacademy.org/science/physics/quantum-physics/photons/v/photoelectric-effect", "Khan Academy — Photoelectric Effect"),
                "Radioactivity": ("https://www.khanacademy.org/science/physics/quantum-physics/in-in-nuclear-physics/v/types-of-decay", "Khan Academy — Radioactive Decay"),
                "Relativity": ("https://www.khanacademy.org/science/physics/special-relativity/einstein-velocity-addition/v/einstein-velocity-addition", "Khan Academy — Special Relativity"),
            }
            
            TOPICS = list(TOPIC_RESOURCES.keys())
            starting_index = st.session_state.starting_topic_index
            session_topics = TOPICS[starting_index:min(starting_index + 5, len(TOPICS))]
            
            st.divider()
            st.write("📖 **Want to learn more? Check out these resources:**")
            for topic in session_topics:
                if topic in TOPIC_RESOURCES:
                    url, label = TOPIC_RESOURCES[topic]
                    st.markdown(f"- [{label}]({url})")
            
            st.write("")
            if st.button("Start New Session"):
                for key in ['messages', 'turn_count', 'interview_complete', 'chat', 'starting_topic_index', 'current_topic_index']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
            return
        
        # Show skip and finish buttons
        col1, col2, col3 = st.columns([2, 1.5, 1])
        with col2:
            if st.button("📚 Haven't Learned This Yet", use_container_width=True):
                if st.session_state.turn_count < len(session_topics):
                    skipped_topic = session_topics[st.session_state.turn_count]
                    
                    skip_message = f"[Student hasn't learned: {skipped_topic} - Not yet covered in class]"
                    st.session_state.messages.append({
                        "role": "user", 
                        "content": skip_message
                    })
                    
                    st.session_state.turn_count += 1
                    st.session_state.current_topic_index += 1
                    
                    if st.session_state.turn_count >= len(session_topics):
                        complete_interview()
                        return
                    
                    next_topic = session_topics[st.session_state.turn_count]
                    try:
                        instruction = f"The student hasn't covered {skipped_topic} yet in class — that's totally fine! Warmly reassure them and smoothly transition to the next topic: {next_topic}. Ask a friendly reflection question about {next_topic}. Do NOT mention topic numbers or progress."
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
        with col3:
            if st.button("🏁 Finish Session", use_container_width=True):
                complete_interview()
                return
    
    # Chat input
    if prompt := st.chat_input("Share your thoughts here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        st.session_state.turn_count += 1
        st.session_state.current_topic_index += 1
        
        if st.session_state.turn_count >= len(session_topics):
            complete_interview()
            return
        
        next_topic = session_topics[st.session_state.turn_count]
        
        try:
            follow_up_instruction = f"Warmly acknowledge the student's answer with encouragement. Then naturally transition to the next topic: {next_topic}. Ask ONE friendly, thought-provoking reflection question about {next_topic}. Keep it conversational and supportive! Do NOT mention topic numbers or progress."
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
    """Complete the session and grade it"""
    st.session_state.interview_complete = True
    
    transcript = "\n\n".join([
        f"{'AI Learning Companion' if msg['role'] == 'assistant' else 'Student'}: {msg['content']}"
        for msg in st.session_state.messages
    ])
    
    with st.spinner("Wrapping up... ✨"):
        score, status, feedback = grade_transcript(transcript)
    
    save_interview(
        st.session_state.student_id, 
        score, 
        status, 
        transcript, 
        st.session_state.current_topic_index
    )
    
    st.rerun()

def main():
    """Main application logic"""
    st.set_page_config(page_title="Reflections on Waves and Modern Physics", page_icon="🎓", layout="wide")
    
    init_db()
    
    if 'student_id' not in st.session_state:
        st.title("🎓 Reflections on Waves and Modern Physics")
        st.write("Welcome! Please enter your Student ID to begin.")
        
        def on_student_id_submit():
            sid = st.session_state.student_id_input.strip()
            if sid:
                st.session_state.student_id = sid
        
        student_id = st.text_input(
            "Student ID:", 
            placeholder="Enter your Student ID", 
            key="student_id_input",
            on_change=on_student_id_submit
        )
        
        if st.button("Start Chat"):
            if student_id:
                st.session_state.student_id = student_id.strip()
                st.rerun()
            else:
                st.error("Please enter a Student ID")
    else:
        if st.session_state.student_id.upper() == "ADMIN123":
            admin_panel()
        else:
            chat_interface(st.session_state.student_id)

if __name__ == "__main__":
    main()
