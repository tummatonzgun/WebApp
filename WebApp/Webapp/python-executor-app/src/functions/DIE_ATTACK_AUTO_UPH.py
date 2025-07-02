import pandas as pd
import os
import glob
import numpy as np
from pathlib import Path
import time
from datetime import datetime  

def validate_input_file(input_path):
    """ตรวจสอบไฟล์ input"""
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"ไม่พบไฟล์ {input_path}")
    return input_path

def apply_zscore(df):
    """ใช้วิธี Z-Score ในการตัด outliers"""
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
    """ใช้วิธี IQR ในการตัด outliers"""
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
    """ตัด outliers อัตโนมัติด้วยการวนลูป Z-Score และ IQR"""
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

def process_die_attach_data(input_path, output_dir):
    """ฟังก์ชันหลักสำหรับประมวลผลข้อมูล Die Attach"""
    try:
        print(f"🔍 เริ่มประมวลผล: {input_path}")
        print(f"📁 Output directory: {output_dir}")
        
        # ตรวจสอบไฟล์ input
        validate_input_file(input_path)
        
        # สร้าง output directory ถ้าไม่มี
        os.makedirs(output_dir, exist_ok=True)
        print(f"✅ สร้าง output directory: {output_dir}")
        
        print("📊 กำลังโหลดข้อมูล...")
        # อ่านข้อมูล
        try:
            df = pd.read_excel(input_path)
        except Exception as e:
            # ลองอ่านเป็น CSV ถ้าอ่าน Excel ไม่ได้
            try:
                df = pd.read_csv(input_path)
                print("ℹ️ อ่านไฟล์เป็นรูปแบบ CSV")
            except:
                raise Exception(f"ไม่สามารถอ่านไฟล์ได้: {str(e)}")
        
        if df.empty:
            raise Exception("ไฟล์ข้อมูลว่างเปล่า")
        
        print(f"📈 ขนาดข้อมูลเริ่มต้น: {len(df)} แถว")
        print(f"📋 คอลัมน์ในข้อมูล: {list(df.columns)}")
        
        # ตรวจสอบคอลัมน์ที่จำเป็น
        required_columns = ['bom_no', 'Machine_Model', 'optn_code','operation']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise Exception(f"ไม่พบคอลัมน์ที่จำเป็น: {missing_columns}")
        
        # ตรวจสอบคอลัมน์ UPH
        col_map = {col.lower(): col for col in df.columns}
        if 'uph' not in col_map:
            raise Exception("ไม่พบคอลัมน์ UPH ในข้อมูล")
        
        uph_col = col_map['uph']
        
        # จัดกลุ่มข้อมูล
        grouped = df.groupby(['bom_no', 'Machine_Model'])
        
        # แสดงข้อมูล group
        print(f"\n🔢 จำนวน groups: {grouped.ngroups}")
        print("\n📊 ขนาดของแต่ละ group:")
        group_sizes = grouped.size()
        print(group_sizes)
        
        if grouped.ngroups == 0:
            raise Exception("ไม่พบข้อมูลสำหรับจัดกลุ่ม")
        
        # ประมวลผลแต่ละ group และสร้างสรุปผลลัพธ์
        print("\n🔧 === เริ่มการตัด outliers ===")
        summary_results = []
        
        for name, group in grouped:
            bom_no, machine_model = name
            print(f"\n⚙️ กำลังประมวลผล BOM: {bom_no}, Machine: {machine_model}")
            print(f"📊 ข้อมูลในกลุ่มนี้: {len(group)} แถว")
            
            # ดึงค่าจากแถวแรกของกลุ่ม
            optn_code = group['optn_code'].iloc[0] if 'optn_code' in group.columns else ''
            operation = group['operation'].iloc[0] if 'operation' in group.columns else ''
            
            original_count = len(group)
            original_mean = group[uph_col].mean()
            
            try:
                # ตัด outliers สำหรับกลุ่มนี้
                cleaned_group = remove_outliers_auto(group.copy())
                
                # คำนวณสถิติหลังตัด outliers
                cleaned_count = len(cleaned_group)
                cleaned_mean = cleaned_group[uph_col].mean()
                removed_count = original_count - cleaned_count
                outlier_method = cleaned_group['Outlier_Method'].iloc[0] if len(cleaned_group) > 0 else 'Error'
                
                print(f"✅ ข้อมูลหลังตัด outliers: {cleaned_count} แถว")
                print(f"📊 UPH เฉลี่ยเดิม: {original_mean:.2f}")
                print(f"📊 UPH เฉลี่ยใหม่: {cleaned_mean:.2f}")
                
                # เพิ่มผลลัพธ์ลงใน summary
                summary_results.append({
                    'bom_no': bom_no,
                    'Machine_Model': machine_model,
                    'optn_code': optn_code,
                    'operation': operation,
                    'Wire Per Hour': round(cleaned_mean, 2)
                })
                
            except Exception as e:
                print(f"⚠️ เกิดข้อผิดพลาดกับกลุ่ม {name}: {str(e)}")
                
                # เพิ่มผลลัพธ์ที่เกิดข้อผิดพลาด
                summary_results.append({
                    'bom_no': bom_no,
                    'Machine_Model': machine_model,
                    'optn_code': optn_code,
                    'operation': operation,
                    'Wire Per Hour': round(original_mean, 2)
                })
        
        # สร้าง DataFrame สรุปผลลัพธ์
        if summary_results:
            summary_df = pd.DataFrame(summary_results)
            
            print(f"\n📋 === สรุปผลลัพธ์ ===")
            print(f"✅ จำนวนกลุ่มที่ประมวลผล: {len(summary_df)} กลุ่ม")
            print(f"📊 Wire Per Hour เฉลี่ยรวม: {summary_df['Wire Per Hour'].mean():.2f}")
            
            # แสดง top 5 Wire Per Hour สูงสุด
            print("\n📈 === Top 5 Wire Per Hour สูงสุดหลังตัด Outliers ===")
            top_uph = summary_df.nlargest(5, 'Wire Per Hour')[['bom_no', 'Machine_Model', 'optn_code', 'operation', 'Wire Per Hour']]
            print(top_uph)
            
            # สร้างชื่อไฟล์ output พร้อม timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"die_attach_uph_summary_{timestamp}.xlsx"
            output_file = os.path.join(output_dir, output_filename)
            
            # บันทึกผลลัพธ์
            print(f"\n💾 กำลังบันทึกไฟล์: {output_file}")
            try:
                summary_df.to_excel(output_file, index=False, engine='openpyxl')
                
                # ตรวจสอบว่าไฟล์ถูกสร้างแล้ว
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    print(f"✅ บันทึกไฟล์สำเร็จ! ขนาด: {file_size} bytes")
                    print(f"📁 ไฟล์ผลลัพธ์: {output_file}")
                else:
                    raise Exception("ไฟล์ไม่ถูกสร้าง")
                    
            except Exception as e:
                # ถ้าบันทึก Excel ไม่ได้ ลองบันทึกเป็น CSV
                output_filename = f"die_attach_uph_summary_{timestamp}.csv"
                output_file = os.path.join(output_dir, output_filename)
                print(f"⚠️ ไม่สามารถบันทึก Excel ได้ กำลังบันทึกเป็น CSV: {output_file}")
                
                summary_df.to_csv(output_file, index=False, encoding='utf-8-sig')
                
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    print(f"✅ บันทึกไฟล์ CSV สำเร็จ! ขนาด: {file_size} bytes")
                else:
                    raise Exception(f"ไม่สามารถบันทึกไฟล์ได้: {str(e)}")
            
            return {
                "success": True,
                "message": f"ประมวลผลสำเร็จ ได้ไฟล์สรุป: {os.path.basename(output_file)}",
                "output_file": output_file,
                "total_groups": len(summary_df),
                "avg_uph": round(summary_df['Wire Per Hour'].mean(), 2),
                "file_size": os.path.getsize(output_file) if os.path.exists(output_file) else 0
            }
            
        else:
            return {
                "success": False,
                "message": "ไม่สามารถประมวลผลข้อมูลได้",
                "error": "No processed groups available"
            }
            
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {str(e)}")
        return {
            "success": False,
            "message": f"เกิดข้อผิดพลาด: {str(e)}",
            "error": str(e)
        }

def run(input_dir, output_dir):
    """ฟังก์ชันสำหรับเรียกใช้จาก app.py"""
    print(f"🚀 เริ่มต้นการประมวลผล...")
    print(f"📁 Input directory: {input_dir}")
    print(f"📁 Output directory: {output_dir}")
    
    try:
        # หาไฟล์ Excel/CSV ใน input directory
        excel_files = []
        csv_files = []
        
        # ค้นหาไฟล์ Excel
        for ext in ['*.xlsx', '*.xls']:
            excel_files.extend(glob.glob(os.path.join(input_dir, ext)))
        
        # ค้นหาไฟล์ CSV
        csv_files.extend(glob.glob(os.path.join(input_dir, '*.csv')))
        
        all_files = excel_files + csv_files
        
        print(f"🔍 พบไฟล์: {len(all_files)} ไฟล์")
        for file in all_files:
            print(f"  - {os.path.basename(file)}")
        
        if not all_files:
            return {
                "success": False,
                "message": "ไม่พบไฟล์ Excel หรือ CSV ใน input directory",
                "error": "No input files found"
            }
        
        # ประมวลผลไฟล์แรกที่พบ
        input_file = all_files[0]
        print(f"📊 กำลังประมวลผลไฟล์: {os.path.basename(input_file)}")
        
        result = process_die_attach_data(input_file, output_dir)
        
        if result["success"]:
            print(f"✅ ประมวลผลเสร็จสิ้น: {result['message']}")
        else:
            print(f"❌ ประมวลผลล้มเหลว: {result['message']}")
        
        return result
        
    except Exception as e:
        error_msg = f"เกิดข้อผิดพลาดในฟังก์ชัน run: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "success": False,
            "message": error_msg,
            "error": str(e)
        }


