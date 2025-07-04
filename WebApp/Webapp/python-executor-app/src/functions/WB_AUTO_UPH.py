import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime

def apply_zscore(df):
    """ตัด outliers ด้วยวิธี Z-Score (±3 standard deviations)"""
    col_map = {col.lower(): col for col in df.columns}
    if 'uph' not in col_map:
        raise KeyError("ไม่พบคอลัมน์ UPH ในข้อมูล")
    uph_col = col_map['uph']

    mean = df[uph_col].mean()
    std = df[uph_col].std()
    if std == 0:
        return df  # ถ้า std = 0, return ค่าเดิม
    z_scores = (df[uph_col] - mean) / std
    filtered = df[(z_scores >= -3) & (z_scores <= 3)].copy()
    filtered['Outlier_Method'] = 'Z-Score ±3'
    return filtered

def has_outlier(df):
    """ตรวจสอบว่ามี outliers หรือไม่ด้วยวิธี IQR"""
    col_map = {col.lower(): col for col in df.columns}
    if 'uph' not in col_map:
        raise KeyError("ไม่พบคอลัมน์ UPH ในข้อมูล")
    uph_col = col_map['uph']

    Q1 = df[uph_col].quantile(0.25)
    Q3 = df[uph_col].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    return ((df[uph_col] < lower) | (df[uph_col] > upper)).sum() > 0

def apply_iqr(df):
    """ตัด outliers ด้วยวิธี IQR (Interquartile Range)"""
    col_map = {col.lower(): col for col in df.columns}
    if 'uph' not in col_map:
        raise KeyError("ไม่พบคอลัมน์ UPH ในข้อมูล")
    uph_col = col_map['uph']

    Q1 = df[uph_col].quantile(0.25)
    Q3 = df[uph_col].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    filtered = df[(df[uph_col] >= lower) & (df[uph_col] <= upper)].copy()
    filtered['Outlier_Method'] = 'IQR'
    return filtered

def remove_outliers_auto(df_model, max_iter=20):
    """ตัด outliers อัตโนมัติด้วยการใช้ Z-Score และ IQR แบบวนลูป"""
    col_map = {col.lower(): col for col in df_model.columns}
    if 'uph' not in col_map:
        raise KeyError("ไม่พบคอลัมน์ UPH ในข้อมูล")
    uph_col = col_map['uph']

    df_model[uph_col] = pd.to_numeric(df_model[uph_col], errors='coerce')
    df_model = df_model.dropna(subset=[uph_col])

    if len(df_model) < 15:  
        df_model['Outlier_Method'] = 'ไม่ตัด (ข้อมูลน้อย)'
        return df_model

    current_df = df_model.copy()

    for i in range(max_iter):
        print(f"=== รอบที่ {i+1} ===")
        z_df = apply_zscore(current_df)
        if not has_outlier(z_df):
            z_df['Outlier_Method'] = f'Z-Score Loop ×{i+1}'
            return z_df

        iqr_df = apply_iqr(z_df)
        if not has_outlier(iqr_df):
            iqr_df['Outlier_Method'] = f'IQR Loop ×{i+1}'
            return iqr_df

        current_df = iqr_df

    current_df['Outlier_Method'] = f'IQR-Z-Score Loop ×{max_iter}+'
    return current_df

def remove_outliers(df):
    """ตัด outliers ตามกลุ่ม BOM และ Machine Model"""
    col_map = {col.lower(): col for col in df.columns}
    
    # หาคอลัมน์ Machine Model
    model_col = None
    if 'machine model' in col_map:
        model_col = col_map['machine model']
    elif 'machine_model' in col_map:
        model_col = col_map['machine_model']
    else:
        raise KeyError("ไม่พบคอลัมน์ Machine Model หรือ Machine_Model ในข้อมูล")
    
    # หาคอลัมน์ bom_no
    bom_col = None
    if 'bom_no' in col_map:
        bom_col = col_map['bom_no']
    elif 'bom no' in col_map:
        bom_col = col_map['bom no']
    else:
        raise KeyError("ไม่พบคอลัมน์ bom_no ในข้อมูล")
    
    # รวมข้อมูลที่ผ่านการตัด outliers ตามกลุ่ม bom_no และ Machine Model
    result_dfs = []
    
    # จัดกลุ่มตาม bom_no และ Machine Model
    for (bom_no, machine_model), group_df in df.groupby([bom_col, model_col]):
        print(f"ประมวลผลกลุ่ม: BOM={bom_no}, Machine={machine_model}, จำนวนข้อมูล={len(group_df)}")
        
        # ตัด outliers สำหรับแต่ละกลุ่ม
        cleaned_group = remove_outliers_auto(group_df)
        result_dfs.append(cleaned_group)
    
    # รวมผลลัพธ์ทั้งหมด
    return pd.concat(result_dfs, ignore_index=True)

def time_series_analysis(df):
    """แปลงข้อมูลวันที่ให้อยู่ในรูปแบบที่ใช้งานได้"""
    col_map = {col.lower(): col for col in df.columns}
    
    # หาคอลัมน์วันที่ที่เป็นไปได้
    date_cols = []
    for col_name in df.columns:
        if any(keyword in col_name.lower() for keyword in ['date', 'time', 'วัน', 'เวลา']):
            date_cols.append(col_name)
    
    if not date_cols:
        print("ไม่พบคอลัมน์วันที่ในข้อมูล")
        return df
    
    # ใช้คอลัมน์วันที่แรกที่พบ
    date_col = date_cols[0]
    print(f"ใช้คอลัมน์วันที่: {date_col}")
    
    # แปลงเป็น datetime และจัดรูปแบบ
    df['date_time_start'] = pd.to_datetime(df[date_col], errors='coerce')
    
    # จัดรูปแบบเป็น YYYY/MM/DD
    df['date_time_start'] = df['date_time_start'].dt.strftime('%Y/%m/%d')
    
    # กรองข้อมูลที่แปลงไม่ได้
    invalid_dates = df['date_time_start'].isna().sum()
    if invalid_dates > 0:
        print(f"พบวันที่ที่แปลงไม่ได้: {invalid_dates} แถว")
        df = df.dropna(subset=['date_time_start'])
    
    print(f"แปลงวันที่เสร็จสิ้น รูปแบบ: {df['date_time_start'].iloc[0] if len(df) > 0 else 'ไม่มีข้อมูล'}")
    
    return df
    
def find_max_or_min_date(df):
    if 'date_time_start' not in df.columns:
        raise KeyError("ไม่พบคอลัมน์ date_time_start ในข้อมูล")

    max_date = df['date_time_start'].max()
    min_date = df['date_time_start'].min()
    return max_date, min_date

def get_date_range_auto(df):
    """สร้างช่วงวันที่อัตโนมัติ (ใช้ทั้งหมด)"""
    max_date, min_date = find_max_or_min_date(df)
    print(f"ใช้ช่วงวันที่ทั้งหมด: {min_date} ถึง {max_date}")
    return min_date, max_date

def filter_data_by_date(df, start_date, end_date):
    """กรองข้อมูลตามช่วงวันที่ที่เลือก"""
    print(f"\n=== กรองข้อมูลตามช่วงวันที่ {start_date} ถึง {end_date} ===")
    
    # กรองข้อมูลตามช่วงวันที่
    filtered_df = df[df['date_time_start'].between(start_date, end_date)].copy()
    
    if len(filtered_df) == 0:
        print("ไม่พบข้อมูลในช่วงวันที่ที่เลือก")
        return None
    
    print(f"พบข้อมูล {len(filtered_df)} แถว ในช่วงวันที่ที่เลือก")
    print(f"ข้อมูลเดิม: {len(df)} แถว")
    print(f"ข้อมูลที่กรอง: {len(filtered_df)} แถว ({len(filtered_df)/len(df)*100:.1f}%)")
    
    return filtered_df

def calculate_group_average(df, start_date, end_date):
    """คำนวณค่าเฉลี่ยตามกลุ่ม"""
    col_map = {col.lower(): col for col in df.columns}
    
    # หาคอลัมน์ Machine Model
    model_col = None
    if 'machine model' in col_map:
        model_col = col_map['machine model']
    elif 'machine_model' in col_map:
        model_col = col_map['machine_model']
    else:
        raise KeyError("ไม่พบคอลัมน์ Machine Model หรือ Machine_Model ในข้อมูล")
    
    # หาคอลัมน์ bom_no
    bom_col = None
    if 'bom_no' in col_map:
        bom_col = col_map['bom_no']
    elif 'bom no' in col_map:
        bom_col = col_map['bom no']
    else:
        raise KeyError("ไม่พบคอลัมน์ bom_no ในข้อมูล")
    
    # หาคอลัมน์ UPH
    uph_col = None
    if 'uph' in col_map:
        uph_col = col_map['uph']
    else:
        raise KeyError("ไม่พบคอลัมน์ UPH ในข้อมูล")
    
    # คำนวณค่าเฉลี่ยตามกลุ่ม
    grouped_average = df.groupby([bom_col, model_col])[uph_col].mean().reset_index()
    
    # แสดงผลลัพธ์
    print(f"\n=== ค่าเฉลี่ย UPH ตามกลุ่ม (ช่วงวันที่ {start_date} ถึง {end_date}) ===")
    print(grouped_average)
    
    return grouped_average

def save_results(df_cleaned, grouped_average, start_date, end_date, output_dir):
    """บันทึกผลลัพธ์ลงไฟล์"""
    os.makedirs(output_dir, exist_ok=True)
    
    # สร้างชื่อไฟล์ด้วยวันที่และเวลา
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    date_range = f"{start_date.replace('/', '')}_to_{end_date.replace('/', '')}"
    
    # บันทึกข้อมูลที่ตัด outliers แล้ว
    cleaned_file = os.path.join(output_dir, f"cleaned_data_{date_range}_{timestamp}.xlsx")
    df_cleaned.to_excel(cleaned_file, index=False)
    print(f"บันทึกข้อมูลที่ตัด outliers แล้ว: {cleaned_file}")
    
    # บันทึกค่าเฉลี่ยตามกลุ่ม
    average_file = os.path.join(output_dir, f"group_average_{date_range}_{timestamp}.xlsx")
    grouped_average.to_excel(average_file, index=False)
    print(f"บันทึกค่าเฉลี่ยตามกลุ่ม: {average_file}")
    
    return cleaned_file, average_file

def process_die_attack_data(file_path):
    """ประมวลผลข้อมูล Die Attack"""
    print("=== เริ่มต้นการประมวลผลข้อมูล Die Attack ===")
    
    # อ่านไฟล์ข้อมูล
    try:
        df = pd.read_excel(file_path)
        print(f"ข้อมูลเริ่มต้น: {len(df)} แถว")
    except Exception as e:
        raise Exception(f"ไม่สามารถอ่านไฟล์ได้: {str(e)}")
    
    # ขั้นตอนที่ 1: แปลงข้อมูลวันที่
    print("\n1. แปลงข้อมูลวันที่...")
    df = time_series_analysis(df)
    
    # ขั้นตอนที่ 2: ใช้ช่วงวันที่ทั้งหมด (อัตโนมัติ)
    print("\n2. กำหนดช่วงวันที่...")
    start_date, end_date = get_date_range_auto(df)
    
    # ขั้นตอนที่ 3: กรองข้อมูลตามวันที่
    print("\n3. กรองข้อมูลตามวันที่...")
    df_filtered = filter_data_by_date(df, start_date, end_date)
    
    if df_filtered is None:
        raise Exception("ไม่มีข้อมูลในช่วงวันที่ที่เลือก")
    
    # ขั้นตอนที่ 4: ตัด outliers
    print("\n4. ตัด outliers...")
    df_cleaned = remove_outliers(df_filtered)
    df_cleaned = df_cleaned.reset_index(drop=True)
    
    print(f"ข้อมูลหลังตัด outliers: {len(df_cleaned)} แถว")
    
    # ขั้นตอนที่ 5: คำนวณค่าเฉลี่ยตามกลุ่ม
    print("\n5. คำนวณค่าเฉลี่ยตามกลุ่ม...")
    grouped_average = calculate_group_average(df_cleaned, start_date, end_date)
    
    print("\n=== การประมวลผลเสร็จสิ้น ===")
    print(f"ข้อมูลสุดท้าย: {len(df_cleaned)} แถว")
    print(f"จำนวนกลุ่ม: {len(grouped_average)} กลุ่ม")
    
    return df_cleaned, grouped_average, start_date, end_date

def process_die_attack_data_with_date_range(file_path, start_date, end_date):
    """ประมวลผลข้อมูล Die Attack ด้วยช่วงวันที่ที่กำหนด"""
    print("=== เริ่มต้นการประมวลผลข้อมูล Die Attack (ช่วงวันที่กำหนด) ===")
    
    # อ่านไฟล์ข้อมูล
    try:
        df = pd.read_excel(file_path)
        print(f"ข้อมูลเริ่มต้น: {len(df)} แถว")
    except Exception as e:
        raise Exception(f"ไม่สามารถอ่านไฟล์ได้: {str(e)}")
    
    # ขั้นตอนที่ 1: แปลงข้อมูลวันที่
    print("\n1. แปลงข้อมูลวันที่...")
    df = time_series_analysis(df)
    
    # ขั้นตอนที่ 2: แปลงวันที่จาก YYYY-MM-DD เป็น YYYY/MM/DD
    print(f"\n2. ใช้ช่วงวันที่ที่กำหนด: {start_date} ถึง {end_date}")
    formatted_start_date = start_date.replace('-', '/')
    formatted_end_date = end_date.replace('-', '/')
    
    # ขั้นตอนที่ 3: กรองข้อมูลตามวันที่
    print("\n3. กรองข้อมูลตามวันที่...")
    df_filtered = filter_data_by_date(df, formatted_start_date, formatted_end_date)
    
    if df_filtered is None:
        raise Exception("ไม่มีข้อมูลในช่วงวันที่ที่เลือก")
    
    # ขั้นตอนที่ 4: ตัด outliers
    print("\n4. ตัด outliers...")
    df_cleaned = remove_outliers(df_filtered)
    df_cleaned = df_cleaned.reset_index(drop=True)
    
    print(f"ข้อมูลหลังตัด outliers: {len(df_cleaned)} แถว")
    
    # ขั้นตอนที่ 5: คำนวณค่าเฉลี่ยตามกลุ่ม
    print("\n5. คำนวณค่าเฉลี่ยตามกลุ่ม...")
    grouped_average = calculate_group_average(df_cleaned, formatted_start_date, formatted_end_date)
    
    print("\n=== การประมวลผลเสร็จสิ้น ===")
    print(f"ข้อมูลสุดท้าย: {len(df_cleaned)} แถว")
    print(f"จำนวนกลุ่ม: {len(grouped_average)} กลุ่ม")
    
    return df_cleaned, grouped_average, formatted_start_date, formatted_end_date

def preview_date_range(file_path):
    """แสดงข้อมูลวันที่ในไฟล์ก่อนประมวลผล"""
    try:
        print("📅 กำลังตรวจสอบช่วงวันที่ในไฟล์...")
        
        # อ่านไฟล์ข้อมูล
        df = pd.read_excel(file_path)
        print(f"📄 ไฟล์มีข้อมูลทั้งหมด: {len(df):,} แถว")
        
        # หาคอลัมน์วันที่
        date_cols = []
        for col_name in df.columns:
            if any(keyword in col_name.lower() for keyword in ['date', 'time', 'วัน', 'เวลา']):
                date_cols.append(col_name)
        
        if not date_cols:
            print("⚠️ ไม่พบคอลัมน์วันที่ในข้อมูล")
            return None
        
        date_col = date_cols[0]
        print(f"🗓️ ใช้คอลัมน์วันที่: '{date_col}'")
        
        # แปลงข้อมูลวันที่
        df['temp_date'] = pd.to_datetime(df[date_col], errors='coerce')
        
        # กรองข้อมูลที่แปลงวันที่ได้
        valid_dates = df.dropna(subset=['temp_date'])
        invalid_count = len(df) - len(valid_dates)
        
        if len(valid_dates) == 0:
            print("❌ ไม่มีข้อมูลวันที่ที่ถูกต้องในไฟล์")
            return None
        
        # หาวันที่เริ่มต้นและสิ้นสุด
        min_date = valid_dates['temp_date'].min()
        max_date = valid_dates['temp_date'].max()
        
        # แสดงผลลัพธ์
        print(f"\n📊 สรุปข้อมูลวันที่:")
        print(f"  🗓️ วันที่เริ่มต้น: {min_date.strftime('%Y-%m-%d')} (ค.ศ.)")
        print(f"  🗓️ วันที่สิ้นสุด: {max_date.strftime('%Y-%m-%d')} (ค.ศ.)")
        print(f"  📈 จำนวนวัน: {(max_date - min_date).days + 1} วัน")
        print(f"  ✅ ข้อมูลวันที่ถูกต้อง: {len(valid_dates):,} แถว")
        
        if invalid_count > 0:
            print(f"  ⚠️ ข้อมูลวันที่ไม่ถูกต้อง: {invalid_count:,} แถว")
        
        # แสดงตัวอย่างข้อมูลตามช่วงเวลา
        print(f"\n📋 การกระจายข้อมูลตามเดือน:")
        monthly_counts = valid_dates.groupby(valid_dates['temp_date'].dt.to_period('M')).size()
        for period, count in monthly_counts.head(10).items():
            print(f"  📅 {period}: {count:,} แถว")
        
        if len(monthly_counts) > 10:
            print(f"  ... และอีก {len(monthly_counts) - 10} เดือน")
        
        return {
            'min_date': min_date.strftime('%Y-%m-%d'),
            'max_date': max_date.strftime('%Y-%m-%d'),
            'total_days': (max_date - min_date).days + 1,
            'valid_records': len(valid_dates),
            'invalid_records': invalid_count,
            'date_column': date_col,
            'monthly_distribution': {str(period): count for period, count in monthly_counts.to_dict().items()}
        }
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการตรวจสอบวันที่: {str(e)}")
        return None

def run(input_dir, output_dir, start_date=None, end_date=None, use_all_dates=True):

    print("🚀 เริ่มต้นการประมวลผล Die Attack Auto UPH")
    print(f"📁 Input directory: {input_dir}")
    print(f"📁 Output directory: {output_dir}")
    
    if not use_all_dates and start_date and end_date:
        print(f"📅 ช่วงวันที่: {start_date} ถึง {end_date}")
    else:
        print("📅 ใช้ข้อมูลทั้งหมด")
    
    try:
        # ตรวจสอบว่าโฟลเดอร์ input มีอยู่จริง
        if not os.path.exists(input_dir):
            raise Exception(f"ไม่พบโฟลเดอร์ input: {input_dir}")
        
        # ค้นหาไฟล์ Excel ในโฟลเดอร์ input
        excel_files = []
        for file in os.listdir(input_dir):
            if file.lower().endswith(('.xlsx', '.xls')):
                excel_files.append(os.path.join(input_dir, file))
        
        if not excel_files:
            raise Exception("ไม่พบไฟล์ Excel ในโฟลเดอร์ input")
        
        # ใช้ไฟล์แรกที่พบ
        input_file = excel_files[0]
        print(f"📄 ใช้ไฟล์: {os.path.basename(input_file)}")
        
        # แสดงข้อมูลช่วงวันที่ในไฟล์ก่อนประมวลผล
        print(f"\n" + "="*50)
        print("🔍 การตรวจสอบข้อมูลวันที่ในไฟล์")
        print("="*50)
        
        date_info = preview_date_range(input_file)
        
        if date_info:
            print(f"\n💡 คำแนะนำ:")
            print(f"  • หากต้องการประมวลผลข้อมูลทั้งหมด ให้เลือก 'ใช้ข้อมูลทั้งหมด'")
            print(f"  • หากต้องการเลือกช่วงวันที่ ให้กำหนดวันที่ระหว่าง {date_info['min_date']} ถึง {date_info['max_date']}")
        
        print(f"\n" + "="*50)
        print("🚀 เริ่มการประมวลผลข้อมูล")
        print("="*50)
        
        # ประมวลผลข้อมูลตามการตั้งค่าวันที่
        if use_all_dates:
            df_cleaned, grouped_average, actual_start_date, actual_end_date = process_die_attack_data(input_file)
        else:
            df_cleaned, grouped_average, actual_start_date, actual_end_date = process_die_attack_data_with_date_range(
                input_file, start_date, end_date
            )
        
        # บันทึกผลลัพธ์
        cleaned_file, average_file = save_results(
            df_cleaned, grouped_average, actual_start_date, actual_end_date, output_dir
        )
        
        # สร้างรายงานสรุป
        summary = {
            'input_file': os.path.basename(input_file),
            'cleaned_file': os.path.basename(cleaned_file),
            'average_file': os.path.basename(average_file),
            'total_records': len(df_cleaned),
            'groups_count': len(grouped_average),
            'date_range': f"{actual_start_date} ถึง {actual_end_date}",
            'use_all_dates': use_all_dates,
            'processing_date_range': {
                'start': actual_start_date,
                'end': actual_end_date,
                'user_defined': not use_all_dates
            },
            'file_date_info': date_info,  # รวมข้อมูลวันที่ของไฟล์
            'status': 'success'
        }
        
        print(f"\n✅ ประมวลผลเสร็จสิ้น!")
        print(f"📊 ไฟล์ข้อมูลที่ตัด outliers: {os.path.basename(cleaned_file)}")
        print(f"📈 ไฟล์ค่าเฉลี่ยตามกลุ่ม: {os.path.basename(average_file)}")
        print(f"📋 จำนวนข้อมูลทั้งหมด: {len(df_cleaned):,} แถว")
        print(f"📊 จำนวนกลุ่ม: {len(grouped_average)} กลุ่ม")
        
        return summary
        
    except Exception as e:
        error_msg = f"❌ เกิดข้อผิดพลาด: {str(e)}"
        print(error_msg)
        
        # สร้างรายงานข้อผิดพลาด
        error_summary = {
            'status': 'error',
            'error_message': str(e),
            'input_dir': input_dir,
            'output_dir': output_dir
        }
        
        return error_summary

