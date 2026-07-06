import os
import sys
import glob
from resume_extraction import process_resume

def main():
    # Directory paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    resumes_dir = os.path.join(base_dir, "Resumes")
    logs_dir = os.path.join(base_dir, "Logs")
    
    # Create logs directory if it doesn't exist
    os.makedirs(logs_dir, exist_ok=True)
    
    # Find all pdf files in the Resumes folder
    pdf_files = glob.glob(os.path.join(resumes_dir, "*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {resumes_dir}")
        return
        
    print(f"Found {len(pdf_files)} PDF files to process.")
    
    # Save the original stdout so we can restore it later
    original_stdout = sys.stdout
    
    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        base_name = os.path.splitext(filename)[0]
        log_file_path = os.path.join(logs_dir, f"{base_name}.log")
        
        print(f"Processing '{filename}' -> Logging to '{log_file_path}'")
        
        try:
            # Open the log file and redirect stdout
            with open(log_file_path, "w", encoding="utf-8") as log_file:
                sys.stdout = log_file
                
                try:
                    process_resume(pdf_path)
                except Exception as e:
                    print(f"Error processing {filename}: {e}")
                    
        except Exception as e:
            # Restore stdout temporarily to print the error
            sys.stdout = original_stdout
            print(f"Could not process or write log for {filename}: {e}")
        finally:
            # Ensure stdout is restored after processing the file
            sys.stdout = original_stdout

    print("Batch processing complete.")

if __name__ == "__main__":
    main()
