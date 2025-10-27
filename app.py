# app.py
from flask import Flask, render_template, request, jsonify
from crawler import search_amazon, search_flipkart, search_myntra, search_meesho

app = Flask(__name__)

# Toggle headless for Selenium scrapers here
HEADLESS = True

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/compare", methods=["POST"])
def compare():
    data = request.json
    product = data.get("product", "").strip()
    if not product:
        return jsonify({"error": "No product provided"}), 400

    # Run scrapers synchronously (fast for single requests; can be improved later)
    results = []
    a = search_amazon(product, headless=HEADLESS)
    f = search_flipkart(product, headless=HEADLESS)
    m = search_myntra(product, headless=HEADLESS)
    me = search_meesho(product, headless=HEADLESS)

    results = [a, f, m, me]
    # Prepare chart data: keep only those with numeric price
    chart = []
    table = []
    for r in results:
        table.append(r)
        if r["price"] is not None:
            chart.append({"store": r["store"], "price": r["price"]})

    return jsonify({"table": table, "chart": chart})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
