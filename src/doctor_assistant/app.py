"""Gradio Chat Interface for Doctor Assistant."""

import sys
import os


SRC_DIR = os.path.abspath(os.path.dirname(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Add parent directory for imports
PARENT_DIR = os.path.abspath(os.path.join(SRC_DIR, ".."))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

import gradio as gr
from doctor_assistant.graph import run_doctor_assistant, create_main_graph
from doctor_assistant.config import setup_langsmith
LANGSMITH_ENABLED = setup_langsmith()

# Number of past interactions to include in context
MAX_HISTORY_INTERACTIONS = 3


def save_graph():
    """Save the agent graph and return the path."""
    try:
        graph = create_main_graph()
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
    Format the doctor assistant response as Markdown.
    """
    if isinstance(result, str):
        return result
    
    if not isinstance(result, dict):
        return str(result)
    
    parts = []
    
    # Urgency Banner
    urgency = result.get('urgency', 'medium').upper()
    if urgency == "HIGH":
        parts.append("🚨 **HIGH URGENCY** - Immediate medical attention recommended!\n")
    elif urgency == "MEDIUM":
        parts.append("⚠️ **MEDIUM URGENCY** - Medical consultation recommended soon.\n")
    else:
        parts.append("✅ **LOW URGENCY** - Monitor symptoms and consult if they persist.\n")
    
    # Patient Info
    patient = result.get('patient_info')
    if patient:
        parts.append(f"""
---
### 👤 Patient Information
- **Name:** {patient.get('name', 'N/A')}
- **Age:** {patient.get('age', 'N/A')}
- **Gender:** {patient.get('gender', 'N/A')}
- **Location:** {patient.get('location', 'N/A')}
- **Medical History:** {', '.join(patient.get('medical_history', [])) or 'None'}
- **Medications:** {', '.join(patient.get('current_medications', [])) or 'None'}
- **Allergies:** {', '.join(patient.get('allergies', [])) or 'None'}
""")
    elif result.get('patient_name'):
        parts.append(f"\n---\n### 👤 Patient: {result.get('patient_name')} (Not found in database)\n")
    
    # Agents Consulted
    plan = result.get('plan_executed', [])
    if plan:
        agent_icons = {
            'patient_data': '👤 Patient Data',
            'cardiovascular': '🫀 Cardiovascular',
            'neurological': '🧠 Neurological'
        }
        agents_str = ' → '.join([agent_icons.get(a, a) for a in plan])
        parts.append(f"\n**🔬 Agents Consulted:** {agents_str}\n")
    
    # Final Response
    final_response = result.get('final_response', '')
    if final_response:
        parts.append(f"""
---
### 📋 Assessment

{final_response}
""")
    
    # Disclaimer
    parts.append("""
---
⚠️ *This is an AI assistant for informational purposes only. Always consult a qualified healthcare professional.*
""")
    
    return '\n'.join(parts)


def ensure_string(value) -> str:
    """Ensure a value is a string."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return format_response(value)
    if isinstance(value, list):
        return "\n".join([f"- {item}" for item in value])
    return str(value)


def respond(message: str, chat_history: list) -> tuple:
    """Generate response and update chat history."""
    
    if not message.strip():
        return "", chat_history
    
    # Add user message to history
    chat_history.append({"role": "user", "content": message})
    
    try:
        # Run the doctor assistant
        result = run_doctor_assistant(message)
        
        # Format the response
        formatted_response = format_response(result)
        
    except Exception as e:
        formatted_response = f"❌ **Error:** {str(e)}\n\nPlease try again or rephrase your query."
    
    # Add assistant response to history
    chat_history.append({"role": "assistant", "content": formatted_response})
    
    return "", chat_history


def clear_chat():
    """Clear the chat history."""
    return [], ""


# ============================================================
# BUILD THE INTERFACE
# ============================================================

with gr.Blocks(title="🏥 Doctor Assistant") as demo:
    
    # Header
    gr.Markdown("""
    # 🏥 Doctor Assistant
    Your AI assistant for **medical symptom analysis** and **preliminary diagnosis**.
    
    **How to use:** Enter the patient's name and describe their symptoms.
    """)
    
    # Chatbot
    chatbot = gr.Chatbot(
        height=500,
        placeholder="Describe the patient and their symptoms...",
        layout="bubble",
    )
    
    # Input Row
    with gr.Row():
        msg = gr.Textbox(
            placeholder="Example: John Doe has chest pain and shortness of breath for 2 days",
            label="Your Query",
            scale=9,
        )
        submit_btn = gr.Button("Send 📤", scale=1, variant="primary")
    
    # Clear Button
    with gr.Row():
        clear_btn = gr.Button("🗑️ Clear Chat")
    
    # Example Prompts
    gr.Markdown("### 💡 Try these examples:")
    gr.Examples(
        examples=[
            "Youssef Kabbaj has been experiencing chest pain and shortness of breath for 2 days",
            "Fatima Zahra Lahlou complains of severe headaches with visual disturbances and numbness in her left hand",
            "Patient Robert Johnson reports chest pain, dizziness, and confusion",
            "John Doe has high blood pressure and feels dizzy with occasional palpitations",
        ],
        inputs=msg,
    )
    
    # Event Handlers
    msg.submit(respond, [msg, chatbot], [msg, chatbot])
    submit_btn.click(respond, [msg, chatbot], [msg, chatbot])
    clear_btn.click(clear_chat, outputs=[chatbot, msg])
    
    # Footer
    gr.Markdown("""
    ---
    ⚠️ **Disclaimer:** This is an AI assistant for informational purposes only. 
    Always consult a qualified healthcare professional for medical advice.
    
    *Built with ❤️ using LangGraph & Gradio*
    """)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    # Save the graph on startup
    graph_path = save_graph()
    if graph_path:
        print(f"✅ Graph saved to: {graph_path}")
    
    print("\n🚀 Starting Doctor Assistant at http://localhost:7860")
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
    )