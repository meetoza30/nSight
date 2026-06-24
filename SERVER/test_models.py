import os
import sys
import json

# Add the SERVER directory to sys.path so we can import services
SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SERVER_DIR)

from services.resume_extraction import extract_text_preserving_layout, extract_resume_json

def run_tests():
    resume_path = os.path.join(SERVER_DIR, "my resume.pdf")
    output_path = os.path.join(SERVER_DIR, "model_comparison_output.txt")
    
    if not os.path.exists(resume_path):
        print(f"Resume not found at {resume_path}")
        return
        
    print(f"Extracting text from: {resume_path}")
    resume_text = extract_text_preserving_layout(resume_path)
    if not resume_text:
        print("Failed to extract text from PDF.")
        return
        
    models_to_test = [
        "mistralai/mistral-nemo",
        "qwen/qwen3-14b"
    ]
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"Model Comparison for: {resume_path}\n")
        f.write("="*60 + "\n\n")
        
    for model in models_to_test:
        print(f"\n--- Testing model: {model} ---")
        extracted_data = extract_resume_json(resume_text, model=model)
        
        with open(output_path, "a", encoding="utf-8") as f:
            f.write(f"MODEL: {model}\n")
            f.write("-" * 60 + "\n")
            if extracted_data:
                f.write(json.dumps(extracted_data, indent=4, ensure_ascii=False))
            else:
                f.write("Extraction failed or returned None.\n")
            f.write("\n" + "="*60 + "\n\n")
            
    print(f"\nTesting complete! Results saved to: {output_path}")

if __name__ == "__main__":
    run_tests()
