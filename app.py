from flask import Flask, request, jsonify
import os
import requests
import logging
import json

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

# Your Make webhook URL
MAKE_WEBHOOK_URL = "https://hook.eu2.make.com/ahjep7qn8dma6kijswv0fw3rns4rcecz"

@app.route("/merge-template", methods=["POST"])
def merge_template():
    if not request.is_json:
        logger.error("Request received is not in JSON format.")
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    logger.info(f"Received payload: {json.dumps(data, indent=2)}")  # Log raw payload for debugging

    # Determine if the payload has an 'original' wrapper or not
    original = data.get("original", data)  # Use entire payload if 'original' is missing

    # Validate required fields
    if not original:
        logger.error("Payload is empty or missing expected fields.")
        return jsonify({"error": "Received empty payload."}), 400

    # Extract name (Handles Fluent Forms variations)
    names = original.get("names") or {}
    if not names:  # Handle cases where Fluent Forms sends a different structure
        full_name = original.get("full_name", "").strip()
        name_parts = full_name.split()
        names = {"first_name": name_parts[0] if name_parts else "", "last_name": name_parts[-1] if len(name_parts) > 1 else ""}

    first_name = names.get("first_name", "").strip()
    last_name = names.get("last_name", "").strip()

    if not first_name or not last_name:
        logger.error("Client name is missing or incomplete.")
        return jsonify({"error": "Missing client first or last name."}), 400

    # Extract explanation (from 'post_content' or alternative fields)
    client_explanation = original.get("post_content", "").strip()
    if not client_explanation:
        logger.warning("Client explanation is missing from request.")

    # Gather all non-empty "description_" fields for breaches
    breach_list = [value.strip() for key, value in original.items() if key.startswith("description_") and value.strip()]
    combined_breaches = "\n- " + "\n- ".join(breach_list) if breach_list else "No specific breaches identified."

    # Generate dispute letter
    dispute_letter = LETTER_TEMPLATE.format(
        first_name=first_name,
        last_name=last_name,
        client_explanation=client_explanation,
        breaches=combined_breaches
    )

    # Prevent sending an empty dispute letter
    if not dispute_letter.strip():
        logger.error("Generated dispute letter is empty! Aborting request.")
        return jsonify({"error": "Generated dispute letter is empty, cannot proceed."}), 400

    # Prepare payload for Make webhook
    payload = {
        "client_name": f"{first_name} {last_name}",
        "dispute_letter": dispute_letter,
        "breaches": breach_list,
        "client_explanation": client_explanation
    }

    logger.info(f"Sending payload to Make: {json.dumps(payload, indent=2)}")  # Log outgoing request

    # Send data to Make webhook with retry logic
    for attempt in range(3):
        try:
            response = requests.post(MAKE_WEBHOOK_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
            if response.status_code == 200:
                logger.info("Dispute letter sent successfully.")
                return jsonify({"message": "Dispute letter generated and sent to Make successfully.", "dispute_letter": dispute_letter}), 200
            else:
                logger.error(f"Make webhook failed: {response.status_code} {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending to Make webhook: {e}")

        if attempt == 2:
            return jsonify({"error": "Failed to send data to Make after multiple attempts."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
