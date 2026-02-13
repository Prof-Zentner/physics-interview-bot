# AP Physics Reflection Chat

A Streamlit-based friendly learning companion that uses Google Gemini AI to conduct reflective physics conversations with students and automatically grade their understanding.

## Features

- **Friendly Socratic Reflection Chat**: Warm, encouraging AI-powered conversations about Waves and Modern Physics (powered by Gemini)
- **Automatic Grading**: AI analyzes the complete transcript and provides a score (0-100) and Pass/Fail status
- **Database Storage**: All sessions saved to SQLite database with student ID, date, score, and transcript
- **Admin Panel**: View all results in a table and download as CSV (access with ID: ADMIN123)
- **Topic Progression**: 17 topics covered across multiple sessions (5 topics per session)
- **Skip Topics**: Students can skip topics they haven't learned yet without penalty

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set API Keys as environment variables**:
   
   **Linux/Mac**:
   ```bash
   export GEMINI_API_KEY="your-gemini-api-key"
   export ANTHROPIC_API_KEY="your-anthropic-api-key"
   ```
   
   **Windows (Command Prompt)**:
   ```cmd
   set GEMINI_API_KEY=your-gemini-api-key
   set ANTHROPIC_API_KEY=your-anthropic-api-key
   ```
   
   **Windows (PowerShell)**:
   ```powershell
   $env:GEMINI_API_KEY="your-gemini-api-key"
   $env:ANTHROPIC_API_KEY="your-anthropic-api-key"
   ```

3. **Run the application**:
   ```bash
   streamlit run main.py
   ```

## API Key Usage

| Key | Service | Used For |
|-----|---------|----------|
| `GEMINI_API_KEY` | Google Gemini | Live chat conversation & grading |
| `ANTHROPIC_API_KEY` | Anthropic (Claude) | Reserved for future features |

## Usage

### Student Mode
1. Enter your Student ID when prompted
2. Chat with the friendly AI companion about physics topics
3. Share your thoughts across 5 topics per session
4. Receive your score, status, and detailed feedback
5. Come back to continue with the next set of topics

### Admin Mode
1. Enter `ADMIN123` as the Student ID
2. View all session results in a table
3. Download results as CSV file

## Grading Criteria

The AI grades based on:
- Correctness of answers (50%)
- Understanding of concepts (30%)
- Depth of explanations (20%)

**Pass threshold**: Score >= 60

## Technologies

- **Streamlit**: Web interface
- **Google Gemini AI**: Conversational AI (friendly Socratic chat) and grading
- **Anthropic Claude**: API key supported (reserved for future use)
- **SQLite**: Local database storage
- **Pandas**: Data manipulation and CSV export
