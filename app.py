from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Your static letter template (no AI)
LETTER_TEMPLATE = """I am writing to dispute the default listed on the credit file of my client, {first_name} {last_name}.
The client has explained the following circumstances:

{client_explanation}

Below are the identified breaches:

{breaches}

In light of these breaches, we request immediate removal or correction of the default on the client's credit file.
Thank you for your attention to this matter.

Sincerely,

[Your Firm Name or Signature]
"""

@app.route("/merge-template", methods=["POST"])
def merge_template():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    original = data.get("original", {})

    # Extract name
    names = original.get("names", {})
    first_name = names.get("first_name", "").strip()
    last_name = names.get("last_name", "").strip()

    # Extract explanation (from 'post_content' or any field you prefer)
    client_explanation = original.get("post_content", "").strip()

    # Gather all non-empty "description_" fields for breaches
    breach_list = []
    for key, value in original.items():
        if key.startswith("description_"):
            val = value.strip()
            if val:
                breach_list.append(val)

    # Join them with a newline or bullet points
    if breach_list:
        combined_breaches = "\n- " + "\n- ".join(breach_list)
    else:
        combined_breaches = "No specific breaches identified."

    # Merge into the template
    dispute_letter = LETTER_TEMPLATE.format(
        first_name=first_name,
        last_name=last_name,
        client_explanation=client_explanation,
        breaches=combined_breaches
    )

    return jsonify({"dispute_letter": dispute_letter}), 200

if __name__ == "__main__":
    # Run locally on port 5000 (for development)
    app.run(host="0.0.0.0", port=5000)
