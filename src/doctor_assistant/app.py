"""
Gradio Chat Interface for Doctor Assistant Multi-Agent System.

Provides a web-based chat UI for interacting with the medical assistant.
Users can describe symptoms, request diagnoses, and find nearby pharmacies.

Features:
- Conversational chat interface with message history
- Example prompts for common use cases
- Automatic graph visualization export
- LangSmith tracing integration

URL: http://localhost:7860
"""

import sys
import os

import gradio as gr

from .graph import run_doctor_assistant, graph
from .config import setup_langsmith


# =============================================================================
# INITIALIZATION
# =============================================================================

# Enable LangSmith tracing if configured
LANGSMITH_ENABLED = setup_langsmith()

# Add source directory to Python path for imports
SRC_DIR = os.path.abspath(os.path.dirname(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Add parent directory for package imports
PARENT_DIR = os.path.abspath(os.path.join(SRC_DIR, ".."))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

# Chat history limit (prevents context from growing too large)
MAX_HISTORY_INTERACTIONS = 3


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def save_graph():
    """
    Export the LangGraph agent workflow as a PNG image.
    
    Generates a Mermaid diagram showing:
    Planner → Supervisor → Specialist Agents → Synthesis
    
    Returns:
        Path to saved PNG, or None if export fails.
    """
    try:
        png_bytes = graph.get_graph().draw_mermaid_png()
        graph_path = os.path.join(SRC_DIR, "doctor_assistant_graph.png")
        with open(graph_path, "wb") as f:
            f.write(png_bytes)
        return graph_path
    except Exception as e:
        print(f"⚠️ Could not save graph: {e}")
        return None


def format_response(result: dict) -> str:
    """
    Format the agent's response as Markdown for display.
    
    Extracts the final message from the graph result and
    adds a medical disclaimer.
    
    Args:
        result: Raw output from run_doctor_assistant().
    
    Returns:
        Formatted Markdown string.
    """
    if isinstance(result, str):
        return result
    
    if not isinstance(result, dict):
        return str(result)
    
    parts = []
    
    # Extract final message from conversation history
    if result.get('messages'):
        final_message = result['messages'][-1].content if hasattr(result['messages'][-1], 'content') else str(result['messages'][-1])
        parts.append("### 📋 Medical Assessment\n")
        parts.append(final_message)
    
    # Always append medical disclaimer
    parts.append("""
---
⚠️ *This is an AI assistant for informational purposes only. Always consult a qualified healthcare professional.*
""")
    
    return '\n'.join(parts)


def ensure_string(value) -> str:
    """
    Convert any value to a display-friendly string.
    
    Handles dicts, lists, and other types gracefully.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return format_response(value)
    if isinstance(value, list):
        return "\n".join([f"- {item}" for item in value])
    return str(value)


# =============================================================================
# CHAT HANDLERS
# =============================================================================

def respond(message: str, chat_history: list) -> tuple:
    """
    Process user message and generate assistant response.
    
    Flow:
    1. Validate input
    2. Add user message to history
    3. Run multi-agent graph
    4. Format and append response
    
    Args:
        message: User's input text.
        chat_history: List of previous messages.
    
    Returns:
        Tuple of (cleared input, updated history).
    """
    if not message.strip():
        return "", chat_history
    
    # Add user message to chat history
    chat_history.append({"role": "user", "content": message})
    
    try:
        # Run the multi-agent system
        result = run_doctor_assistant(message)
        
        # Format response for display
        if isinstance(result, dict) and result.get('messages'):
            formatted_response = format_response(result)
        else:
            formatted_response = str(result)
        
    except Exception as e:
        # Display error message on failure
        formatted_response = f"❌ **Error:** {str(e)}\n\nPlease try again or rephrase your query."
    
    # Add assistant response to history
    chat_history.append({"role": "assistant", "content": formatted_response})
    
    return "", chat_history


def clear_chat():
    """Reset chat history and input field."""
    return [], ""


# =============================================================================
# GRADIO INTERFACE
# =============================================================================

with gr.Blocks(title="🏥 Doctor Assistant") as demo:
    
    # -------------------------------------------------------------------------
    # HEADER
    # -------------------------------------------------------------------------
    gr.Markdown("""
    # 🏥 Doctor Assistant
    Your AI assistant for **medical symptom analysis**, **preliminary diagnosis** and **finding nearby pharmacies.**
    
    **How to use:** Enter the patient's name when entering your query.
    """)
    
    # -------------------------------------------------------------------------
    # CHAT DISPLAY
    # -------------------------------------------------------------------------
    chatbot = gr.Chatbot(
        height=500,
        placeholder="Describe the patient and their symptoms...",
        layout="bubble",
    )
    
    # -------------------------------------------------------------------------
    # INPUT CONTROLS
    # -------------------------------------------------------------------------
    with gr.Row():
        msg = gr.Textbox(
            placeholder="Example: John Doe has chest pain and shortness of breath for 2 days",
            label="Your Query",
            scale=9,
        )
        submit_btn = gr.Button("Send 📤", scale=1, variant="primary")
    
    with gr.Row():
        clear_btn = gr.Button("🗑️ Clear Chat")
    
    # -------------------------------------------------------------------------
    # EXAMPLE PROMPTS
    # -------------------------------------------------------------------------
    gr.Markdown("### 💡 Try these examples:")
    gr.Examples(
        examples=[
            "Youssef Kabbaj has been experiencing chest pain and shortness of breath for 2 days",
            "Fatima Zahra Lahlou complains of severe headaches with visual disturbances and numbness in her left hand",
            "Salma Rami needs to find nearby pharmacies within 5000 meters to buy his medications. She is walking.",
            "Youssef Kabbaj is looking for nearby pharmacies within 10000 meters to buy his medications. He is driving.",
        ],
        inputs=msg,
    )
    
    # -------------------------------------------------------------------------
    # EVENT HANDLERS
    # -------------------------------------------------------------------------
    msg.submit(respond, [msg, chatbot], [msg, chatbot])       # Enter key
    submit_btn.click(respond, [msg, chatbot], [msg, chatbot])  # Button click
    clear_btn.click(clear_chat, outputs=[chatbot, msg])        # Clear button
    
    # -------------------------------------------------------------------------
    # FOOTER
    # -------------------------------------------------------------------------
    gr.Markdown("""
    ---
    ⚠️ **Disclaimer:** This is an AI assistant for informational purposes only. 
    Always consult a qualified healthcare professional for medical advice.
    
    *Built with ❤️ using LangGraph & Gradio*
    """)


# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

def main():
    """
    Main entry point for the Doctor Assistant application.

    Called when running:
    - python -m doctor_assistant.app
    - doctor-assistant (CLI command after pip install)
    """
    # Export graph visualization on startup
    graph_path = save_graph()
    if graph_path:
        print(f"✅ Graph saved to: {graph_path}")

    # Launch Gradio server
    print("\n🚀 Starting Doctor Assistant at http://localhost:7860")
    demo.launch(
        server_name="0.0.0.0",  # Accept connections from any IP
        server_port=7860,
        share=False,            # Set True to create public URL
    )


if __name__ == "__main__":
    main()