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


# AUTH
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


# COMPANIES
@app.route('/api/companies', methods=['GET'])
def get_companies():
    result = seatable_request("GET", "rows/?table_name=Companies")
    if not result:
        return jsonify({"error": "Failed to load companies"}), 500
    companies = []
    for row in result.get('rows', []):
        # Try both normal and encrypted column names
        name = row.get('company_name') or row.get('ma2n') or ''
        if name:
            companies.append({
                "name": name, 
                "partner_id": row.get('partner_id') or row.get('0000') or ''
            })
    return jsonify({"companies": companies})


@app.route('/api/companies', methods=['POST'])
def create_company():
    data = request.json
    result = seatable_request("POST", "rows/", {
        "table_name": "Companies",
        "rows": [{
            "partner_id": data.get('partner_id', ''),
            "company_name": data.get('company_name', ''),
            "contact_email": data.get('contact_email', ''),
            "setup_package": data.get('setup_package', ''),
            "monthly_package": data.get('monthly_package', ''),
            "setup_fee_aed": data.get('setup_fee_aed', 0),
            "monthly_fee_aed": data.get('monthly_fee_aed', 0),
            "free_minutes": data.get('free_minutes', 0),
            "whatsapp_enabled": data.get('whatsapp_enabled', False),
            "whatsapp_fee_aed": data.get('whatsapp_fee_aed', 0),
            "email_enabled": data.get('email_enabled', False),
            "email_fee_aed": data.get('email_fee_aed', 0),
            "additional_lines": data.get('additional_lines', 0),
            "lines_fee_aed": data.get('lines_fee_aed', 0),
            "additional_numbers": data.get('additional_numbers', 0),
            "numbers_fee_aed": data.get('numbers_fee_aed', 0),
            "total_monthly_fee_aed": data.get('total_monthly_fee_aed', 0),
            "start_date": data.get('start_date', ''),
            "contract_start_date": data.get('contract_start_date', ''),
            "end_date": data.get('end_date'),
            "status": data.get('status', 'active'),
            "message_price": data.get('message_price', 0.95),
            "notes": data.get('notes', '')
        }]
    })
    if result:
        return jsonify({"success": True, "result": result})
    return jsonify({"error": "Failed to create company"}), 500


@app.route('/api/companies/<company_id>', methods=['PUT'])
def update_company(company_id):
    data = request.json
    result = seatable_request("PUT", "rows/", {
        "table_name": "Companies",
        "updates": [{"row_id": company_id, "row": data}]
    })
    if result:
        return jsonify({"success": True})
    return jsonify({"error": "Failed to update company"}), 500


@app.route('/api/companies/by-name', methods=['GET'])
def get_company_by_name():
    company_name = request.args.get('name', '')
    partner_id = request.args.get('partner_id', '')
    result = seatable_request("GET", "rows/?table_name=Companies")
    if not result:
        return jsonify({"error": "Failed to load companies"}), 500
    for row in result.get('rows', []):
        name = row.get('company_name') or row.get('ma2n') or ''
        pid = row.get('partner_id') or row.get('0000') or ''
        end_date = row.get('end_date')
        if name == company_name and pid == partner_id and not end_date:
            return jsonify({"company": {"id": row.get('_id'), "name": name}})
    return jsonify({"company": None})


@app.route('/api/companies/partner', methods=['GET'])
def get_partner_companies():
    """Get all companies for a specific partner"""
    partner_id = request.args.get('partner_id', '')
    result = seatable_request("GET", "rows/?table_name=Companies")
    if not result:
        return jsonify({"error": "Failed to load companies"}), 500
    companies = []
    for row in result.get('rows', []):
        # Try both encrypted and normal column names
        pid = row.get('partner_id') or row.get('0000') or ''
        end_date = row.get('end_date')
        # Only return active companies (no end_date) for this partner
        if pid == partner_id and not end_date:
            companies.append({
                "id": row.get('_id'),
                "name": row.get('company_name') or row.get('ma2n') or '',
                "partner_id": pid,
                "contact_email": row.get('contact_email') or '',
                "monthly_package": row.get('monthly_package') or '',
                "setup_package": row.get('setup_package') or '',
                "whatsapp_enabled": row.get('whatsapp_enabled') == True or row.get('whatsapp_enabled') == 'True',
                "email_enabled": row.get('email_enabled') == True or row.get('email_enabled') == 'True',
                "additional_lines": row.get('additional_lines') or 0,
                "additional_numbers": row.get('additional_numbers') or 0,
                "start_date": (str(row.get('start_date') or '')).split('T')[0],
                "contract_start_date": (str(row.get('contract_start_date') or '')).split('T')[0],
                "status": row.get('status') or 'active',
                "free_minutes": row.get('free_minutes') or 0,
                "monthly_fee_aed": row.get('monthly_fee_aed') or row.get('total_monthly_fee_aed') or 0,
                "setup_fee_aed": row.get('setup_fee_aed') or 0,
                "whatsapp_fee_aed": row.get('whatsapp_fee_aed') or 0,
                "email_fee_aed": row.get('email_fee_aed') or 0,
                "lines_fee_aed": row.get('lines_fee_aed') or 0,
                "total_monthly_fee_aed": row.get('total_monthly_fee_aed') or 0,
                "message_price": row.get('message_price') or 0.95,
                "notes": row.get('notes') or '',
                "account_manager": row.get('account_manager') or ''
            })
    return jsonify({"companies": companies})


# LEADS
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


# HEALTH
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})


@app.route('/api/debug/companies-raw', methods=['GET'])
def debug_companies_raw():
    """Debug: Show raw SeaTable response for Companies"""
    result = seatable_request("GET", "rows/?table_name=Companies")
    if not result:
        return jsonify({"error": "Failed"}), 500
    # Return first non-empty row to see column names
    for row in result.get('rows', []):
        # Find a row that has actual data
        has_data = any(v is not None and v != '' for k, v in row.items() if not k.startswith('_'))
        if has_data:
            return jsonify({"sample_row": row, "total": len(result['rows'])})
    return jsonify({"rows": [], "message": "All rows empty"})


@app.route('/', methods=['GET'])
def index():
    return jsonify({"service": "Amira Partner Portal API", "version": "1.1"})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
