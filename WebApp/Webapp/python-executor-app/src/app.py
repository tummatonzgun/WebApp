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

@app.route("/api/folders")
def get_folders():
    """Get available folders for file selection"""
    try:
        # Define allowed folders (customize as needed)
        base_paths = [
            os.path.join(Config.BASE_DIR, "data_logview"),  # For LOGVIEW files
            os.path.join(Config.BASE_DIR, "Upload"),        # Upload folder
            os.path.join(Config.BASE_DIR, "data"),          # General data folder
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
    
    if request.method == "POST":
        try:
            # Get function name from form
            func_name = request.form.get('func_name')
            if not func_name:
                flash("กรุณาเลือกฟังก์ชันที่ต้องการประมวลผล", "error")
                return redirect(url_for("index"))

            # Check input method
            input_method = request.form.get('inputMethod', 'upload')
            temp_input = None
            
            if input_method == 'folder':
                # Handle folder-based file selection
                selected_folder = request.form.get('selected_folder')
                selected_files_str = request.form.get('selected_files')
                
                if not selected_folder or not selected_files_str:
                    flash("กรุณาเลือกโฟลเดอร์และไฟล์ที่ต้องการประมวลผล", "error")
                    return redirect(url_for("index"))
                
                selected_filenames = selected_files_str.split(',')
                
                # Create temporary directory and copy selected files
                temp_input = tempfile.mkdtemp()
                try:
                    copied_files = 0
                    for filename in selected_filenames:
                        if filename.strip():  # Skip empty strings
                            source_path = os.path.join(selected_folder, filename.strip())
                            if os.path.exists(source_path):
                                dest_path = os.path.join(temp_input, filename.strip())
                                shutil.copy2(source_path, dest_path)
                                copied_files += 1
                                logger.info(f"Copied file: {filename.strip()}")
                    
                    if copied_files == 0:
                        flash("ไม่พบไฟล์ที่เลือกในโฟลเดอร์", "error")
                        if temp_input:
                            shutil.rmtree(temp_input)
                        return redirect(url_for("index"))
                    
                    logger.info(f"Successfully copied {copied_files} files to temp directory")
                        
                except Exception as e:
                    logger.error(f"Error copying files: {e}")
                    if temp_input and os.path.exists(temp_input):
                        shutil.rmtree(temp_input)
                    raise e
                    
            else:
                # Handle normal file upload
                files = request.files.getlist("input_files")
                if not files or all(f.filename == "" for f in files):
                    flash("กรุณาเลือกไฟล์ก่อน", "error")
                    return redirect(url_for("index"))
                
                # Create temporary directory and save uploaded files
                temp_input = tempfile.mkdtemp()
                try:
                    for f in files:
                        if f.filename:
                            file_path = os.path.join(temp_input, f.filename)
                            f.save(file_path)
                            logger.info(f"Saved uploaded file: {f.filename}")
                            
                except Exception as e:
                    logger.error(f"Error saving uploaded files: {e}")
                    if temp_input and os.path.exists(temp_input):
                        shutil.rmtree(temp_input)
                    raise e
            
            # Continue with processing
            output_dir = os.path.join(Config.BASE_DIR, f"output_{func_name}")
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Import and run function
            logger.info(f"Running function: {func_name}")
            logger.info(f"Input directory: {temp_input}")
            logger.info(f"Output directory: {output_dir}")
            
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
            show_table = True
            if show_table:
                try:
                    # อ่านไฟล์ผลลัพธ์เพื่อแสดงเป็นตาราง
                    df, read_warning = FileUtils.read_file_safely(output_fp)
                    
                    if df is not None:
                        # แสดงคำเตือนถ้าอ่านไฟล์มีปัญหา
                        if read_warning:
                            flash(read_warning, "warning")
                        
                        # เพิ่มเลขลำดับให้แต่ละแถว
                        df.index = range(1, len(df) + 1)
                        
                        # สร้างตาราง HTML
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
            # ลบไฟล์ชั่วคราวเสมอ
            if temp_input and os.path.exists(temp_input):
                shutil.rmtree(temp_input)
    
    # ถ้าเป็น GET request ให้แสดงหน้าหลัก
    return render_template("index.html", functions=functions)

@app.route("/result")
def result():
    """
    หน้าผลลัพธ์ - ใช้เป็น fallback route 
    ถ้ามีคนเข้า /result โดยตรง จะ redirect กลับหน้าหลัก
    """
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

# ===== Service Classes สำหรับแยก Business Logic =====

class FileProcessingService:
    """
    Service สำหรับจัดการไฟล์ทั้งหมด
    - การตรวจสอบไฟล์
    - การประมวลผลไฟล์
    - การลบไฟล์ชั่วคราว
    """
    
    @staticmethod
    def process_files(files, func_name):
        """
        ประมวลผลไฟล์และรัน function ที่เลือก
        Args:
            files: ไฟล์ที่อัปโหลด
            func_name: ชื่อ function ที่จะรัน
        Returns:
            tuple: (temp_input_dir, output_dir)
        """
        temp_input = tempfile.mkdtemp()  # สร้างโฟลเดอร์ชั่วคราว
        output_dir = os.path.join(Config.BASE_DIR, f"output_{func_name}")
        
        try:
            # สร้างโฟลเดอร์ output ถ้ายังไม่มี
            os.makedirs(output_dir, exist_ok=True)
            
            # บันทึกไฟล์ที่อัปโหลดลงโฟลเดอร์ชั่วคราว
            for f in files:
                if f.filename:
                    file_path = os.path.join(temp_input, f.filename)
                    f.save(file_path)
            
            # โหลดและรัน function ที่เลือก
            module = importlib.import_module(f"functions.{func_name}")
            module.run(temp_input, output_dir)
            
            return temp_input, output_dir
            
        except Exception as e:
            # ถ้าเกิดข้อผิดพลาด ลบไฟล์ชั่วคราวแล้ว raise error
            if os.path.exists(temp_input):
                shutil.rmtree(temp_input)
            raise e
    
    @staticmethod
    def validate_files(files):
        """
        ตรวจสอบความถูกต้องของไฟล์ที่อัปโหลด
        Args:
            files: รายการไฟล์ที่อัปโหลด
        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        # ตรวจสอบว่ามีไฟล์หรือไม่
        if not files or files[0].filename == "":
            return False, "กรุณาอัปโหลดไฟล์"
        
        # ตรวจสอบไฟล์แต่ละไฟล์
        for file in files:
            if file.filename:
                is_valid, error_msg = FileUtils.validate_file(file)
                if not is_valid:
                    return False, error_msg
        
        return True, None
    
    @staticmethod
    def get_output_files(output_dir):
        """
        หาไฟล์ผลลัพธ์ในโฟลเดอร์ output
        Args:
            output_dir: path ของโฟลเดอร์ output
        Returns:
            list: รายการชื่อไฟล์ (เรียงจากใหม่ไปเก่า)
        """
        if not os.path.exists(output_dir):
            return []
        
        # หาไฟล์ที่เป็น Excel หรือ CSV
        output_files = [f for f in os.listdir(output_dir) if f.endswith((".xlsx", ".csv"))]
        
        # เรียงจากไฟล์ใหม่ไปเก่า (ตาม modified time)
        output_files.sort(key=lambda x: os.path.getmtime(os.path.join(output_dir, x)), reverse=True)
        return output_files
    
    @staticmethod
    def cleanup_temp_files(temp_dir):
        """
        ลบไฟล์ชั่วคราว
        Args:
            temp_dir: path ของโฟลเดอร์ชั่วคราว
        """
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

class TableRenderingService:
    """
    Service สำหรับสร้างและจัดการตาราง HTML
    """
    
    @staticmethod
    def generate_table_html(df, include_index=True):
        """
        สร้าง HTML table จาก DataFrame
        Args:
            df: pandas DataFrame
            include_index: แสดงเลขลำดับหรือไม่
        Returns:
            str: HTML table string หรือ None ถ้า df ว่าง
        """
        if df is None or df.empty:
            return None
        
        # เพิ่มเลขลำดับถ้าต้องการ
        if include_index:
            df.index = range(1, len(df) + 1)
        
        # สร้าง HTML table พร้อม Bootstrap CSS classes
        table_html = df.to_html(
            classes="result-table table table-striped table-hover",  # CSS classes
            table_id="dataTable",                                    # ID สำหรับ JavaScript/CSS
            index=include_index,                                     # แสดงเลขลำดับ
            border=0,                                               # ไม่มีขอบ
            escape=False                                            # อนุญาต HTML tags
        )
        
        return table_html
    
    @staticmethod
    def create_download_link(func_name, filename):
        """
        สร้าง link สำหรับดาวน์โหลดไฟล์
        Args:
            func_name: ชื่อ function
            filename: ชื่อไฟล์
        Returns:
            str: URL สำหรับดาวน์โหลด
        """
        return url_for("download_file", func_name=func_name, filename=filename)
    
    @staticmethod
    def render_result_page(table_html=None, download_link=None, total_records=0, func_name=""):
        """
        render หน้าผลลัพธ์พร้อมพารามิเตอร์ที่ครบถ้วน
        Args:
            table_html: HTML table string
            download_link: link ดาวน์โหลด
            total_records: จำนวนข้อมูลทั้งหมด
            func_name: ชื่อ function
        Returns:
            flask Response object
        """
        return render_template("result.html", 
                             table_html=table_html, 
                             download_link=download_link,
                             total_records=total_records,
                             func_name=func_name)

class LookupService:
    """
    Service สำหรับการค้นหา Last Type (BOM lookup)
    """
    
    @staticmethod
    def process_lookup(file_path):
        """
        ประมวลผลการค้นหา Last Type
        Args:
            file_path: path ของไฟล์ที่ต้องการค้นหา
        Returns:
            pandas DataFrame: ผลลัพธ์การค้นหา
        """
        # สร้างโฟลเดอร์ output สำหรับ PNP_CHANG_TYPE
        output_dir = os.path.join(Config.BASE_DIR, "output_PNP_CHANG_TYPE")
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info("🔍 เริ่มค้นหาข้อมูล...")
        # เรียกใช้ function lookup_last_type จาก PNP_CHANG_TYPE module
        df_result = lookup_last_type(file_path, output_dir)
        
        return df_result
    
    @staticmethod
    def validate_bom_columns(df):
        """
        ตรวจสอบว่า DataFrame มีคอลัมน์ BOM หรือไม่
        Args:
            df: pandas DataFrame
        Returns:
            tuple: (is_valid: bool, column_name_or_error: str)
        """
        has_bom, bom_col = FileUtils.check_bom_column(df)
        if not has_bom:
            available_cols = ", ".join(str(col) for col in df.columns)
            return False, f"ไฟล์ไม่มีคอลัมน์ bom_no - คอลัมน์ที่มี: {available_cols}"
        
        return True, bom_col
    
    @staticmethod
    def save_lookup_result(df_result, prefix="last_type_result"):
        """
        บันทึกผลลัพธ์การค้นหาลงไฟล์
        Args:
            df_result: pandas DataFrame ผลลัพธ์
            prefix: prefix ของชื่อไฟล์
        Returns:
            tuple: (filename, file_path)
        """
        download_dir = os.path.join(Config.BASE_DIR, "output_lookup_last_type")
        filename, result_path = FileUtils.save_result_file(df_result, download_dir, prefix)
        return filename, result_path
    
    @staticmethod
    def count_lookup_results(df_result):
        """
        นับจำนวนผลลัพธ์ที่พบและไม่พบ
        Args:
            df_result: pandas DataFrame ผลลัพธ์
        Returns:
            tuple: (found_count: int, not_found_count: int)
        """
        if df_result is None or df_result.empty:
            return 0, 0
        
        total_records = len(df_result)
        # นับจำนวนที่พบ Last_type (ไม่เป็น null)
        found_count = df_result['Last_type'].notna().sum() if 'Last_type' in df_result.columns else 0
        not_found_count = total_records - found_count
        
        return found_count, not_found_count

# ===== Error Handler Class =====
class ErrorHandler:
    """
    Class สำหรับจัดการ error แบบรวมศูนย์
    """
    
    @staticmethod
    def handle_lookup_error(error_msg):
        """
        จัดการ error สำหรับ lookup operations โดยแปลงเป็นข้อความที่ user เข้าใจง่าย
        Args:
            error_msg: ข้อความ error ดั้งเดิม
        Returns:
            str: ข้อความ error ที่เข้าใจง่าย
        """
        if "ไม่พบไฟล์ Last_Type.xlsx" in error_msg:
            return "ไม่พบไฟล์ Last_Type.xlsx กรุณาวางไฟล์ในโฟลเดอร์ Upload หรือ output_PNP_CHANG_TYPE"
        elif "ไม่มีคอลัมน์ bom_no" in error_msg:
            return "ไฟล์ที่อัปโหลดไม่มีคอลัมน์ bom_no กรุณาตรวจสอบไฟล์"
        elif "ไม่มีคอลัมน์: ['bom_no', 'Last_type']" in error_msg or "ไม่มีคอลัมน์: ['Last_type']" in error_msg:
            return "ไฟล์ Last_Type.xlsx ไม่มีคอลัมน์ที่จำเป็น (bom_no, Last_type)"
        else:
            return f"เกิดข้อผิดพลาด: {error_msg}"
    
    @staticmethod
    def log_and_flash_error(error, context="", flash_message=None):
        """
        บันทึก log และแสดงข้อความ error ให้ user
        Args:
            error: Exception หรือ error message
            context: บริบทของ error (เช่น "File upload", "Function execution")
            flash_message: ข้อความที่จะแสดงให้ user (ถ้าไม่ระบุ จะใช้ error message)
        """
        logger.error(f"{context}: {error}")
        if flash_message:
            flash(flash_message, "error")
        else:
            flash(f"เกิดข้อผิดพลาด: {str(error)}", "error")

# ===== Constants Class =====
class AppConstants:
    """
    รวม constants ทั้งหมดไว้ที่เดียว เพื่อง่ายต่อการแก้ไข
    """
    
    # นามสกุลไฟล์ที่รองรับ
    OUTPUT_FILE_EXTENSIONS = (".xlsx", ".csv")
    
    # CSS Classes สำหรับ HTML table
    TABLE_CSS_CLASSES = "result-table table table-striped table-hover"
    
    # ประเภทของข้อความแจ้งเตือน
    MSG_SUCCESS = "success"
    MSG_ERROR = "error"
    MSG_WARNING = "warning"
    MSG_INFO = "info"
    
    # ชื่อโฟลเดอร์ output
    OUTPUT_DIR_LOOKUP = "output_lookup_last_type"
    OUTPUT_DIR_PNP = "output_PNP_CHANG_TYPE"

if __name__ == "__main__":
    # ===== การเตรียมโฟลเดอร์และเริ่มต้น Application =====
    
    # สร้างโฟลเดอร์ที่จำเป็น
    os.makedirs(os.path.join(Config.BASE_DIR, AppConstants.OUTPUT_DIR_LOOKUP), exist_ok=True)
    os.makedirs(Config.FUNCTIONS_DIR, exist_ok=True)
    
    # หา IP address สำหรับแสดงใน log
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
    
    # เริ่มต้น Flask application
    app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT, threaded=True)

# ===== Version Information =====
# version 2.3 Boss - Refactored with Service Classes and Better Comments