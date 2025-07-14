import os
import sqlite3
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from sqlalchemy import text
from database import SessionLocal # This is for the Historical Docs feature
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# --- App Initialization ---
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)


# --- Endpoint 1: DA Contacts ---
@app.route('/contacts', methods=['GET'])
def get_contacts():
    # ... (existing contact logic is fine) ...
    logging.info("Request received for /contacts")
    try:
        con = sqlite3.connect('contact_info.db')
        cur = con.cursor()
        cur.execute("SELECT * FROM contact")
        rows = cur.fetchall()
        con.close()
        contacts = [{'County': r[0], 'Name': r[1], 'Address': r[2], 'Phone': r[3], 'Fax': r[4], 'Website': r[5]} for r in rows]
        return jsonify(contacts)
    except Exception as e:
        logging.error(f"Error in /contacts: {e}")
        return jsonify({"error": "Failed to retrieve contacts from database"}), 500


# --- Endpoint 2: FDA Enforcement ---
@app.route("/fda-enforcement", methods=['POST'])
def search_fda_enforcement():
    # ... (existing enforcement logic is fine) ...
    logging.info("Request received for /fda-enforcement")
    data = request.get_json()
    product_description = data.get('productDescription', '')
    recalling_firm = data.get('recallingFirm', '')
    recall_number = data.get('recallNumber', '')
    recall_class = data.get('recallClass', '')
    apikey = os.getenv('FDA_API_KEY')
    if not apikey: return jsonify({"error": "API key is missing"}), 500
    query_params = []
    if product_description: query_params.append(f'product_description:"{product_description}"')
    if recalling_firm: query_params.append(f'recalling_firm:"{recalling_firm}"')
    if recall_number: query_params.append(f'recall_number:"{recall_number}"')
    if recall_class: query_params.append(f'classification:"{recall_class}"')
    if not query_params: return jsonify({"error": "At least one search field is required"}), 400
    query = ' AND '.join(query_params)
    url = f'https://api.fda.gov/device/enforcement.json?api_key={apikey}&search={query}&limit=100'
    try:
        response = requests.get(url)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.RequestException as e:
        logging.error(f"Error fetching data from FDA API: {e}")
        return jsonify({"error": "Failed to fetch data from the API"}), 500


# --- Endpoint 3: Warning Letters ---
@app.route("/warning_letters", methods=['POST'])
def search_warning_letters():
    # ... (existing warning letter logic is fine) ...
    logging.info("Request received for /warning_letters")
    data = request.get_json()
    firm_name = data.get('firmName', '')
    if not firm_name: return jsonify({"error": "Firm name is required"}), 400
    try:
        search_url = f"https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters?search_api_views_fulltext={firm_name.replace(' ', '+')}"
        response = requests.get(search_url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        results = []
        for row in soup.select('table.views-table tbody tr'):
            cells = row.find_all('td')
            if len(cells) >= 3:
                company_cell, _, posted_date_cell = cells[0], cells[1], cells[2]
                legal_name = company_cell.get_text(strip=True)
                link_tag = company_cell.find('a')
                letter_url = urljoin(search_url, link_tag['href']) if link_tag else ""
                results.append({"LegalName": legal_name, "ActionTakenDate": posted_date_cell.get_text(strip=True), "ActionType": "Warning Letter", "State": "N/A", "CaseInjunctionID": letter_url, "warning_letter_url": letter_url})
        return jsonify(results)
    except Exception as e:
        logging.error(f"Error scraping FDA Warning Letters: {e}")
        return jsonify({"error": "An internal error occurred"}), 500

# --- NEW Endpoint 4: MAUDE Adverse Events ---
@app.route("/maude", methods=['POST'])
def search_maude():
    logging.info("Request received for /maude")
    data = request.get_json()
    
    device_name = data.get('deviceName', '')
    from_date = data.get('fromDate', '') # Expected format: YYYY-MM-DD
    to_date = data.get('toDate', '')     # Expected format: YYYY-MM-DD

    if not all([device_name, from_date, to_date]):
        return jsonify({"error": "Device name and date range are required"}), 400

    apikey = os.getenv('FDA_API_KEY')
    if not apikey:
        return jsonify({"error": "API key is missing"}), 500

    # Format dates for the FDA API query
    from_date_formatted = from_date.replace('-', '')
    to_date_formatted = to_date.replace('-', '')

    # Construct the search query
    query_params = [
        f'device.generic_name:"{device_name}"',
        f'date_of_event:[{from_date_formatted}+TO+{to_date_formatted}]'
    ]
    query = ' AND '.join(query_params)
    
    url = f"https://api.fda.gov/device/event.json?api_key={apikey}&search={query}&limit=100"
    
    logging.info(f"Querying MAUDE API: {url}")

    try:
        response = requests.get(url)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.RequestException as e:
        logging.error(f"Error fetching data from MAUDE API: {e}")
        return jsonify({"error": "Failed to fetch data from the MAUDE API"}), 500


# --- Endpoint 5: Historical Documents ---
@app.route("/historical-documents/search", methods=['GET'])
def search_historical_documents():
    # ... (existing historical docs logic is fine) ...
    logging.info("Request received for /historical-documents/search")
    query = request.args.get("query", "").strip()
    session = SessionLocal()
    try:
        sql = text("SELECT * FROM historical_documents WHERE text LIKE :query LIMIT 20")
        results = session.execute(sql, {"query": f"%{query}%"}).fetchall()
        result_dicts = [dict(row._mapping) for row in results]
        return jsonify({"results": result_dicts})
    except Exception as e:
        logging.error(f"Error in /historical-documents/search: {e}")
        return jsonify({"error": "Failed to search historical documents"}), 500
    finally:
        session.close()


# --- Server Execution ---
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)

