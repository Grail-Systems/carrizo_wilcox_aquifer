import os

output_file = 'current_schema.txt'
ignore_dirs = {'.git', 'node_modules', '__pycache__', 'venv', '.env'}
ignore_exts = {'.png', '.jpg', '.jpeg', '.ico', '.pdf', '.zip', '.sqlite3'}

with open(output_file, 'w', encoding='utf-8') as outfile:
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in ignore_exts or file == output_file or file == 'sweeper.py':
                continue
            filepath = os.path.join(root, file)
            outfile.write(f"\n\n{'='*50}\n")
            outfile.write(f"FILE: {filepath}\n")
            outfile.write(f"{'='*50}\n\n")
            try:
                with open(filepath, 'r', encoding='utf-8') as infile:
                    outfile.write(infile.read())
            except Exception as e:
                outfile.write(f"[Error reading file: {e}]\n")

print(f"Sweep complete. Your entire codebase is now inside '{output_file}'.")
