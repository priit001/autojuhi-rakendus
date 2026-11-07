from flask import Flask, render_template, request, redirect

app = Flask(__name__)

rides = [
    {"date": "2026-01-01", "km": 50, "income": 25},
    {"date": "2026-01-02", "km": 120, "income": 60},
    {"date": "2026-01-03", "km": 80, "income": 40}
]

@app.route('/')
def index():
    return render_template("index.html")


@app.route('/statistika')
def statistika():
    if not rides:
        total_km = 0
        total_income = 0
        avg_price = 0
    else:
        total_km = sum(r["km"] for r in rides)
        total_income = sum(r["income"] for r in rides)
        avg_price = total_income / total_km if total_km else 0

    return render_template("stats.html",
                           total_km=total_km,
                           total_income=round(total_income, 2),
                           avg_price=round(avg_price, 2))

@app.route('/lisa', methods=['GET', 'POST'])
def lisa():
    if request.method == 'POST':
        date = request.form['date']
        km = float(request.form['km'])
        income = float(request.form['income'])

        rides.append({
            "date": date,
            "km": km,
            "income": income
        })

        return redirect('/statistika')
    else:
        return render_template("add_ride.html")
@app.route('/soidud')
def soidud():
    return render_template("rides.html", rides=rides)
@app.route('/kustuta/<int:index>', methods=['POST'])
def kustuta(index):
    if 0 <= index < len(rides):
        rides.pop(index)
    return redirect('/soidud')
import csv
from flask import make_response

@app.route('/export')
def export():
    # Loome CSV sisu mällu
    output = []
    output.append(["Kuupäev", "Kilomeetrid", "Tulu (€)"])

    for r in rides:
        output.append([r["date"], r["km"], r["income"]])

    # Loome HTTP vastuse CSV failina
    response = make_response("\n".join([",".join(map(str, row)) for row in output]))
    response.headers["Content-Disposition"] = "attachment; filename=soidud.csv"
    response.headers["Content-Type"] = "text/csv"

    return response

if __name__ == "__main__":
    app.run(debug=True)
