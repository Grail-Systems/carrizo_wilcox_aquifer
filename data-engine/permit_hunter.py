import requests
from bs4 import BeautifulSoup
import PyPDF2
import io
import json

print("Spinning up the Grail Systems Autonomous Hunter...")
target_url = "https://www.pgcd.org/agendas"
headers = {"User-Agent": "Mozilla/5.0"}
threat_keywords = ['permit', 'gallons', 'industrial', 'application', 'amendment', 'hearing']

try:
    print("Breaching the server and locating recent PDF documents...")
    response = requests.get(target_url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a')
        
        intel_feed = []
        found_hrefs = []

        for link in links:
            href = link.get('href')
            text = link.get_text().strip()
            
            if href and '.pdf' in href.lower() and href not in found_hrefs:
                found_hrefs.append(href)
                if href.startswith('/'):
                    href = "https://www.pgcd.org" + href
                
                doc_name = text if len(text) > 3 else href.split('/')[-1]
                
                # Limit to the 3 most recent documents so we don't overload the system
                if len(intel_feed) >= 3:
                    break
                    
                print(f"\n[SCANNING] {doc_name}...")
                
                try:
                    # Download the PDF into temporary memory
                    pdf_response = requests.get(href, headers=headers, timeout=10)
                    pdf_file = io.BytesIO(pdf_response.content)
                    reader = PyPDF2.PdfReader(pdf_file)
                    
                    # Extract text from the first 3 pages
                    pdf_text = ""
                    for page_num in range(min(3, len(reader.pages))):
                        pdf_text += reader.pages[page_num].extract_text().lower()
                        
                    # Check for our red-flag keywords
                    hits = [kw for kw in threat_keywords if kw in pdf_text]
                    status = "HIGH THREAT" if hits else "CLEAR"
                    
                    intel_feed.append({
                        "title": doc_name,
                        "link": href,
                        "status": status,
                        "hits": hits
                    })
                    print(f" -> Status: {status} | Keywords Found: {hits}")
                    
                except Exception as e:
                    print(" -> [WARNING] Could not read text. PDF might be a scanned image.")
                    intel_feed.append({
                        "title": doc_name,
                        "link": href,
                        "status": "MANUAL REVIEW REQ",
                        "hits": []
                    })
                    
        # Export the dossier to the frontend
        with open('frontend/threat_feed.json', 'w') as f:
            json.dump(intel_feed, f)
        print("\n[SUCCESS] Threat feed compiled and routed to the UI Dashboard.")
        
    else:
        print(f"Connection blocked. Status: {response.status_code}")

except Exception as e:
    print(f"System Error: {e}")
