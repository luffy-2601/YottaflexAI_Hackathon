import os
import sys
import shutil
import json

sys.path.insert(0, os.path.abspath("."))
from scripts.generate_data import generate_dataset

def verify_reproducibility(seed: int = 20261022):
    dir_run1 = os.path.join("data", "reproducibility_run1")
    dir_run2 = os.path.join("data", "reproducibility_run2")

    shutil.rmtree(dir_run1, ignore_errors=True)
    shutil.rmtree(dir_run2, ignore_errors=True)

    print(f"Executing Run 1 with Seed {seed}...")
    manifest1 = generate_dataset(scale="starter", seed=seed, output_dir=dir_run1)

    print(f"Executing Run 2 with Seed {seed}...")
    manifest2 = generate_dataset(scale="starter", seed=seed, output_dir=dir_run2)

    files1 = manifest1["files"]
    files2 = manifest2["files"]

    all_matched = True
    print("\n--- Checksum & Count Comparison Table ---")
    print(f"{'Filename':<25} | {'Run 1 SHA256':<16} | {'Run 2 SHA256':<16} | {'Match?':<6}")
    print("-" * 75)

    for fname, meta1 in files1.items():
        meta2 = files2.get(fname)
        if not meta2 or meta1["sha256"] != meta2["sha256"] or meta1["count"] != meta2["count"]:
            all_matched = False
            print(f"{fname:<25} | {meta1['sha256'][:16]} | {meta2['sha256'][:16] if meta2 else 'MISSING'} | FAIL")
        else:
            print(f"{fname:<25} | {meta1['sha256'][:16]} | {meta2['sha256'][:16]} | PASS")

    # Clean up temp dirs
    shutil.rmtree(dir_run1, ignore_errors=True)
    shutil.rmtree(dir_run2, ignore_errors=True)

    if all_matched:
        print("\nSUCCESS: 100% Deterministic Reproducibility Confirmed across all generated files.")
        return 0
    else:
        print("\nFAILURE: Checksums mismatch between identical seed runs.")
        return 1

if __name__ == "__main__":
    sys.exit(verify_reproducibility())
