import streamlit as st
import subprocess
import requests
import sys
import os
import re
import difflib

# --- CONFIGURATION ---
MODEL_NAME = "qwen2.5-coder:1.5b"
OLLAMA_URL = "http://localhost:11434/api/generate"

LANGUAGE_CONFIG = {
    ".py": {
        "name": "Python",
        "command": [sys.executable],
        "markdown_tag": "python"
    },
    ".js": {
        "name": "JavaScript",
        "command": ["node"],
        "markdown_tag": "javascript"
    },
    ".java": {
        "name": "Java",
        "command": ["java"],
        "markdown_tag": "java"
    },
    ".cpp": {
        "name": "C++",
        "command": ["g++"],
        "markdown_tag": "cpp"
    },
    ".go": {
        "name": "Go",
        "command": ["go", "run"],
        "markdown_tag": "go"
    }
}


def get_language_config(file_path):
    _, ext = os.path.splitext(file_path)
    return LANGUAGE_CONFIG.get(ext)


# --- BACKEND LOGIC (Reused) ---
def run_code(file_path):
    config = get_language_config(file_path)
    if not config:
        return 1, "", f"Unsupported file extension: {os.path.splitext(file_path)[1]}"

    command = config["command"] + [file_path]

    try:
        # Note: Added shell=True for some environments where commands like 'node' or 'go'
        # might not be found directly, though typically not needed for standard runtimes.
        # Keeping timeout.
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "CRITICAL ERROR: Code Execution Timed Out (Possible Infinite Loop)"
    except FileNotFoundError:
        return 1, "", f"CRITICAL ERROR: Runtime not found for command: {command[0]}"
    except Exception as e:
        return 1, "", str(e)


# --- BACKEND LOGIC (MODIFIED: Refined prompt for logical reasoning) ---
def get_ai_fix(code_content, error_log, stdout_log, user_request, file_path):
    config = get_language_config(file_path)
    lang_name = config["name"] if config else "Unknown"
    markdown_tag = config["markdown_tag"] if config else ""

    # The prompt is simplified and places maximum emphasis on the User Request,
    # treating STDOUT/STDERR as diagnostic feedback for the LLM.
    prompt = f"""
    You are an expert {lang_name} debugging agent specialized in **Code Reasoning**.
    Your task is to fix both runtime errors and logical flaws based on the user's description.

    ### ULTIMATE GOAL (USER REQUEST):
    "{user_request}"

    ### BROKEN CODE (Current Version):
    ```{markdown_tag}
    {code_content}
    ```

    ### EXECUTION RESULT (Diagnostics):
    - STDERR (Errors): {error_log if error_log else "None. The code ran without crashing."}
    - STDOUT (Output): {stdout_log if stdout_log else "None"}

    ### INSTRUCTION:
    1. Analyze the **ULTIMATE GOAL** and the **EXECUTION RESULT**.
    2. Fix the code to address the issue described by the user, prioritizing functional correctness.
    3. Return **ONLY** the fully fixed {lang_name} code inside a markdown block.
    4. NO explanations, no added text outside the code block.
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

        # Try to find code block with specific tag, fallback to generic or just text
        pattern = r"```" + re.escape(markdown_tag) + r"(.*?)```"
        code_match = re.search(pattern, result_text, re.DOTALL)

        if not code_match:
            code_match = re.search(r"```(.*?)```", result_text, re.DOTALL)

        return code_match.group(1).strip() if code_match else result_text.strip()
    except Exception as e:
        return None


# --- STREAMLIT UI (MODIFIED: Removed Expected Output) ---
st.set_page_config(page_title="AutoDebug AI", page_icon="🤖", layout="wide")

# Sidebar: File Selection
st.sidebar.title("📂 Workspace")
supported_extensions = tuple(LANGUAGE_CONFIG.keys())
files = [f for f in os.listdir('.') if f.endswith(supported_extensions) and f != 'app.py']
selected_file = st.sidebar.selectbox("Select a file to debug:", files)

# Main Chat Interface
st.title("🤖 Local AI Debugger (Logic Mode)")
st.caption(f"Connected to **{MODEL_NAME}** | Editing: `{selected_file}`")
st.warning("⚠️ **Logical error fixing relies entirely on the quality of your description.**")

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant",
                                  "content": "Hello! Select a file and clearly describe the bug (e.g., 'The loop runs infinitely' or 'The calculation is off by one')."}]

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle User Input
if user_input := st.chat_input("Describe the bug..."):
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
            # --- FEATURE 2: AUTONOMOUS REPAIR LOOP (SIMPLIFIED LOGIC CHECK) ---
            MAX_RETRIES = 5

            # 1. Read Original Content (for diff & backup)
            with open(selected_file, 'r') as f:
                original_code = f.read()

            current_code = original_code

            # The success flag now only tracks if a non-crash state was reached AND
            # if the model successfully provided a fix candidate. True success is assumed
            # by the model having more context in the final step.
            success = False

            config = get_language_config(selected_file)
            markdown_tag = config["markdown_tag"] if config else ""

            with st.status("🔄 Autonomous Debugging Loop (Logic/Runtime Fix)...", expanded=True) as status:

                for iteration in range(1, MAX_RETRIES + 1):
                    status.write(f"**Attempt {iteration}/{MAX_RETRIES}:** Running Sandbox...")

                    # Write the current version to file to test it
                    with open(selected_file, 'w') as f:
                        f.write(current_code)

                    # Run the code
                    return_code, stdout, stderr = run_code(selected_file)

                    is_crash_error = (return_code != 0)

                    # Log the result for the user
                    if is_crash_error:
                        error_msg = stderr.strip().splitlines()[-1] if stderr else "Unknown Error"
                        status.write(f"Attempt {iteration} Result: ❌ Runtime Error. Error: `{error_msg}`")
                    else:
                        status.write(
                            f"Attempt {iteration} Result: ✅ Code ran successfully. Now checking for logical fix...")

                    # Always consult the AI (unless it's the last try)
                    if iteration < MAX_RETRIES:
                        status.write(f"Consulting AI for fix #{iteration} based on user goal...")
                        # We pass the CURRENT code and the NEW execution results to the AI
                        fixed_code_candidate = get_ai_fix(current_code, stderr, stdout, user_input, selected_file)

                        if fixed_code_candidate:
                            # If the new code is identical to the old code, stop the loop early
                            if fixed_code_candidate.strip() == current_code.strip():
                                status.write(
                                    f"Attempt {iteration}: AI returned identical code. Assuming no further fix can be determined.")
                                success = True
                                break

                            current_code = fixed_code_candidate
                        else:
                            status.error("AI failed to generate a fix.")
                            break
                    else:
                        # On the last iteration, we check the final state
                        if not is_crash_error:
                            success = True  # Assume success if no crash on last attempt
                        break  # Exit loop after last attempt

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
                    st.code(original_code, language=markdown_tag)

                with col2:
                    st.caption(f"✅ Fixed (Iter {iteration})")
                    st.code(current_code, language=markdown_tag)

                # Persistence
                response_msg = f"✅ I have completed the repair process for `{selected_file}` after **{iteration} iterations**. The model attempted to fix the logical issue based on your request. A backup was saved to `{selected_file}.bak`."
                st.session_state.messages.append({"role": "assistant", "content": response_msg})

            else:
                message_placeholder.error(
                    f"❌ Auto-repair failed after {MAX_RETRIES} attempts, or the code still has a critical error.")
                with st.expander("View Final Error Log"):
                    st.code(stderr, language="bash")

