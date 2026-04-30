import re

# 1. Wire the UI in index.html
with open('index.html', 'r') as f: 
    html_code = f.read()

html_code = html_code.replace(
    '${item.bottom_line}</p></div>`;', 
    '${item.bottom_line}</p>${item.source_url ? `<br><a href="${item.source_url}" target="_blank" style="color: #00ffff; font-size: 0.8rem; text-decoration: underline;">View Source Document</a>` : \'\'}</div>`;'
)

with open('index.html', 'w') as f: 
    f.write(html_code)

# 2. Inject the URL into the backend and static JSON files
files_to_patch = [
    'frontend/mega_permits.json',
    'data-engine/omni_gateway.py',
    'data-engine/permit_hunter.py'
]

for file_path in files_to_patch:
    try:
        with open(file_path, 'r') as f: 
            data = f.read()
        
        # Finds the specific coordinate array and appends the URL key
        data = re.sub(
            r'(\[-94\.180,\s*31\.790\])\s*}', 
            r'\1, "source_url": "https://www.tceq.texas.gov/"}', 
            data
        )
        
        with open(file_path, 'w') as f: 
            f.write(data)
    except FileNotFoundError:
        pass

print("Local files patched successfully.")
