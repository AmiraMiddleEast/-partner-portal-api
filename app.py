"""
Amira Partner Portal Backend
============================
Secure API proxy for SeaTable - keeps API token server-side.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# Configuration from Environment Variables
SEATABLE_API_TOKEN = os.environ.get('SEATABLE_API_TOKEN', '')
SEATABLE_URL = os.environ.get('SEATABLE_URL', 'https://cloud.seatable.io')

_access_token = None
_dtable_uuid = None


def get_seatable_access():
    global _access_token, _dtable_uuid
    if _access_token and _dtable_uuid:
        return _access_token, _dtable_uuid
    response = requests.get(
        f"{SEATABLE_URL}/api/v2.1/dtable/app-access-token/",
        headers={"Authorization": f"Token {SEATABLE_API_TOKEN}"}
    )
    if response.status_code != 200:
        raise Exception("Failed to get SeaTable access token")
    data = response.json()
    _access_token = data["access_token"]
    _dtable_uuid = data["dtable_uuid"]
    return _access_token, _dtable_uuid


def seatable_request(method, endpoint, data=None):
    access_token, dtable_uuid = get_seatable_access()
    url = f"{SEATABLE_URL}/api-gateway/api/v2/dtables/{dtable_uuid}/{endpoint}"
    headers = {"Authorization": f"Bearer {access_token}"}
    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "POST":
        headers["Content-Type"] = "application/json"
        response = requests.post(url, headers=headers, json=data)
    elif method == "PUT":
        headers["Content-Type"] = "application/json"
        response = requests.put(url, headers=headers, json=data)
    return response.json() if response.status_code == 200 else None


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    if not email:
        return jsonify({"error": "Email required"}), 400
    result = seatable_request("GET", "rows/?table_name=Partners")
    if not result:
        return jsonify({"error": "Database connection failed"}), 500
    partner = None
    for p in result.get('rows', []):
        p_email = (p.get('email') or p.get('s9S4') or '').lower().strip()
        if p_email == email:
            partner = p
            break
    if not partner:
        return jsonify({"error": "Partner not found"}), 404
    stored_pw = partner.get('password_hash') or partner.get('xK33') or ''
    if password and stored_pw and password != stored_pw:
        return jsonify({"error": "Invalid password"}), 401
    return jsonify({
        "success": True,
        "partner": {
            "email": partner.get('email') or partner.get('s9S4') or '',
            "name": partner.get('name') or partner.get('Doq7') or '',
            "company": partner.get('name') or partner.get('Doq7') or '',
            "message_price": partner.get('message_price') or partner.get('774a') or 0.95,
            "type": partner.get('type') or 'white_label'
        }
    })


@app.route('/api/companies', methods=['GET'])
def get_companies():
    result = seatable_request("GET", "rows/?table_name=Companies")
    if not result:
        return jsonify({"error": "Failed to load companies"}), 500
    companies = []
    for row in result.get('rows', []):
        name = row.get('ma2n') or row.get('company_name') or ''
        if name:
            companies.append({"name": name, "partner_id": row.get('0000') or row.get('partner_id') or ''})
    return jsonify({"companies": companies})


@app.route('/api/leads', methods=['GET'])
def get_leads():
    result = seatable_request("GET", "rows/?table_name=LeadProtection")
    if not result:
        return jsonify({"error": "Failed to load leads"}), 500
    leads = []
    for row in result.get('rows', []):
        leads.append({
            "id": row.get('_id'),
            "company_name": row.get('0000') or row.get('company_name') or '',
            "city": row.get('gOM7') or row.get('city') or '',
            "country": row.get('ld4j') or row.get('country') or '',
            "partner_id": row.get('uBXT') or row.get('partner_id') or '',
            "partner_name": row.get('WDY8') or row.get('partner_name') or '',
            "registration_date": (row.get('86us') or row.get('registration_date') or '').split('T')[0],
            "protection_end": (row.get('5niV') or row.get('protection_end') or '').split('T')[0],
            "extended": row.get('37u2') or row.get('extended') or False,
            "status": row.get('j0p2') or row.get('status') or 'protected'
        })
    return jsonify({"leads": leads})


@app.route('/api/leads', methods=['POST'])
def create_lead():
    data = request.json
    result = seatable_request("POST", "rows/", {
        "table_name": "LeadProtection",
        "rows": [{
            "company_name": data['company_name'],
            "city": data.get('city', ''),
            "country": data['country'],
            "partner_id": data['partner_id'],
            "partner_name": data['partner_name'],
            "registration_date": data['registration_date'],
            "protection_end": data['protection_end'],
            "extended": False,
            "status": "protected"
        }]
    })
    if result:
        return jsonify({"success": True})
    return jsonify({"error": "Failed to create lead"}), 500


@app.route('/api/leads/<lead_id>', methods=['PUT'])
def update_lead(lead_id):
    data = request.json
    update_data = {k: v for k, v in data.items() if k in ['protection_end', 'extended', 'status']}
    result = seatable_request("PUT", "rows/", {
        "table_name": "LeadProtection",
        "updates": [{"row_id": lead_id, "row": update_data}]
    })
    if result:
        return jsonify({"success": True})
    return jsonify({"error": "Failed to update lead"}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})


@app.route('/', methods=['GET'])
def index():
    return jsonify({"service": "Amira Partner Portal API", "version": "1.0"})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
