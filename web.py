from flask import Flask, render_template, request, redirect, url_for, session
from func.database import get_global_db
from datetime import datetime, timedelta
from secrets import token_urlsafe

app = Flask(__name__)
app.secret_key = "secretkey" # Cambiar por una clave segura en producción

@app.route("/")
def fairy():
    return render_template("fairy.html", error=request.args.get("error"))

@app.route("/login", methods=["POST"])
def login():
    token = request.form["token"]
    password = request.form["password"]
    db_info = get_global_db(token)
    if db_info is not None:
        if password == db_info[2]:
            bearer = token_urlsafe(32)
            expiration = (datetime.now() + timedelta(seconds=30)).isoformat() # 1800 segundos = 30 minutos #! Importante usar esto para la base de datos xd
            bearers = session.get("bearers", [])
            bearers.append({"bearer": bearer, "expiration": expiration})
            session["bearers"] = bearers  
            return redirect(url_for("inicio", bearer=bearer, token=token))
    return redirect(url_for("fairy", error=True))

@app.route("/inicio")
def inicio():
    bearer = request.args.get("bearer")
    bearers = session.get("bearers", [])
    print(bearers)
    
    now = datetime.now()
    
    valid_bearers = []
    for b in bearers:
        expiration = datetime.fromisoformat(b["expiration"])
        if expiration > now:
            valid_bearers.append(b)
    
    valid = None
    for b in valid_bearers:
        if b["bearer"] == bearer:
            valid = b
            break
        
    if not valid:
        session["bearers"] = valid_bearers
        return redirect(url_for("deny"))
    
    session["bearers"] = valid_bearers
    
    token = request.args.get("token")
    return render_template("inicio.html", token=request.args.get("token"))

@app.route("/deny")
def deny():
    return render_template("deny.html")

if __name__ == "__main__":
    app.run(debug=True)