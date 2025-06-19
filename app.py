from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/v1/data/DMARC_Reports", methods=["POST"])
def receive_report():
    data = request.get_json()
    print("📩 קיבלתי דוח:", data)
    return jsonify({"status": "ok"})
