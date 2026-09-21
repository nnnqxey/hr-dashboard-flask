import io
from flask import Flask, request, jsonify, render_template_string
import pandas as pd

app = Flask(__name__)

df_data = None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HR Analytics Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { background-color: #f8f9fa; font-family: system-ui, -apple-system, sans-serif; }
        .card-kpi { border-left: 5px solid #0d6efd; }
    </style>
</head>
<body>
    <div class="container py-4">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2 class="text-primary m-0">📊 HR Analytics & Dashboard</h2>
            <button id="btnClear" class="btn btn-outline-danger" style="display: none;" onclick="clearData()">🗑️ ล้างข้อมูลทั้งหมด</button>
        </div>

        <div class="card mb-4 shadow-sm">
            <div class="card-body">
                <h5 class="card-title">อัปโหลดไฟล์ข้อมูลพนักงาน (.txt / .csv)</h5>
                <form id="uploadForm" class="row g-3 mt-1">
                    <div class="col-auto">
                        <input type="file" id="fileInput" class="form-control" accept=".csv, .txt, .tsv" required>
                    </div>
                    <div class="col-auto">
                        <button type="submit" class="btn btn-primary">อัปโหลดและประมวลผล</button>
                    </div>
                </form>
                <div id="uploadAlert" class="mt-3"></div>
            </div>
        </div>

        <div class="card mb-4 shadow-sm" id="filterSection" style="display: none;">
            <div class="card-body">
                <h5 class="card-title">🔍 ตัวกรองข้อมูล (Filters)</h5>
                <div class="row g-3">
                    <div class="col-md-3">
                        <label class="form-label">แผนก (Department)</label>
                        <select id="filterDept" class="form-select" onchange="loadDashboardData()">
                            <option value="All">ทั้งหมด</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label font-weight-bold text-primary">เพศ (Gender)</label>
                        <select id="filterGender" class="form-select" onchange="loadDashboardData()">
                            <option value="All">ทั้งหมด</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">สถานะการทำงาน (Status)</label>
                        <select id="filterStatus" class="form-select" onchange="loadDashboardData()">
                            <option value="All">ทั้งหมด</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">คะแนนประเมิน (Performance)</label>
                        <select id="filterPerf" class="form-select" onchange="loadDashboardData()">
                            <option value="All">ทั้งหมด</option>
                        </select>
                    </div>
                </div>
            </div>
        </div>

        <div id="dashboardContent" style="display: none;">
            <div class="row mb-4">
                <div class="col-md-4">
                    <div class="card card-kpi shadow-sm p-3">
                        <small class="text-muted">จำนวนพนักงานทั้งหมด</small>
                        <h3 id="kpiTotal" class="text-primary mb-0">0</h3>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card card-kpi shadow-sm p-3" style="border-left-color: #198754;">
                        <small class="text-muted">อัตราค่าจ้างเฉลี่ย ($/hr)</small>
                        <h3 id="kpiPayRate" class="text-success mb-0">$0.00</h3>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card card-kpi shadow-sm p-3" style="border-left-color: #ffc107;">
                        <small class="text-muted">พนักงานสถานะ Active</small>
                        <h3 id="kpiActive" class="text-warning mb-0">0</h3>
                    </div>
                </div>
            </div>

            <div class="row mb-4">
                <div class="col-md-4">
                    <div class="card shadow-sm p-3">
                        <h6>จำนวนพนักงานแยกตามเพศ (Gender)</h6>
                        <canvas id="genderChart"></canvas>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card shadow-sm p-3">
                        <h6>จำนวนพนักงานแยกตามแผนก</h6>
                        <canvas id="deptChart"></canvas>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card shadow-sm p-3">
                        <h6>ระดับผลการปฏิบัติงาน (Performance)</h6>
                        <canvas id="perfChart"></canvas>
                    </div>
                </div>
            </div>

            <div class="card shadow-sm">
                <div class="card-body">
                    <h5>รายการข้อมูลพนักงาน (แสดงผลสูงสุด 100 รายการ)</h5>
                    <div class="table-responsive">
                        <table class="table table-hover table-striped mt-3" id="empTable">
                            <thead class="table-dark">
                                <tr>
                                    <th>Emp ID</th>
                                    <th>ชื่อ - นามสกุล</th>
                                    <th>เพศ (Gender)</th>
                                    <th>ตำแหน่ง</th>
                                    <th>แผนก</th>
                                    <th>สถานะ</th>
                                    <th>Pay Rate</th>
                                    <th>Performance</th>
                                </tr>
                            </thead>
                            <tbody></tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let genderChartObj = null;
        let deptChartObj = null;
        let perfChartObj = null;

        document.getElementById('uploadForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const fileInput = document.getElementById('fileInput');
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            const alertDiv = document.getElementById('uploadAlert');
            alertDiv.innerHTML = '<div class="alert alert-info">กำลังประมวลผลไฟล์...</div>';

            try {
                const res = await fetch('/api/upload', { method: 'POST', body: formData });
                const data = await res.json();

                if (res.ok) {
                    alertDiv.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
                    
                    populateDropdown('filterDept', data.filters.departments);
                    populateDropdown('filterGender', data.filters.genders);
                    populateDropdown('filterStatus', data.filters.statuses);
                    populateDropdown('filterPerf', data.filters.perf_scores);

                    document.getElementById('filterSection').style.display = 'block';
                    document.getElementById('dashboardContent').style.display = 'block';
                    document.getElementById('btnClear').style.display = 'block';
                    
                    loadDashboardData();
                } else {
                    alertDiv.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                }
            } catch (err) {
                alertDiv.innerHTML = `<div class="alert alert-danger">เกิดข้อผิดพลาดในการเชื่อมต่อกับ Server</div>`;
            }
        });

        function populateDropdown(elemId, list) {
            const select = document.getElementById(elemId);
            select.innerHTML = '<option value="All">ทั้งหมด</option>';
            list.forEach(item => {
                select.innerHTML += `<option value="${item}">${item}</option>`;
            });
        }

        async function loadDashboardData() {
            const dept = document.getElementById('filterDept').value;
            const gender = document.getElementById('filterGender').value;
            const status = document.getElementById('filterStatus').value;
            const perf = document.getElementById('filterPerf').value;

            const url = `/api/data?department=${encodeURIComponent(dept)}&gender=${encodeURIComponent(gender)}&status=${encodeURIComponent(status)}&performance=${encodeURIComponent(perf)}`;
            const res = await fetch(url);
            const data = await res.json();

            document.getElementById('kpiTotal').innerText = data.kpi.total;
            document.getElementById('kpiPayRate').innerText = `$${data.kpi.avg_pay}`;
            document.getElementById('kpiActive').innerText = data.kpi.active;

            renderChart('genderChart', 'doughnut', data.charts.gender, 'จำนวนพนักงาน', genderChartObj, (chart) => genderChartObj = chart, ['#0d6efd', '#dc3545', '#6c757d']);
            renderChart('deptChart', 'bar', data.charts.department, 'จำนวนพนักงาน', deptChartObj, (chart) => deptChartObj = chart);
            renderChart('perfChart', 'pie', data.charts.performance, 'สัดส่วนคะแนน', perfChartObj, (chart) => perfChartObj = chart);

            const tbody = document.querySelector('#empTable tbody');
            tbody.innerHTML = '';
            data.table.forEach(emp => {
                const genderVal = emp.Sex || emp.Gender || emp.GenderID || '';
                tbody.innerHTML += `
                    <tr>
                        <td>${emp.EmpID || ''}</td>
                        <td>${emp.Employee_Name || ''}</td>
                        <td><span class="badge ${genderVal === 'M' || genderVal === 'Male' ? 'bg-primary' : 'bg-danger'}">${genderVal || '-'}</span></td>
                        <td>${emp.Position || ''}</td>
                        <td>${emp.Department || ''}</td>
                        <td><span class="badge ${emp.EmploymentStatus === 'Active' ? 'bg-success' : 'bg-secondary'}">${emp.EmploymentStatus || ''}</span></td>
                        <td>$${emp.PayRate || 0}</td>
                        <td>${emp.PerformanceScore || ''}</td>
                    </tr>
                `;
            });
        }

        function renderChart(canvasId, type, chartData, label, chartInstance, setChart, customColors) {
            const ctx = document.getElementById(canvasId).getContext('2d');
            if (chartInstance) chartInstance.destroy();

            const colors = customColors || ['#0d6efd', '#198754', '#ffc107', '#dc3545', '#0dcaf0', '#6c757d'];

            const newChart = new Chart(ctx, {
                type: type,
                data: {
                    labels: Object.keys(chartData),
                    datasets: [{
                        label: label,
                        data: Object.values(chartData),
                        backgroundColor: colors
                    }]
                },
                options: { responsive: true }
            });
            setChart(newChart);
        }

        async function clearData() {
            if (!confirm('คุณต้องการล้างข้อมูลทั้งหมดใช่หรือไม่?')) return;

            try {
                await fetch('/api/clear', { method: 'POST' });
                
                document.getElementById('fileInput').value = '';
                document.getElementById('uploadAlert').innerHTML = '<div class="alert alert-secondary">ล้างข้อมูลเรียบร้อยแล้ว</div>';
                document.getElementById('filterSection').style.display = 'none';
                document.getElementById('dashboardContent').style.display = 'none';
                document.getElementById('btnClear').style.display = 'none';

                if (genderChartObj) genderChartObj.destroy();
                if (deptChartObj) deptChartObj.destroy();
                if (perfChartObj) perfChartObj.destroy();
            } catch (err) {
                alert('เกิดข้อผิดพลาดในการล้างข้อมูล');
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
@app.route('/<path:path>')
def home(path=None):
    return render_template_string(HTML_TEMPLATE)

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
        delimiter = '\t' if '\t' in content else ','
        df_data = pd.read_csv(io.StringIO(content), sep=delimiter)
        df_data.columns = df_data.columns.str.strip()

        # หาคอลัมน์ Gender / Sex
        gender_col = next((col for col in ['Sex', 'Gender', 'GenderID'] if col in df_data.columns), None)

        departments = sorted(df_data['Department'].dropna().unique().tolist()) if 'Department' in df_data.columns else []
        genders = sorted(df_data[gender_col].dropna().unique().tolist()) if gender_col else []
        statuses = sorted(df_data['EmploymentStatus'].dropna().unique().tolist()) if 'EmploymentStatus' in df_data.columns else []
        perf_scores = sorted(df_data['PerformanceScore'].dropna().unique().tolist()) if 'PerformanceScore' in df_data.columns else []

        return jsonify({
            'message': 'อัปโหลดและประมวลผลไฟล์สำเร็จ!',
            'filters': {
                'departments': departments,
                'genders': genders,
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

    dept = request.args.get('department')
    gender = request.args.get('gender')
    status = request.args.get('status')
    perf = request.args.get('performance')

    gender_col = next((col for col in ['Sex', 'Gender', 'GenderID'] if col in filtered_df.columns), None)

    if dept and dept != 'All' and 'Department' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Department'] == dept]
    if gender and gender != 'All' and gender_col:
        filtered_df = filtered_df[filtered_df[gender_col] == gender]
    if status and status != 'All' and 'EmploymentStatus' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['EmploymentStatus'] == status]
    if perf and perf != 'All' and 'PerformanceScore' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['PerformanceScore'] == perf]

    total_emp = len(filtered_df)
    avg_pay = round(filtered_df['PayRate'].mean(), 2) if 'PayRate' in filtered_df.columns and total_emp > 0 else 0
    active_emp = len(filtered_df[filtered_df['EmploymentStatus'] == 'Active']) if 'EmploymentStatus' in filtered_df.columns else 0

    gender_chart = filtered_df[gender_col].value_counts().to_dict() if gender_col else {}
    dept_chart = filtered_df['Department'].value_counts().to_dict() if 'Department' in filtered_df.columns else {}
    perf_chart = filtered_df['PerformanceScore'].value_counts().to_dict() if 'PerformanceScore' in filtered_df.columns else {}

    table_data = filtered_df.head(100).fillna('').to_dict(orient='records')

    return jsonify({
        'kpi': {
            'total': total_emp,
            'avg_pay': avg_pay,
            'active': active_emp
        },
        'charts': {
            'gender': gender_chart,
            'department': dept_chart,
            'performance': perf_chart
        },
        'table': table_data
    })

@app.route('/api/clear', methods=['POST'])
def clear_data():
    global df_data
    df_data = None
    return jsonify({'message': 'ล้างข้อมูลเรียบร้อยแล้ว'})

handler = app
