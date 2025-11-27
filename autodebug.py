import subprocess
import requests
import json
import difflib
import sys
import os
import re
import time

# --- CONFIGURATION ---
MODEL_NAME = "qwen2.5-coder:1.5b"  # Ensure this matches your pulled model
OLLAMA_URL = "http://localhost:11434/api/generate"
MAX_RETRIES = 3


# --- MODULE 1: THE SANDBOX ---
def run_code(file_path):
    """
    Runs the python script locally.
    Captures stdout (logic checks) and stderr (crashes).
    """
    print(f"    > Executing {file_path}...")
    try:
        # Timeout set to 5s to catch infinite loops
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


# --- MODULE 2: THE BRAIN (Now Context-Aware) ---
def get_ai_fix(code_content, error_log, stdout_log, user_request):
    """
    Sends Code + Errors + User Context to Ollama.
    """
    print("    > Consulting Local AI...")

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

        # Extract code from markdown
        code_match = re.search(r"```python(.*?)```", result_text, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        else:
            # Fallback for models that forget markdown
            return result_text.strip()
    except Exception as e:
        print(f"    [!] AI Connection Error: {e}")
        return None


# --- MODULE 3: THE PATCHER ---
def generate_patch(original_code, fixed_code, filename):
    original_lines = original_code.splitlines(keepends=True)
    fixed_lines = fixed_code.splitlines(keepends=True)

    diff = difflib.unified_diff(
        original_lines,
        fixed_lines,
        fromfile=f'original_{filename}',
        tofile=f'fixed_{filename}',
        lineterm=''
    )
    return ''.join(diff)


# --- CORE LOGIC: THE REPAIR LOOP ---
def process_debugging_task(filename, user_query):
    print(f"\n[+] Starting Debugging Session for: {filename}")

    for iteration in range(1, MAX_RETRIES + 1):
        print(f"\n--- Iteration {iteration} ---")

        # 1. Read Code
        try:
            with open(filename, 'r') as f:
                current_code = f.read()
        except FileNotFoundError:
            print(f"    [!] Error: File {filename} not found.")
            return

        # 2. Run Code
        return_code, stdout, stderr = run_code(filename)

        # 3. Validation Logic
        # If code crashed (return_code != 0), we MUST fix it.
        # If code ran (return_code == 0), we fix it ONLY if it's the first run (user complaint)
        # or if the user explicitly mentioned logic errors.
        if return_code == 0 and iteration > 1:
            print(f"    [SUCCESS] Code ran successfully with exit code 0.")
            print(f"    > Output: {stdout.strip()}")
            return

        # If it's the first run, even if exit code is 0, we trust the user that something is wrong.
        if return_code == 0:
            print(f"    [!] Code ran without crash, but investigating user complaint: '{user_query}'")
        else:
            print(f"    [!] Runtime Error Detected: {stderr.strip().splitlines()[-1] if stderr else 'Unknown Error'}")

        # 4. Get Fix from AI
        fixed_code = get_ai_fix(current_code, stderr, stdout, user_query)

        if not fixed_code:
            print("    [!] AI failed to generate a fix.")
            return

        # 5. Generate Patch
        patch = generate_patch(current_code, fixed_code, filename)
        if not patch:
            print("    [?] AI generated identical code. No changes needed?")
            return

        print("    > Generated Patch Instructions (Unified Diff)")

        # 6. Apply Fix
        backup_name = f"{filename}.bak"
        if not os.path.exists(backup_name):
            os.rename(filename, backup_name)  # Save backup of original only
            with open(filename, 'w') as f:
                f.write(current_code)  # Restore original to file so we can overwrite it below (trick for simple logic)

        with open(filename, 'w') as f:
            f.write(fixed_code)

        print(f"    [*] Patch applied.")


# --- INTERACTIVE CHATBOT ---
def start_chat():
    print("=====================================================")
    print("   AI AUTONOMOUS DEBUGGER (LOCAL OLLAMA ENGINE)      ")
    print("=====================================================")
    print("usage: Describe the bug and mention the file with @")
    print("example: 'Fix the recursion error in @script.py'")
    print("type 'exit' to quit.\n")

    while True:
        try:
            user_input = input(">> ").strip()

            if user_input.lower() in ['exit', 'quit']:
                print("Exiting...")
                break

            if not user_input:
                continue

            # Parse @filename using Regex
            # Matches @filename.py or @path/to/filename.py
            match = re.search(r"@([\w./\-\\]+\.py)", user_input)

            if match:
                target_file = match.group(1)
                process_debugging_task(target_file, user_input)
            else:
                print("[!] Please specify a file using '@filename.py'")

        except KeyboardInterrupt:
            print("\nExiting...")
            break


if __name__ == "__main__":
    start_chat()