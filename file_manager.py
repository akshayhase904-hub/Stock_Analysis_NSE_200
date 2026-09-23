import os
import glob

def split_file(filepath, chunk_size_mb=20):
    if not os.path.exists(filepath):
        return
        
    chunk_size = chunk_size_mb * 1024 * 1024
    file_size = os.path.getsize(filepath)
    
    if file_size <= chunk_size:
        return # No need to split
        
    print(f"Splitting {filepath} into {chunk_size_mb}MB chunks...")
    
    # Clean up old parts first
    old_parts = glob.glob(filepath + ".part*")
    for part in old_parts:
        os.remove(part)
        
    part_num = 0
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            part_name = f"{filepath}.part{part_num}"
            with open(part_name, 'wb') as chunk_file:
                chunk_file.write(chunk)
            print(f"Created {part_name}")
            part_num += 1
            
    print(f"Successfully split {filepath} into {part_num} parts.")

def combine_file(filepath):
    parts = sorted(glob.glob(filepath + ".part*"), key=lambda x: int(x.split('.part')[-1]))
    if not parts:
        return
        
    print(f"Combining {len(parts)} parts to restore {filepath}...")
    with open(filepath, 'wb') as outfile:
        for part in parts:
            with open(part, 'rb') as infile:
                outfile.write(infile.read())
                
    print(f"Successfully restored {filepath}")

def scan_and_split_all(directory='.', chunk_size_mb=20):
    """Scans directory for any file > 20MB and splits it automatically."""
    chunk_size = chunk_size_mb * 1024 * 1024
    for root, dirs, files in os.walk(directory):
        if '.git' in root: continue
        for file in files:
            # Ignore already split parts
            if '.part' in file: continue
            filepath = os.path.join(root, file)
            try:
                if os.path.getsize(filepath) > chunk_size:
                    print(f"Detected large file: {filepath}")
                    split_file(filepath, chunk_size_mb)
            except:
                pass

def scan_and_combine_all(directory='.'):
    """Scans directory for any split files (.part0) and combines them automatically."""
    for root, dirs, files in os.walk(directory):
        if '.git' in root: continue
        for file in files:
            if file.endswith('.part0'):
                # Original filename
                original_filepath = os.path.join(root, file.replace('.part0', ''))
                combine_file(original_filepath)
