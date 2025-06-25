from flask import Flask, request, render_template, redirect, url_for, flash, session
import os
import importlib
import tempfile
import shutil
import pandas as pd
import socket

app = Flask(__name__)
app.secret_key = "your_secret_key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FUNCTIONS_DIR = os.path.join(BASE_DIR, "functions")

def list_functions():
    files = []
    for f in os.listdir(FUNCTIONS_DIR):
        if f.endswith(".py") and not f.startswith("__"):
            files.append(f[:-3])
    return files

@app.route("/", methods=["GET", "POST"])
def index():
    functions = list_functions()
    table_html = None
    if request.method == "POST":
        func_name = request.form.get("func_name")
        files = request.files.getlist("input_files")
        if not func_name or not files or files[0].filename == "":
            flash("กรุณาเลือกฟังก์ชันและอัปโหลดไฟล์")
            return redirect(url_for("index"))

        temp_input = tempfile.mkdtemp()
        output_dir = os.path.join(BASE_DIR, f"output_{func_name}")
        os.makedirs(output_dir, exist_ok=True)
        try:
            for f in files:
                f.save(os.path.join(temp_input, f.filename))
            module = importlib.import_module(f"functions.{func_name}")
            module.run(temp_input, output_dir)
            output_files = [f for f in os.listdir(output_dir) if f.endswith((".xlsx", ".csv"))]
            if not output_files:
                flash("ไม่พบไฟล์ผลลัพธ์ใน output")
                return redirect(url_for("index"))
            
            output_files.sort(key=lambda x: os.path.getmtime(os.path.join(output_dir, x)), reverse=True)
            output_fp = os.path.join(output_dir, output_files[0])  # <-- ต้องเป็น path

            if output_fp.endswith(".xlsx"):
                df = pd.read_excel(output_fp)
            else:
                df = pd.read_csv(output_fp)
            table_html = df.to_html(classes="result-table", index=False, border=0)
            flash("ประมวลผลสำเร็จ")
            return render_template("result.html", table_html=table_html)
        except Exception as e:
            flash(f"เกิดข้อผิดพลาด: {e}")
            return redirect(url_for("index"))
        finally:
            shutil.rmtree(temp_input)
    return render_template("index.html", functions=functions)

@app.route("/result")
def result():
    table_html = session.get('table_html')
    if not table_html:
        flash("ไม่พบข้อมูลผลลัพธ์")
        return redirect(url_for("index"))
    return render_template("result.html", table_html=table_html)

if __name__ == "__main__":
    ip= socket.gethostbyname(socket.gethostname())
    app.run(debug=True, host='0.0.0.0', port=80)
    
# To run the app, use the command:
# python app.py 
# http://127.0.0.1:80
# or http://<your-ip>:80/ if running on a server