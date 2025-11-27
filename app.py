import streamlit as st
import subprocess
import requests
import sys
import os
import re
import difflib

MODEL_NAME = "qwen2.5-coder:1.5b"
OLLAMA_URL = "http://localhost:11434/api/generate"


# --- BACKEND LOGIC (Reused) ---
def run_code(file_path):
    try:
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "CRITICAL ERROR: Code Execution Timed Out (Possible Infinite Loop)"
    except Exception as e:
        return 1, "", str(e)


def get_ai_fix(code_content, error_log, stdout_log, user_request):
    prompt = f"""
    You are an expert Python debugging agent.

    ### USER REQUEST:
    "{user_request}"

    ### BROKEN CODE:
    ```python
    {code_content}
    ```

    ### EXECUTION RESULT:
    - STDERR (Errors): {error_log if error_log else "None"}
    - STDOUT (Output): {stdout_log if stdout_log else "None"}

    ### INSTRUCTION:
    1. Analyze the User Request and the Execution Result.
    2. Fix the code.
    3. Return ONLY the fully fixed Python code inside markdown blocks.
    4. NO explanations.
    """

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2}
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        result_text = response.json().get('response', '')
        code_match = re.search(r"```python(.*?)```", result_text, re.DOTALL)
        return code_match.group(1).strip() if code_match else result_text.strip()
    except Exception as e:
        return None


# --- STREAMLIT UI ---
st.set_page_config(page_title="AutoDebug AI", page_icon="🤖", layout="wide")

# Sidebar: File Selection
st.sidebar.title("📂 Workspace")
files = [f for f in os.listdir('.') if f.endswith('.py') and f != 'app.py']
selected_file = st.sidebar.selectbox("Select a file to debug:", files)

# Main Chat Interface
st.title("🤖 Local AI Debugger")
st.caption(f"Connected to **{MODEL_NAME}** | Editing: `{selected_file}`")

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! Select a file and tell me what's wrong."}]

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle User Input
if user_input := st.chat_input("Describe the bug (e.g., 'Fix the recursion error')..."):
    # 1. Show User Message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. AI Processing
    with st.chat_message("assistant"):
        message_placeholder = st.empty()

        if not selected_file:
            message_placeholder.error("Please select a file from the sidebar first!")
        else:
            # --- FEATURE 2: AUTONOMOUS REPAIR LOOP ---
            MAX_RETRIES = 5

            # 1. Read Original Content (for diff & backup)
            with open(selected_file, 'r') as f:
                original_code = f.read()

            current_code = original_code  # This variable tracks the code as it evolves
            success = False

            with st.status("🔄 Autonomous Debugging Loop...", expanded=True) as status:

                for iteration in range(1, MAX_RETRIES + 1):
                    status.write(f"**Attempt {iteration}/{MAX_RETRIES}:** Running Sandbox...")

                    # Write the current version to file to test it
                    with open(selected_file, 'w') as f:
                        f.write(current_code)

                    # Run the code
                    return_code, stdout, stderr = run_code(selected_file)

                    # Logic Check: Did it run without crashing?
                    if return_code == 0:
                        status.success(f"Code ran successfully on Attempt {iteration}!")
                        success = True
                        break

                    # If failed, show error and continue
                    error_msg = stderr.strip().splitlines()[-1] if stderr else "Unknown Error"
                    status.write(f"Attempt {iteration} Failed. Error: `{error_msg}`")

                    # Consult AI for next fix (unless it's the last try)
                    if iteration < MAX_RETRIES:
                        status.write(f"Consulting AI for fix #{iteration}...")
                        # We pass the CURRENT code and the NEW error to the AI
                        fixed_code_candidate = get_ai_fix(current_code, stderr, stdout, user_input)

                        if fixed_code_candidate:
                            current_code = fixed_code_candidate
                        else:
                            status.error("AI failed to generate a fix.")
                            break

            # --- FINAL RESULTS ---
            if success:
                # Create Backup of the ORIGINAL code
                backup_path = f"{selected_file}.bak"
                if not os.path.exists(backup_path):
                    with open(backup_path, 'w') as f:
                        f.write(original_code)

                # Visual Diff (Original vs Final)
                st.write("### ⚖️ Code Comparison")
                col1, col2 = st.columns(2)

                with col1:
                    st.caption("❌ Original")
                    st.code(original_code, language="python")

                with col2:
                    st.caption(f"✅ Fixed (Iter {iteration})")
                    st.code(current_code, language="python")

                # Persistence
                response_msg = f"✅ I have fixed `{selected_file}` after **{iteration} iterations**. A backup was saved to `{selected_file}.bak`."
                st.session_state.messages.append({"role": "assistant", "content": response_msg})

            else:
                message_placeholder.error(f"❌ Auto-repair failed after {MAX_RETRIES} attempts.")
                with st.expander("View Final Error Log"):
                    st.code(stderr, language="bash")