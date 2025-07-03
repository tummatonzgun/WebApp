from flask import Flask, request, render_template, redirect, url_for, flash, session, send_file, jsonify
import os
import importlib
import tempfile
import shutil
import pandas as pd
import socket
import datetime
import logging
from typing import Tuple, List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

try:
    from functions.PNP_CHANG_TYPE import lookup_last_type
except ImportError:
    def lookup_last_type(file_path, output_dir):
        raise NotImplementedError("lookup_last_type function is not implemented.")

# ===== LOGGING SETUP =====
def setup_logging() -> logging.Logger:
    """Configure application logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('app.log')
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

# ===== Constants =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FUNCTIONS_DIR = os.path.join(BASE_DIR, "functions")
ALLOWED_EXTENSIONS = ['.xlsx', '.xls', '.csv', '.txt', '.TXT']

# Message types for flash messages
MESSAGE_ERROR = "error"
MESSAGE_WARNING = "warning"
MESSAGE_SUCCESS = "success"

# ===== Utility Functions =====
def validate_file(file) -> tuple:
    if not file or file.filename == "":
        return False, "กรุณาอัปโหลดไฟล์"
    if not file.filename.lower().endswith(tuple(ALLOWED_EXTENSIONS)):
        return False, f"กรุณาอัปโหลดไฟล์ {', '.join(ALLOWED_EXTENSIONS)} เท่านั้น"
    return True, None

def get_file_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()

def is_excel_file(filename: str) -> bool:
    ext = get_file_extension(filename)
    return ext in ['.xlsx', '.xls']

def is_csv_file(filename: str) -> bool:
    return get_file_extension(filename) == '.csv'

def read_file_safely(file_path: str):
    try:
        if is_excel_file(file_path):
            try:
                ext = get_file_extension(file_path)
                engine = 'openpyxl' if ext == '.xlsx' else 'xlrd'
                df = pd.read_excel(file_path, engine=engine)
                return df, None
            except Exception as excel_error:
                try:
                    df = pd.read_csv(file_path, encoding='utf-8')
                    return df, "ไฟล์ถูกอ่านเป็น CSV format"
                except:
                    try:
                        df = pd.read_csv(file_path, encoding='tis-620')
                        return df, "ไฟล์ถูกอ่านเป็น CSV format (TIS-620)"
                    except:
                        return None, f"ไม่สามารถอ่านไฟล์ได้: {str(excel_error)}"
        elif is_csv_file(file_path):
            encodings = ['utf-8', 'tis-620', 'cp1252']
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    warning = f"ไฟล์ถูกอ่านด้วย {encoding.upper()} encoding" if encoding != 'utf-8' else None
                    return df, warning
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    return None, f"ไม่สามารถอ่านไฟล์ CSV ได้: {str(e)}"
            return None, "ไม่สามารถอ่านไฟล์ CSV ด้วย encoding ที่รองรับได้"
        else:
            return None, "รูปแบบไฟล์ไม่ถูกต้อง"
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None, f"เกิดข้อผิดพลาดในการอ่านไฟล์: {str(e)}"

def save_dataframe(df: pd.DataFrame, output_dir: str, prefix: str = "result"):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.xlsx"
    file_path = os.path.join(output_dir, filename)
    try:
        df.to_excel(file_path, index=False, engine='openpyxl')
    except Exception as e:
        logger.warning(f"Failed to save as Excel, saving as CSV: {e}")
        filename = f"{prefix}_{timestamp}.csv"
        file_path = os.path.join(output_dir, filename)
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
    return filename, file_path

def list_functions() -> list:
    functions = []
    try:
        for filename in os.listdir(FUNCTIONS_DIR):
            if filename.endswith(".py") and not filename.startswith("__"):
                functions.append(filename[:-3])
    except Exception as e:
        logger.error(f"Error listing functions: {e}")
    return functions

def execute_function(func_name: str, input_dir: str, output_dir: str):
    try:
        logger.info(f"Executing function: {func_name}")
        logger.info(f"Input directory: {input_dir}")
        logger.info(f"Output directory: {output_dir}")
        module = importlib.import_module(f"functions.{func_name}")
        module.run(input_dir, output_dir)
    except ImportError as e:
        logger.error(f"Function module not found: {func_name} - {e}")
        raise Exception(f"ไม่พบฟังก์ชัน {func_name}")
    except AttributeError as e:
        logger.error(f"Function run method not found in {func_name} - {e}")
        raise Exception(f"ฟังก์ชัน {func_name} ไม่มี method 'run'")
    except Exception as e:
        logger.error(f"Error executing function {func_name}: {e}")
        raise

def process_uploaded_files(files: list, func_name: str):
    temp_input = tempfile.mkdtemp()
    output_dir = os.path.join(BASE_DIR, f"output_{func_name}")
    try:
        os.makedirs(output_dir, exist_ok=True)
        for file in files:
            if file.filename:
                file_path = os.path.join(temp_input, file.filename)
                file.save(file_path)
                logger.info(f"Saved uploaded file: {file.filename}")
        execute_function(func_name, temp_input, output_dir)
        return temp_input, output_dir
    except Exception as e:
        if os.path.exists(temp_input):
            shutil.rmtree(temp_input)
        raise e

def process_folder_files(selected_folder: str, selected_files: list, func_name: str):
    temp_input = tempfile.mkdtemp()
    output_dir = os.path.join(BASE_DIR, f"output_{func_name}")
    try:
        os.makedirs(output_dir, exist_ok=True)
        copied_files = 0
        for filename in selected_files:
            if filename.strip():
                source_path = os.path.join(selected_folder, filename.strip())
                if os.path.exists(source_path):
                    dest_path = os.path.join(temp_input, filename.strip())
                    shutil.copy2(source_path, dest_path)
                    copied_files += 1
                    logger.info(f"Copied file: {filename.strip()}")
        if copied_files == 0:
            raise Exception("ไม่พบไฟล์ที่เลือกในโฟลเดอร์")
        logger.info(f"Successfully copied {copied_files} files to temp directory")
        execute_function(func_name, temp_input, output_dir)
        return temp_input, output_dir
    except Exception as e:
        if os.path.exists(temp_input):
            shutil.rmtree(temp_input)
        raise e

def get_output_files(output_dir: str) -> list:
    if not os.path.exists(output_dir):
        return []
    output_files = [f for f in os.listdir(output_dir) if f.endswith((".xlsx", ".csv"))]
    output_files.sort(key=lambda x: os.path.getmtime(os.path.join(output_dir, x)), reverse=True)
    return output_files

def cleanup_temp_files(temp_dir: str):
    if temp_dir and os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        logger.info(f"Cleaned up temporary directory: {temp_dir}")

def generate_table_html(df: pd.DataFrame, include_index: bool = True) -> str:
    if df is None or df.empty:
        return None
    if include_index:
        df.index = range(1, len(df) + 1)
    table_html = df.to_html(
        classes="result-table table table-striped table-hover",
        table_id="dataTable",
        index=include_index,
        border=0,
        escape=False
    )
    return table_html

def create_download_link(func_name: str, filename: str) -> str:
    return url_for("download_file", func_name=func_name, filename=filename)

def process_lookup(file_path: str) -> pd.DataFrame:
    output_dir = os.path.join(BASE_DIR, "output_PNP_CHANG_TYPE")
    os.makedirs(output_dir, exist_ok=True)
    logger.info("Starting BOM lookup process...")
    return lookup_last_type(file_path, output_dir)

def validate_bom_file(df: pd.DataFrame):
    has_bom = any(col.lower() == 'bom_no' for col in df.columns)
    if not has_bom:
        available_cols = ", ".join(str(col) for col in df.columns)
        return False, f"ไฟล์ไม่มีคอลัมน์ bom_no - คอลัมน์ที่มี: {available_cols}"
    return True, 'bom_no'

def count_lookup_results(df_result: pd.DataFrame):
    if df_result is None or df_result.empty:
        return 0, 0
    total_records = len(df_result)
    found_count = (df_result['Last_type'].notna().sum() if 'Last_type' in df_result.columns else 0)
    not_found_count = total_records - found_count
    return found_count, not_found_count


def log_and_flash_error(error, context="", flash_message=None):
    logger.error(f"{context}: {error}")
    message = flash_message or f"เกิดข้อผิดพลาด: {str(error)}"
    flash(message, MESSAGE_ERROR)

@app.route("/api/folders")
def get_folders():
    """Get available folders for file selection"""
    try:
        # Define allowed folders (customize as needed)
        base_paths = [
            os.path.join(BASE_DIR, "data_logview"),  # For LOGVIEW files
            os.path.join(BASE_DIR, "Upload"),        # Upload folder
            os.path.join(BASE_DIR, "data"),          # General data folder
        ]
        
        folders = []
        for base_path in base_paths:
            if os.path.exists(base_path):
                folder_name = os.path.basename(base_path)
                folders.append({
                    "name": folder_name,
                    "path": base_path
                })
        
        return jsonify({
            "success": True,
            "folders": folders
        })
    
    except Exception as e:
        logger.error(f"Error getting folders: {e}")
        return jsonify({
            "success": False,
            "message": str(e)
        })

@app.route("/api/folder-files")
def get_folder_files():
    """Get files in a specific folder"""
    try:
        folder_path = request.args.get('path')
        if not folder_path:
            return jsonify({
                "success": False,
                "message": "ไม่ได้ระบุ path ของโฟลเดอร์"
            })
        
        if not os.path.exists(folder_path):
            return jsonify({
                "success": False,
                "message": "ไม่พบโฟลเดอร์ที่ระบุ"
            })
        
        files = []
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                try:
                    file_size = os.path.getsize(file_path)
                    files.append({
                        "name": filename,
                        "size": file_size,
                        "path": file_path
                    })
                except OSError:
                    continue  # Skip files that can't be accessed
        
        # Sort files by name
        files.sort(key=lambda x: x['name'].lower())
        
        return jsonify({
            "success": True,
            "files": files
        })
    
    except Exception as e:
        logger.error(f"Error getting folder files: {e}")
        return jsonify({
            "success": False,
            "message": str(e)
        })

@app.route("/", methods=["GET", "POST"])
def index():
    functions = list_functions()
    #ฟังชั่นในโฟลเดอร์ functions
    if request.method == "POST":
        try:
            # Get function name from form
            func_name = request.form.get('func_name')
            if not func_name:
                flash("กรุณาเลือกฟังก์ชันที่ต้องการประมวลผล", MESSAGE_ERROR)
                return redirect(url_for("index"))

            # Check input method
            input_method = request.form.get('inputMethod', 'upload')
            temp_input = None
            
            if input_method == 'folder':
                # Handle folder-based file selection
                selected_folder = request.form.get('selected_folder')
                selected_files_str = request.form.get('selected_files')
                
                if not selected_folder or not selected_files_str:
                    flash("กรุณาเลือกโฟลเดอร์และไฟล์ที่ต้องการประมวลผล", MESSAGE_ERROR)
                    return redirect(url_for("index"))
                
                selected_filenames = selected_files_str.split(',')
                
                # Process folder files using service
                try:
                    temp_input, output_dir = process_folder_files(
                        selected_folder, selected_filenames, func_name
                    )
                except Exception as e:
                    log_and_flash_error(e, "Folder file processing")
                    return redirect(url_for("index"))
                    
            else:
                # Handle normal file upload
                files = request.files.getlist("input_files")
                if not files or all(f.filename == "" for f in files):
                    flash("กรุณาเลือกไฟล์ก่อน", MESSAGE_ERROR)
                    return redirect(url_for("index"))
                
                # Process uploaded files using service
                try:
                    temp_input, output_dir = process_uploaded_files(files, func_name)
                except Exception as e:
                    log_and_flash_error(e, "File upload processing")
                    return redirect(url_for("index"))
            
            # Find output files using service
            output_files = get_output_files(output_dir)
            if not output_files:
                flash("ไม่พบไฟล์ผลลัพธ์ใน output", MESSAGE_ERROR)
                return redirect(url_for("index"))

            # Get latest file
            output_fp = os.path.join(output_dir, output_files[0])
            download_link = create_download_link(func_name, output_files[0])

            # Handle table display
            show_table = True
            if show_table:
                try:
                    # อ่านไฟล์ผลลัพธ์เพื่อแสดงเป็นตาราง
                    df, read_warning = read_file_safely(output_fp)
                    
                    if df is not None:
                        # แสดงคำเตือนถ้าอ่านไฟล์มีปัญหา
                        if read_warning:
                            flash(read_warning, MESSAGE_WARNING)
                        
                        # สร้างตาราง HTML using service
                        table_html = generate_table_html(df, include_index=True)
                        
                        flash("ประมวลผลสำเร็จ", MESSAGE_SUCCESS)
                        return render_template("result.html", 
                                             table_html=table_html, 
                                             download_link=download_link,
                                             total_records=len(df),
                                             func_name=func_name)
                    else:
                        flash(f"ไม่สามารถแสดงตารางได้: {read_warning}", MESSAGE_WARNING)
                        return render_template("result.html", 
                                             table_html=None, 
                                             download_link=download_link,
                                             func_name=func_name)
                        
                except Exception as e:
                    logger.error(f"Error displaying table: {e}")
                    flash(f"ไม่สามารถแสดงตารางได้: {str(e)}", MESSAGE_WARNING)
                    return render_template("result.html", 
                                         table_html=None, 
                                         download_link=download_link,
                                         func_name=func_name)
            else:
                flash("ประมวลผลสำเร็จ สามารถดาวน์โหลดไฟล์ผลลัพธ์ได้", MESSAGE_SUCCESS)
                return render_template("result.html", 
                                     table_html=None, 
                                     download_link=download_link,
                                     func_name=func_name)
                
        except Exception as e:
            log_and_flash_error(e, "Main processing route")
            return redirect(url_for("index"))
        finally:
            # ลบไฟล์ชั่วคราวเสมอ
            if temp_input:
                cleanup_temp_files(temp_input)
    
    # ถ้าเป็น GET request ให้แสดงหน้าหลัก
    return render_template("index.html", functions=functions)

@app.route("/result", methods=["POST"])
def result():
    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")
    func_name = request.form.get("func_name")
    output_fp = request.form.get("output_fp")
    min_date = request.form.get("min_date")
    max_date = request.form.get("max_date")

    df, read_warning = read_file_safely(output_fp)
    if df is None:
        flash("ไม่สามารถอ่านไฟล์ผลลัพธ์เดิมได้", "error")
        return redirect(url_for("index"))

    # กรองข้อมูลตามวันที่ที่เลือก
    if "date_time_start" in df.columns:
        df["date_time_start"] = pd.to_datetime(df["date_time_start"], errors="coerce").dt.date
        if start_date:
            start_date = pd.to_datetime(start_date).date()
            df = df[df["date_time_start"] >= start_date]
        if end_date:
            end_date = pd.to_datetime(end_date).date()
            df = df[df["date_time_start"] <= end_date]

    table_html = generate_table_html(df, include_index=True)
    download_link = create_download_link(func_name, os.path.basename(output_fp))
    return render_template(
        "result.html",
        table_html=table_html,
        download_link=download_link,
        total_records=len(df),
        func_name=func_name,
        output_fp=output_fp,
        min_date=min_date,
        max_date=max_date,
        start_date=request.form.get("start_date"),
        end_date=request.form.get("end_date")
    )

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
            flash("ไม่พบไฟล์ที่ต้องการดาวน์โหลด", MESSAGE_ERROR)
            return redirect(url_for("index"))
        
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        logger.error(f"Download error: {e}")
        flash(f"เกิดข้อผิดพลาดในการดาวน์โหลด: {str(e)}", MESSAGE_ERROR)
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
        is_valid, error_msg = validate_file(file)
        if not is_valid:
            flash(error_msg, MESSAGE_ERROR)
            return redirect(url_for("lookup_last_type_route"))
        
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, file.filename)
        
        try:
            # บันทึกไฟล์ก่อน
            file.save(file_path)
            logger.info(f"💾 บันทึกไฟล์แล้ว: {file_path}")
            
            # ตรวจสอบไฟล์หลังบันทึกแล้ว
            temp_df, read_warning = read_file_safely(file_path)
            
            if temp_df is None:
                flash(f"ไม่สามารถอ่านไฟล์ได้: {read_warning}", MESSAGE_ERROR)
                return redirect(url_for("lookup_last_type_route"))
            
            # แสดง warning ถ้ามี
            if read_warning:
                flash(read_warning, MESSAGE_WARNING)
            
            logger.info(f"📋 ไฟล์ที่อัปโหลดมีคอลัมน์: {list(temp_df.columns)}")
            logger.info(f"📊 จำนวนแถว: {len(temp_df)}")
            
            # ตรวจสอบคอลัมน์ bom_no ด้วย service
            is_valid_bom, result = validate_bom_file(temp_df)
            if not is_valid_bom:
                flash(result, MESSAGE_ERROR)
                return redirect(url_for("lookup_last_type_route"))
            
            logger.info(f"✅ พบคอลัมน์ BOM: {result}")
            
            # ดำเนินการ lookup ด้วย service
            logger.info("🔍 เริ่มค้นหาข้อมูล...")
            df_result = process_lookup(file_path)
            
            if df_result is not None and not df_result.empty:
                # สร้างตาราง HTML ด้วย service
                table_html = generate_table_html(df_result, include_index=True)
                
                # Save result using service
                download_dir = os.path.join(BASE_DIR, "output_lookup_last_type")
                filename, result_path = save_dataframe(df_result, download_dir, "last_type_result")
                
                download_link = create_download_link('lookup_last_type', filename)
                total_records = len(df_result)
                
                # นับจำนวนที่พบและไม่พบ ด้วย service
                found_count, not_found_count = count_lookup_results(df_result)
                
                flash(f"ค้นหาเสร็จสิ้น: พบข้อมูล {found_count} รายการ, ไม่พบ {not_found_count} รายการ", MESSAGE_SUCCESS)
            else:
                flash("ไม่พบข้อมูลที่ตรงกัน", MESSAGE_WARNING)
                
                
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    return render_template("lookup_last_type.html", 
                         table_html=table_html, 
                         download_link=download_link,
                         total_records=total_records)
   
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=80)
# For production, set debug=False and use a proper WSGI server