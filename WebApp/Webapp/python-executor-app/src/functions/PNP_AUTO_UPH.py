import pandas as pd
import numpy as np  

df = pd.read_excel("data/APL_utl1_2024Q1_DIE_ATTACH_MAP.xlsx")

def apply_zscore(df):
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
    """Apply IQR Method one time."""
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

def select_date_range(df):
    """ให้ผู้ใช้เลือกช่วงวันที่ก่อนประมวลผล"""
    print("=== การเลือกช่วงวันที่สำหรับประมวลผล ===")
    
    # แสดงข้อมูลช่วงวันที่ที่มีในข้อมูล
    max_date, min_date = find_max_or_min_date(df)
    print(f"ช่วงวันที่ที่มีข้อมูล: {min_date} ถึง {max_date}")
    
    # แสดงตัวอย่างวันที่ที่มีในข้อมูล
    print("\nตัวอย่างวันที่ที่มีในข้อมูล:")
    sample_dates = df['date_time_start'].unique()[:5]
    for date in sample_dates:
        print(f"  - {date}")
    
    print("\nกรอกวันที่ในรูปแบบ YYYY/MM/DD (เช่น 2024/01/15)")
    print("(กดเว้นวรรคเพื่อใช้ค่าเริ่มต้น)")
    
    # รับ input วันที่เริ่มต้น
    while True:
        start_date = input(f"กรุณาใส่วันที่เริ่มต้น (เริ่มต้น: {min_date}): ").strip()
        if start_date == "":
            start_date = min_date
            print(f"ใช้วันที่เริ่มต้น: {start_date}")
            break
        # ตรวจสอบรูปแบบวันที่
        try:
            pd.to_datetime(start_date, format='%Y/%m/%d')
            break
        except:
            print("รูปแบบวันที่ไม่ถูกต้อง กรุณาใส่ในรูปแบบ YYYY/MM/DD")
    
    # รับ input วันที่สิ้นสุด
    while True:
        end_date = input(f"กรุณาใส่วันที่สิ้นสุด (เริ่มต้น: {max_date}): ").strip()
        if end_date == "":
            end_date = max_date
            print(f"ใช้วันที่สิ้นสุด: {end_date}")
            break
        # ตรวจสอบรูปแบบวันที่
        try:
            pd.to_datetime(end_date, format='%Y/%m/%d')
            break
        except:
            print("รูปแบบวันที่ไม่ถูกต้อง กรุณาใส่ในรูปแบบ YYYY/MM/DD")
    
    return start_date, end_date

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
    
    # บันทึกไฟล์
    date_range = f"{start_date.replace('/', '')}_to_{end_date.replace('/', '')}"
    output_file = f"data/filtered_average_{date_range}.xlsx"
    
    grouped_average.to_excel(output_file, index=False)
    print(f"\nบันทึกค่าเฉลี่ยตามช่วงวันที่ไปที่: {output_file}")
    
    return grouped_average

# ===== MAIN EXECUTION =====

print("=== เริ่มต้นการประมวลผลข้อมูล ===")
print(f"ข้อมูลเริ่มต้น: {len(df)} แถว")

# ขั้นตอนที่ 1: แปลงข้อมูลวันที่
print("\n1. แปลงข้อมูลวันที่...")
df = time_series_analysis(df)

# ขั้นตอนที่ 2: เลือกช่วงวันที่
print("\n2. เลือกช่วงวันที่...")
start_date, end_date = select_date_range(df)

# ขั้นตอนที่ 3: กรองข้อมูลตามวันที่
print("\n3. กรองข้อมูลตามวันที่...")
df_filtered = filter_data_by_date(df, start_date, end_date)

if df_filtered is None:
    print("ไม่สามารถดำเนินการต่อได้ เนื่องจากไม่มีข้อมูลในช่วงวันที่ที่เลือก")
else:
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