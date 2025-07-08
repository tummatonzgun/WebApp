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
import time
import threading
from datetime import datetime, timedelta


# Import custom modules
from functions.PNP_CHANG_TYPE import lookup_last_type

# ===== CONFIGURATION =====
@dataclass
class Config:
    """Application configuration with type hints and validation"""
    SECRET_KEY: str = os.environ.get('SECRET_KEY', 'your_secret_key_change_this_in_production')
    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
    FUNCTIONS_DIR: str = os.path.join(BASE_DIR, "functions")
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: List[str] = None
    HOST: str = '0.0.0.0'
    PORT: int = 80
    DEBUG: bool = True
    
    def __post_init__(self):
        if self.ALLOWED_EXTENSIONS is None:
            self.ALLOWED_EXTENSIONS = ['.xlsx', '.xls', '.csv', '.txt']

# ===== ENUMS =====
class MessageType(Enum):
    """Flash message types"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class FileType(Enum):
    """Supported file types"""
    EXCEL_NEW = ".xlsx"
    EXCEL_OLD = ".xls"
    CSV = ".csv"
    TEXT = ".txt"


# ===== FLASK APP INITIALIZATION =====
def create_app(config: Config = None) -> Flask:
    """Application factory pattern"""
    app = Flask(__name__)
    
    if config is None:
        config = Config()
    
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = config.MAX_FILE_SIZE
    
    return app

config = Config()
app = create_app(config)

# ===== UTILITY CLASSES =====
class FileValidator:
    """File validation utilities"""
    
    @staticmethod
    def validate_file(file) -> Tuple[bool, Optional[str]]:
        """
        Validate uploaded file
        
        Args:
            file: FileStorage object from Flask
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not file or file.filename == "":
            return False, "กรุณาอัปโหลดไฟล์"
        
        if not file.filename.lower().endswith(tuple(config.ALLOWED_EXTENSIONS)):
            return False, f"กรุณาอัปโหลดไฟล์ {', '.join(config.ALLOWED_EXTENSIONS)} เท่านั้น"
        
        return True, None
    
    @staticmethod
    def get_file_extension(filename: str) -> str:
        """Get file extension in lowercase"""
        return os.path.splitext(filename)[1].lower()
    
    @staticmethod
    def is_excel_file(filename: str) -> bool:
        """Check if file is Excel format"""
        ext = FileValidator.get_file_extension(filename)
        return ext in [FileType.EXCEL_NEW.value, FileType.EXCEL_OLD.value]
    
    @staticmethod
    def is_csv_file(filename: str) -> bool:
        """Check if file is CSV format"""
        return FileValidator.get_file_extension(filename) == FileType.CSV.value

class FileReader:
    """File reading utilities with proper encoding handling"""
    
    @staticmethod
    def read_file_safely(file_path: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        Safely read Excel or CSV file with proper engine detection
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (DataFrame, warning_message)
        """
        try:
            if FileValidator.is_excel_file(file_path):
                return FileReader._read_excel_file(file_path)
            elif FileValidator.is_csv_file(file_path):
                return FileReader._read_csv_file(file_path)
            else:
                return None, "รูปแบบไฟล์ไม่ถูกต้อง"
                
        except Exception as e:
            
            return None, f"เกิดข้อผิดพลาดในการอ่านไฟล์: {str(e)}"
    
    @staticmethod
    def _read_excel_file(file_path: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """Read Excel file with appropriate engine"""
        try:
            ext = FileValidator.get_file_extension(file_path)
            engine = 'openpyxl' if ext == FileType.EXCEL_NEW.value else 'xlrd'
            df = pd.read_excel(file_path, engine=engine)
            return df, None
        except Exception as excel_error:
            # Fallback to CSV reading
            try:
                df = pd.read_csv(file_path, encoding='utf-8')
                return df, "ไฟล์ถูกอ่านเป็น CSV format"
            except:
                try:
                    df = pd.read_csv(file_path, encoding='tis-620')
                    return df, "ไฟล์ถูกอ่านเป็น CSV format (TIS-620)"
                except:
                    return None, f"ไม่สามารถอ่านไฟล์ได้: {str(excel_error)}"
    
    @staticmethod
    def _read_csv_file(file_path: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """Read CSV file with encoding detection"""
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

class DataFrameUtils:
    """DataFrame utility functions"""
    
    @staticmethod
    def check_bom_column(df: pd.DataFrame) -> Tuple[bool, Optional[str]]:
        """
        Check if DataFrame has BOM column
        
        Args:
            df: pandas DataFrame
            
        Returns:
            Tuple of (has_bom_column, column_name)
        """
        bom_columns = ['bom_no', 'bomno', 'bom no', 'bom_number', 'BOM_NO', 'BOMNO']
        
        for col in df.columns:
            if str(col).lower().strip() in [bc.lower() for bc in bom_columns]:
                return True, col
        
        return False, None
    
    @staticmethod
    def save_dataframe(df: pd.DataFrame, output_dir: str, prefix: str = "result") -> Tuple[str, str]:
        """
        Save DataFrame to Excel with timestamp
        
        Args:
            df: DataFrame to save
            output_dir: Output directory
            prefix: Filename prefix
            
        Returns:
            Tuple of (filename, file_path)
        """
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


# ===== BUSINESS LOGIC SERVICES =====
class FunctionService:
    """Service for managing and executing functions"""
    
    @staticmethod
    def list_functions() -> List[str]:
        """List all available function modules"""
        functions = []
        try:
            for filename in os.listdir(config.FUNCTIONS_DIR):
                if filename.endswith(".py") and not filename.startswith("__"):
                    functions.append(filename[:-3])
        except Exception as e:
            logger.error(f"Error listing functions: {e}")
        return functions
    
    @staticmethod
    def execute_function(func_name: str, input_dir: str, output_dir: str, **kwargs) -> None:
        """
        Execute a function module
        
        Args:
            func_name: Name of the function to execute
            input_dir: Input directory path
            output_dir: Output directory path
            **kwargs: Additional arguments to pass to the function
        """
        try:
            logger.info(f"Executing function: {func_name}")
            logger.info(f"Input directory: {input_dir}")
            logger.info(f"Output directory: {output_dir}")
            logger.info(f"Additional arguments: {kwargs}")
            
            module = importlib.import_module(f"functions.{func_name}")
            
            # Check if function accepts additional arguments
            import inspect
            sig = inspect.signature(module.run)
            
            if len(sig.parameters) > 2:  # More than input_dir and output_dir
                module.run(input_dir, output_dir, **kwargs)
            else:
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

class FileProcessingService:
    """Service for file processing operations"""
    
    @staticmethod
    def process_uploaded_files(files: List, func_name: str, **kwargs) -> Tuple[str, str]:
        """
        Process uploaded files and execute function
        
        Args:
            files: List of uploaded files
            func_name: Function name to execute
            **kwargs: Additional arguments to pass to function
            
        Returns:
            Tuple of (temp_input_dir, output_dir)
        """
        temp_input = tempfile.mkdtemp()
        output_dir = os.path.join(config.BASE_DIR, f"output_{func_name}")
        
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # Save uploaded files
            for file in files:
                if file.filename:
                    file_path = os.path.join(temp_input, file.filename)
                    file.save(file_path)
                    logger.info(f"Saved uploaded file: {file.filename}")
            
            # Execute function with additional arguments
            FunctionService.execute_function(func_name, temp_input, output_dir, **kwargs)
            
            return temp_input, output_dir
            
        except Exception as e:
            if os.path.exists(temp_input):
                shutil.rmtree(temp_input)
            raise e
    
    @staticmethod
    def process_folder_files(selected_folder: str, selected_files: List[str], func_name: str, **kwargs) -> Tuple[str, str]:
        """
        Process files from folder selection
        
        Args:
            selected_folder: Path to selected folder
            selected_files: List of selected file names
            func_name: Function name to execute
            **kwargs: Additional arguments to pass to function
            
        Returns:
            Tuple of (temp_input_dir, output_dir)
        """
        temp_input = tempfile.mkdtemp()
        output_dir = os.path.join(config.BASE_DIR, f"output_{func_name}")
        
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
            
            # Execute function with additional arguments
            FunctionService.execute_function(func_name, temp_input, output_dir, **kwargs)
            
            return temp_input, output_dir
            
        except Exception as e:
            if os.path.exists(temp_input):
                shutil.rmtree(temp_input)
            raise e
    
    @staticmethod
    def get_output_files(output_dir: str) -> List[str]:
        """Get list of output files sorted by modification time"""
        if not os.path.exists(output_dir):
            return []
        
        output_files = [f for f in os.listdir(output_dir) 
                       if f.endswith((".xlsx", ".csv"))]
        
        output_files.sort(
            key=lambda x: os.path.getmtime(os.path.join(output_dir, x)), 
            reverse=True
        )
        return output_files
    
    @staticmethod
    def cleanup_temp_files(temp_dir: str) -> None:
        """Clean up temporary files"""
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")

class TableRenderingService:
    """Service for generating HTML tables and download links"""
    
    @staticmethod
    def generate_table_html(df: pd.DataFrame, include_index: bool = True) -> Optional[str]:
        """
        Generate HTML table from DataFrame
        
        Args:
            df: pandas DataFrame
            include_index: Whether to include row numbers
            
        Returns:
            HTML table string or None if DataFrame is empty
        """
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
    
    @staticmethod
    def create_download_link(func_name: str, filename: str) -> str:
        """Create download URL for result file"""
        return url_for("download_file", func_name=func_name, filename=filename)

class LookupService:
    """Service for BOM lookup operations"""
    
    @staticmethod
    def process_lookup(file_path: str) -> pd.DataFrame:
        """
        Process BOM lookup operation
        
        Args:
            file_path: Path to the file to lookup
            
        Returns:
            DataFrame with lookup results
        """
        output_dir = os.path.join(config.BASE_DIR, "output_PNP_CHANG_TYPE")
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info("Starting BOM lookup process...")
        return lookup_last_type(file_path, output_dir)
    
    @staticmethod
    def validate_bom_file(df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Validate BOM file structure
        
        Args:
            df: DataFrame to validate
            
        Returns:
            Tuple of (is_valid, message)
        """
        has_bom, bom_col = DataFrameUtils.check_bom_column(df)
        if not has_bom:
            available_cols = ", ".join(str(col) for col in df.columns)
            return False, f"ไฟล์ไม่มีคอลัมน์ bom_no - คอลัมน์ที่มี: {available_cols}"
        
        return True, bom_col
    
    @staticmethod
    def count_lookup_results(df_result: pd.DataFrame) -> Tuple[int, int]:
        """
        Count lookup results
        
        Args:
            df_result: DataFrame with lookup results
            
        Returns:
            Tuple of (found_count, not_found_count)
        """
        if df_result is None or df_result.empty:
            return 0, 0
        
        total_records = len(df_result)
        found_count = (df_result['Last_type'].notna().sum() 
                      if 'Last_type' in df_result.columns else 0)
        not_found_count = total_records - found_count
        
        return found_count, not_found_count

class ErrorHandler:
    """Centralized error handling"""
    
    @staticmethod
    def handle_lookup_error(error_msg: str) -> str:
        """Convert technical errors to user-friendly messages"""
        error_mappings = {
            "ไม่พบไฟล์ Last_Type.xlsx": 
                "ไม่พบไฟล์ Last_Type.xlsx กรุณาวางไฟล์ในโฟลเดอร์ Upload หรือ output_PNP_CHANG_TYPE",
            "ไม่มีคอลัมน์ bom_no": 
                "ไฟล์ที่อัปโหลดไม่มีคอลัมน์ bom_no กรุณาตรวจสอบไฟล์",
            "ไม่มีคอลัมน์: ['bom_no', 'Last_type']": 
                "ไฟล์ Last_Type.xlsx ไม่มีคอลัมน์ที่จำเป็น (bom_no, Last_type)",
            "ไม่มีคอลัมน์: ['Last_type']": 
                "ไฟล์ Last_Type.xlsx ไม่มีคอลัมน์ที่จำเป็น (bom_no, Last_type)"
        }
        
        for key, message in error_mappings.items():
            if key in error_msg:
                return message
        
        return f"เกิดข้อผิดพลาด: {error_msg}"
    
    @staticmethod
    def log_and_flash_error(error: Exception, context: str = "", 
                          flash_message: str = None) -> None:
        """Log error and show flash message"""
        logger.error(f"{context}: {error}")
        message = flash_message or f"เกิดข้อผิดพลาด: {str(error)}"
        flash(message, MessageType.ERROR.value)

@app.route("/api/folders")
def get_folders():
    """Get available folders for file selection"""
    try:
        # Define allowed folders (customize as needed)
        base_paths = [
            os.path.join(config.BASE_DIR, "data_logview"),  # For LOGVIEW files
            os.path.join(config.BASE_DIR, "Upload"),        # Upload folder
            os.path.join(config.BASE_DIR, "data"),          # General data folder
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
    functions = FunctionService.list_functions()
    
    if request.method == "POST":
        try:
            # Get function name from form
            func_name = request.form.get('func_name')
            if not func_name:
                flash("กรุณาเลือกฟังก์ชันที่ต้องการประมวลผล", MessageType.ERROR.value)
                return redirect(url_for("index"))

            # Get date range parameters
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            use_all_dates = request.form.get('use_all_dates') == 'on'
            
            # Prepare additional arguments for function
            func_args = {}
            if func_name in ['DIE_ATTACK_AUTO_UPH', 'PNP_AUTO_UPH', 'WB_AUTO_UPH']:
                func_args['start_date'] = start_date
                func_args['end_date'] = end_date
                func_args['use_all_dates'] = use_all_dates
                logger.info(f"Date range parameters - start: {start_date}, end: {end_date}, use_all: {use_all_dates}")

            # Check input method
            input_method = request.form.get('inputMethod', 'upload')
            temp_input = None
            
            if input_method == 'folder':
                # Handle folder-based file selection
                selected_folder = request.form.get('selected_folder')
                selected_files_str = request.form.get('selected_files')
                
                if not selected_folder or not selected_files_str:
                    flash("กรุณาเลือกโฟลเดอร์และไฟล์ที่ต้องการประมวลผล", MessageType.ERROR.value)
                    return redirect(url_for("index"))
                
                selected_filenames = selected_files_str.split(',')
                
                # Process folder files using service
                try:
                    temp_input, output_dir = FileProcessingService.process_folder_files(
                        selected_folder, selected_filenames, func_name, **func_args
                    )
                except Exception as e:
                    ErrorHandler.log_and_flash_error(e, "Folder file processing")
                    return redirect(url_for("index"))
                    
            else:
                # Handle normal file upload
                files = request.files.getlist("input_files")
                if not files or all(f.filename == "" for f in files):
                    flash("กรุณาเลือกไฟล์ก่อน", MessageType.ERROR.value)
                    return redirect(url_for("index"))
                
                # Process uploaded files using service
                try:
                    temp_input, output_dir = FileProcessingService.process_uploaded_files(files, func_name, **func_args)
                except Exception as e:
                    ErrorHandler.log_and_flash_error(e, "File upload processing")
                    return redirect(url_for("index"))
            
            # Find output files using service
            output_files = FileProcessingService.get_output_files(output_dir)
            if not output_files:
                flash("ไม่พบไฟล์ผลลัพธ์ใน output", MessageType.ERROR.value)
                return redirect(url_for("index"))

            # Get latest file
            output_fp = os.path.join(output_dir, output_files[0])
            download_link = TableRenderingService.create_download_link(func_name, output_files[0])

            # Handle table display
            show_table = True
            if show_table:
                try:
                    # อ่านไฟล์ผลลัพธ์เพื่อแสดงเป็นตาราง
                    df, read_warning = FileReader.read_file_safely(output_fp)
                    
                    if df is not None:
                        # แสดงคำเตือนถ้าอ่านไฟล์มีปัญหา
                        if read_warning:
                            flash(read_warning, MessageType.WARNING.value)
                        
                        # สร้างตาราง HTML using service
                        table_html = TableRenderingService.generate_table_html(df, include_index=True)
                        
                        flash("ประมวลผลสำเร็จ", MessageType.SUCCESS.value)
                        return render_template("result.html", 
                                             table_html=table_html, 
                                             download_link=download_link,
                                             total_records=len(df),
                                             func_name=func_name)
                    else:
                        flash(f"ไม่สามารถแสดงตารางได้: {read_warning}", MessageType.WARNING.value)
                        return render_template("result.html", 
                                             table_html=None, 
                                             download_link=download_link,
                                             func_name=func_name)
                        
                except Exception as e:
                    logger.error(f"Error displaying table: {e}")
                    flash(f"ไม่สามารถแสดงตารางได้: {str(e)}", MessageType.WARNING.value)
                    return render_template("result.html", 
                                         table_html=None, 
                                         download_link=download_link,
                                         func_name=func_name)
            else:
                flash("ประมวลผลสำเร็จ สามารถดาวน์โหลดไฟล์ผลลัพธ์ได้", MessageType.SUCCESS.value)
                return render_template("result.html", 
                                     table_html=None, 
                                     download_link=download_link,
                                     func_name=func_name)
                
        except Exception as e:
            ErrorHandler.log_and_flash_error(e, "Main processing route")
            return redirect(url_for("index"))
        finally:
            # ลบไฟล์ชั่วคราวเสมอ
            if temp_input:
                FileProcessingService.cleanup_temp_files(temp_input)
    
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
            output_dir = os.path.join(config.BASE_DIR, "output_lookup_last_type")
        else:
            output_dir = os.path.join(config.BASE_DIR, f"output_{func_name}")
        
        file_path = os.path.join(output_dir, filename)
        
        if not os.path.exists(file_path):
            flash("ไม่พบไฟล์ที่ต้องการดาวน์โหลด", MessageType.ERROR.value)
            return redirect(url_for("index"))
        
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        logger.error(f"Download error: {e}")
        flash(f"เกิดข้อผิดพลาดในการดาวน์โหลด: {str(e)}", MessageType.ERROR.value)
        return redirect(url_for("index"))

@app.route("/api/preview-date-range", methods=["POST"])
def preview_date_range_api():
    """API สำหรับดู preview ช่วงวันที่ในไฟล์"""
    try:
        # ตรวจสอบการอัปโหลดไฟล์
        if 'file' not in request.files:
            return jsonify({'error': 'ไม่พบไฟล์ที่อัปโหลด'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'ไม่ได้เลือกไฟล์'}), 400
        
        # ตรวจสอบนามสกุลไฟล์
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'error': 'รองรับเฉพาะไฟล์ Excel (.xlsx, .xls)'}), 400
        
        # บันทึกไฟล์ชั่วคราว
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, file.filename)
        file.save(temp_file_path)
        
        try:
            # นำเข้าฟังก์ชัน preview_date_range
            import importlib
            die_attack_module = importlib.import_module('functions.DIE_ATTACK_AUTO_UPH')
            preview_date_range = die_attack_module.preview_date_range
            
            # วิเคราะห์ข้อมูลวันที่
            date_info = preview_date_range(temp_file_path)
            
            if date_info:
                # แปลงข้อมูลวันที่ให้เป็น JSON serializable format
                serializable_data = {}
                for key, value in date_info.items():
                    if key == 'monthly_distribution' and isinstance(value, dict):
                        # แปลง Period objects เป็น string format
                        serializable_data[key] = {
                            str(period): count for period, count in value.items()
                        }
                    elif hasattr(value, 'strftime'):
                        # แปลง datetime objects เป็น string format (ค.ศ.)
                        serializable_data[key] = value.strftime('%Y-%m-%d')
                    else:
                        serializable_data[key] = value
                
                return jsonify({
                    'success': True,
                    'data': serializable_data,
                    'message': 'วิเคราะห์ข้อมูลวันที่เรียบร้อย'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'ไม่สามารถวิเคราะห์ข้อมูลวันที่ได้'
                }, 400)
                
        finally:
            # ลบไฟล์ชั่วคราว
            shutil.rmtree(temp_dir)
            
    except Exception as e:
        logger.error(f"Error in preview_date_range_api: {e}")
        return jsonify({'error': f'เกิดข้อผิดพลาด: {str(e)}'}), 500

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
        is_valid, error_msg = FileValidator.validate_file(file)
        if not is_valid:
            flash(error_msg, MessageType.ERROR.value)
            return redirect(url_for("lookup_last_type_route"))
        
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, file.filename)
        
        try:
            # บันทึกไฟล์ก่อน
            file.save(file_path)
            logger.info(f"💾 บันทึกไฟล์แล้ว: {file_path}")
            
            # ตรวจสอบไฟล์หลังบันทึกแล้ว
            temp_df, read_warning = FileReader.read_file_safely(file_path)
            
            if temp_df is None:
                flash(f"ไม่สามารถอ่านไฟล์ได้: {read_warning}", MessageType.ERROR.value)
                return redirect(url_for("lookup_last_type_route"))
            
            # แสดง warning ถ้ามี
            if read_warning:
                flash(read_warning, MessageType.WARNING.value)
            
            logger.info(f"📋 ไฟล์ที่อัปโหลดมีคอลัมน์: {list(temp_df.columns)}")
            logger.info(f"📊 จำนวนแถว: {len(temp_df)}")
            
            # ตรวจสอบคอลัมน์ bom_no ด้วย service
            is_valid_bom, result = LookupService.validate_bom_file(temp_df)
            if not is_valid_bom:
                flash(result, MessageType.ERROR.value)
                return redirect(url_for("lookup_last_type_route"))
            
            logger.info(f"✅ พบคอลัมน์ BOM: {result}")
            
            # ดำเนินการ lookup ด้วย service
            logger.info("🔍 เริ่มค้นหาข้อมูล...")
            df_result = LookupService.process_lookup(file_path)
            
            if df_result is not None and not df_result.empty:
                # สร้างตาราง HTML ด้วย service
                table_html = TableRenderingService.generate_table_html(df_result, include_index=True)
                
                # Save result using service
                download_dir = os.path.join(config.BASE_DIR, "output_lookup_last_type")
                filename, result_path = DataFrameUtils.save_dataframe(df_result, download_dir, "last_type_result")
                
                download_link = TableRenderingService.create_download_link('lookup_last_type', filename)
                total_records = len(df_result)
                
                # นับจำนวนที่พบและไม่พบ ด้วย service
                found_count, not_found_count = LookupService.count_lookup_results(df_result)
                
                flash(f"ค้นหาเสร็จสิ้น: พบข้อมูล {found_count} รายการ, ไม่พบ {not_found_count} รายการ", MessageType.SUCCESS.value)
            else:
                flash("ไม่พบข้อมูลที่ตรงกัน", MessageType.WARNING.value)
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Error details: {error_msg}")
            
            # ใช้ ErrorHandler แปลงข้อความ error
            user_friendly_msg = ErrorHandler.handle_lookup_error(error_msg)
            flash(user_friendly_msg, MessageType.ERROR.value)
                
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    return render_template("lookup_last_type.html", 
                         table_html=table_html, 
                         download_link=download_link,
                         total_records=total_records)


@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all other exceptions"""
    logger.error(f"Unhandled exception: {e}")
    flash("เกิดข้อผิดพลาดที่ไม่คาดคิด กรุณาลองใหม่อีกครั้ง", "error")
    return redirect(url_for("index"))

# ===== Error Handler Class =====
class ErrorHandler:
    """
    Class สำหรับจัดการ error แบบรวมศูนย์
    """
    
    @staticmethod
    def handle_lookup_error(error_msg):

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
            flash(flash_message, MessageType.ERROR.value)
        else:
            flash(f"เกิดข้อผิดพลาด: {str(error)}", MessageType.ERROR.value)

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

# ===== LOGGING CONFIGURATION =====
def setup_logging() -> logging.Logger:
    """Configure application logging (console only, no file)"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        handlers=[
            logging.StreamHandler()  # log เฉพาะที่ console
            # ไม่มี FileHandler('app.log')
        ]
    )
    return logging.getLogger("webapp")

logger = setup_logging()

# ===== FILE CLEANUP SERVICE =====
class FileCleanupService:
    """Service สำหรับจัดการทำความสะอาดไฟล์เก่า"""
    
    @staticmethod
    def cleanup_old_files(directory: str, days_old: int = 7, dry_run: bool = False) -> Dict[str, int]:
        """
        ลบไฟล์เก่าที่เก็บไว้เกินกำหนด
        
        Args:
            directory: โฟลเดอร์ที่ต้องการทำความสะอาด
            days_old: จำนวนวันที่จะเก็บไฟล์ (default: 7 วัน)
            dry_run: ถ้า True จะแสดงผลเฉพาะไฟล์ที่จะลบ (ไม่ลบจริง)
            
        Returns:
            Dict ที่มีสถิติการลบไฟล์
        """
        if not os.path.exists(directory):
            return {"deleted": 0, "total_size": 0, "error": "Directory not found"}
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        deleted_count = 0
        deleted_size = 0
        errors = []
        
        try:
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                
                # ตรวจสอบว่าเป็นไฟล์และไม่ใช่โฟลเดอร์
                if os.path.isfile(file_path):
                    try:
                        # ตรวจสอบวันที่แก้ไขล่าสุด
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        
                        if file_mtime < cutoff_date:
                            file_size = os.path.getsize(file_path)
                            
                            if not dry_run:
                                os.remove(file_path)
                                logger.info(f"🗑️ ลบไฟล์เก่า: {filename} (อายุ: {(datetime.now() - file_mtime).days} วัน)")
                            
                            deleted_count += 1
                            deleted_size += file_size
                            
                    except Exception as e:
                        errors.append(f"Error processing {filename}: {str(e)}")
                        logger.error(f"Error deleting file {filename}: {e}")
                        
        except Exception as e:
            errors.append(f"Error accessing directory: {str(e)}")
            logger.error(f"Error accessing directory {directory}: {e}")
        
        return {
            "deleted": deleted_count,
            "total_size": deleted_size,
            "errors": errors,
            "cutoff_date": cutoff_date.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    @staticmethod
    def cleanup_all_output_folders(days_old: int = 7, dry_run: bool = False) -> Dict[str, Dict]:
        """ทำความสะอาดโฟลเดอร์ output ทั้งหมด"""
        output_dirs = [
            os.path.join(config.BASE_DIR, "output_lookup_last_type"),
            os.path.join(config.BASE_DIR, "output_DIE_ATTACK_AUTO_UPH"),
            os.path.join(config.BASE_DIR, "output_PNP_AUTO_UPH"),
            os.path.join(config.BASE_DIR, "output_WB_AUTO_UPH"),
            os.path.join(config.BASE_DIR, "output_PNP_CHANG_TYPE"),
        ]
        
        results = {}
        total_deleted = 0
        total_size = 0
        
        for output_dir in output_dirs:
            if os.path.exists(output_dir):
                folder_name = os.path.basename(output_dir)
                result = FileCleanupService.cleanup_old_files(output_dir, days_old, dry_run)
                results[folder_name] = result
                total_deleted += result["deleted"]
                total_size += result["total_size"]
        
        results["summary"] = {
            "total_deleted": total_deleted,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "cleanup_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return results
    
    @staticmethod
    def schedule_cleanup():
        """ตั้งเวลาทำความสะอาดไฟล์เก่าทุก 24 ชั่วโมง"""
        def cleanup_job():
            while True:
                try:
                    logger.info("🧹 เริ่มทำความสะอาดไฟล์เก่า...")
                    results = FileCleanupService.cleanup_all_output_folders(days_old=7, dry_run=False)
                    
                    if results["summary"]["total_deleted"] > 0:
                        logger.info(f" ทำความสะอาดเสร็จสิ้น: ลบ {results['summary']['total_deleted']} ไฟล์ "
                                  f"ประหยัดพื้นที่ {results['summary']['total_size_mb']} MB")
                    else:
                        logger.info("ℹ ไม่มีไฟล์เก่าที่ต้องลบ")
                    
                    # รอ 24 ชั่วโมง (86400 วินาที)
                    time.sleep(86400)
                    
                except Exception as e:
                    logger.error(f"Error in cleanup job: {e}")
                    time.sleep(3600)  # รอ 1 ชั่วโมงแล้วลองใหม่
        
        # เริ่ม background thread
        cleanup_thread = threading.Thread(target=cleanup_job, daemon=True)
        cleanup_thread.start()
        logger.info("🕐 ตั้งระบบทำความสะอาดไฟล์เก่าแล้ว (ทุก 24 ชั่วโมง)")

@app.route("/process_logview_all")
def process_logview_all():
    try:
        from functions.LOGVIEW import run
        data_logview = os.path.join(config.BASE_DIR, "data_logview")  # ✅ ชี้ไปที่ src/data_logview
        output_dir = os.path.join(config.BASE_DIR, "output_LOGVIEW")
        os.makedirs(output_dir, exist_ok=True)
        run(data_logview, output_dir)
        flash("ประมวลผล LOGVIEW ทั้งหมดเสร็จสิ้น!", "success")
    except Exception as e:
        import traceback
        logger.error(f"Error in process_logview_all: {e}\n{traceback.format_exc()}")
        flash(f"เกิดข้อผิดพลาด: {e}", "error")
    return redirect(url_for("index"))

if __name__ == "__main__":
    
    os.makedirs(os.path.join(config.BASE_DIR, AppConstants.OUTPUT_DIR_LOOKUP), exist_ok=True)
    os.makedirs(config.FUNCTIONS_DIR, exist_ok=True)
    
    # ⭐ เริ่มระบบทำความสะอาดไฟล์เก่าอัตโนมัติ
    FileCleanupService.schedule_cleanup()
    
    # หา IP address สำหรับแสดงใน log
    try:
        ip = socket.gethostbyname(socket.gethostname())
        logger.info("🚀 IE Function : Starting...")
        logger.info(f"   Local:   http://127.0.0.1:{config.PORT}")
        logger.info(f"   Network: http://{ip}:{config.PORT}")
        logger.info(f"   Debug:   {config.DEBUG}")
        logger.info(f"   Functions: {FunctionService.list_functions()}")
    except Exception as e:
        logger.error(f"Network detection failed: {e}")
        ip = "127.0.0.1"
    
    # เริ่มต้น Flask application
    app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT, threaded=True)

# ===== Version Information =====
# version 3.0 - Fully Refactored with Service Classes and Modern Architecture