# src/main.py
from src.llm_handler import get_llm_response

def main():
    print("Intelligent Multimodal Avatar Prototype (Text-based)")
    print("Type 'exit' to quit.")

    while True:
        user_input = input("\nUser: ")
        if user_input.lower() == 'exit':
            break
        
        response = get_llm_response(user_input)
        print(f"Avatar: {response}")

if __name__ == "__main__":
    main()