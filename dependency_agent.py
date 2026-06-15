import json
from pmas_controller import PMASController

def build_endpoint_tree(spec):
    tree = {}
    for path, methods in spec.get('paths', {}).items():
        parts = [p for p in path.strip('/').split('/') if p]
        current_level = tree
        for part in parts:
            if part not in current_level:
                current_level[part] = {"_methods": {}, "_children": {}}
            current_level = current_level[part]["_children"]
            
        curr = tree
        for part in parts:
            node = curr[part]
            curr = node["_children"]
            
        for method, details in methods.items():
            node["_methods"][method.upper()] = {
                "parameters": details.get('parameters', []),
                "requestBody": details.get('requestBody', {})
            }
    return tree

def generate_spdg():
    controller = PMASController()
    print("Loading OpenAPI Spec...")
    
    
    with open("...", "r") as f: # Update to appropriate json as needed
        spec = json.load(f)
    
    tree_summary = build_endpoint_tree(spec)
    endpoints_json = json.dumps({"hierarchical_tree": tree_summary}, indent=2)

    system_prompt = """
    You are the Dependency Agent. Analyze this hierarchical tree-based OpenAPI summary.
    
    Critical Directives:
    1. Distinguish State vs Data: Explicitly classify each parameter/property in the API as either "STATEFUL" (IDs, tokens, session keys) or "SEMANTIC" (names, emails, titles, search queries).
    2. Fuzzy Matching: Map dependencies ONLY for STATEFUL parameters (e.g., Endpoint A produces 'user_id', Endpoint B consumes 'id').
    
    Output ONLY a strict JSON object with:
    - "stateful_dependencies": array of objects {producer, consumer, property}
    - "semantic_parameters": array of strings listing properties that need context-aware fuzzing (e.g., ["email", "username", "book_title"])
    """

    print(f"Routing to {controller.models['dependency']} for inference...")
    spdg_json = controller.query_agent("dependency", system_prompt, endpoints_json)

    os_path = "..."
    with open(os_path, "w") as f:
        f.write(spdg_json)
    print(f"Inference complete. State-Aware SPDG saved to {os_path}")

if __name__ == "__main__":
    generate_spdg()
