from flask import Flask, request, render_template, redirect, url_for, flash, session, send_file
import os
import importlib
import tempfile
import shutil
import pandas as pd
import socket
from functions.PNP_CHANG_TYPE import lookup_last_type


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
    download_link = None
    if request.method == "POST":
        func_name = request.form.get("func_name")
        files = request.files.getlist("input_files")
        show_table = request.form.get("show_table") == "on"
        if not func_name or not files or files[0].filename == "":
            flash("กรุณาเลือกฟังก์ชันและอัปโหลดไฟล์")
            return redirect(url_for("index"))

        temp_input = tempfile.mkdtemp()
        output_dir = os.path.join(BASE_DIR, f"output_{func_name}")
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
            output_fp = os.path.join(output_dir, output_files[0])
            download_link = url_for("download_file", func_name=func_name, filename=output_files[0])

            # เงื่อนไขแสดงผล
            if show_table:
                if output_fp.endswith(".xlsx"):
                    df = pd.read_excel(output_fp)
                else:
                    df = pd.read_csv(output_fp)
                table_html = df.to_html(classes="result-table", index=False, border=0)
                flash("ประมวลผลสำเร็จ")
                return render_template("result.html", table_html=table_html, download_link=download_link)
            else:
                flash("ประมวลผลสำเร็จ สามารถดาวน์โหลดไฟล์ผลลัพธ์ได้")
                return render_template("result.html", table_html=None, download_link=download_link)
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

@app.route("/download/<func_name>/<filename>")
def download_file(func_name, filename):
    output_dir = os.path.join(BASE_DIR, f"output_{func_name}")
    file_path = os.path.join(output_dir, filename)
    return send_file(file_path, as_attachment=True)

#เป็นฟังก์ชันสำหรับค้นหา Last Type ในไฟล์ PNP_CHANG_TYPE
# ใช้สำหรับอัปโหลดไฟล์ bom_no และค้นหา Last Type จากไฟล์
@app.route("/lookup_last_type", methods=["GET", "POST"]) 
def lookup_last_type_route():
    table_html = None
    download_link = None
    if request.method == "POST":
        file = request.files.get("bom_file")
        if not file or file.filename == "":
            flash("กรุณาอัปโหลดไฟล์ที่มีคอลัมน์ bom_no")
            return redirect(url_for("lookup_last_type_route"))
        
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, file.filename)
        file.save(file_path)
        try:
            output_dir = os.path.join(BASE_DIR, "output_PNP_CHANG_TYPE")
            df_result = lookup_last_type(file_path, output_dir)
            if df_result is not None:
                table_html = df_result.to_html(classes="result-table", index=False, border=0)
                # สร้างโฟลเดอร์ output_lookup_last_type ถ้ายังไม่มี
                download_dir = os.path.join(BASE_DIR, "output_lookup_last_type")
                os.makedirs(download_dir, exist_ok=True)
                # บันทึกไฟล์ Excel
                result_path = os.path.join(download_dir, "last_type_result.xlsx")
                df_result.to_excel(result_path, index=False)
                # สร้างลิงก์ดาวน์โหลด
                download_link = url_for('download_file', func_name='lookup_last_type', filename='last_type_result.xlsx')
            else:
                flash("ไม่พบข้อมูลที่ตรงกัน")
        except Exception as e:
            flash(f"เกิดข้อผิดพลาด: {e}")
        finally:
            shutil.rmtree(temp_dir)
    else:
        download_link = None
    return render_template("lookup_last_type.html", table_html=table_html, download_link=download_link)

if __name__ == "__main__":
    ip= socket.gethostbyname(socket.gethostname())
    app.run(debug=True, host='0.0.0.0', port=80)

# http://<your-ip>:80/ if running on a server
# Make sure to have the functions directory with Python files containing a run function
# Version 1.3