import json
import csv
import os

def save_items(items: list, output_config: dict):
    if not items:
        print("No items to save.")
        return

    fmt = output_config.get("format", "csv")
    filename = output_config.get("file", f"output.{fmt}")

    if fmt == "json":
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    elif fmt == "csv":
        keys = []
        for item in items:
            for k in item.keys():
                if k not in keys:
                    keys.append(k)
        # Always overwrite — data comes from cache, all items are in memory
        with open(filename, 'w', encoding='utf-8', newline='') as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
            dict_writer.writeheader()
            dict_writer.writerows(items)
    else:
        raise ValueError(f"Unsupported output format: {fmt}")
