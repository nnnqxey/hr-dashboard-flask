import os
import io
from flask import Flask, render_template, request, jsonify
import pandas as pd

# กำหนดเส้นทางโฟลเดอร์ templates ให้ถูกต้องบน Vercel
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
app = Flask(__name__, template_folder=template_dir)

# ตัวแปรเก็บข้อมูลชั่วคราว (Global DataFrame)
df_data = None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    global df_data
    if 'file' not in request.files:
        return jsonify({'error': 'กรุณาเลือกไฟล์ก่อนอัปโหลด'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'ไม่ได้เลือกไฟล์'}), 400

    try:
        content = file.read().decode('utf-8', errors='ignore')
        # ตรวจสอบตัวคั่นข้อมูล (Comma หรือ Tab)
        delimiter = '\t' if '\t' in content else ','
        df_data = pd.read_csv(io.StringIO(content), sep=delimiter)
        
        # จัดการชื่อคอลัมน์ตัด space ออก
        df_data.columns = df_data.columns.str.strip()

        # สร้างตัวเลือก Filters
        departments = sorted(df_data['Department'].dropna().unique().tolist()) if 'Department' in df_data.columns else []
        statuses = sorted(df_data['EmploymentStatus'].dropna().unique().tolist()) if 'EmploymentStatus' in df_data.columns else []
        perf_scores = sorted(df_data['PerformanceScore'].dropna().unique().tolist()) if 'PerformanceScore' in df_data.columns else []

        return jsonify({
            'message': 'อัปโหลดและประมวลผลไฟล์สำเร็จ!',
            'filters': {
                'departments': departments,
                'statuses': statuses,
                'perf_scores': perf_scores
            }
        })
    except Exception as e:
        return jsonify({'error': f'ไม่สามารถประมวลผลไฟล์ได้: {str(e)}'}), 500

@app.route('/api/data', methods=['GET'])
def get_data():
    global df_data
    if df_data is None:
        return jsonify({'error': 'ยังไม่มีข้อมูล'}), 400

    filtered_df = df_data.copy()

    # กรองข้อมูลตาม Parameters
    dept = request.args.get('department')
    status = request.args.get('status')
    perf = request.args.get('performance')

    if dept and dept != 'All' and 'Department' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Department'] == dept]
    if status and status != 'All' and 'EmploymentStatus' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['EmploymentStatus'] == status]
    if perf and perf != 'All' and 'PerformanceScore' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['PerformanceScore'] == perf]

    # คำนวณ KPI
    total_emp = len(filtered_df)
    avg_pay = round(filtered_df['PayRate'].mean(), 2) if 'PayRate' in filtered_df.columns and total_emp > 0 else 0
    active_emp = len(filtered_df[filtered_df['EmploymentStatus'] == 'Active']) if 'EmploymentStatus' in filtered_df.columns else 0

    # ข้อมูลสำหรับกราฟ
    dept_chart = filtered_df['Department'].value_counts().to_dict() if 'Department' in filtered_df.columns else {}
    perf_chart = filtered_df['PerformanceScore'].value_counts().to_dict() if 'PerformanceScore' in filtered_df.columns else {}

    # ข้อมูลตาราง (จำกัด 100 แถว)
    table_data = filtered_df.head(100).fillna('').to_dict(orient='records')

    return jsonify({
        'kpi': {
            'total': total_emp,
            'avg_pay': avg_pay,
            'active': active_emp
        },
        'charts': {
            'department': dept_chart,
            'performance': perf_chart
        },
        'table': table_data
    })

if __name__ == '__main__':
    app.run(debug=True)