from flask import Flask, request, render_template, redirect, url_for, flash, session, send_file, jsonify
import os
import importlib
import tempfile
import shutil
import pandas as pd
import socket
import datetime
import logging
from functions.PNP_CHANG_TYPE import lookup_last_type

# Configuration Class
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key_change_this_in_production'
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    FUNCTIONS_DIR = os.path.join(BASE_DIR, "functions")
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = ['.xlsx', '.xls', '.csv']
    HOST = '0.0.0.0'
    PORT = 80
    DEBUG = True

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

# Utility Classes
class FileUtils:
    @staticmethod
    def validate_file(file):
        """Validate uploaded file"""
        if not file or file.filename == "":
            return False, "กรุณาอัปโหลดไฟล์"
        
        if not file.filename.lower().endswith(tuple(Config.ALLOWED_EXTENSIONS)):
            return False, f"กรุณาอัปโหลดไฟล์ {', '.join(Config.ALLOWED_EXTENSIONS)} เท่านั้น"
        
        return True, None
    
    @staticmethod
    def read_file_safely(file_path):
        """Safely read Excel or CSV file with proper engine detection"""
        try:
            # ตรวจสอบนามสกุลไฟล์
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext in ['.xlsx', '.xls']:
                # สำหรับไฟล์ Excel
                try:
                    # ลองใช้ openpyxl สำหรับ .xlsx
                    if file_ext == '.xlsx':
                        df = pd.read_excel(file_path, engine='openpyxl')
                    else:
                        # ลองใช้ xlrd สำหรับ .xls
                        df = pd.read_excel(file_path, engine='xlrd')
                    return df, None
                except Exception as excel_error:
                    # ถ้าอ่าน Excel ไม่ได้ ลองอ่านเป็น CSV
                    try:
                        df = pd.read_csv(file_path, encoding='utf-8')
                        return df, "ไฟล์ถูกอ่านเป็น CSV format"
                    except:
                        try:
                            df = pd.read_csv(file_path, encoding='tis-620')
                            return df, "ไฟล์ถูกอ่านเป็น CSV format (TIS-620)"
                        except:
                            return None, f"ไม่สามารถอ่านไฟล์ได้: {str(excel_error)}"
            
            elif file_ext == '.csv':
                # สำหรับไฟล์ CSV
                try:
                    df = pd.read_csv(file_path, encoding='utf-8')
                    return df, None
                except:
                    try:
                        df = pd.read_csv(file_path, encoding='tis-620')
                        return df, "ไฟล์ถูกอ่านด้วย TIS-620 encoding"
                    except:
                        try:
                            df = pd.read_csv(file_path, encoding='cp1252')
                            return df, "ไฟล์ถูกอ่านด้วย CP1252 encoding"
                        except Exception as csv_error:
                            return None, f"ไม่สามารถอ่านไฟล์ CSV ได้: {str(csv_error)}"
            
            else:
                return None, "รูปแบบไฟล์ไม่ถูกต้อง"
                
        except Exception as e:
            return None, f"เกิดข้อผิดพลาดในการอ่านไฟล์: {str(e)}"
    
    @staticmethod
    def check_bom_column(df):
        """Check if DataFrame has BOM column"""
        bom_columns = ['bom_no', 'bomno', 'bom no', 'bom_number', 'BOM_NO', 'BOMNO']
        for col in df.columns:
            if str(col).lower().strip() in [bc.lower() for bc in bom_columns]:
                return True, col
        return False, None
    
    @staticmethod
    def save_result_file(df, output_dir, prefix="result"):
        """Save DataFrame to Excel with timestamp"""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.xlsx"
        file_path = os.path.join(output_dir, filename)
        
        try:
            df.to_excel(file_path, index=False, engine='openpyxl')
        except:
            # ถ้าเซฟ Excel ไม่ได้ เซฟเป็น CSV
            filename = f"{prefix}_{timestamp}.csv"
            file_path = os.path.join(output_dir, filename)
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
        return filename, file_path

def list_functions():
    """List all available function modules"""
    files = []
    try:
        for f in os.listdir(Config.FUNCTIONS_DIR):
            if f.endswith(".py") and not f.startswith("__"):
                files.append(f[:-3])
    except Exception as e:
        logger.error(f"Error listing functions: {e}")
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
        output_dir = os.path.join(Config.BASE_DIR, f"output_{func_name}")
        
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
                    # ใช้ read_file_safely แทน
                    df, read_warning = FileUtils.read_file_safely(output_fp)
                    
                    if df is not None:
                        if read_warning:
                            flash(read_warning, "warning")
                        
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
                    else:
                        flash(f"ไม่สามารถแสดงตารางได้: {read_warning}", "warning")
                        return render_template("result.html", 
                                             table_html=None, 
                                             download_link=download_link,
                                             func_name=func_name)
                        
                except Exception as e:
                    logger.error(f"Error displaying table: {e}")
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
            logger.error(f"Error in index route: {e}")
            flash(f"เกิดข้อผิดพลาด: {str(e)}", "error")
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
            output_dir = os.path.join(Config.BASE_DIR, "output_lookup_last_type")
        else:
            output_dir = os.path.join(Config.BASE_DIR, f"output_{func_name}")
        
        file_path = os.path.join(output_dir, filename)
        
        if not os.path.exists(file_path):
            flash("ไม่พบไฟล์ที่ต้องการดาวน์โหลด", "error")
            return redirect(url_for("index"))
        
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        logger.error(f"Download error: {e}")
        flash(f"เกิดข้อผิดพลาดในการดาวน์โหลด: {str(e)}", "error")
        return redirect(url_for("index"))

@app.route("/lookup_last_type", methods=["GET", "POST"]) 
def lookup_last_type_route():
    table_html = None
    download_link = None
    total_records = 0
    
    if request.method == "POST":
        # Debug: ตรวจสอบข้อมูลที่ส่งมา
        logger.info(f"📨 Form data: {request.form}")
        logger.info(f"📁 Files: {request.files}")
        
        file = request.files.get("file")
        logger.info(f"🔍 File object: {file}")
        logger.info(f"📄 File name: {file.filename if file else 'None'}")
        
        # Validate file using utility
        is_valid, error_msg = FileUtils.validate_file(file)
        if not is_valid:
            flash(error_msg, "error")
            return redirect(url_for("lookup_last_type_route"))
        
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, file.filename)
        
        try:
            # บันทึกไฟล์ก่อน
            file.save(file_path)
            logger.info(f"💾 บันทึกไฟล์แล้ว: {file_path}")
            
            # ตรวจสอบไฟล์หลังบันทึกแล้ว
            temp_df, read_warning = FileUtils.read_file_safely(file_path)
            
            if temp_df is None:
                flash(f"ไม่สามารถอ่านไฟล์ได้: {read_warning}", "error")
                return redirect(url_for("lookup_last_type_route"))
            
            # แสดง warning ถ้ามี
            if read_warning:
                flash(read_warning, "warning")
            
            logger.info(f"📋 ไฟล์ที่อัปโหลดมีคอลัมน์: {list(temp_df.columns)}")
            logger.info(f"📊 จำนวนแถว: {len(temp_df)}")
            
            # ตรวจสอบคอลัมน์ bom_no ด้วย utility
            has_bom, bom_col = FileUtils.check_bom_column(temp_df)
            if not has_bom:
                available_cols = ", ".join(str(col) for col in temp_df.columns)
                flash(f"ไฟล์ไม่มีคอลัมน์ bom_no - คอลัมน์ที่มี: {available_cols}", "error")
                return redirect(url_for("lookup_last_type_route"))
            
            logger.info(f"✅ พบคอลัมน์ BOM: {bom_col}")
            
            # ดำเนินการ lookup
            output_dir = os.path.join(Config.BASE_DIR, "output_PNP_CHANG_TYPE")
            os.makedirs(output_dir, exist_ok=True)
            
            logger.info("🔍 เริ่มค้นหาข้อมูล...")
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
                
                # Save result using utility
                download_dir = os.path.join(Config.BASE_DIR, "output_lookup_last_type")
                filename, result_path = FileUtils.save_result_file(df_result, download_dir, "last_type_result")
                
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
            logger.error(f"❌ Error details: {error_msg}")
            
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

@app.route('/api/get_data_all_files')
def get_data_all_files():
    try:
        data_all_path = os.path.join(Config.BASE_DIR, 'data_all')
        
        if not os.path.exists(data_all_path):
            return jsonify({'files': [], 'error': 'ไม่พบโฟลเดอร์ data_all'})
        
        files = [f for f in os.listdir(data_all_path) 
                if f.lower().endswith(('.txt', '.log'))]
        files.sort()
        
        return jsonify({'files': files})
    except Exception as e:
        return jsonify({'files': [], 'error': str(e)})

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
    logger.error(f"Unhandled exception: {e}")
    flash("เกิดข้อผิดพลาดที่ไม่คาดคิด กรุณาลองใหม่อีกครั้ง", "error")
    return redirect(url_for("index"))

if __name__ == "__main__":
    # Ensure output directories exist
    os.makedirs(os.path.join(Config.BASE_DIR, "output_lookup_last_type"), exist_ok=True)
    os.makedirs(Config.FUNCTIONS_DIR, exist_ok=True)
    
    # Get local IP
    try:
        ip = socket.gethostbyname(socket.gethostname())
        logger.info("🚀 IE Function : Starting...")
        logger.info(f"   Local:   http://127.0.0.1:{Config.PORT}")
        logger.info(f"   Network: http://{ip}:{Config.PORT}")
        logger.info(f"   Debug:   {Config.DEBUG}")
        logger.info(f"   Functions: {list_functions()}")
    except Exception as e:
        logger.error(f"Network detection failed: {e}")
        ip = "127.0.0.1"
    
    # Use port 80 
    app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT, threaded=True)

#version 2.0