from flask import Flask, request, jsonify
import os
import requests
import logging

# Initialize Flask app
app = Flask(__name__)

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Static letter template
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

# Make webhook URL
MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL", "https://hook.eu2.make.com/ahjep7qn8dma6kijswv0fw3rns4rcecz")

@app.route("/merge-template", methods=["POST"])
def merge_template():
    # Validate JSON payload
    if not request.is_json:
        logger.error("Request is not JSON")
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    original = data.get("original", {})

    # Validate required fields
    required_fields = ["names", "post_content"]
    missing_fields = [field for field in required_fields if not original.get(field)]
    if missing_fields:
        logger.error(f"Missing required fields: {', '.join(missing_fields)}")
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    # Extract fields
    names = original.get("names", {})
    first_name = names.get("first_name", "").strip()
    last_name = names.get("last_name", "").strip()
    client_explanation = original.get("post_content", "").strip()

    # Validate breaches
    breach_list = [
        value.strip() for key, value in original.items() if key.startswith("description_") and value.strip()
    ]
    combined_breaches = "\n- " + "\n- ".join(breach_list) if breach_list else "No specific breaches identified."

    # Generate dispute letter
    dispute_letter = LETTER_TEMPLATE.format(
        first_name=first_name,
        last_name=last_name,
        client_explanation=client_explanation,
        breaches=combined_breaches
    )

    # Prepare payload
    payload = {
        "client_name": f"{first_name} {last_name}",
        "dispute_letter": dispute_letter,
        "breaches": breach_list,
        "client_explanation": client_explanation
    }

    # Send data to Make webhook
    for attempt in range(3):  # Retry logic
        try:
            response = requests.post(MAKE_WEBHOOK_URL, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("Dispute letter sent successfully")
                return jsonify({"message": "Dispute letter generated and sent to Make successfully.", "dispute_letter": dispute_letter}), 200
            else:
                logger.error(f"Make webhook failed: {response.status_code} {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending to Make webhook: {e}")
        if attempt == 2:  # Final attempt failed
            return jsonify({"error": "Failed to send data to Make after multiple attempts."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
