import os
import time
import pytest
import pandas as pd
import tempfile
from app.services.excel_service import excel_service

def test_benchmark_100k_csv():
    """Benchmark reading and querying a 100k row CSV file."""
    # 1. Generate 100k row CSV
    num_rows = 100000
    data = {
        "ID": range(num_rows),
        "Name": [f"Name_{i}" for i in range(num_rows)],
        "Value": [i * 1.5 for i in range(num_rows)],
        "Category": ["A", "B", "C", "D"] * (num_rows // 4)
    }
    df = pd.DataFrame(data)
    
    # Create temp file in project's docs directory to avoid DocAccessError
    docs_dir = os.path.join(os.getcwd(), "docs")
    os.makedirs(docs_dir, exist_ok=True)
    temp_dir = os.path.join(docs_dir, "temp_test")
    os.makedirs(temp_dir, exist_ok=True)
    
    with tempfile.NamedTemporaryFile(suffix=".csv", dir=temp_dir, delete=False) as tmp:
        csv_path = tmp.name
        df.to_csv(csv_path, index=False)
    
    try:
        # 2. Benchmark Profile
        # Pass root_dir to help resolve
        start = time.time()
        profile_res = excel_service.profile(csv_path, root_dir=docs_dir, allow_roots=[docs_dir])
        profile_time = time.time() - start
        print(f"\nCSV Profile time (100k rows): {profile_time:.4f}s")
        assert profile_res["ok"] is True
        
        # 3. Benchmark Read (with truncation)
        start = time.time()
        read_res = excel_service.read(csv_path, root_dir=docs_dir, allow_roots=[docs_dir])
        read_time = time.time() - start
        print(f"CSV Read time (truncation to {excel_service.read_limit}): {read_time:.4f}s")
        assert read_res["ok"] is True
        assert read_res["is_truncated"] is True
        assert len(read_res["data"]) == excel_service.read_limit
        
        # 4. Benchmark Query (SQL aggregation)
        start = time.time()
        query = "SELECT Category, SUM(Value) as Total FROM excel_data GROUP BY Category ORDER BY Total DESC"
        query_res = excel_service.query(csv_path, query, root_dir=docs_dir, allow_roots=[docs_dir])
        query_time = time.time() - start
        print(f"CSV Query time (Aggregation on 100k rows): {query_time:.4f}s")
        assert query_res["ok"] is True
        assert len(query_res["data"]) == 4
        
    finally:
        if os.path.exists(csv_path):
            os.remove(csv_path)
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)

def test_benchmark_100k_xlsx():
    """Benchmark reading and querying a 100k row XLSX file (Read-only mode)."""
    # Note: Generating a 100k row XLSX is much slower than CSV. 
    # We'll do it once for this benchmark.
    num_rows = 100000
    data = {
        "ID": range(num_rows),
        "Name": [f"Name_{i}" for i in range(num_rows)],
        "Value": [i * 1.5 for i in range(num_rows)],
        "Category": ["A", "B", "C", "D"] * (num_rows // 4)
    }
    df = pd.DataFrame(data)
    
    docs_dir = os.path.join(os.getcwd(), "docs")
    os.makedirs(docs_dir, exist_ok=True)
    temp_dir = os.path.join(docs_dir, "temp_test")
    os.makedirs(temp_dir, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".xlsx", dir=temp_dir, delete=False) as tmp:
        xlsx_path = tmp.name
        # Use openpyxl engine for writing
        df.to_excel(xlsx_path, index=False, engine='openpyxl')
    
    try:
        # 2. Benchmark Profile
        start = time.time()
        profile_res = excel_service.profile(xlsx_path, root_dir=docs_dir, allow_roots=[docs_dir])
        profile_time = time.time() - start
        print(f"\nXLSX Profile time (100k rows): {profile_time:.4f}s")
        assert profile_res["ok"] is True
        
        # 3. Benchmark Read (with truncation)
        start = time.time()
        read_res = excel_service.read(xlsx_path, root_dir=docs_dir, allow_roots=[docs_dir])
        read_time = time.time() - start
        print(f"XLSX Read time (truncation to {excel_service.read_limit}): {read_time:.4f}s")
        assert read_res["ok"] is True
        assert read_res["is_truncated"] is True
        
        # 4. Benchmark Query (SQL aggregation)
        start = time.time()
        query = "SELECT Category, AVG(Value) as AvgValue FROM excel_data GROUP BY Category"
        query_res = excel_service.query(xlsx_path, query, root_dir=docs_dir, allow_roots=[docs_dir])
        query_time = time.time() - start
        print(f"XLSX Query time (Aggregation on 100k rows): {query_time:.4f}s")
        assert query_res["ok"] is True
        
    finally:
        if os.path.exists(xlsx_path):
            os.remove(xlsx_path)
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)
