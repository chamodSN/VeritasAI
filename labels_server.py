from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/case_types')
def case_types():
    return jsonify([
        "criminal", "civil", "tax", "intellectual property",
        "contract", "labor", "family", "property", "bankruptcy",
        "administrative", "constitutional", "environmental", "immigration"
    ])

@app.route('/topics')
def topics():
    return jsonify([
        "cyber fraud", "data privacy", "theft", "contract dispute",
        "intellectual property", "bribery", "tax evasion",
        "employment discrimination", "breach of contract", "consumer protection",
        "environmental regulation", "immigration policy", "constitutional rights"
    ])

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)  # Disable debug for production