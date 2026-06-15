import os
import json
import glob
from pmas_controller import PMASController

class PostFuzzingAnalyzer:
    def __init__(self):
        self.controller = PMASController()
        # Your current 1-hour experiment folder
        self.log_dir = "..."
        self.sequence_length = 3  

    def extract_event_sentences(self):
        print(f"[*] Scanning logs for Event Sentences in: {self.log_dir}")
        transactions = []
        
        log_files = glob.glob(os.path.join(self.log_dir, "*.txt"))
        print(f"    [Diagnostic] Found {len(log_files)} text files in directory.")

        total_exchanges_parsed = 0

        for file_path in log_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
            except Exception:
                continue
            
            # --- UNIVERSAL HTTP STATE MACHINE ---
            valid_exchanges = []
            current_req = []
            current_resp = []
            in_resp = False

            for line in lines:
                clean_line = line.strip()
                if not clean_line:
                    continue
                
                # Detect the start of a new HTTP Request
                is_new_req = any(method in clean_line for method in ["GET /", "POST /", "PUT /", "DELETE /", "PATCH /"])
                
                if is_new_req:
                    # Save the previous transaction if one exists
                    if current_req and current_resp:
                        req_str = "\n".join(current_req)
                        resp_str = "\n".join(current_resp)
                        valid_exchanges.append(f"REQUEST:\n{req_str[:300]}\nRESPONSE:\n{resp_str[:500]}\n")
                    
                    current_req = [clean_line]
                    current_resp = []
                    in_resp = False
                    
                # Detect the start of an HTTP Response
                elif "HTTP/1.1 " in clean_line or "HTTP/1.0 " in clean_line:
                    in_resp = True
                    current_resp.append(clean_line)
                    
                # Append payload/header data to the correct block
                else:
                    if in_resp:
                        current_resp.append(clean_line)
                    elif current_req:
                        current_req.append(clean_line)

            # Catch the very last transaction in the file
            if current_req and current_resp:
                req_str = "\n".join(current_req)
                resp_str = "\n".join(current_resp)
                valid_exchanges.append(f"REQUEST:\n{req_str[:300]}\nRESPONSE:\n{resp_str[:500]}\n")

            total_exchanges_parsed += len(valid_exchanges)
            
            # --- EVENT SENTENCE SLIDING WINDOW ---
            for i in range(len(valid_exchanges) - self.sequence_length + 1):
                sequence = valid_exchanges[i:i + self.sequence_length]
                combined_sequence = "\n--- NEXT SEQUENTIAL EVENT ---\n".join(sequence)
                lower_seq = combined_sequence.lower()
                
                # Broadened heuristic filter
                has_crash = " 500" in combined_sequence or "status: 500" in lower_seq or "internal server error" in lower_seq
                has_suspicious_success = (" 200" in combined_sequence or " 201" in combined_sequence or " 204" in combined_sequence) and ("fail" in lower_seq or "error" in lower_seq or "password" in lower_seq)
                
                if has_crash:
                    transactions.append({"type": f"Sequence ({self.sequence_length} steps) - Contains 500 Crash", "content": combined_sequence})
                elif has_suspicious_success:
                    transactions.append({"type": f"Sequence ({self.sequence_length} steps) - Suspicious 2xx", "content": combined_sequence})

        print(f"    [Diagnostic] Successfully parsed {total_exchanges_parsed} individual API request/response pairs.")

        unique_txs = []
        seen = set()
        for tx in transactions:
            fingerprint = tx['content'][:300]
            if fingerprint not in seen:
                seen.add(fingerprint)
                unique_txs.append(tx)

        print(f"[*] Extracted {len(unique_txs)} unique Event Sequences for State Analysis.")
        return unique_txs

    def generate_owasp_report(self, transactions):
        if not transactions:
            print("[*] No suspicious sequences found.")
            return

        print("\n[*] Routing Event Sequences to DeepSeek-V3 for BLV Analysis...")
        report_output = "### PMAS Sequential State Transition Report\n\n"

        for i, tx in enumerate(transactions[:15]):
            print(f"    Analyzing Sequence {i+1}/{min(len(transactions), 15)}...")
            
            system_prompt = """
            You are the Analysis Agent. Evaluate this sequential "Event Sentence" (an ordered trace of API calls).
            Analyze how the system state transitions from the first request to the last. 
            Identify multi-step Business Logic Vulnerabilities (BLVs) such as quota bypasses, state corruption, or multi-step authorization flaws.
            
            Output ONLY a strict JSON object with:
            - "vulnerability_found" (boolean)
            - "owasp_category" (string, e.g., "API1:2023 - BOLA")
            - "state_transition_analysis" (Explain the sequence of events and why the state transition is flawed)
            """
            
            user_content = f"Event Trace:\n{tx['content']}"

            try:
                analysis_str = self.controller.query_agent("analysis", system_prompt, user_content)
                analysis = json.loads(analysis_str)
                
                if analysis.get("vulnerability_found"):
                    report_output += f"#### Sequence {i+1}: {tx['type']}\n"
                    report_output += f"- **OWASP Category:** {analysis.get('owasp_category')}\n"
                    report_output += f"- **State Transition Flaw:** {analysis.get('state_transition_analysis')}\n\n"
            except Exception as e:
                print(f"    [!] JSON Parse Error: {e}")

        report_path = "../logs/post_fuzzing_report_event_sentences_1hr.md"
        with open(report_path, "w") as f:
            f.write(report_output)
        print(f"\n[SUCCESS] Event Sequence Report saved to {report_path}")

if __name__ == "__main__":
    analyzer = PostFuzzingAnalyzer()
    suspicious_txs = analyzer.extract_event_sentences()
    analyzer.generate_owasp_report(suspicious_txs)
