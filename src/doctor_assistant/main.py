"""Main entry point for Doctor Assistant."""

from .graph import run_doctor_assistant, print_response


def main():
    """Interactive Doctor Assistant."""
    
    print("\n" + "=" * 70)
    print("🏥 DOCTOR ASSISTANT")
    print("=" * 70)
    print("Enter your medical query including the patient's name.")
    print("Example: 'John Doe has chest pain and shortness of breath'")
    print("Type 'quit' to exit.")
    print("=" * 70)
    
    while True:
        print("\n")
        query = input("📝 Enter query: ").strip()
        
        if query.lower() in ["quit", "exit", "q"]:
            print("\n👋 Goodbye!")
            break
        
        if not query:
            print("⚠️ Please enter a query.")
            continue
        
        try:
            result = run_doctor_assistant(query)
            print_response(result)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again.")


if __name__ == "__main__":
    main()