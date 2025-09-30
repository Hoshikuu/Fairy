from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

@app.route("/")
def fairy():
    return render_template("fairy.html", error=request.args.get("error"))

@app.route("/login", methods=["POST"])
def login():
    token = request.form["token"]

    if token == "12345":
        return redirect(url_for("inicio"))
    else:
        return redirect(url_for("fairy", error=True))

@app.route("/inicio")
def inicio():
    return render_template("inicio.html")

if __name__ == "__main__":
    app.run(debug=True)