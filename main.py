import streamlit as st
import google.generativeai as genai
import os
import sqlite3
import time
from datetime import datetime
import pandas as pd
import io

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    st.error("⚠️ Gemini API Key not found! Please set the GEMINI_API_KEY environment variable.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)

DB_NAME = "interview_results.db"

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
    "Relativity",
]

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

TOPIC_KEYWORDS = {
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

# ──────────────────────────────────────────────
# Database helpers
# ──────────────────────────────────────────────

def init_db():
    """Initialize the SQLite database and migrate if needed."""
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
            topic_index INTEGER DEFAULT 0,
            correctness INTEGER DEFAULT 0,
            understanding INTEGER DEFAULT 0,
            explanation INTEGER DEFAULT 0
        )
    ''')

    # Migrate older databases that may be missing columns
    cursor.execute("PRAGMA table_info(interviews)")
    columns = [col[1] for col in cursor.fetchall()]

    for col_name in ('topic_index', 'correctness', 'understanding', 'explanation'):
        if col_name not in columns:
            cursor.execute(f'ALTER TABLE interviews ADD COLUMN {col_name} INTEGER DEFAULT 0')

    conn.commit()
    conn.close()


def save_interview(student_id, score, status, transcript, topic_index,
                   correctness=0, understanding=0, explanation=0):
    """Save interview results to database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO interviews
            (student_id, date, score, status, transcript, topic_index, correctness, understanding, explanation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (student_id, date, score, status, transcript, topic_index,
          correctness, understanding, explanation))
    conn.commit()
    conn.close()


def get_all_interviews():
    """Retrieve all interview records as a DataFrame."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM interviews", conn)
    conn.close()
    return df


def get_student_topic_progress(student_id):
    """Get the next topic index for a student (where they should continue from)."""
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
    return result[0] if result else 0


# ──────────────────────────────────────────────
# AI helpers (Gemini)
# ──────────────────────────────────────────────

def _gemini_call_with_retries(prompt, max_retries=3):
    """Send a prompt to Gemini with automatic retry on rate-limit errors.
    Returns the response text on success, raises on failure."""
    model = genai.GenerativeModel('gemini-2.5-flash')
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if ("ResourceExhausted" in str(e) or "429" in str(e)) and attempt < max_retries - 1:
                time.sleep(5)
                continue
            raise
    return None


def grade_transcript(transcript):
    """Grade the interview transcript with a 40/40/20 breakdown.
    Returns (score, status, feedback_text, correctness, understanding, explanation)."""

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

Grade each component out of 100, then compute the weighted total:
- Correctness: How accurate are the student's physics answers? (weight: 40%)
- Understanding: How deeply does the student grasp the concepts? (weight: 40%)
- Explanation Quality: How well does the student articulate and explain ideas? (weight: 20%)

Status: "Pass" if weighted total >= 60, otherwise "Fail"

Respond in this EXACT format (do not change the labels):
Correctness: [number out of 100]
Understanding: [number out of 100]
Explanation: [number out of 100]
Score: [weighted total out of 100]
Status: [Pass/Fail]
Feedback: [2-3 sentences about how the student did in THIS session specifically]
"""

    default = (75, "Pass", "Unable to grade. Session saved with default passing grade.", 0, 0, 0)

    try:
        result_text = _gemini_call_with_retries(grading_prompt)
    except Exception:
        return default

    if not result_text:
        return default

    score = 0
    status = "Fail"
    correctness = 0
    understanding = 0
    explanation = 0

    for line in result_text.split('\n'):
        line = line.strip()
        if line.startswith('Correctness:'):
            correctness = int(''.join(filter(str.isdigit, line.split(':')[1])))
        elif line.startswith('Understanding:'):
            understanding = int(''.join(filter(str.isdigit, line.split(':')[1])))
        elif line.startswith('Explanation:'):
            explanation = int(''.join(filter(str.isdigit, line.split(':')[1])))
        elif line.startswith('Score:'):
            score = int(''.join(filter(str.isdigit, line.split(':')[1])))
        elif line.startswith('Status:'):
            status = line.split(':')[1].strip()

    # Recalculate weighted score to ensure consistency
    if correctness or understanding or explanation:
        score = round(correctness * 0.4 + understanding * 0.4 + explanation * 0.2)
        status = "Pass" if score >= 60 else "Fail"

    return score, status, result_text, correctness, understanding, explanation


def analyze_student_session(transcript, score, status):
    """Use Gemini to generate a detailed analysis of a student session (admin only)."""

    analysis_prompt = f"""You are a physics teacher analyzing a student's reflection chat session about Waves and Modern Physics.

The student scored {score}/100 and received a status of "{status}".

Here is the full transcript:

{transcript}

Please provide a detailed, constructive analysis covering:

1. **Key Weaknesses**: What specific physics concepts did the student struggle with or get wrong? Give concrete examples from the transcript.
2. **Misconceptions Identified**: Are there any physics misconceptions the student seems to hold? Be specific.
3. **What They Did Well**: What topics or concepts did the student demonstrate good understanding of?
4. **Breakdown Assessment**:
   - Correctness (40%): How accurate were their answers? Which specific answers were incorrect?
   - Understanding (40%): Did they show surface-level memorization or deep conceptual understanding?
   - Explanation Quality (20%): Could they articulate their reasoning clearly?
5. **Recommended Next Steps**: What should this student focus on to improve? Be specific about topics and suggest study strategies.

Keep the tone constructive and helpful — this is for the teacher to understand how to help the student improve.
"""

    try:
        return _gemini_call_with_retries(analysis_prompt)
    except Exception:
        return "⚠️ Unable to generate analysis. Please try again in a few minutes."


# ──────────────────────────────────────────────
# Admin panel
# ──────────────────────────────────────────────

def admin_panel():
    """Display admin panel with student summaries and transcript access."""
    st.title("📊 Admin Panel")

    df = get_all_interviews()

    if df.empty:
        st.info("No session records found.")
        return

    # ── Viewing a specific student's transcripts ──
    if 'admin_view_student' in st.session_state:
        student_id = st.session_state.admin_view_student
        st.subheader(f"📝 Conversations for: {student_id}")

        if st.button("← Back to Student List"):
            del st.session_state.admin_view_student
            st.session_state.pop('analysis_results', None)
            st.rerun()

        student_df = df[df['student_id'] == student_id].sort_values('date', ascending=False)

        for _, row in student_df.iterrows():
            row_id = row['id']
            correctness = int(row.get('correctness', 0) or 0)
            understanding = int(row.get('understanding', 0) or 0)
            explanation_score = int(row.get('explanation', 0) or 0)

            with st.expander(
                f"Session: {row['date']} — Score: {row['score']}/100 "
                f"({row['status']}) — Topics up to #{row.get('topic_index', 'N/A')}"
            ):
                # 40/40/20 breakdown
                if correctness or understanding or explanation_score:
                    st.markdown("**📊 Score Breakdown (40/40/20):**")
                    bc1, bc2, bc3 = st.columns(3)
                    with bc1:
                        st.metric("Correctness (40%)", f"{correctness}/100")
                    with bc2:
                        st.metric("Understanding (40%)", f"{understanding}/100")
                    with bc3:
                        st.metric("Explanation (20%)", f"{explanation_score}/100")
                    st.caption(
                        f"Weighted Total: {correctness}×0.4 + {understanding}×0.4 "
                        f"+ {explanation_score}×0.2 = **{row['score']}/100**"
                    )
                    st.divider()

                # Transcript
                st.text_area(
                    "Transcript", row['transcript'],
                    height=400, key=f"transcript_{row_id}", disabled=True,
                )

                # AI Analysis button
                analysis_key = f"analysis_{row_id}"
                if st.button("🔍 Analyze This Session", key=f"btn_analyze_{row_id}", use_container_width=True):
                    with st.spinner("Generating AI analysis... This may take a moment."):
                        analysis = analyze_student_session(row['transcript'], row['score'], row['status'])
                        if 'analysis_results' not in st.session_state:
                            st.session_state.analysis_results = {}
                        st.session_state.analysis_results[analysis_key] = analysis
                        st.rerun()

                # Display cached analysis
                if 'analysis_results' in st.session_state and analysis_key in st.session_state.analysis_results:
                    st.markdown("---")
                    st.markdown("### 🔍 AI Analysis")
                    st.markdown(st.session_state.analysis_results[analysis_key])
        return

    # ── Student overview table ──
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
        avg_score = round(student_data['score'].mean(), 1)

        if topic_index >= len(TOPICS):
            learning_status = "✅ Completed All Topics"
        elif topic_index == 0:
            learning_status = f"🔵 Just Started (0/{len(TOPICS)})"
        else:
            learning_status = f"🟡 In Progress ({topic_index}/{len(TOPICS)})"

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

    # CSV download — summary
    csv_buffer = io.StringIO()
    summary_df.to_csv(csv_buffer, index=False)
    st.download_button(
        label="📥 Download Summary as CSV",
        data=csv_buffer.getvalue(),
        file_name=f"student_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
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

    # CSV download — full data
    csv_buffer_full = io.StringIO()
    df.to_csv(csv_buffer_full, index=False)
    st.download_button(
        label="📥 Download Full Data (all transcripts) as CSV",
        data=csv_buffer_full.getvalue(),
        file_name=f"full_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )


# ──────────────────────────────────────────────
# Student chat interface
# ──────────────────────────────────────────────

def chat_interface(student_id):
    """Main chat interface for student reflection sessions."""
    st.title("🎓 Reflections on Waves and Modern Physics")
    st.write(f"**Student ID:** {student_id}")
    st.divider()

    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []
        st.session_state.turn_count = 0
        st.session_state.interview_complete = False

        starting_topic_index = get_student_topic_progress(student_id)
        if starting_topic_index >= len(TOPICS):
            starting_topic_index = 0  # Restart from beginning

        st.session_state.starting_topic_index = starting_topic_index
        st.session_state.current_topic_index = starting_topic_index

        try:
            with st.spinner("Getting things ready for you... 😊"):
                model = genai.GenerativeModel('gemini-2.5-flash')
                st.session_state.chat = model.start_chat(history=[])

                session_topics = TOPICS[starting_topic_index:starting_topic_index + 5]

                initial_prompt = f"""You are a warm, friendly, and encouraging physics learning companion having a reflective conversation with a grade 12 student about Waves and Modern Physics.

YOUR PERSONALITY & STYLE:
- You are NOT a strict interviewer or examiner. You're more like a chill, knowledgeable friend who happens to love physics.
- Use a relaxed, conversational tone — not overly enthusiastic or preachy. Think casual tutor, not motivational speaker.
- When a student gets something right, keep it real — "Yeah, that's solid" or "Exactly, nice" works better than over-the-top praise.
- When a student struggles, be low-key supportive — "Hmm, not quite but you're close — think about it this way..." or "No stress, let's work through it."
- Use emojis naturally but don't overdo it 🌊✨
- NEVER tell the student which topic number they are on, how many topics are left, or mention any progress tracking. Just have a natural conversation.

HOOKING THE STUDENT — REAL-WORLD SCENARIOS:
- Open each question with a quick, relatable real-world scenario BEFORE the physics question. Keep it casual — just a sentence or two to set the scene.
- The goal is to ground the physics in something the student has actually experienced.
- Examples:
  * Simple Harmonic Motion: "So you know when you're on a swing and you just let it go back and forth without pumping..."
  * Sound Waves: "You know that feeling at a concert when the bass hits so hard you feel it in your ribs?"
  * Doppler effect: "Ever noticed how an ambulance siren sounds different as it passes you?"
  * Light as a wave: "You've probably seen those rainbow swirls on a soap bubble, right?"
  * Radioactivity: "In pretty much every sci-fi movie there's a Geiger counter clicking away..."
- Create your OWN scenario for each topic — keep it short and something a 17-19 year old would actually relate to (music, phones, sports, space, movies, games, etc.)
- Then lead naturally into your question.

"WHAT IF" TWISTS — DEEPEN ENGAGEMENT:
- After the student answers, occasionally (about half the time) drop a casual "what if" follow-up before moving on. It should feel like a side thought, not a bonus exam question.
- Examples:
  * "Solid. Quick thought though — what if you took that pendulum to the Moon? What changes? 🌙"
  * "Right. But what if the string had zero mass — would the wave still behave the same?"
  * "Yeah exactly. Now what if you were floating in space with no air — could you still hear anything? 🚀"
  * "What if the slit was smaller than the wavelength of light — what would you expect to happen?"
- Keep these low-pressure. If the student doesn't bite or struggles, just move on — no big deal.

CRITICAL INSTRUCTIONS - THIS SESSION'S TOPICS:
This is a 5-question session. You MUST cover these topics in order for THIS session:
{chr(10).join([f"{i+1}. {topic}" for i, topic in enumerate(session_topics)])}

RULES:
- Start with topic: {session_topics[0]}
- Ask ONE clear, interesting question about each topic in order, leading with a quick real-world scenario
- After the student answers, acknowledge briefly, optionally drop a "what if" side thought, then move naturally to the NEXT topic
- Do NOT skip topics or go out of order
- Do NOT mention topic numbers, progress, or how many questions remain
- Make each question feel like a natural part of a conversation, not a test
- This session will cover {len(session_topics)} topics

Now greet the student casually and kick things off with a relatable real-world scenario about {session_topics[0]} before asking your first question. Keep it chill."""

                response = st.session_state.chat.send_message(initial_prompt)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response.text,
                })
        except Exception as e:
            st.error("⚠️ API Error: Unable to start the session. This might be due to rate limits.")
            st.info("Please wait a few minutes and try again, or contact your instructor.")
            if "ResourceExhausted" in str(e) or "429" in str(e):
                st.warning("🕐 The API has reached its rate limit. Please wait 1-2 minutes before starting a new session.")
            return

    # Session info
    starting_index = st.session_state.starting_topic_index
    session_topics = TOPICS[starting_index:min(starting_index + 5, len(TOPICS))]

    # Keywords sidebar — only show the CURRENT topic being discussed
    with st.sidebar:
        st.markdown("### 🔑 Key Terms")
        st.caption("Use these terms to guide your reflections!")
        st.divider()
        current_q = st.session_state.turn_count
        if current_q < len(session_topics):
            current_topic = session_topics[current_q]
            keywords = TOPIC_KEYWORDS.get(current_topic, [])
            if keywords:
                st.markdown(f"**{current_topic}**")
                st.markdown(", ".join(f"`{kw}`" for kw in keywords))
        elif session_topics:
            # Session complete — show last discussed topic
            last_topic = session_topics[-1]
            keywords = TOPIC_KEYWORDS.get(last_topic, [])
            if keywords:
                st.markdown(f"**{last_topic}**")
                st.markdown(", ".join(f"`{kw}`" for kw in keywords))

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # ── Session complete ──
    if st.session_state.interview_complete:
        st.divider()
        st.success("✅ Great job completing this session! Your responses have been saved. Keep up the great work! 🎉")

        session_topics_res = TOPICS[starting_index:min(starting_index + 5, len(TOPICS))]

        st.divider()
        st.write("📖 **Want to learn more? Check out these resources:**")
        for topic in session_topics_res:
            if topic in TOPIC_RESOURCES:
                url, label = TOPIC_RESOURCES[topic]
                st.markdown(f"- [{label}]({url})")

        st.write("")
        if st.button("Start New Session"):
            for key in ['messages', 'turn_count', 'interview_complete', 'chat',
                        'starting_topic_index', 'current_topic_index']:
                st.session_state.pop(key, None)
            st.rerun()
        return

    # ── Skip & Finish buttons ──
    col1, col2, col3 = st.columns([2, 1.5, 1])
    with col2:
        if st.button("📚 Haven't Learned This Yet", use_container_width=True):
            if st.session_state.turn_count < len(session_topics):
                skipped_topic = session_topics[st.session_state.turn_count]

                st.session_state.messages.append({
                    "role": "user",
                    "content": f"[Student hasn't learned: {skipped_topic} - Not yet covered in class]",
                })

                st.session_state.turn_count += 1
                st.session_state.current_topic_index += 1

                if st.session_state.turn_count >= len(session_topics):
                    complete_interview()
                    return

                next_topic = session_topics[st.session_state.turn_count]
                try:
                    instruction = (
                        f"The student hasn't covered {skipped_topic} yet — no worries. "
                        f"Briefly reassure them and move on to: {next_topic}. "
                        f"Open with a short, relatable real-world scenario about {next_topic}, "
                        f"then ask a clear question about it. Keep it chill. "
                        f"Do NOT mention topic numbers or progress."
                    )
                    response = st.session_state.chat.send_message(instruction)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response.text,
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

    # ── Chat input ──
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
            follow_up = (
                f"Briefly acknowledge the student's answer — keep it genuine, not over-the-top. "
                f"If it feels natural, drop a quick casual 'what if' on what they just said (not every time). "
                f"Then move on to the next topic: {next_topic}. "
                f"Open with a short, relatable real-world scenario about {next_topic} that a 17-19 year old would get — "
                f"music, phones, sports, space, movies, etc. "
                f"Then ask ONE clear question about {next_topic}. "
                f"Keep it conversational and chill. Do NOT mention topic numbers or progress."
            )
            response = st.session_state.chat.send_message(
                f"{prompt}\n\n[INSTRUCTION TO AI: {follow_up}]"
            )
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            with st.chat_message("assistant"):
                st.write(response.text)
            st.rerun()
        except Exception as e:
            st.error("⚠️ API Error: Unable to get next question.")
            if "ResourceExhausted" in str(e) or "429" in str(e):
                st.warning("🕐 Rate limit reached. Please wait 1-2 minutes and click 'Finish Session' to save your progress.")
            else:
                st.info("Please try clicking 'Finish Session' to save your progress so far.")


def complete_interview():
    """Complete the session, grade it, and save to database."""
    st.session_state.interview_complete = True

    transcript = "\n\n".join([
        f"{'AI Learning Companion' if msg['role'] == 'assistant' else 'Student'}: {msg['content']}"
        for msg in st.session_state.messages
    ])

    with st.spinner("Wrapping up... ✨"):
        score, status, feedback, correctness, understanding, explanation = grade_transcript(transcript)

    save_interview(
        st.session_state.student_id,
        score, status, transcript,
        st.session_state.current_topic_index,
        correctness, understanding, explanation,
    )

    st.rerun()


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

def main():
    """Main application logic."""
    st.set_page_config(
        page_title="Reflections on Waves and Modern Physics",
        page_icon="🎓",
        layout="wide",
    )

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
            on_change=on_student_id_submit,
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
