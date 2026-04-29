import zipfile
import csv

zip_path = 'data-engine/TEC_CF_CSV.zip'

print("--- DEPLOYING DIAGNOSTIC SCOPE ---")

try:
    with zipfile.ZipFile(zip_path, 'r') as z:
        # Find the first CSV inside the state's zip file
        first_file = [f for f in z.namelist() if f.endswith('.csv')][0]
        print(f"[TARGET LOCKED] Inspecting: {first_file}\n")
        
        with z.open(first_file) as f:
            decoded_file = (line.decode('utf-8', errors='ignore') for line in f)
            reader = csv.reader(decoded_file)
            
            headers = next(reader)
            print("--- STATE DATABASE HEADERS ---")
            for index, col_name in enumerate(headers):
                print(f"Column [{index}]: {col_name}")
                
            sample_row = next(reader)
            print("\n--- SAMPLE DATA (WHAT IS ACTUALLY INSIDE) ---")
            for index, data in enumerate(sample_row):
                print(f"Column [{index}]: {data}")
                
except Exception as e:
    print(f"[SYSTEM ERROR] Could not read file: {e}")
