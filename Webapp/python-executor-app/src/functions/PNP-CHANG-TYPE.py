import pandas as pd
import glob
import os
import re

def run_all_years(input_path, output_dir):
    target_years = [2023, 2024, 2025, 2026, 2027]
    print(f"กำลังประมวลผลไฟล์จาก {input_path} สำหรับปี {target_years}")
    # หาไฟล์ทั้งหมดที่ตรงชื่อ
    all_files = glob.glob(os.path.join(input_path, "WF size* (UTL1).*"))
    print(f"เจอไฟล์ทั้งหมด {len(all_files)} ไฟล์")

    # แยกไฟล์ตามปี
    files_by_year = {}
    for filepath in all_files:
        filename = os.path.basename(filepath)
        match = re.search(r"'(\d{2})", filename)
        if match:
            file_year = 2000 + int(match.group(1))
            if file_year in target_years:
                files_by_year.setdefault(file_year, []).append(filepath)
        else:
            print(f"⚠️ ไฟล์ {filename} ไม่มีปีในชื่อ")

    df_list = []

    for year in sorted(files_by_year):
        for filepath in files_by_year[year]:
            filename = os.path.basename(filepath)
            month_match = re.search(r"WF size ([^ ]+)", filename)
            month = month_match.group(1) if month_match else "Unknown"

            try:
                if filepath.endswith(('.xls', '.xlsx')):
                    df = pd.read_excel(filepath, engine="openpyxl" if filepath.endswith('.xlsx') else None)
                elif filepath.endswith('.csv'):
                    df = pd.read_csv(filepath)
                else:
                    print(f"❌ ไม่รู้จักฟอร์แมต: {filename}")
                    continue
            except Exception as e:
                print(f"❌ อ่านไฟล์ {filename} ผิดพลาด: {e}")
                continue

            df['month'] = month
            df['file_year'] = year
            df_list.append(df)

    if not df_list:
        print("❌ ไม่มีไฟล์ที่โหลดได้เลย")
        return

    df_all = pd.concat(df_list, ignore_index=True)

    # คอลัมน์ที่ต้องใช้
    required_cols = ['cust_code', 'package_code', 'product_no', 'bom_no', 'assy_pack_type', 'start_date', 'month']
    missing = [c for c in required_cols if c not in df_all.columns]
    if missing:
        print(f"❌ คอลัมน์หายไป: {missing}")
        return

    df_all = df_all[required_cols + ['file_year']]

    # จัดเรียงเดือน
    month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    month_map = {m: i for i, m in enumerate(month_order, 1)}
    df_all['month_short'] = df_all['month'].str[:3]
    df_all['month_num'] = df_all['month_short'].map(month_map)

    # เรียงตาม BOM → เวลา
    df_all = df_all.sort_values(by=[
        'bom_no', 'package_code', 'product_no',
        'file_year', 'month_num', 'start_date'
    ]).reset_index(drop=True)

    # ตรวจจับการเปลี่ยนแปลง
    def detect_change(group):
        group = group.copy()
        group['assy_pack_type_prev'] = group['assy_pack_type'].shift(1)
        group['month_prev'] = group['month'].shift(1).str[:3] 
        group['month'] = group['month'].str[:3] 
        group['start_date_prev'] = group['start_date'].shift(1)
        group['changed'] = group['assy_pack_type'] != group['assy_pack_type_prev']
        group['change_date'] = group['start_date']
        group.loc[~group['changed'], 'change_date'] = pd.NaT
        group.loc[group.index[0], 'changed'] = False
        return group

    df_changes = df_all.groupby(['bom_no', 'package_code', 'product_no'], group_keys=False).apply(detect_change)
    df_changes = df_changes.drop(columns=['month_num', 'month_short'])

    # เอาเฉพาะบรรทัดที่มีการเปลี่ยน
    changes_only = df_changes[df_changes['changed']].copy()

    # ติดดาวที่การเปลี่ยนครั้งสุดท้าย
    last_change_idx = changes_only.groupby(['bom_no', 'package_code', 'product_no']).tail(1).index
    changes_only['last_update'] = ''
    changes_only.loc[last_change_idx, 'last_update'] = '*'

    # จัดรูปแบบวันที่ให้อ่านง่าย
    for col in ['start_date', 'start_date_prev', 'change_date']:
        changes_only[col] = pd.to_datetime(changes_only[col], errors='coerce').dt.strftime('%d/%m/%Y')

    # บันทึกผลลัพธ์
    #df_to_save = df_all.drop(columns=['month_short', 'month_num'], errors='ignore')
    #df_to_save.to_excel(os.path.join(output_path, "all_bom_data_2023_to_2025.xlsx"), index=False)

    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"bom_assy_pack_type_changes_2023_to_2025.xlsx")
    changes_only.drop(columns=['changed'], errors='ignore').to_excel(output_file, index=False)

    print(f"✅ บันทึกไฟล์การเปลี่ยนแปลงรวมปี 2023-2025 ไว้ที่: {output_file}")
    return changes_only

def run(input_path, output_dir):
    return run_all_years(input_path, output_dir)

run_all_years(
    input_path="data_all",     # โฟลเดอร์ที่รวมไฟล์ปี 2023, 2024, 2025 ไว้หมด
    output_dir="Output_Pnp_change_type"
)
