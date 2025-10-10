from flask import Flask, render_template, request, redirect, url_for, session
from func.database import get_global_db, update_global_db, insert_db, select_db, update_db
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
            expiration = (datetime.now() + timedelta(seconds=1800)).isoformat() # 1800 segundos = 30 minutos #! Importante usar esto para la base de datos xd
            bearers = session.get("bearers", [])
            bearers.append({"bearer": bearer, "expiration": expiration})
            session["bearers"] = bearers
            if not update_global_db(db_info[0], None, None):
                raise Exception("Error al actualizar token y contraseña en la base de datos global")
            return redirect(url_for("inicio", bearer=bearer, cid=db_info[0]))
    return redirect(url_for("fairy", error=True))

@app.route("/save", methods=["POST"])
def save():
    cid = request.form["cid"]
    prefix = request.form["prefix"]
    log = request.form["log"]
    op_id = request.form["op_id"]
    op_name = request.form["op_name"]
    general = request.form["general"]
    category = request.form["category"]
    member = request.form["member"]
    message = request.form["message"]

    if select_db(cid, "*", "config", "id", 1) is not None:
        update_db(cid, "config", ("id", "setup", "prefix", "log"), (1, 1, prefix, log), "id", 1)
    else:
        insert_db(cid, "config", "id,setup,prefix,log", (1, 1, prefix, log))

    if select_db(cid, "*", "op", "id", op_id) is not None:
        update_db(cid, "op", ("id", "name"), (op_id, op_name), "id", op_id)
    else:
        insert_db(cid, "op", "id,name", (op_id, op_name))

    if select_db(cid, "*", "ticket", "id", 1) is not None:
        update_db(cid, "ticket", ("id", "general", "category", "member", "message"), (1, general, category, member, message), "id", 1)
    else:
        insert_db(cid, "ticket", "id,general,category,member,message", (1, general, category, member, message))

    return redirect(url_for("saved"))

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
    return render_template("inicio.html", cid=request.args.get("cid"))

@app.route("/deny")
def deny():
    return render_template("deny.html")

@app.route("/saved")
def saved():
    return render_template("saved.html")

if __name__ == "__main__":
    app.run(debug=True)