import os
import sqlite3
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from sqlalchemy import text
from database import SessionLocal # This is for the Historical Docs feature
from bs4 import BeautifulSoup # Added for web scraping
from urllib.parse import urljoin # Added for web scraping

# --- App Initialization ---
# Initialize the Flask app and CORS once at the top.
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)


# --- Endpoint 1: DA Contacts ---
@app.route('/contacts', methods=['GET'])
def get_contacts():
    logging.info("Request received for /contacts")
    try:
        con = sqlite3.connect('contact_info.db')
        cur = con.cursor()
        cur.execute("SELECT * FROM contact")
        rows = cur.fetchall()
        con.close()
        
        contacts = []
        for row in rows:
            contacts.append({
                'County': row[0], 'Name': row[1], 'Address': row[2],
                'Phone': row[3], 'Fax': row[4], 'Website': row[5],
            })
        return jsonify(contacts)
    except Exception as e:
        logging.error(f"Error in /contacts: {e}")
        return jsonify({"error": "Failed to retrieve contacts from database"}), 500


# --- Endpoint 2: FDA Enforcement ---
@app.route("/fda-enforcement", methods=['POST'])
def search_fda_enforcement():
    logging.info("Request received for /fda-enforcement")
    data = request.get_json()
    
    # --- This section is now complete ---
    product_description = data.get('productDescription', '')
    recalling_firm = data.get('recallingFirm', '')
    recall_number = data.get('recallNumber', '')
    recall_class = data.get('recallClass', '')
    # --- End of complete section ---
    
    apikey = os.getenv('FDA_API_KEY')
    if not apikey:
        return jsonify({"error": "API key is missing"}), 500
    
    query_params = []
    if product_description:
        query_params.append(f'product_description:"{product_description}"')
    if recalling_firm:
        query_params.append(f'recalling_firm:"{recalling_firm}"')
    # Add the new parameters to the query
    if recall_number:
        query_params.append(f'recall_number:"{recall_number}"')
    if recall_class:
        query_params.append(f'classification:"{recall_class}"')

    # Ensure at least one search term is present
    if not query_params:
        return jsonify({"error": "At least one search field is required"}), 400
    
    query = ' AND '.join(query_params)
    url = f'https://api.fda.gov/device/enforcement.json?api_key={apikey}&search={query}&limit=100'

    try:
        response = requests.get(url)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.RequestException as e:
        logging.error(f"Error fetching data from FDA API: {e}")
        return jsonify({"error": "Failed to fetch data from the API"}), 500


# --- Endpoint 3: Warning Letters (Now with scraping logic) ---
@app.route("/warning_letters", methods=['POST'])
def search_warning_letters():
    logging.info("Request received for /warning_letters")
    data = request.get_json()
    firm_name = data.get('firmName', '')

    if not firm_name:
        return jsonify({"error": "Firm name is required"}), 400

    try:
        # Construct the search URL for the FDA website
        search_url = f"https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters?search_api_views_fulltext={firm_name}"
        
        # Make the request to the FDA website
        response = requests.get(search_url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()

        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        results = []
        # Find all table rows in the search results
        for row in soup.select('table.views-table tbody tr'):
            cells = row.find_all('td')
            if len(cells) >= 3:
                # Extract the data from the cells
                company_name = cells[0].get_text(strip=True)
                issuing_office = cells[1].get_text(strip=True)
                posted_date = cells[2].get_text(strip=True)
                
                # Find the link to the warning letter PDF
                link_tag = cells[0].find('a')
                letter_url = ""
                if link_tag and link_tag.has_attr('href'):
                    letter_url = urljoin(search_url, link_tag['href'])

                # Assemble the result dictionary to match the Swift model
                # Note: Not all fields are available from the search results page.
                # We use placeholder or derived values where necessary.
                result = {
                    "LegalName": company_name,
                    "ActionTakenDate": posted_date,
                    "ActionType": "Warning Letter",
                    "State": "N/A", # State is not provided in search results
                    "CaseInjunctionID": letter_url, # Use URL as a unique ID
                    "warning_letter_url": letter_url
                }
                results.append(result)

        return jsonify(results)

    except requests.RequestException as e:
        logging.error(f"Error scraping FDA Warning Letters: {e}")
        return jsonify({"error": "Failed to fetch data from FDA website"}), 500
    except Exception as e:
        logging.error(f"An unexpected error occurred during scraping: {e}")
        return jsonify({"error": "An internal error occurred"}), 500


# --- Endpoint 4: Historical Documents ---
@app.route("/historical-documents/search", methods=['GET'])
def search_historical_documents():
    logging.info("Request received for /historical-documents/search")
    # This logic is taken from the app.py file you provided for this feature.
    # It uses SQLAlchemy and a separate database session.
    query = request.args.get("query", "").strip()
    # ... (Add the full logic from your historical docs app.py here) ...
    
    session = SessionLocal()
    try:
        # Simplified example of the query logic
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
# This part is for running the app locally.
# Render will use the 'gunicorn' command from your render.yaml instead.
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)

