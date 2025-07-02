# Template สำหรับ Function ใหม่

import pandas as pd
import os
import glob
from datetime import datetime

def run(input_path, output_dir):
    """
    Template สำหรับสร้าง function ใหม่
    
    Args:
        input_path (str): path ของโฟลเดอร์ที่มีไฟล์อัปโหลด
        output_dir (str): path ของโฟลเดอร์สำหรับบันทึกผลลัพธ์
    
    Returns:
        pandas.DataFrame: ผลลัพธ์ที่จะแสดงในตาราง (optional)
    """
    try:
        print(f"🚀 เริ่มต้น TEMPLATE_FUNCTION")
        print(f"📁 Input path: {input_path}")
        print(f"📁 Output path: {output_dir}")
        
        # 1. หาไฟล์ที่อัปโหลด
        excel_files = []
        for pattern in ['*.xlsx', '*.xls', '*.csv']:
            excel_files.extend(glob.glob(os.path.join(input_path, pattern)))
        
        if not excel_files:
            raise ValueError("ไม่พบไฟล์ Excel หรือ CSV ในโฟลเดอร์")
        
        print(f"📋 พบไฟล์: {len(excel_files)} ไฟล์")
        
        # 2. อ่านไฟล์แรก
        input_file = excel_files[0]
        print(f"📖 กำลังอ่านไฟล์: {os.path.basename(input_file)}")
        
        if input_file.lower().endswith('.csv'):
            df = pd.read_csv(input_file, encoding='utf-8')
        else:
            df = pd.read_excel(input_file)
        
        print(f"📊 อ่านข้อมูลสำเร็จ: {len(df)} แถว, {len(df.columns)} คอลัมน์")
        print(f"📋 คอลัมน์: {list(df.columns)}")
        
        # 3. ประมวลผลข้อมูล (แก้ไขส่วนนี้ตามต้องการ)
        
        # ตัวอย่าง: เพิ่มคอลัมน์ timestamp
        df['processed_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # ตัวอย่าง: เพิ่มคอลัมน์ status
        df['processing_status'] = 'completed'
        
        # ตัวอย่าง: คำนวณสถิติ
        if len(df.select_dtypes(include='number').columns) > 0:
            numeric_cols = df.select_dtypes(include='number').columns
            df['row_sum'] = df[numeric_cols].sum(axis=1)
        
        print(f"✅ ประมวลผลเสร็จสิ้น")
        
        # 4. บันทึกผลลัพธ์
        os.makedirs(output_dir, exist_ok=True)
        
        # สร้างชื่อไฟล์ผลลัพธ์
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"TEMPLATE_FUNCTION_result_{timestamp}.xlsx"
        output_file = os.path.join(output_dir, output_filename)
        
        # บันทึกไฟล์
        df.to_excel(output_file, index=False)
        print(f"💾 บันทึกผลลัพธ์: {output_file}")
        
        # 5. แสดงสถิติ
        print(f"📈 สถิติผลลัพธ์:")
        print(f"   - จำนวนแถว: {len(df)}")
        print(f"   - จำนวนคอลัมน์: {len(df.columns)}")
        if 'processing_status' in df.columns:
            status_counts = df['processing_status'].value_counts()
            for status, count in status_counts.items():
                print(f"   - {status}: {count} รายการ")
        
        # 6. คืนค่า DataFrame สำหรับแสดงในเว็บ
        return df
        
    except Exception as e:
        print(f"❌ Error in TEMPLATE_FUNCTION: {e}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        raise e

def validate_input_data(df):
    """
    Validate input data
    
    Args:
        df (pd.DataFrame): Input DataFrame
        
    Returns:
        bool: True if valid, False otherwise
        str: Error message if invalid
    """
    try:
        # ตรวจสอบว่า DataFrame ไม่ว่าง
        if df.empty:
            return False, "ไฟล์ไม่มีข้อมูล"
        
        # ตรวจสอบคอลัมน์ที่จำเป็น (แก้ไขตามต้องการ)
        required_columns = []  # เช่น ['column1', 'column2']
        
        if required_columns:
            missing_cols = [col for col in required_columns if col not in df.columns]
            if missing_cols:
                available_cols = ", ".join(df.columns)
                return False, f"ไม่พบคอลัมน์ที่จำเป็น: {missing_cols}. คอลัมน์ที่มี: {available_cols}"
        
        # ตรวจสอบอื่นๆ เพิ่มเติม
        
        return True, None
        
    except Exception as e:
        return False, f"Error in validation: {str(e)}"

def cleanup_data(df):
    """
    Clean and prepare data
    
    Args:
        df (pd.DataFrame): Input DataFrame
        
    Returns:
        pd.DataFrame: Cleaned DataFrame
    """
    try:
        # ลบแถวที่ว่าง
        df = df.dropna(how='all')
        
        # ลบ duplicates (ถ้าต้องการ)
        # df = df.drop_duplicates()
        
        # เปลี่ยน data types (ถ้าต้องการ)
        # df['column_name'] = df['column_name'].astype('type')
        
        # ล้างข้อมูลในคอลัมน์ text
        for col in df.select_dtypes(include='object').columns:
            df[col] = df[col].astype(str).str.strip()
        
        return df
        
    except Exception as e:
        print(f"❌ Error in cleanup_data: {e}")
        return df

# เพิ่ม helper functions อื่นๆ ตามต้องการ
