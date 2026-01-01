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
        name = row.get('ma2n') or ''  # company_name
        if name:
            companies.append({
                "name": name, 
                "partner_id": row.get('0000') or ''  # partner_id
            })
    return jsonify({"companies": companies})


@app.route('/api/companies', methods=['POST'])
def create_company():
    data = request.json
    print(f"=== CREATE COMPANY ===")
    print(f"Input: {data}")
    
    row_data = {
        "0000": data.get('partner_id', ''),
        "ma2n": data.get('company_name', ''),
        "cptN": data.get('contact_email', ''),
        "8Zo4": data.get('setup_package', ''),
        "n7lc": data.get('monthly_package', ''),
        "B15W": data.get('setup_fee_aed', 0),
        "M5Hm": data.get('monthly_fee_aed', 0),
        "1DrM": data.get('free_minutes', 0),
        "C8Rt": data.get('whatsapp_enabled', False),
        "27eL": data.get('whatsapp_fee_aed', 0),
        "Sve5": data.get('email_enabled', False),
        "2sQI": data.get('email_fee_aed', 0),
        "L4l4": data.get('additional_lines', 0),
        "F3eu": data.get('lines_fee_aed', 0),
        "rgTU": data.get('additional_numbers', 0),
        "NR8V": data.get('numbers_fee_aed', 0),
        "oPaK": data.get('total_monthly_fee_aed', 0),
        "6cwl": data.get('start_date', ''),
        "H7aK": data.get('contract_start_date', ''),
        "0It0": data.get('end_date'),  # Correct column for end_date!
        "SN3i": data.get('status', 'active'),
        "gmf4": data.get('message_price', 0.95),
        "jm8q": data.get('notes', '')
    }
    print(f"Row data: {row_data}")
    
    result = seatable_request("POST", "rows/", {
        "table_name": "Companies",
        "rows": [row_data]
    })
    print(f"SeaTable result: {result}")
    
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
        name = row.get('ma2n') or ''  # company_name
        pid = row.get('0000') or ''   # partner_id
        end_date = row.get('7cNe')    # end_date
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
    
    # Detect package from free_minutes (more reliable than IDs)
    def get_package_from_minutes(minutes):
        if minutes >= 500: return 'amira_pro'
        if minutes >= 350: return 'amira_core'
        if minutes >= 250: return 'amira_start'
        return ''
    
    status_id_map = {'795802': 'active'}
    
    companies = []
    for row in result.get('rows', []):
        pid = row.get('0000') or ''
        # Check end_date - column 0It0
        end_date = row.get('0It0')
        has_end_date = end_date is not None and end_date != '' and str(end_date) != 'None'
        
        # Only return ACTIVE companies (no end_date) for this partner
        if pid == partner_id and not has_end_date:
            free_minutes = row.get('1DrM') or 0
            
            # Get monthly_package from free_minutes (more reliable)
            monthly_pkg = get_package_from_minutes(free_minutes)
            # Fallback to stored value if we can't detect
            if not monthly_pkg:
                monthly_pkg = row.get('n7lc') or ''
            
            # Get status
            status = row.get('SN3i') or ''
            if status in status_id_map:
                status = status_id_map[status]
            elif status not in ['active', 'cancelled', 'pending']:
                status = 'active'
                
            companies.append({
                "id": row.get('_id'),
                "name": row.get('ma2n') or '',
                "partner_id": pid,
                "contact_email": row.get('cptN') or '',
                "monthly_package": monthly_pkg,
                "setup_package": row.get('8Zo4') or '',
                "whatsapp_enabled": row.get('C8Rt') == True,
                "email_enabled": row.get('Sve5') == True,
                "additional_lines": row.get('L4l4') or 0,
                "additional_numbers": row.get('rgTU') or 0,
                "start_date": (str(row.get('6cwl') or '')).split('T')[0],
                "contract_start_date": (str(row.get('H7aK') or '')).split('T')[0],
                "status": status,
                "free_minutes": free_minutes,
                "monthly_fee_aed": row.get('M5Hm') or 0,
                "setup_fee_aed": row.get('B15W') or 0,
                "whatsapp_fee_aed": row.get('27eL') or 0,
                "email_fee_aed": row.get('2sQI') or 0,
                "lines_fee_aed": row.get('F3eu') or 0,
                "numbers_fee_aed": row.get('NR8V') or 0,
                "total_monthly_fee_aed": row.get('oPaK') or 0,
                "message_price": row.get('gmf4') or 0.95,
                "notes": row.get('jm8q') or '',
                "account_manager": row.get('Gr2k') or ''
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


@app.route('/api/test/write', methods=['GET'])
def test_write():
    """Test writing to SeaTable"""
    # Try with REAL column names, not encrypted
    result = seatable_request("POST", "rows/", {
        "table_name": "Companies",
        "rows": [{
            "partner_id": "TEST_PARTNER",
            "company_name": "TEST_COMPANY_DELETE_ME",
            "free_minutes": 999
        }]
    })
    return jsonify({
        "test": "write with real column names",
        "result": result,
        "success": result is not None and result.get('inserted_row_count', 0) > 0
    })


@app.route('/api/debug/companies-raw', methods=['GET'])
def debug_companies_raw():
    """Debug: Show raw SeaTable response for Companies"""
    result = seatable_request("GET", "rows/?table_name=Companies")
    if not result:
        return jsonify({"error": "Failed"}), 500
    # Find ALL FY Marketing rows
    fy_rows = []
    for row in result.get('rows', []):
        name = row.get('ma2n') or ''
        if 'FY Marketing' in name:
            data = {k: v for k, v in row.items() if v is not None and v != '' and not k.startswith('_')}
            fy_rows.append({
                "name": name,
                "end_date_0It0": row.get('0It0'),
                "monthly_pkg_n7lc": row.get('n7lc'),
                "all_data": data
            })
    return jsonify({"fy_marketing_rows": fy_rows, "count": len(fy_rows)})


@app.route('/', methods=['GET'])
def index():
    return jsonify({"service": "Amira Partner Portal API", "version": "1.1"})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
