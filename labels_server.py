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


@app.route('/legal_words')
def legal_words():
    return jsonify([
        '11', '12', '13', '15', 'subpoena', 'substance', 'test', 'testify', 'testimony', 'the', 'time', 'title', 'to', 'toll', 'tort', 'transcript', 'transfer', 'transportation', 'treatment', 'trial', 'trustee', 'typing', 'u', 'uncared', 'unconditional', 'undersecured', 'undue', 'unit', 'united', 'unlawful', 'unliquidated', 'unscheduled', 'unsecured', 'uns', 'uphold', 'vacate', 'venue', 'verdict', 'victim', 'violation', 'violence', 'visitation', 'voir', 'voluntary', 'wage', 'warrant', 'with', 'withholding', 'without', 'witness', 'writ'
    ])


if __name__ == '__main__':
    # Disable debug for production
    app.run(host='127.0.0.1', port=5000, debug=False)
