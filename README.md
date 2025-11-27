# 🤖 AutoDebug AI: Local Autonomous Repair Engine

AutoDebug AI is a fully autonomous, local debugging environment that executes broken code, analyzes runtime signals, and iteratively repairs logic errors without sending a single byte of data to the cloud.


## 🏆 Problem Statement Solution

Track: DevForge Problem Statement 4 (Local AI-Supervised Autonomous Debugging Sandbox)

Debugging manually is slow and frustrating. Beginners struggle to interpret stack traces, and fixing one bug often reveals another. AutoDebug AI solves this by implementing a loop that runs entirely on your machine.

## Key Features

🔄 Autonomous Repair Loop: Unlike standard chatbots, this system runs your code in a sandbox. If the fix fails, it captures the new error and retries up to 3 times automatically.

⚖️ Visual Side-by-Side Diffs: Instantly see exactly what changed between your broken code and the fixed version.

🔒 100% Local & Private: Powered by qwen2.5-coder:1.5b via Ollama. No API keys, no cloud latency, full data privacy.

🛡️ Safety First: Automatically creates .bak backups before applying any patches.

🧠 Context-Aware: Understands both runtime errors (stderr) and logic errors (wrong stdout) based on user prompts.

## 🛠️ Tech Stack

Frontend: Streamlit (Python-based Reactive UI)

AI Engine: Ollama (running qwen2.5-coder:1.5b)

Sandbox: Python subprocess with timeout constraints (preventing infinite loops).

Diffing Engine: Python difflib for generating structured patch instructions.

## 🚀 Installation & Setup

Prerequisites

Python 3.8+

Ollama (installed and running)

Step 1: Install Dependencies

```pip install streamlit requests```


Step 2: Setup Local AI

Make sure Ollama is installed, then pull the lightweight coding model:

```ollama pull qwen2.5-coder:1.5b```


Step 3: Run the Engine

Start the Ollama server (if not running):

```ollama serve```


Launch the AutoDebug UI:

```streamlit run app.py```


## 📖 How to Use

Select a File: Use the sidebar to choose a Python script from your directory.

Describe the Issue: In the chat box, type the problem (e.g., "This binary search hangs forever" or "Fix the recursion depth error").

Watch the Loop:

The system puts the code in a sandbox.

It detects the error (Crash or Timeout).

It consults the Local AI.

It applies the patch and re-runs the code to verify.

Review: If successful, you see a green "Fix Applied" message and a visual comparison of the changes.

## 🧪 Validated Test Cases

We stress-tested the system against the following common bugs:


🔮 Future Roadmap

Security Static Analysis: Pre-scan code for dangerous imports (os.system, shutil) before execution.

Multi-File Support: Allow debugging across multiple imported modules.

IDE Extension: Porting the core logic to a VS Code Extension (Prototype CLI available).

Made with ❤️ for the DevForge Hackathon.
