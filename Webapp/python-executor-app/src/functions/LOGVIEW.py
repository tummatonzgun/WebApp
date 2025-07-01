import pandas as pd
import os
import glob
import numpy as np
from pathlib import Path
import time
from datetime import datetime  

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ---------- 1. TXT → Excel ----------

def find_input_files(input_pattern: str):
    if os.path.isdir(input_pattern):
        files = glob.glob(os.path.join(input_pattern, "*.txt")) + \
        glob.glob(os.path.join(input_pattern, "*.TXT"))
        files = list(set(os.path.abspath(f) for f in files))
    else:
        files = glob.glob(input_pattern)
    return files

def load_and_parse_file(input_file: str) -> pd.DataFrame:
    try:
        with open(input_file, 'r', encoding='latin-1') as file:
            lines = file.readlines()
    except Exception as e:
        print(f"Error reading {input_file}: {e}")
        return pd.DataFrame()
    rows = []
    max_values_len = 0
    for line in lines:
        parts = line.strip().split('\t')
        if len(parts) < 3:
            continue
        timestamp, data_type, data_values = parts[0], parts[1], parts[2]
        try:
            date_part, time_part = timestamp.split(' ')
            time_part = time_part.replace('AM', '').replace('PM', '').strip()
        except ValueError:
            continue
        values = data_values.split(',')
        if len(values) > max_values_len:
            max_values_len = len(values)
        row = [date_part, time_part, data_type] + values
        rows.append(row)
    if not rows:
        return pd.DataFrame()
    max_len = 6 + max_values_len
    for row in rows:
        row += [''] * (max_len - len(row))
    columns = ['date', 'time', 'step', 'frame', 'G', 'No_strip'] + [f'value_{i}' for i in range(1, max_values_len + 1)]
    df = pd.DataFrame(rows, columns=columns)
    pattern = r'(FU|FR|FA|FW|FN|FJ|F1|F2|F3|F4|F5|F6|F7|F8|F9|F0)(\w{4})'
    df['frame'] = df['frame'].astype(str)
    df['frame'] = df['frame'].str.extract(pattern).fillna('').agg(''.join, axis=1)
    return df

def extract_pro_and_speed(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    df_pro = df[df['step'] == 'PRO'].copy()
    if df_pro.empty:
        return pd.DataFrame()
    df_pro['speed'] = None
    for idx in df_pro.index:
        speed_value = None
        pos = df.index.get_loc(idx)
        for j in range(pos + 1, len(df)):
            if df.loc[df.index[j], 'step'] == 'CUC':
                if 'value_5' in df.columns and len(df.columns) > df.columns.get_loc('value_5'):
                    speed_value = df.loc[df.index[j], 'value_5']
                break
        df_pro.at[idx, 'speed'] = speed_value
    df_pro['speed'] = pd.to_numeric(df_pro['speed'], errors='coerce')
    df_pro['speed'] = df_pro['speed'] / 10 / 25.4
    df_pro['speed'] = df_pro['speed'].apply(lambda x: int(x) if x % 1 == 0 else round(x, 2))
    return df_pro

def mark_errors(df: pd.DataFrame, df_pro: pd.DataFrame) -> pd.DataFrame:
    if df.empty or df_pro.empty:
        return df_pro
    df_pro['MC'] = None
    pro_indices = df.index[df['step'] == 'PRO'].tolist()
    for i in range(1, len(pro_indices)):
        current_idx = pro_indices[i]
        prev_idx = pro_indices[i - 1]
        start_idx = min(prev_idx, current_idx)
        end_idx = max(prev_idx, current_idx)
        df_slice = df.loc[start_idx:end_idx]
        error_steps = ['ERRSET', 'ERRRCV', 'ERRCLR', 'DMC', 'DMW']
        has_error = df_slice['step'].isin(error_steps).any()
        if has_error and prev_idx in df_pro.index:
            df_pro.at[prev_idx, 'MC'] = 'MC error'
    return df_pro

def insert_blank_rows(df_pro: pd.DataFrame) -> pd.DataFrame:
    if df_pro.empty:
        return df_pro
    new_rows = []
    for i in range(len(df_pro)):
        row = df_pro.iloc[i]
        new_rows.append(row)
        try:
            first_strip = float(row['No_strip']) == 1
        except (ValueError, TypeError):
            first_strip = False
        if first_strip:
            empty_row = pd.Series([None] * len(df_pro.columns), index=df_pro.columns)
            new_rows.append(empty_row)
    df_with_blank = pd.DataFrame(new_rows).reset_index(drop=True)
    return df_with_blank

def calculate_time_diff(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'], errors='coerce')
    df['minute'] = df['datetime'] - df['datetime'].shift(-1)
    df['seconds'] = df['minute'].dt.total_seconds()
    df = df[df['seconds'].isna() | ((df['seconds'] >= 0) & (df['seconds'] <= 86400))]
    df['minute'] = df['minute'].astype(str)
    df.loc[df['minute'] == 'NaT', 'minute'] = ''
    df['minute'] = df['minute'].str.replace('0 days ', '')
    df = df.drop(columns=['datetime'])
    return df

def assign_subgroups_and_insert_empty_rows(df, column_strip='No_strip', frame_group='frame'):
    subgroup_id = 0
    subgroups = []
    prev_val = None
    for val in df[column_strip]:
        if pd.isna(val):
            subgroups.append(np.nan)
            prev_val = None
            continue
        if prev_val is None:
            subgroup_id += 1
        elif val > prev_val:
            subgroup_id += 1
        subgroups.append(subgroup_id)
        prev_val = val
    df['subgroup_id'] = subgroups
    result_rows = []
    subgroup_keys = df['subgroup_id'].dropna().unique()
    for group in subgroup_keys:
        group_df = df[df['subgroup_id'] == group].reset_index(drop=True)
        result_rows.append(group_df.iloc[[0]])
        for i in range(1, len(group_df)):
            prev_frame = group_df.loc[i - 1, frame_group]
            curr_frame = group_df.loc[i, frame_group]
            if prev_frame != curr_frame:
                empty_row = pd.DataFrame({col: [np.nan] for col in df.columns})
                result_rows.append(empty_row)
            result_rows.append(group_df.iloc[[i]])
        empty_row = pd.DataFrame({col: [np.nan] for col in df.columns})
        result_rows.append(empty_row)
    result_df = pd.concat(result_rows, ignore_index=True).reset_index(drop=True)
    return result_df

def mark_outlier_subgroups(df, subgroup_col='subgroup_id', no_strip_col='No_strip'):
    outlier_groups = []
    for subgroup, group_df in df.groupby(subgroup_col):
        if 1 not in group_df[no_strip_col].values:
            outlier_groups.append(subgroup)
    df['outlier_subgroup'] = df[subgroup_col].isin(outlier_groups)
    return df

def detect_outliers_combined(df, group_col='frame', value_col='seconds', no_strip_col='No_strip',
                             iqr_factor=1, zscore_threshold=2, min_diff_seconds=90):
    df['is_outlier'] = False
    df_filtered = df[~((df[no_strip_col] == 2) & (df[no_strip_col].shift(-1) == 1))]
    for group_name, group in df_filtered.groupby(group_col):
        values = group[value_col].dropna().values
        if len(values) == 0:
            continue
        median = np.median(values)
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        upper_bound = q3 + iqr_factor * iqr
        mean = np.mean(values)
        std = np.std(values)
        for idx in group.index:
            val = df.loc[idx, value_col]
            if pd.isna(val):
                continue
            if val > upper_bound and abs(val - median) > min_diff_seconds:
                df.at[idx, 'is_outlier'] = True
            elif std > 0:
                z_score = (val - mean) / std
                if z_score > zscore_threshold and abs(val - mean) > min_diff_seconds:
                    df.at[idx, 'is_outlier'] = True
    return df

def add_avg_exclude_outliers_by_frame(
    df, 
    value_col='seconds', 
    group_col='frame', 
    outlier_col='is_outlier',
    outlier_subgroup_col='outlier_subgroup',
    outlier_mc='MC'
):
    df['avg_ex_outliers'] = pd.NA
    df['count_avg'] = pd.NA
    df['count_outliers'] = pd.NA
    for frame_val in df[group_col].dropna().unique():
        group_df = df[df[group_col] == frame_val]
        good_values = group_df[(group_df[outlier_col] != True) & (group_df[outlier_subgroup_col] != True) & (group_df[outlier_mc] != 'MC error')][value_col].dropna()
        if len(good_values) < 5:
            continue
        avg_val = good_values.mean()
        count_avg_val = len(good_values)
        count_all = group_df[value_col].count()
        count_outliers = count_all - count_avg_val
        idx = df[df[group_col] == frame_val].index
        if len(idx) > 0:
            first_idx = idx[0]
            df.at[first_idx, 'avg_ex_outliers'] = round(avg_val, 2)
            df.at[first_idx, 'count_avg'] = count_avg_val
            df.at[first_idx, 'count_outliers'] = count_outliers
    return df

def summarize_by_frame(df):
    summary = df.groupby(['frame', 'speed']).agg({
        'sec/strip': 'first',
    }).reset_index()
    return summary

def process_single_file_complete(input_file: str, output_dir: str):
    print(f"กำลังประมวลผล: {input_file}")
    input_path = Path(input_file)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # สร้างชื่อไฟล์ใหม่ด้วยวันที่และเวลา
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_path / f"{input_path.stem}_{timestamp}.xlsx"
    
    try:
        df = load_and_parse_file(input_file)
        if df.empty:
            return False, f"ไม่สามารถโหลดข้อมูลจาก {input_file}"
        
        df_pro = extract_pro_and_speed(df)
        if df_pro.empty:
            return False, f"ไม่พบข้อมูล PRO ในไฟล์ {input_file}"
        
        df_pro = mark_errors(df, df_pro)
        
        # เลือกคอลัมน์ที่ต้องการ
        available_value_cols = [col for col in df_pro.columns if col.startswith('value_')]
        value_cols = available_value_cols[:1] if available_value_cols else []
        selected_cols = ['date', 'time', 'step', 'package', 'frame', 'No_strip'] + value_cols + ['speed','MC']
        existing_cols = [col for col in selected_cols if col in df_pro.columns]
        df_pro = df_pro[existing_cols]
        
        # ประมวลผลข้อมูล
        df_with_blank = insert_blank_rows(df_pro)
        df_time = calculate_time_diff(df_with_blank)
        
        # แปลงชนิดข้อมูล
        for col in ['frame', 'speed','value_1']:
            if col in df_time.columns:
                if col == 'frame':
                    df_time[col] = df_time[col].astype(str).str.strip()
                else:
                    df_time[col] = pd.to_numeric(df_time[col], errors='coerce')
        
        if 'No_strip' in df_time.columns:
            df_time['No_strip'] = pd.to_numeric(df_time['No_strip'], errors='coerce')
        
        df_filtered = df_time[df_time['frame'].notna()]
        if df_filtered.empty:
            return False, f"ไม่พบข้อมูล frame ที่ใช้งานได้ในไฟล์ {input_file}"
        
        # วิเคราะห์ข้อมูล
        df_analyzed = assign_subgroups_and_insert_empty_rows(df_filtered, 'No_strip', 'frame')
        df_analyzed = mark_outlier_subgroups(df_analyzed, 'subgroup_id', 'No_strip')
        df_analyzed = detect_outliers_combined(df_analyzed, 'frame', 'seconds', 'No_strip')
        df_analyzed = add_avg_exclude_outliers_by_frame(df_analyzed, value_col='seconds', group_col='frame')
        
        # จัดการ Error columns
        if 'outlier_subgroup' in df_analyzed.columns and 'is_outlier' in df_analyzed.columns and 'MC' in df_analyzed.columns:
            df_analyzed['Error'] = (df_analyzed['outlier_subgroup'] | df_analyzed['is_outlier'] | (df_analyzed['MC'] == 'MC error'))
        elif 'outlier_subgroup' in df_analyzed.columns and 'is_outlier' in df_analyzed.columns:
            df_analyzed['Error'] = df_analyzed['outlier_subgroup'] | df_analyzed['is_outlier']
        else:
            df_analyzed['Error'] = False
        
        # ลบคอลัมน์ที่ไม่ต้องการ
        df_analyzed.drop(columns=['outlier_subgroup', 'is_outlier','MC'], inplace=True, errors='ignore')
        df_analyzed['Error'] = df_analyzed['Error'].apply(lambda x: "MC ERROR" if x else "")
        df_analyzed.drop(columns=['subgroup_id'], inplace=True, errors='ignore')
        df_analyzed['sec/strip'] = df_analyzed['avg_ex_outliers']
        
        # สร้าง Summary
        summary = summarize_by_frame(df_analyzed)
        df_final = df_analyzed.drop(columns=['avg_ex_outliers'])
        
        # บันทึกไฟล์ Excel
        with pd.ExcelWriter(output_file) as writer:
            df_final.to_excel(writer, index=False, sheet_name='Processed_Data')
            summary.to_excel(writer, index=False, sheet_name='Summary')
        
        return True, str(output_file)
        
    except Exception as e:
        return False, f"เกิดข้อผิดพลาดในการประมวลผล {input_file}: {str(e)}"

def process_multiple_files_complete(input_pattern: str, output_dir: str):
    files = find_input_files(input_pattern)
    if not files:
        print(f" ไม่พบไฟล์ที่ตรงกับ pattern: {input_pattern}")
        return
    print(f" พบไฟล์ทั้งหมด {len(files)} ไฟล์")
    print("=" * 60)
    successful = 0
    failed = 0
    start_time = time.time()
    for i, file_path in enumerate(files, 1):
        print(f"[{i}/{len(files)}] ", end="")
        success, message = process_single_file_complete(file_path, output_dir)
        if success:
            print(f" สำเร็จ: {message}")
            successful += 1
        else:
            print(f" ล้มเหลว: {message}")
            failed += 1
    end_time = time.time()
    print("\n" + "=" * 60)
    print(f" ใช้เวลา: {end_time - start_time:.2f} วินาที")
    print(f" ผลลัพธ์: สำเร็จ {successful} ไฟล์, ล้มเหลว {failed} ไฟล์")

# ---------- 2. รวม Summary ----------

def load_sec_strip_by_frame(filepath, sheet_name='Processed_Data'):
    try:
        df = pd.read_excel(filepath, sheet_name=sheet_name)
    except ValueError:
        # ถ้าไม่มีชีท Processed_Data ให้ลองอ่าน Sheet1
        df = pd.read_excel(filepath, sheet_name='Sheet1')
    if not all(col in df.columns for col in ['frame', 'speed', 'sec/strip']):
        raise ValueError("ไม่มีคอลัมน์ที่ต้องการ")
    df['frame'] = df['frame'].astype(str)
    df['speed'] = pd.to_numeric(df['speed'], errors='coerce')
    df['sec/strip'] = pd.to_numeric(df['sec/strip'], errors='coerce')
    df = df[df['sec/strip'].notna() & df['speed'].notna()]
    return df

def summarize_sec_strip(files_folder, file_list):
    data = {}
    for filename in file_list:
        filepath = os.path.join(files_folder, filename)
        try:
            df = load_sec_strip_by_frame(filepath)
            summary = df.groupby(['frame', 'speed'])['sec/strip'].mean()
            summary.index = summary.index.map(lambda x: f"{x[0]}_speed{x[1]}")
            file_key = os.path.splitext(filename)[0]
            data[file_key] = summary
        except Exception as e:
            print(f"ข้ามไฟล์ {filename} : {e}")
            continue
    result_df = pd.DataFrame(data)
    result_df = result_df.sort_index()
    return result_df

def save_summary(df, output_path):
    df.index.name = "FRAME_STOCK"
    df.to_excel(output_path, index=True)
    print(f"✅ Saved comparison summary to: {output_path}")

# ---------- 3. Export CSV ----------

def remove_outliers(data):
    if not data:
        return []
    arr = np.array(data)
    q1 = np.percentile(arr, 25)
    q3 = np.percentile(arr, 75)
    iqr = q3 - q1
    upper_bound = q3 + 1.5 * iqr
    filtered = arr[(arr <= upper_bound)]
    return filtered.tolist()

def filtered_mean(lst):
    filtered = remove_outliers(lst)
    if len(filtered) == 0:
        return float('nan')
    return sum(filtered) / len(filtered)

# กำหนด mapping เงื่อนไข Package group → Lead frame
MAPPING = {
    ('QFN', '5.0'): 'CU',
    ('QFN', '4.0'): 'PPF',
}

def analyze_and_export_csv(summary_path, package_path, output_csv):
    df = pd.read_excel(summary_path)
    df2 = pd.read_excel(package_path)
    df['non_null_values'] = df.loc[:, df.columns != 'FRAME_STOCK'].apply(
        lambda row: row.dropna().tolist(), axis=1)
    df = df[['FRAME_STOCK', 'non_null_values']]
    df['TIME/STRIP'] = df['non_null_values'].apply(filtered_mean)
    df = df[['FRAME_STOCK', 'TIME/STRIP']]
    df['SPEED'] = df['FRAME_STOCK'].astype(str).str[-3:]
    df['X'] = df['FRAME_STOCK'].astype(str).str[0:6]
    df = df[['X', 'SPEED', 'TIME/STRIP', 'FRAME_STOCK']]
    df = df.drop(columns='FRAME_STOCK')
    df['TIME/STRIP'] = df['TIME/STRIP'].round(2)
    df.rename(columns={'X': 'FRAME_STOCK'}, inplace=True)
    df.rename(columns={'SPEED': 'SPEED (IPS)'},inplace=True)
    df_merged = pd.merge(df, df2[['FRAME_STOCK', 'PACKAGE_CODE']], on='FRAME_STOCK', how='left')
    df_merged.to_csv(output_csv, index=False)
    print(f"✅ Exported summary CSV: {output_csv}")

def analyze_and_export_csv_from_df(summary_df, package_path, output_csv):
    df = summary_df.reset_index()
    # ตรวจสอบและเปลี่ยนชื่อคอลัมน์ index ให้เป็น 'FRAME_STOCK'
    if df.columns[0] != 'FRAME_STOCK':
        df = df.rename(columns={df.columns[0]: 'FRAME_STOCK'})
    df2 = pd.read_excel(package_path)
    df['non_null_values'] = df.loc[:, df.columns != 'FRAME_STOCK'].apply(
        lambda row: row.dropna().tolist(), axis=1)
    df = df[['FRAME_STOCK', 'non_null_values']]
    df['TIME/STRIP'] = df['non_null_values'].apply(filtered_mean)
    df = df[['FRAME_STOCK', 'TIME/STRIP']]
    df['SPEED (IPS)'] = df['FRAME_STOCK'].astype(str).str[-3:]
    df['X'] = df['FRAME_STOCK'].astype(str).str[0:6]
    df = df[['X', 'SPEED (IPS)', 'TIME/STRIP', 'FRAME_STOCK']]
    df = df.drop(columns='FRAME_STOCK')
    df['TIME/STRIP'] = df['TIME/STRIP'].round(2)
    df.rename(columns={'X': 'FRAME_STOCK'}, inplace=True)
    df_merged = pd.merge(
        df,
        df2[['FRAME_STOCK', 'PACKAGE_CODE','Package size ','Package group','Lead frame','Unit/strip','Strip/lot']],
        on='FRAME_STOCK',
        how='left'
    )
    # แก้ไขการใช้ MAPPING
    df_merged['Lead frame'] = df_merged.apply(
        lambda row: MAPPING.get((str(row['Package group']), str(row['SPEED (IPS)'])), row['Lead frame']),
        axis=1
    )
    
    df_merged['Process'] = None
    df_merged['Package group'] = df_merged['Package group'].astype(str).str.strip().str.upper()
    # แปลง SPEED ให้เป็นตัวเลข
    df_merged['SPEED (IPS)'] = pd.to_numeric(df_merged['SPEED (IPS)'], errors='coerce')

    # สร้างคอลัมน์ Process ด้วยเงื่อนไข
    choices = [
       (df_merged['SPEED (IPS)'] == 5) & (df_merged['Package group'] == 'SLP'),
       (df_merged['SPEED (IPS)'] == 3) & (df_merged['Package group'] == 'SLP')
    ]

    answer = ['Full Cut', 'Step Cut']

    df_merged['Process'] = np.select(choices, answer, default=None)

    df_merged.to_csv(output_csv, index=False)
    print(f"✅ Exported summary CSV: {output_csv}")

def run(input_path, output_dir):
    """
    ฟังก์ชันหลักสำหรับประมวลผลไฟล์ LOGVIEW
    """
    print(f"🚀 เริ่มประมวลผล LOGVIEW")
    print(f"📁 Input: {input_path}")
    print(f"📁 Output: {output_dir}")
    
    # 1. ประมวลผลไฟล์ input และเก็บชื่อไฟล์ .xlsx ที่สร้างใหม่
    before_files = set(f for f in os.listdir(output_dir) if f.lower().endswith('.xlsx'))
    
    process_multiple_files_complete(input_path, output_dir)
    
    after_files = set(f for f in os.listdir(output_dir) if f.lower().endswith('.xlsx'))
    new_files = list(after_files - before_files)
    
    if not new_files:
        print("❌ ไม่พบไฟล์ .xlsx ใหม่")
        return

    print(f"✅ สร้างไฟล์ใหม่ {len(new_files)} ไฟล์")

    # 2. ส่งเฉพาะไฟล์ใหม่ไปให้ summarize_sec_strip
    summary_df = summarize_sec_strip(output_dir, new_files)
    
    # 3. ตรวจสอบไฟล์ package
    package_path = os.path.join(BASE_DIR, "..", "Upload", "export package and frame stock Rev.02.xlsx")
    package_path = os.path.abspath(package_path)
    
    if not os.path.exists(package_path):
        print("❌ ไม่พบไฟล์ export package and frame stock Rev.02.xlsx ใน Upload")
        return
    
    # 4. สร้างไฟล์ Summary.csv ด้วย timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_csv = os.path.join(output_dir, f"Summary_{timestamp}.csv")
    
    analyze_and_export_csv_from_df(summary_df, package_path, output_csv)
    
    print(f"🎉 ประมวลผลเสร็จสิ้น!")
    print(f"📊 ไฟล์ผลลัพธ์: {output_csv}")

def group_and_average_across_frames_unique_frame(df):
    grouping_cols = [
        'Package size ',
        'Package group',
        'Lead frame',
        'Unit/strip',
        'SPEED (IPS)'
    ]
    
    df_unique = df.drop_duplicates(subset=['FRAME_STOCK'])
    group_avg_map = {}

    for group_key, group_df in df_unique.groupby(grouping_cols):
        values = group_df['TIME/STRIP'].dropna().tolist()
        print(f"Group: {group_key}, Values Count: {len(values)}")  # debug
        if len(values) < 2:
            continue
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        filtered = [v for v in values if lower <= v <= upper]
        print(f"Filtered Values Count: {len(filtered)}")  # debug
        if filtered:
            avg_val = round(np.mean(filtered), 2)
            group_avg_map[group_key] = avg_val

    def assign_avg(row):
        key = tuple(row[col] for col in grouping_cols)
        return group_avg_map.get(key, row['TIME/STRIP'])

    df['TIME/STRIP'] = df.apply(assign_avg, axis=1)
    return df


