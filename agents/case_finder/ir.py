import faiss
import numpy as np
from transformers import AutoTokenizer, AutoModel
from common.models import Case
from common.config import Config
from common.security import encrypt_data, decrypt_data
import requests
import json
import os

# Initialize tokenizer and model
tokenizer = AutoTokenizer.from_pretrained(
    "sentence-transformers/all-MiniLM-L6-v2")
model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")

# Initialize FAISS index
dimension = 384
index = faiss.IndexFlatL2(dimension)
cases = []
case_vectors = []


def fetch_courtlistener_cases(query: str) -> list:
    headers = {"Authorization": f"Token {Config.COURTLISTENER_API_KEY}"}
    response = requests.get(
        "https://www.courtlistener.com/api/rest/v4/search/", params={"q": query}, headers=headers)
    if response.status_code != 200:
        return []
    results = response.json().get("results", [])
    return [
        {
            "case_name": r["caseName"],
            "year": int(r["dateFiled"][:4]) if r["dateFiled"] else 0,
            "court": r["court"],
            "snippet": r.get("snippet", ""),
            "full_text": r.get("plain_text", "")
        }
        for r in results
    ]


def load_sample_data():
    global cases, case_vectors
    sample_file = "data/samples/cases.jsonl"
    if os.path.exists(sample_file):
        with open(sample_file, "r") as f:
            cases.extend([Case(**json.loads(line)) for line in f])
    for case in cases:
        inputs = tokenizer(case.snippet, return_tensors="pt",
                           padding=True, truncation=True)
        embedding = model(
            **inputs).last_hidden_state.mean(dim=1).detach().numpy()
        case_vectors.append(embedding)
    if case_vectors:
        index.add(np.vstack(case_vectors))
    # Encrypt index
    with open("data/indexes/cases.faiss", "wb") as f:
        faiss.write_index(index, f)
    with open("data/indexes/cases.json", "w") as f:
        json.dump([case.dict() for case in cases], f)
    with open("data/indexes/cases.key", "w") as f:
        f.write(encrypt_data(json.dumps([case.dict() for case in cases])))


def search_cases(query: str) -> list[Case]:
    # Try CourtListener API
    cl_cases = fetch_courtlistener_cases(query)
    if cl_cases:
        global cases, case_vectors, index
        cases = [Case(**case) for case in cl_cases]
        case_vectors = []
        index = faiss.IndexFlatL2(dimension)
        for case in cases:
            inputs = tokenizer(case.snippet, return_tensors="pt",
                               padding=True, truncation=True)
            embedding = model(
                **inputs).last_hidden_state.mean(dim=1).detach().numpy()
            case_vectors.append(embedding)
        if case_vectors:
            index.add(np.vstack(case_vectors))

    # Load local data if no API results
    if not cases and os.path.exists("data/indexes/cases.key"):
        with open("data/indexes/cases.key", "r") as f:
            decrypted = decrypt_data(f.read())
            cases = [Case(**case) for case in json.loads(decrypted)]
        with open("data/indexes/cases.faiss", "rb") as f:
            index = faiss.read_index(f)

    # Search FAISS index
    inputs = tokenizer(query, return_tensors="pt",
                       padding=True, truncation=True)
    query_vector = model(
        **inputs).last_hidden_state.mean(dim=1).detach().numpy()
    distances, indices = index.search(query_vector, k=2)
    return [cases[i] for i in indices[0] if i < len(cases)]


# Load sample data on startup
load_sample_data()
