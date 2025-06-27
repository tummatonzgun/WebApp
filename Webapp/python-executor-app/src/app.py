from flask import Flask, request, render_template, redirect, url_for, flash, session, send_file
import os
import importlib
import tempfile
import shutil
import pandas as pd
import socket
import datetime
from functions.PNP_CHANG_TYPE import lookup_last_type

app = Flask(__name__)
app.secret_key = "your_secret_key_change_this_in_production"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FUNCTIONS_DIR = os.path.join(BASE_DIR, "functions")

def list_functions():
    """List all available function modules"""
    files = []
    try:
        for f in os.listdir(FUNCTIONS_DIR):
            if f.endswith(".py") and not f.startswith("__"):
                files.append(f[:-3])
    except Exception as e:
        print(f"Error listing functions: {e}")
    return files

@app.route("/", methods=["GET", "POST"])
def index():
    functions = list_functions()
    
    if request.method == "POST":
        func_name = request.form.get("func_name")
        files = request.files.getlist("input_files")
        show_table = request.form.get("show_table") == "on"
        
        # Validation
        if not func_name or func_name == "":
            flash("กรุณาเลือก function", "error")
            return redirect(url_for("index"))
            
        if not files or files[0].filename == "":
            flash("กรุณาอัปโหลดไฟล์", "error")
            return redirect(url_for("index"))

        temp_input = tempfile.mkdtemp()
        output_dir = os.path.join(BASE_DIR, f"output_{func_name}")
        
        try:
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Save uploaded files
            for f in files:
                if f.filename:
                    file_path = os.path.join(temp_input, f.filename)
                    f.save(file_path)
            
            # Import and run function
            module = importlib.import_module(f"functions.{func_name}")
            module.run(temp_input, output_dir)
            
            # Find output files
            output_files = [f for f in os.listdir(output_dir) if f.endswith((".xlsx", ".csv"))]
            if not output_files:
                flash("ไม่พบไฟล์ผลลัพธ์ใน output", "error")
                return redirect(url_for("index"))

            # Get latest file
            output_files.sort(key=lambda x: os.path.getmtime(os.path.join(output_dir, x)), reverse=True)
            output_fp = os.path.join(output_dir, output_files[0])
            download_link = url_for("download_file", func_name=func_name, filename=output_files[0])

            # Handle table display
            if show_table:
                try:
                    if output_fp.endswith(".xlsx"):
                        df = pd.read_excel(output_fp)
                    else:
                        df = pd.read_csv(output_fp, encoding='utf-8')
                    
                    # Add row numbers and format table
                    df.index = range(1, len(df) + 1)
                    table_html = df.to_html(
                        classes="result-table table table-striped table-hover", 
                        table_id="dataTable",
                        index=True, 
                        border=0,
                        escape=False
                    )
                    
                    flash("ประมวลผลสำเร็จ", "success")
                    return render_template("result.html", 
                                         table_html=table_html, 
                                         download_link=download_link,
                                         total_records=len(df),
                                         func_name=func_name)
                except Exception as e:
                    flash(f"ไม่สามารถแสดงตารางได้: {str(e)}", "warning")
                    return render_template("result.html", 
                                         table_html=None, 
                                         download_link=download_link,
                                         func_name=func_name)
            else:
                flash("ประมวลผลสำเร็จ สามารถดาวน์โหลดไฟล์ผลลัพธ์ได้", "success")
                return render_template("result.html", 
                                     table_html=None, 
                                     download_link=download_link,
                                     func_name=func_name)
                
        except Exception as e:
            flash(f"เกิดข้อผิดพลาด: {str(e)}", "error")
            print(f"Error in index route: {e}")
            return redirect(url_for("index"))
        finally:
            if os.path.exists(temp_input):
                shutil.rmtree(temp_input)
    
    return render_template("index.html", functions=functions)

@app.route("/result")
def result():
    """Redirect route for result page"""
    flash("ไม่พบข้อมูลผลลัพธ์", "error")
    return redirect(url_for("index"))

@app.route("/download/<func_name>/<filename>")
def download_file(func_name, filename):
    """Download processed files"""
    try:
        if func_name == 'lookup_last_type':
            output_dir = os.path.join(BASE_DIR, "output_lookup_last_type")
        else:
            output_dir = os.path.join(BASE_DIR, f"output_{func_name}")
        
        file_path = os.path.join(output_dir, filename)
        
        if not os.path.exists(file_path):
            flash("ไม่พบไฟล์ที่ต้องการดาวน์โหลด", "error")
            return redirect(url_for("index"))
        
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        flash(f"เกิดข้อผิดพลาดในการดาวน์โหลด: {str(e)}", "error")
        return redirect(url_for("index"))

@app.route("/lookup_last_type", methods=["GET", "POST"]) 
def lookup_last_type_route():
    table_html = None
    download_link = None
    total_records = 0
    
    if request.method == "POST":
        # Debug: ตรวจสอบข้อมูลที่ส่งมา
        print(f"📨 Form data: {request.form}")
        print(f"📁 Files: {request.files}")
        print(f"📋 Files keys: {list(request.files.keys())}")
        
        file = request.files.get("file")
        print(f"🔍 File object: {file}")
        print(f"📄 File name: {file.filename if file else 'None'}")
        
        if not file or file.filename == "":
            flash("กรุณาอัปโหลดไฟล์", "error")
            return redirect(url_for("lookup_last_type_route"))
        
        # ตรวจสอบประเภทไฟล์
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            flash("กรุณาอัปโหลดไฟล์ Excel (.xlsx หรือ .xls) เท่านั้น", "error")
            return redirect(url_for("lookup_last_type_route"))
        
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, file.filename)
        
        try:
            # บันทึกไฟล์ก่อน
            file.save(file_path)
            
            # ตรวจสอบไฟล์หลังบันทึกแล้ว
            try:
                temp_df = pd.read_excel(file_path)
                print(f"📋 ไฟล์ที่อัปโหลดมีคอลัมน์: {list(temp_df.columns)}")
                
                # ตรวจสอบคอลัมน์ bom_no
                has_bom = any(str(col).lower().strip() in ['bom_no', 'bomno', 'bom no', 'bom_number'] 
                             for col in temp_df.columns)
                
                if not has_bom:
                    available_cols = ", ".join(str(col) for col in temp_df.columns)
                    flash(f"ไฟล์ไม่มีคอลัมน์ bom_no - คอลัมน์ที่มี: {available_cols}", "error")
                    return redirect(url_for("lookup_last_type_route"))
                    
            except Exception as read_error:
                flash(f"ไม่สามารถอ่านไฟล์ Excel ได้: {str(read_error)}", "error")
                return redirect(url_for("lookup_last_type_route"))
            
            # ดำเนินการ lookup
            output_dir = os.path.join(BASE_DIR, "output_PNP_CHANG_TYPE")
            os.makedirs(output_dir, exist_ok=True)
            
            print(f"🔍 เริ่มค้นหาข้อมูล...")
            df_result = lookup_last_type(file_path, output_dir)
            
            if df_result is not None and not df_result.empty:
                # เพิ่มเลขแถว
                df_result.index = range(1, len(df_result) + 1)
                table_html = df_result.to_html(
                    classes="result-table table table-striped table-hover", 
                    table_id="dataTable",
                    index=True, 
                    border=0,
                    escape=False
                )
                
                # Save result
                download_dir = os.path.join(BASE_DIR, "output_lookup_last_type")
                os.makedirs(download_dir, exist_ok=True)
                
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"last_type_result_{timestamp}.xlsx"
                result_path = os.path.join(download_dir, filename)
                df_result.to_excel(result_path, index=False)
                
                download_link = url_for('download_file', func_name='lookup_last_type', filename=filename)
                total_records = len(df_result)
                
                # นับจำนวนที่พบและไม่พบ
                found_count = df_result['Last_type'].notna().sum() if 'Last_type' in df_result.columns else 0
                not_found_count = total_records - found_count
                
                flash(f"ค้นหาเสร็จสิ้น: พบข้อมูล {found_count} รายการ, ไม่พบ {not_found_count} รายการ", "success")
            else:
                flash("ไม่พบข้อมูลที่ตรงกัน", "warning")
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error details: {error_msg}")
            
            if "ไม่พบไฟล์ Last_Type.xlsx" in error_msg:
                flash("ไม่พบไฟล์ Last_Type.xlsx กรุณาวางไฟล์ในโฟลเดอร์ Upload หรือ output_PNP_CHANG_TYPE", "error")
            elif "ไม่มีคอลัมน์ bom_no" in error_msg:
                flash("ไฟล์ที่อัปโหลดไม่มีคอลัมน์ bom_no กรุณาตรวจสอบไฟล์", "error")
            elif "ไม่มีคอลัมน์: ['bom_no', 'Last_type']" in error_msg or "ไม่มีคอลัมน์: ['Last_type']" in error_msg:
                flash("ไฟล์ Last_Type.xlsx ไม่มีคอลัมน์ที่จำเป็น (bom_no, Last_type)", "error")
            else:
                flash(f"เกิดข้อผิดพลาด: {error_msg}", "error")
                
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    return render_template("lookup_last_type.html", 
                         table_html=table_html, 
                         download_link=download_link,
                         total_records=total_records)

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return render_template('500.html'), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all other exceptions"""
    print(f"Unhandled exception: {e}")
    flash("เกิดข้อผิดพลาดที่ไม่คาดคิด กรุณาลองใหม่อีกครั้ง", "error")
    return redirect(url_for("index"))

if __name__ == "__main__":
    # Ensure output directories exist
    os.makedirs(os.path.join(BASE_DIR, "output_lookup_last_type"), exist_ok=True)
    os.makedirs(FUNCTIONS_DIR, exist_ok=True)
    
    # Get local IP
    try:
        ip = socket.gethostbyname(socket.gethostname())
        print(f"🚀 IE Function : Starting...")
        print(f"   Local:   http://127.0.0.1:80")
        print(f"   Network: http://{ip}:80")
        print(f"   Debug:   {app.debug}")
        print(f"   Functions: {list_functions()}")
    except Exception as e:
        print(f"Network detection failed: {e}")
        ip = "127.0.0.1"
    
    # Use port 80 
    app.run(debug=True, host='0.0.0.0', port=80, threaded=True)