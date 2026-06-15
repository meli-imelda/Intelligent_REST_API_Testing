import json
from pmas_controller import PMASController

def generate_smart_dictionary():
    controller = PMASController()
    print("Loading State-Aware SPDG...")
    
    try:
        with open("...", 'r') as file:
            spdg = json.load(file)
    except FileNotFoundError:
        spdg = {}

    system_prompt = """
    You are the Value Agent. Create a RESTler custom dictionary based on the SPDG's "semantic_parameters" list.
    
    CRITICAL DIRECTIVES TO PREVENT STATE CORRUPTION:
    1. NO FAKE TOKENS OR IDs: Do NOT generate values for 'Authorization', 'token', 'jwt', or resource IDs. Leave them out completely so the fuzzer can dynamically extract real ones from the server.
    2. Context-Aware Data: Generate arrays of 5 to 10 highly targeted, context-aware values ONLY for the fields listed in "semantic_parameters" (e.g., valid email formats for 'email', realistic names for 'username').
    
    Output ONLY a strict JSON object containing EXACTLY one top-level key: "restler_custom_payload".
    The values inside MUST be arrays of strings. DO NOT include headers or markdown.
    """

    user_content = json.dumps({"semantic_targets": spdg.get("semantic_parameters", [])}, indent=2)

    print(f"Routing to {controller.models['navigation']} to generate State-Safe Smart Dictionary...")
    smart_dict_json = controller.query_agent("navigation", system_prompt, user_content)

    output_path = "..."
    with open(output_path, "w") as f:
        f.write(smart_dict_json)

    print(f"Value Agent complete. Dictionary saved to {output_path}")

if __name__ == "__main__":
    generate_smart_dictionary()
