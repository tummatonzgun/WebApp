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



    # หา Type ล่าสุดสำหรับแต่ละกลุ่ม (ก่อนเรียงข้อมูล)
    def get_latest_type(group):
        # เรียงข้อมูลตามเวลาจากใหม่ไปเก่าเพื่อหา Type ล่าสุด
        group_sorted = group.sort_values(
            by=['file_year', 'month_num', 'start_date'], 
            ascending=[False, False, False]
        )
        # เอา assy_pack_type แรก (ล่าสุด)
        latest_type = group_sorted['assy_pack_type'].iloc[0]
        return latest_type

    # สร้าง mapping ของ Type ล่าสุดสำหรับแต่ละกลุ่ม
    latest_types = df_all.groupby(['bom_no', 'package_code', 'product_no']).apply(get_latest_type)
    latest_types_dict = latest_types.to_dict()

    # เรียงข้อมูลตาม BOM → เวลา (จากเก่าไปใหม่)
    df_all = df_all.sort_values(by=[
        'bom_no', 'package_code', 'product_no',
        'file_year', 'month_num', 'start_date'
    ]).reset_index(drop=True)

    # เพิ่มคอลัมน์ Type สุดท้ายเข้าไปใน DataFrame
    df_all['Last_type'] = df_all.apply(
        lambda row: latest_types_dict[(row['bom_no'], row['package_code'], row['product_no'])], 
        axis=1
    )

    # จัดรูปแบบวันที่ให้อ่านง่าย
    df_all['start_date'] = pd.to_datetime(df_all['start_date'], errors='coerce').dt.strftime('%d/%m/%Y')\

    # เตรียมข้อมูลสำหรับบันทึก (ลบคอลัมน์ที่ไม่จำเป็น)
    df_to_save = df_all.drop(columns=['month', 'month_num',], errors='ignore')
    df_to_save.rename(columns={'month_short': 'month'}, inplace=True)

    # บันทึกผลลัพธ์
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "Last_Type.xlsx")
    df_to_save.to_excel(output_file, index=False)

    print(f"✅ บันทึกไฟล์ข้อมูลทั้งหมดพร้อม Type สุดท้าย ไว้ที่: {output_file}")
    print(f"📊 จำนวนแถวทั้งหมด: {len(df_to_save)}")
    print(f"📈 จำนวนกลุ่ม BOM ที่ไม่ซ้ำ: {len(df_to_save.groupby(['bom_no', 'package_code', 'product_no']))}")
    
    return df_to_save

def lookup_last_type(input_bom_file, output_dir):
    # โหลดไฟล์ Last_Type.xlsx
    last_type_path = os.path.join(output_dir, "Last_Type.xlsx")
    if not os.path.exists(last_type_path):
        print(f"❌ ไม่พบไฟล์ {last_type_path}")
        return

    df_last = pd.read_excel(last_type_path)
    # เลือกเฉพาะคอลัมน์ที่จำเป็น
    cols = ['bom_no', 'Last_type']
    df_last = df_last[cols].drop_duplicates()

    # โหลดไฟล์ bom_no ที่อัปโหลด
    df_bom = pd.read_excel(input_bom_file) if input_bom_file.endswith('.xlsx') else pd.read_csv(input_bom_file)
    if 'bom_no' not in df_bom.columns:
        print("❌ ไฟล์ที่อัปโหลดไม่มีคอลัมน์ bom_no")
        return

    # รวมข้อมูล (merge) เพื่อดึง Last_type
    merge_cols = ['bom_no']
    if 'package_code' in df_bom.columns and 'product_no' in df_bom.columns:
        merge_cols += ['package_code', 'product_no']

    df_merged = pd.merge(df_bom, df_last, on=merge_cols, how='left')
    return df_merged


def run(input_path, output_dir):
    """
    Entry point สำหรับการรัน PNP_CHANG_TYPE
    """
    print(f"🚀 เริ่มต้น PNP_CHANG_TYPE")
    
    try:
        # ตรวจสอบว่ามีไฟล์ WF size หรือไม่
        wf_files = glob.glob(os.path.join(input_path, "WF size*"))
        
        if wf_files:
            print(f"📁 พบไฟล์ WF size {len(wf_files)} ไฟล์")
            # รันการสร้าง Last_Type.xlsx จากไฟล์ WF
            df_result = run_all_years(input_path, output_dir)
            return df_result
        else:
            # ถ้าเป็นการ lookup BOM
            excel_files = glob.glob(os.path.join(input_path, "*.xlsx")) + glob.glob(os.path.join(input_path, "*.xls"))
            
            if excel_files:
                print(f"📁 พบไฟล์ Excel {len(excel_files)} ไฟล์ - จะทำ lookup")
                result_df = lookup_last_type(excel_files[0], output_dir)
                
                if result_df is not None:
                    output_file = os.path.join(output_dir, "PNP_CHANG_TYPE_result.xlsx")
                    result_df.to_excel(output_file, index=False)
                    print(f"💾 บันทึกผลลัพธ์: {output_file}")
                    
                return result_df
            else:
                raise ValueError("ไม่พบไฟล์ WF size หรือไฟล์ Excel ที่สามารถประมวลผลได้")
        
    except Exception as e:
        print(f"❌ Error in run: {e}")
        raise e




