# 📝 **คู่มือการเพิ่ม Function ใหม่**

## 🚀 **วิธีเพิ่ม Function ใหม่ (ง่ายมาก!):**

### 1️⃣ **สร้างไฟล์ Function ใหม่**
สร้างไฟล์ในโฟลเดอร์ `functions/` ตามรูปแบบ:

```python
# functions/MY_NEW_FUNCTION.py

import pandas as pd
import os

def run(input_path, output_dir):
    """
    Entry point สำหรับ function ใหม่
    
    Args:
        input_path (str): path ของไฟล์ที่อัปโหลด
        output_dir (str): path ของโฟลเดอร์ output
    
    Returns:
        pandas.DataFrame: ผลลัพธ์ที่จะแสดงในตาราง (optional)
    """
    try:
        print(f"🚀 เริ่มต้น MY_NEW_FUNCTION")
        
        # 1. อ่านไฟล์ที่อัปโหลด
        excel_files = []
        for ext in ['*.xlsx', '*.xls', '*.csv']:
            excel_files.extend(glob.glob(os.path.join(input_path, ext)))
        
        if not excel_files:
            raise ValueError("ไม่พบไฟล์ Excel หรือ CSV")
        
        # อ่านไฟล์แรก
        input_file = excel_files[0]
        if input_file.endswith('.csv'):
            df = pd.read_csv(input_file)
        else:
            df = pd.read_excel(input_file)
        
        print(f"📋 อ่านไฟล์สำเร็จ: {len(df)} รายการ")
        
        # 2. ประมวลผลข้อมูล (ใส่ logic ของคุณที่นี่)
        # ตัวอย่าง: เพิ่มคอลัมน์ใหม่
        df['processed_date'] = pd.Timestamp.now()
        df['status'] = 'processed'
        
        # 3. บันทึกผลลัพธ์
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "MY_NEW_FUNCTION_result.xlsx")
        df.to_excel(output_file, index=False)
        
        print(f"💾 บันทึกผลลัพธ์: {output_file}")
        
        # 4. คืนค่า DataFrame สำหรับแสดงผล (optional)
        return df
        
    except Exception as e:
        print(f"❌ Error in MY_NEW_FUNCTION: {e}")
        raise e

# ถ้ามี function อื่นๆ เพิ่มเติม ใส่ที่นี่
def helper_function():
    """Helper function"""
    pass
```

### 2️⃣ **เพิ่ม Template HTML (ถ้าต้องการหน้าเฉพาะ)**

สร้างไฟล์ `templates/my_new_function.html`:

```html
{% extends "base.html" %}

{% block title %}MY NEW FUNCTION - IE Function Portal{% endblock %}

{% block css %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
{% endblock %}

{% block content %}
<div class="main-container">
    <div class="header">
        <i class="fas fa-magic icon"></i>
        <h1>MY NEW FUNCTION</h1>
        <p>คำอธิบาย function ของคุณ</p>
    </div>
    
    <!-- เพิ่ม content เฉพาะของคุณที่นี่ -->
    
</div>
{% endblock %}
```

### 3️⃣ **เพิ่ม Route (ถ้าต้องการหน้าเฉพาะ)**

ในไฟล์ `app.py` เพิ่ม:

```python
@app.route("/my_new_function", methods=["GET", "POST"]) 
def my_new_function_route():
    if request.method == "GET":
        return render_template("my_new_function.html")
    
    # Handle POST request
    # ใส่ logic การประมวลผลที่นี่
    pass
```

### 4️⃣ **เพิ่ม CSS/JS (ถ้าต้องการ)**

- `static/css/my_new_function.css`
- `static/js/my_new_function.js`

---

## 🎯 **ข้อกำหนดสำคัญ:**

### ✅ **ต้องมี:**
1. **Function `run(input_path, output_dir)`** - entry point หลัก
2. **ชื่อไฟล์ตรงกับชื่อ function** (เช่น MY_FUNCTION.py)
3. **ไฟล์อยู่ในโฟลเดอร์ `functions/`**
4. **Return DataFrame หรือ None**

### ⚠️ **ข้อควรระวัง:**
- **ไฟล์ต้องไม่ขึ้นต้นด้วย `__`** (เช่น `__init__.py`)
- **ใช้ proper error handling**
- **ใส่ print statements เพื่อ debug**
- **บันทึกไฟล์ผลลัพธ์ใน output_dir**

---

## 🔧 **ตัวอย่าง Function ง่ายๆ:**

```python
# functions/EXCEL_MERGER.py

import pandas as pd
import os
import glob

def run(input_path, output_dir):
    """รวมไฟล์ Excel หลายไฟล์เป็นไฟล์เดียว"""
    
    # หาไฟล์ Excel ทั้งหมด
    excel_files = glob.glob(os.path.join(input_path, "*.xlsx"))
    
    if not excel_files:
        raise ValueError("ไม่พบไฟล์ Excel")
    
    # รวมไฟล์
    combined_df = pd.DataFrame()
    for file in excel_files:
        df = pd.read_excel(file)
        df['source_file'] = os.path.basename(file)
        combined_df = pd.concat([combined_df, df], ignore_index=True)
    
    # บันทึกผลลัพธ์
    output_file = os.path.join(output_dir, "merged_excel.xlsx")
    combined_df.to_excel(output_file, index=False)
    
    return combined_df
```

---

## 🎉 **เสร็จแล้ว!**

หลังจากสร้างไฟล์ใน `functions/` แล้ว:

1. **รีสตาร์ทแอป**
2. **Function จะปรากฏในหน้าหลักอัตโนมัติ**
3. **User สามารถเลือกใช้งานได้เลย**

**ง่ายมาก!** ไม่ต้องแก้ไข `app.py` เลย ระบบจะ detect function ใหม่อัตโนมัติ! 🚀
