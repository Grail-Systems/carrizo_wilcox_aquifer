#!/bin/bash
echo "--- HUNTER BOT ACTIVATED: $(date) ---"
cd /home/scottzion1984/Carrizo_Wilcox_Aquifer

# 1. Run the Python Scanners
/usr/bin/python3 data-engine/permit_hunter.py
/usr/bin/python3 data-engine/toxin_hunter.py

# 2. Package the newly generated intelligence
git add frontend/threat_feed.json
git add frontend/toxin_feed.json
git commit -m "Automated Intel Update: $(date +'%Y-%m-%d')"

# 3. Push it securely using the restricted token
# Note: We are embedding the token temporarily for the push command
git push origin main

echo "--- SCAN & DEPLOY COMPLETE ---"


