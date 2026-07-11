import os
import json
import shutil

ANOMALY_STORAGE_ROOT = "anomaly_storage"

def purge_all_filtered():
    if not os.path.isdir(ANOMALY_STORAGE_ROOT):
        print("No anomaly storage found.")
        return

    deleted = 0
    for session_name in os.listdir(ANOMALY_STORAGE_ROOT):
        session_path = os.path.join(ANOMALY_STORAGE_ROOT, session_name)
        if not os.path.isdir(session_path):
            continue
            
        for anom_name in os.listdir(session_path):
            anom_dir = os.path.join(session_path, anom_name)
            if not anom_name.startswith("anomaly_") or not os.path.isdir(anom_dir):
                continue
                
            meta_path = os.path.join(anom_dir, "metadata.json")
            if os.path.isfile(meta_path):
                try:
                    with open(meta_path) as f:
                        meta = json.load(f)
                    if meta.get("status") == "false_positive":
                        shutil.rmtree(anom_dir)
                        deleted += 1
                        print(f"Deleted false positive: {anom_dir}")
                except Exception as e:
                    print(f"Error reading {meta_path}: {e}")
                    
    print(f"\nPurge complete. Deleted {deleted} false positive items.")

if __name__ == "__main__":
    purge_all_filtered()
