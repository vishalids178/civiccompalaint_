from flask import Flask, request, jsonify
from google import genai
from google.genai import types
import os
import json

app = Flask(__name__)

# ==================================================
# GEMINI API SETUP
# ==================================================

API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY is not set.")

client = genai.Client(api_key=API_KEY)

MODEL_NAME = "gemini-3.7-flash"


# ==================================================
# HOME PAGE
# ==================================================

@app.route("/")
def home():
    return "Civic Complaint Backend is Running!"


# ==================================================
# GEMINI COMPLAINT ANALYSIS
# ==================================================

def analyze_complaint(description, complaint_type):

    prompt = f"""
You are an AI civic complaint classification system.

Analyze the citizen complaint and return ONLY JSON.

Citizen complaint:
{description}

Citizen selected category:
{complaint_type}

PRIORITY RULES:

CRITICAL:
- Hospital emergency
- Accident
- Immediate danger to human life
- Situation that could cause serious injury or loss of life if not handled urgently

HIGH:
- Water supply shortage
- Road potholes or major road damage
- Electricity/current shortage
- Serious electrical problems that are not immediately life-threatening

MEDIUM:
- Tree breakage
- Illegal sign boards
- Similar public infrastructure problems that require attention but are not immediately dangerous

LOW:
- All other complaints that do not match the above conditions

IMPORTANT:
- Use ONLY: Critical, High, Medium, Low.
- Severity must be an integer from 1 to 5.
- Give a short reason for the priority.
- Identify the appropriate department.
- Identify the complaint category.
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "object",
                "properties": {
                    "complaint_category": {
                        "type": "string"
                    },
                    "priority": {
                        "type": "string",
                        "enum": [
                            "Critical",
                            "High",
                            "Medium",
                            "Low"
                        ]
                    },
                    "severity": {
                        "type": "integer"
                    },
                    "reason": {
                        "type": "string"
                    },
                    "department": {
                        "type": "string"
                    }
                },
                "required": [
                    "complaint_category",
                    "priority",
                    "severity",
                    "reason",
                    "department"
                ]
            }
        )
    )

    result = json.loads(response.text)

    # Keep severity between 1 and 5
    result["severity"] = max(
        1,
        min(5, int(result["severity"]))
    )

    return result


# ==================================================
# RECEIVE COMPLAINT
# ==================================================

@app.route("/api/complaints", methods=["POST"])
def receive_complaint():

    try:

        # ------------------------------------------
        # Get citizen information
        # ------------------------------------------

        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        location = request.form.get("location", "").strip()
        complaint_type = request.form.get(
            "complaint_type", ""
        ).strip()
        description = request.form.get(
            "description", ""
        ).strip()

        # ------------------------------------------
        # Check required fields
        # ------------------------------------------

        if not name or not phone or not email:
            return jsonify({
                "success": False,
                "error": "Name, phone number and email are required."
            }), 400

        if not location or not description:
            return jsonify({
                "success": False,
                "error": "Location and complaint description are required."
            }), 400

        # ------------------------------------------
        # Receive uploaded files
        # ------------------------------------------

        image = request.files.get("image")
        voice = request.files.get("voice")

        # ------------------------------------------
        # Send complaint to Gemini
        # ------------------------------------------

        ai_result = analyze_complaint(
            description,
            complaint_type
        )

        # ------------------------------------------
        # Create complaint data
        # ------------------------------------------

        complaint = {
            "citizen_name": name,
            "phone": phone,
            "email": email,
            "location": location,

            "complaint_type": ai_result[
                "complaint_category"
            ],

            "description": description,

            "priority": ai_result[
                "priority"
            ],

            "severity": ai_result[
                "severity"
            ],

            "reason": ai_result[
                "reason"
            ],

            "department": ai_result[
                "department"
            ],

            "status": "Received",

            "image_received": image is not None,
            "voice_received": voice is not None
        }

        # ------------------------------------------
        # Print AI result in CMD
        # ------------------------------------------

        print("\n========================================")
        print("        AI COMPLAINT ANALYSIS")
        print("========================================")

        print(json.dumps(
            complaint,
            indent=4
        ))

        print("========================================\n")

        # ------------------------------------------
        # Send result back to dashboard
        # ------------------------------------------

        return jsonify({
            "success": True,
            "message": "Complaint analyzed successfully",
            "data": complaint
        }), 200

    except Exception as e:

        print("\nERROR:", str(e))

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ==================================================
# RUN FLASK SERVER
# ==================================================

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )