
# ============================================================
# WARMINDO BY DHOO_CO
# Copyright (c) 2026 dhoo_co. All rights reserved.
# Original project / source code branding watermark.
# Unauthorized redistribution or removal of this notice is not permitted.
# ============================================================


from store_config import load_store_settings, save_store_settings
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3, os, csv, io
from datetime import datetime, date

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "data", "warmindo.db")
EXPORT_DIR = os.path.join(BASE, "exports")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = "fnb-v8-2-change-this-secret"

def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def rupiah(n):
    return "Rp {:,.0f}".format(float(n or 0)).replace(",", ".")

@app.template_filter("rupiah")
def rupiah_filter(n):
    return rupiah(n)

@app.template_filter("qty")
def qty_filter(n):
    x = float(n or 0)
    return f"{x:g}"

def init_db():
    c = db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'owner'
    );
    CREATE TABLE IF NOT EXISTS settings(
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'Aktif'
    );
    CREATE TABLE IF NOT EXISTS ingredients(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        unit TEXT NOT NULL,
        stock REAL NOT NULL DEFAULT 0,
        min_stock REAL NOT NULL DEFAULT 0,
        cost REAL NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS bom(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        ingredient_id INTEGER NOT NULL,
        qty REAL NOT NULL,
        UNIQUE(product_id, ingredient_id),
        FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE,
        FOREIGN KEY(ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trx_no TEXT UNIQUE NOT NULL,
        created_at TEXT NOT NULL,
        subtotal REAL NOT NULL,
        discount REAL NOT NULL DEFAULT 0,
        total REAL NOT NULL,
        payment REAL NOT NULL DEFAULT 0,
        change_amount REAL NOT NULL DEFAULT 0,
        payment_method TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS transaction_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        qty INTEGER NOT NULL,
        price REAL NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY(transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
        FOREIGN KEY(product_id) REFERENCES products(id)
    );
    CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        amount REAL NOT NULL,
        created_at TEXT NOT NULL
    );
    """)
    if not c.execute("SELECT 1 FROM users LIMIT 1").fetchone():
        c.execute("INSERT INTO users(username,password,role) VALUES('admin','admin','owner')")
    defaults = {
        "store_name":"WARMINDO BY DHOO_CO",
        "store_address":"Alamat toko",
        "store_phone":"",
        "receipt_footer":"Terima kasih, sampai jumpa!",
    }
    for k,v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",(k,v))
    if not c.execute("SELECT 1 FROM products LIMIT 1").fetchone():
        products = [
            ("Ayam Geprek","Makanan",18000),("Chicken Rice Bowl","Makanan",22000),
            ("Nasi Goreng","Makanan",15000),("Es Teh","Minuman",5000),
            ("Kopi Susu","Minuman",12000),("Matcha Latte","Minuman",15000),
            ("French Fries","Snack",10000),
        ]
        c.executemany("INSERT INTO products(name,category,price) VALUES(?,?,?)",products)
    if not c.execute("SELECT 1 FROM ingredients LIMIT 1").fetchone():
        ingredients = [
            ("Ayam","pcs",50,10,9000),("Beras","kg",12,3,15000),("Telur","pcs",48,12,2500),
            ("Minyak","liter",10,2,18000),("Gula","kg",5,1,16000),("Teh","gram",1000,200,120),
            ("Kopi","gram",1000,200,180),("Susu","liter",10,2,18000),("Kentang","kg",8,2,14000),
            ("Matcha","gram",500,100,500),("Cup","pcs",100,20,700)
        ]
        c.executemany("INSERT INTO ingredients(name,unit,stock,min_stock,cost) VALUES(?,?,?,?,?)",ingredients)
    if not c.execute("SELECT 1 FROM bom LIMIT 1").fetchone():
        p={r["name"]:r["id"] for r in c.execute("SELECT id,name FROM products")}
        i={r["name"]:r["id"] for r in c.execute("SELECT id,name FROM ingredients")}
        rows=[
            (p["Ayam Geprek"],i["Ayam"],1),(p["Ayam Geprek"],i["Beras"],.15),(p["Ayam Geprek"],i["Minyak"],.03),
            (p["Chicken Rice Bowl"],i["Ayam"],1),(p["Chicken Rice Bowl"],i["Beras"],.15),(p["Chicken Rice Bowl"],i["Cup"],1),
            (p["Nasi Goreng"],i["Beras"],.15),(p["Nasi Goreng"],i["Telur"],1),(p["Nasi Goreng"],i["Minyak"],.02),
            (p["Es Teh"],i["Teh"],8),(p["Es Teh"],i["Gula"],.015),(p["Es Teh"],i["Cup"],1),
            (p["Kopi Susu"],i["Kopi"],15),(p["Kopi Susu"],i["Susu"],.12),(p["Kopi Susu"],i["Gula"],.01),(p["Kopi Susu"],i["Cup"],1),
            (p["Matcha Latte"],i["Matcha"],8),(p["Matcha Latte"],i["Susu"],.15),(p["Matcha Latte"],i["Gula"],.01),(p["Matcha Latte"],i["Cup"],1),
            (p["French Fries"],i["Kentang"],.15),(p["French Fries"],i["Minyak"],.03)
        ]
        c.executemany("INSERT INTO bom(product_id,ingredient_id,qty) VALUES(?,?,?)",rows)
    c.commit(); c.close()

def logged():
    return "user_id" in session

def require_login():
    if not logged():
        return redirect(url_for("login"))
    return None

@app.context_processor
def common():
    c=db()
    s={r["key"]:r["value"] for r in c.execute("SELECT key,value FROM settings")}
    c.close()
    return {"store":s,"username":session.get("username"),"role":session.get("role")}

@app.route("/", methods=["GET"])
def index():
    return redirect(url_for("dashboard") if logged() else url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        u=request.form.get("username","").strip()
        p=request.form.get("password","")
        c=db(); r=c.execute("SELECT * FROM users WHERE username=? AND password=?",(u,p)).fetchone(); c.close()
        if r:
            session.update(user_id=r["id"],username=r["username"],role=r["role"])
            return redirect(url_for("dashboard"))
        flash("Username atau password salah.","error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    r=require_login()
    if r:return r
    today=date.today().isoformat()
    c=db()
    omzet=c.execute("SELECT COALESCE(SUM(total),0) v FROM transactions WHERE date(created_at)=?",(today,)).fetchone()["v"]
    trx=c.execute("SELECT COUNT(*) v FROM transactions WHERE date(created_at)=?",(today,)).fetchone()["v"]
    low=c.execute("SELECT COUNT(*) v FROM ingredients WHERE stock<=min_stock").fetchone()["v"]
    top=c.execute("""SELECT p.name,SUM(ti.qty) qty FROM transaction_items ti
        JOIN products p ON p.id=ti.product_id JOIN transactions t ON
    + CategoryInfo          : ObjectNotFound: (git:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
PS C:\Users\LENOVO\OneDrive\Desktop\Warmindo By dhoo_coV7> 
.id=ti.transaction_id
        WHERE date(t.created_at)=? GROUP BY p.id ORDER BY qty DESC LIMIT 5""",(today,)).fetchall()
    c.close()
    return render_template("dashboard.html",omzet=omzet,trx=trx,low=low,top=top)

@app.route("/pos")
def pos():
    r=require_login()
    if r:return r
    c=db()
    products=c.execute("SELECT * FROM products WHERE status='Aktif' ORDER BY category,name").fetchall()
    c.close()
    return render_template("pos.html",products=products)

@app.route("/api/check-stock",methods=["POST"])
def check_stock():
    if not logged(): return jsonify(ok=False,error="Login diperlukan"),401
    items=request.get_json().get("items",[])
    c=db()
    needs={}
    problems=[]
    for it in items:
        rows=c.execute("""SELECT b.ingredient_id,b.qty,i.name,i.unit,i.stock
                          FROM bom b JOIN ingredients i ON i.id=b.ingredient_id
                          WHERE b.product_id=?""",(it["id"],)).fetchall()
        for x in rows:
            needs[x["ingredient_id"]]=needs.get(x["ingredient_id"],0)+x["qty"]*int(it["qty"])
    for iid,n in needs.items():
        x=c.execute("SELECT name,unit,stock FROM ingredients WHERE id=?",(iid,)).fetchone()
        if x and x["stock"] < n:
            problems.append({"name":x["name"],"unit":x["unit"],"stock":x["stock"],"need":n})
    c.close()
    return jsonify(ok=not problems,problems=problems)

@app.route("/checkout",methods=["POST"])
def checkout():
    r=require_login()
    if r:return r
    data=request.get_json()
    items=data.get("items",[])
    discount=float(data.get("discount") or 0)
    method=data.get("method","Cash")
    payment=float(data.get("payment") or 0)
    if not items:return jsonify(ok=False,error="Keranjang kosong")
    c=db()
    try:
        ids=[int(x["id"]) for x in items]
        placeholders=",".join("?"*len(ids))
        rows=c.execute(f"SELECT * FROM products WHERE id IN ({placeholders})",ids).fetchall()
        byid={r["id"]:r for r in rows}
        subtotal=sum(byid[int(x["id"])]["price"]*int(x["qty"]) for x in items)
        total=max(0,subtotal-discount)
        if method!="Cash":
            payment=total
        if payment < total:
            return jsonify(ok=False,error=f"Pembayaran kurang {rupiah(total-payment)}")
        # calculate and lock logical stock requirement before modifying
        needs={}
        for it in items:
            bomrows=c.execute("""SELECT b.ingredient_id,b.qty,i.name,i.unit,i.stock
                                FROM bom b JOIN ingredients i ON i.id=b.ingredient_id
                                WHERE b.product_id=?""",(int(it["id"]),)).fetchall()
            for b in bomrows:
                needs[b["ingredient_id"]]=needs.get(b["ingredient_id"],0)+b["qty"]*int(it["qty"])
        for iid,n in needs.items():
            x=c.execute("SELECT name,unit,stock FROM ingredients WHERE id=?",(iid,)).fetchone()
            if x["stock"] < n:
                return jsonify(ok=False,error=f"Stok {x['name']} tidak cukup. Tersedia {x['stock']:g} {x['unit']}, dibutuhkan {n:g} {x['unit']}.")
        now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        no="TRX-"+datetime.now().strftime("%Y%m%d%H%M%S%f")[:17]
        change=payment-total
        cur=c.cursor()
        cur.execute("""INSERT INTO transactions(trx_no,created_at,subtotal,discount,total,payment,change_amount,payment_method)
                       VALUES(?,?,?,?,?,?,?,?)""",(no,now,subtotal,discount,total,payment,change,method))
        tid=cur.lastrowid
        for it in items:
            p=byid[int(it["id"])]; q=int(it["qty"])
            cur.execute("""INSERT INTO transaction_items(transaction_id,product_id,qty,price,subtotal)
                           VALUES(?,?,?,?,?)""",(tid,p["id"],q,p["price"],p["price"]*q))
        for iid,n in needs.items():
            cur.execute("UPDATE ingredients SET stock=stock-? WHERE id=?",(n,iid))
        c.commit()
        return jsonify(ok=True,url=url_for("receipt",no=no))
    except Exception as e:
        c.rollback()
        return jsonify(ok=False,error=str(e))
    finally:
        c.close()

@app.route("/receipt/<no>")
def receipt(no):
    r=require_login()
    if r:return r
    c=db()
    t=c.execute("SELECT * FROM transactions WHERE trx_no=?",(no,)).fetchone()
    if not t:
        c.close(); return "Not found",404
    items=c.execute("""SELECT ti.*,p.name FROM transaction_items ti JOIN products p ON p.id=ti.product_id
                       WHERE ti.transaction_id=?""",(t["id"],)).fetchall()
    c.close()
    return render_template("receipt.html",t=t,items=items)

@app.route("/products",methods=["GET","POST"])
def products():
    r=require_login()
    if r:return r
    c=db()
    if request.method=="POST":
        pid=request.form.get("id")
        vals=(request.form["name"].strip(),request.form["category"],float(request.form["price"]),request.form.get("status","Aktif"))
        if pid:
            c.execute("UPDATE products SET name=?,category=?,price=?,status=? WHERE id=?",(*vals,int(pid)))
        else:
            c.execute("INSERT INTO products(name,category,price,status) VALUES(?,?,?,?)",vals)
        c.commit()
    rows=c.execute("SELECT * FROM products ORDER BY category,name").fetchall(); c.close()
    return render_template("products.html",products=rows)

@app.route("/products/delete/<int:pid>",methods=["POST"])
def product_delete(pid):
    r=require_login()
    if r:return r
    c=db(); c.execute("DELETE FROM products WHERE id=?",(pid,)); c.commit(); c.close()
    return redirect(url_for("products"))

@app.route("/stock",methods=["GET","POST"])
def stock():
    r=require_login()
    if r:return r
    c=db()
    if request.method=="POST":
        action=request.form.get("action")
        if action=="save":
            iid=request.form.get("id")
            vals=(request.form["name"].strip(),request.form["unit"],float(request.form["stock"]),float(request.form["min_stock"]),float(request.form["cost"]))
            if iid:c.execute("UPDATE ingredients SET name=?,unit=?,stock=?,min_stock=?,cost=? WHERE id=?",(*vals,int(iid)))
            else:c.execute("INSERT INTO ingredients(name,unit,stock,min_stock,cost) VALUES(?,?,?,?,?)",vals)
        elif action in ("in","out"):
            iid=int(request.form["id"]); q=float(request.form["qty"])
            if q<0: q=0
            if action=="in": c.execute("UPDATE ingredients SET stock=stock+? WHERE id=?",(q,iid))
            else:
                row=c.execute("SELECT stock FROM ingredients WHERE id=?",(iid,)).fetchone()
                if row and row["stock"]-q >= 0: c.execute("UPDATE ingredients SET stock=stock-? WHERE id=?",(q,iid))
                else: flash("Stok tidak boleh menjadi negatif.","error")
        c.commit()
    rows=c.execute("SELECT * FROM ingredients ORDER BY name").fetchall(); c.close()
    return render_template("stock.html",ingredients=rows)

@app.route("/stock/delete/<int:iid>",methods=["POST"])
def stock_delete(iid):
    r=require_login()
    if r:return r
    c=db(); c.execute("DELETE FROM ingredients WHERE id=?",(iid,)); c.commit(); c.close()
    return redirect(url_for("stock"))

@app.route("/recipes",methods=["GET","POST"])
def recipes():
    r=require_login()
    if r:return r
    c=db()
    if request.method=="POST":
        pid=int(request.form["product_id"]); iid=int(request.form["ingredient_id"]); q=float(request.form["qty"])
        c.execute("""INSERT INTO bom(product_id,ingredient_id,qty) VALUES(?,?,?)
                     ON CONFLICT(product_id,ingredient_id) DO UPDATE SET qty=excluded.qty""",(pid,iid,q))
        c.commit()
    products=c.execute("SELECT * FROM products ORDER BY name").fetchall()
    ingredients=c.execute("SELECT * FROM ingredients ORDER BY name").fetchall()
    rows=c.execute("""SELECT b.id,b.qty,p.name product,i.name ingredient,i.unit FROM bom b
                      JOIN products p ON p.id=b.product_id JOIN ingredients i ON i.id=b.ingredient_id
                      ORDER BY p.name,i.name""").fetchall()
    c.close()
    return render_template("recipes.html",products=products,ingredients=ingredients,rows=rows)

@app.route("/recipes/delete/<int:bid>",methods=["POST"])
def recipe_delete(bid):
    r=require_login()
    if r:return r
    c=db(); c.execute("DELETE FROM bom WHERE id=?",(bid,)); c.commit(); c.close()
    return redirect(url_for("recipes"))

@app.route("/monitor")
def monitor():
    r=require_login()
    if r:return r
    c=db(); rows=c.execute("SELECT * FROM ingredients ORDER BY stock<=min_stock DESC,name").fetchall(); c.close()
    return render_template("monitor.html",ingredients=rows)

@app.route("/finance")
def finance():
    r=require_login()
    if r:return r
    c=db()
    omzet=c.execute("SELECT COALESCE(SUM(total),0) v FROM transactions").fetchone()["v"]
    expense=c.execute("SELECT COALESCE(SUM(amount),0) v FROM expenses").fetchone()["v"]
    methods=c.execute("SELECT payment_method method,COUNT(*) cnt,COALESCE(SUM(total),0) total FROM transactions GROUP BY payment_method ORDER BY method").fetchall()
    expenses=c.execute("SELECT * FROM expenses ORDER BY id DESC LIMIT 30").fetchall()
    c.close()
    return render_template("finance.html",omzet=omzet,expense=expense,methods=methods,expenses=expenses)

@app.route("/expense",methods=["POST"])
def expense():
    r=require_login()
    if r:return r
    c=db(); c.execute("INSERT INTO expenses(title,category,amount,created_at) VALUES(?,?,?,?)",
                       (request.form["title"],request.form["category"],float(request.form["amount"]),datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    c.commit(); c.close()
    return redirect(url_for("finance"))

@app.route("/reports")
def reports():
    r=require_login()
    if r:return r
    c=db()
    rows=c.execute("""SELECT date(created_at) day,COUNT(*) trx,COALESCE(SUM(total),0) omzet
                      FROM transactions GROUP BY date(created_at) ORDER BY day DESC LIMIT 30""").fetchall()

    details=c.execute("""
        SELECT t.id,t.trx_no,t.created_at,t.total,t.payment_method,
               GROUP_CONCAT(p.name || ' × ' || ti.qty, ', ') AS items
        FROM transactions t
        JOIN transaction_items ti ON ti.transaction_id=t.id
        JOIN products p ON p.id=ti.product_id
        GROUP BY t.id
        ORDER BY t.created_at DESC
        LIMIT 100
    """).fetchall()
    c.close()
    return render_template("reports.html",rows=rows,details=details)

@app.route("/settings",methods=["GET","POST"])
def settings():
    r=require_login()
    if r:return r
    c=db()
    if request.method=="POST":
        action=request.form.get("action","store")
        if action=="store":
            for k in ("store_name","store_owner","store_address","store_phone","store_qris","receipt_footer"):
                c.execute("""INSERT INTO settings(key,value) VALUES(?,?)
                             ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                          (k,request.form.get(k,"").strip()))
            flash("Identitas toko berhasil disimpan.","success")
        elif action=="password":
            old=request.form.get("old_password",""); new=request.form.get("new_password","")
            u=c.execute("SELECT password FROM users WHERE id=?",(session["user_id"],)).fetchone()
            if not new: flash("Password baru tidak boleh kosong.","error")
            elif not u or u["password"]!=old: flash("Password lama salah.","error")
            else:
                c.execute("UPDATE users SET password=? WHERE id=?",(new,session["user_id"]))
                flash("Password berhasil diganti.","success")
        c.commit()
    s={r["key"]:r["value"] for r in c.execute("SELECT key,value FROM settings")}
    c.close()
    return render_template("settings.html",s=s)

@app.route("/api/store-settings",methods=["GET","POST"])
def api_store_settings():
    r=require_login()
    if r:return jsonify(ok=False,error="Login diperlukan"),401
    c=db()
    if request.method=="POST":
        payload=request.get_json(silent=True) or {}
        for k in ("store_name","store_owner","store_address","store_phone","store_qris","receipt_footer"):
            if k in payload:
                c.execute("""INSERT INTO settings(key,value) VALUES(?,?)
                             ON CONFLICT(key) DO UPDATE SET value=excluded.value""",(k,str(payload[k])))
        c.commit()
    s={row["key"]:row["value"] for row in c.execute("SELECT key,value FROM settings")}
    c.close(); return jsonify(ok=True,store=s)

@app.route("/game")
def game():
    r=require_login()
    if r:return r
    return render_template("game.html")

@app.route("/export/<kind>")
def export_csv(kind):
    r=require_login()
    if r:return r
    c=db()
    if kind=="stock":
        rows=c.execute("SELECT name,unit,stock,min_stock,cost FROM ingredients ORDER BY name").fetchall()
        head=["name","unit","stock","min_stock","cost"]
    else:
        rows=c.execute("SELECT trx_no,created_at,total,payment,change_amount,payment_method FROM transactions ORDER BY id DESC").fetchall()
        head=["trx_no","created_at","total","payment","change_amount","payment_method"]
    c.close()
    path=os.path.join(EXPORT_DIR,f"{kind}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    with open(path,"w",newline="",encoding="utf-8-sig") as f:
        w=csv.writer(f); w.writerow(head)
        for r in rows:w.writerow([r[h] for h in head])
    from flask import send_file
    return send_file(path,as_attachment=True)

if __name__=="__main__":
    init_db()
    app.run(host="0.0.0.0",port=5000,debug=True)

PROJECT_OWNER = "dhoo_co / Warmindo By dhoo_co"


# --- V9 Store Configuration API ---
@app.get("/api/store-settings")
def api_get_store_settings():
    return load_store_settings()

@app.post("/api/store-settings")
def api_save_store_settings():
    from flask import request, jsonify
    payload = request.get_json(silent=True) or {}
    return jsonify(save_store_settings(payload))

WARMINDO_V9 = True
PROJECT_OWNER = "dhoo_co"

PROJECT_VERSION="V10"
PROJECT_OWNER="dhoo_co"
PROJECT_COPYRIGHT="Copyright (c) 2026 dhoo_co. All rights reserved."
