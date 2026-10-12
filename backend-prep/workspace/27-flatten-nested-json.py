"""27. Flatten nested JSON to CSV and back

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import csv
import io
import re
from typing import Any

INDEX = re.compile(r"0|[1-9][0-9]*")


def flatten(obj: dict, sep: str = ".") -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise TypeError(f"flatten expects a dict, got {type(obj).__name__}")
    
    out = {}
    
    def walk(value, prefix):
        if isinstance(value, dict):
            for key, child in value.items():
                
                if not isinstance(key,str) or not key or sep in key:
                    raise ValueError(f"key {key!r} is empty or contains {sep!r}")
                
                walk(child, f"{prefix}{sep}{key}" if prefix else key)
                
        elif isinstance(value, list):
            for i, child in enumerate(value):
                walk(child, f"{prefix}{sep}{i}")
        
        else:
            out[prefix] = value
        
    
    walk(obj,"")
    return out
                
           

def to_csv_text(records: list[dict], sep: str = ".") -> str:
    raise NotImplementedError


def unflatten(flat: dict[str, Any], sep: str = ".") -> dict:
    raise NotImplementedError


if __name__ == "__main__":
    from problem_api import load_tasks

    tasks = load_tasks()
    print(flatten(tasks[0]))
    print()
    print(to_csv_text(tasks))
