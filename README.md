# AP Physics Interview Bot

A Streamlit-based interview bot that uses Google Gemini AI to conduct physics interviews with students and automatically grade their performance.

## Features

- **Student Interview Mode**: Interactive AI-powered interview about Waves and Modern Physics
- **Automatic Grading**: AI analyzes the complete transcript and provides a score (0-100) and Pass/Fail status
- **Database Storage**: All interviews saved to SQLite database with student ID, date, score, and transcript
- **Admin Panel**: View all results in a table and download as CSV (access with ID: ADMIN123)
- **Turn Limit**: Interviews automatically end after 5 questions or manual finish

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set API Key as environment variable**:
   
   **Linux/Mac**:
   ```bash
   export AIzaSyCxLVxwPeweZee6jhN-K4ZEa8s49Rp7Y20="your-actual-gemini-api-key"
   ```
   
   **Windows (Command Prompt)**:
   ```cmd
   set AIzaSyCxLVxwPeweZee6jhN-K4ZEa8s49Rp7Y20=your-actual-gemini-api-key
   ```
   
   **Windows (PowerShell)**:
   ```powershell
   $env:AIzaSyCxLVxwPeweZee6jhN-K4ZEa8s49Rp7Y20="your-actual-gemini-api-key"
   ```

3. **Run the application**:
   ```bash
   streamlit run main.py
   ```

## Usage

### Student Mode
1. Enter your Student ID when prompted
2. Answer AI questions about Waves and Modern Physics
3. Continue for 5 turns or click "Finish Interview" when ready
4. Receive your score, status, and detailed feedback
5. Results are automatically saved to the database

### Admin Mode
1. Enter `ADMIN123` as the Student ID
2. View all interview results in a table
3. Download results as CSV file

## Database

The application creates `interview_results.db` with the following structure:
- `id`: Auto-incrementing primary key
- `student_id`: Student identifier
- `date`: Interview timestamp
- `score`: Grade (0-100)
- `status`: Pass/Fail
- `transcript`: Complete conversation history

## Grading Criteria

The AI grades based on:
- Correctness of answers (50%)
- Understanding of concepts (30%)
- Depth of explanations (20%)

**Pass threshold**: Score ≥ 60

## Technologies

- **Streamlit**: Web interface
- **Google Gemini AI**: Conversational AI and grading
- **SQLite**: Local database storage
- **Pandas**: Data manipulation and CSV export
