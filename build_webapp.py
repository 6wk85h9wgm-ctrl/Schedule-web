#!/usr/bin/env python3
"""Parse all 8 teachers' schedule data and generate a mobile-friendly HTML web app."""

import json
import csv
import io
from datetime import datetime, timedelta

# Sheet ID to teacher name mapping (8 teachers with current data)
SHEET_MAP = {
    'hb5wxe': '米开-Ivory',
    'BB08J2': '张颜清-Anakin',
    'g8lkcs': '才鼎龙-Parker',
    't6yzbv': '刘适妤-Naomi',
    'p0q6uh': '方露-Luna',
    'h9uq1n': '上官旭东-Alex',
    'q1blqg': '黄心如-Shannon',
    'zj12m5': '艾尔夏提-Earry',
}

# Half-hour time slots from 13:00 to 22:00
TIME_SLOTS = []
for h in range(13, 23):
    TIME_SLOTS.append(f"{h:02d}:00")
    if h < 22:
        TIME_SLOTS.append(f"{h:02d}:30")
# ["13:00", "13:30", "14:00", ..., "21:30", "22:00"]


def parse_time_to_minutes(time_str):
    """Parse a time string like '14:00', '14：00', '14点' to minutes since midnight."""
    time_str = time_str.strip().replace('：', ':')
    if '点' in time_str:
        time_str = time_str.replace('点', ':00')
    if ':' in time_str:
        parts = time_str.split(':')
        return int(parts[0]) * 60 + int(parts[1])
    else:
        try:
            return int(time_str) * 60
        except:
            return None


def parse_time_slot(time_str):
    """Parse a time slot like '14:00-15:00' and return list of half-hour slot strings it covers."""
    time_str = time_str.strip().replace('：', ':').replace('点', ':00')
    
    # Try different separators
    for sep in ['-', '—', '–', '~']:
        if sep in time_str:
            parts = time_str.split(sep)
            if len(parts) == 2:
                start_min = parse_time_to_minutes(parts[0])
                end_min = parse_time_to_minutes(parts[1])
                if start_min is not None and end_min is not None:
                    if end_min <= start_min:
                        end_min += 24 * 60  # Handle overnight
                    
                    slots = []
                    current = start_min
                    while current < end_min:
                        h = current // 60
                        m = current % 60
                        slot = f"{h:02d}:{m:02d}"
                        if slot in TIME_SLOTS:
                            slots.append(slot)
                        current += 30
                    return slots
    return []


def parse_csv_content(content, teacher_name):
    """Parse CSV content and return busy entries and dates_with_data."""
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    
    busy_entries = []  # (date, time_slot, content)
    rest_entries = []  # (date, time_slot) — teacher is on rest
    dates_with_data = set()
    current_year = None
    current_dates = {}  # col_index -> date_iso
    REST_MARKERS = ['休息', '假期', '放假', '休假']

    def is_rest_cell(text):
        return any(m in text for m in REST_MARKERS)

    for row_idx, row in enumerate(rows):
        if not row:
            continue
        
        first_cell = row[0].strip() if row[0] else ''
        
        # Detect year header (e.g., "2026年" or "2026年5月" or "2025年,")
        if '年' in first_cell:
            try:
                year_part = first_cell.split('年')[0].strip()
                current_year = int(''.join(c for c in year_part if c.isdigit()))
            except:
                pass
            continue
        
        # Detect month-only header (e.g., "5月" or "10月") — skip, we parse month from date strings
        if first_cell.endswith('月') and '年' not in first_cell and len(first_cell) <= 5:
            continue
        
        # Skip weekday header rows (",星期一,星期二,...")
        if not first_cell and len(row) > 1 and '星期' in str(row[1]):
            continue
        
        # Detect "时间" header row
        if first_cell == '时间':
            current_dates = {}
            for i in range(1, len(row)):
                cell = row[i].strip()
                if not cell:
                    continue
                
                # Format 1: "YYYY/M/D/星期X" or "YYYY/M/D"
                if '/' in cell and cell[0:4].isdigit():
                    parts = cell.split('/')
                    try:
                        year = int(parts[0])
                        month = int(parts[1])
                        day = int(parts[2])
                        date_iso = f"{year}-{month:02d}-{day:02d}"
                        current_dates[i] = date_iso
                        dates_with_data.add(date_iso)
                        if year:
                            current_year = year
                        continue
                    except:
                        pass
                
                # Format 2: "M月D日" or "M月D日/星期X"
                date_str = cell.split('/')[0].split('星期')[0].split('周')[0].strip()
                try:
                    if '月' in date_str:
                        month_part = date_str.split('月')[0].strip()
                        day_part = date_str.split('月')[1].replace('日', '').strip()
                        month = int(''.join(c for c in month_part if c.isdigit()))
                        day = int(''.join(c for c in day_part if c.isdigit()))
                        if current_year:
                            date_iso = f"{current_year}-{month:02d}-{day:02d}"
                            current_dates[i] = date_iso
                            dates_with_data.add(date_iso)
                except:
                    pass
            continue
        
        # Skip standalone date serials
        try:
            serial = int(float(first_cell))
            if 40000 < serial < 50000:
                continue
        except:
            pass
        
        # Data row: first cell is time slot
        time_str = first_cell
        
        # If time column is empty, try to infer time slot from context
        if not time_str:
            if not current_dates:
                continue
            # Check if any data column has content
            has_data = any(
                col_idx < len(row) and row[col_idx].strip()
                for col_idx in current_dates
            )
            if not has_data:
                continue
            # Infer time slot by looking ahead at next row with a time label
            for look_ahead in range(row_idx + 1, min(row_idx + 10, len(rows))):
                next_r = rows[look_ahead]
                next_t = next_r[0].strip() if next_r[0] else ''
                if next_t and ('-' in next_t or '—' in next_t or '~' in next_t):
                    gap = look_ahead - row_idx
                    t = next_t.replace('—', '-').replace('~', '-')
                    parts = t.split('-')
                    try:
                        sp = parts[0].strip().split(':')
                        sh = int(sp[0])
                        sm = int(sp[1]) if len(sp) > 1 and sp[1] else 0
                        ih = sh - gap
                        if ih >= 0:
                            time_str = f"{ih:02d}:{sm:02d}-{ih+1:02d}:{sm:02d}"
                    except:
                        pass
                    break
            if not time_str:
                time_str = "13:00-14:00"  # Default first slot
        
        if '-' not in time_str and '—' not in time_str and '~' not in time_str:
            continue
        
        slots = parse_time_slot(time_str)
        if not slots:
            continue
        
        # Check columns for student data
        for col_idx, date_iso in current_dates.items():
            if col_idx < len(row):
                cell_content = row[col_idx].strip()
                if cell_content:
                    if is_rest_cell(cell_content):
                        # Rest marker — track as rest, not busy
                        for slot in slots:
                            rest_entries.append((date_iso, slot))
                    else:
                        for slot in slots:
                            busy_entries.append((date_iso, slot, cell_content))

                    # Forward extension for merged "休息"/"假期" cells
                    # These are merged cells in the original spreadsheet —
                    # CSV export only shows text in the first row, leaving
                    # subsequent rows empty. We can't get exact merge boundaries
                    # from the API, so we use a smart heuristic:
                    # - If there are classes later in the day (content in a later row),
                    #   the rest is probably 4 hours (typical merge), so cap at 3 rows
                    # - If all remaining cells are empty (no classes at all),
                    #   the rest likely covers the entire day, so extend fully
                    if is_rest_cell(cell_content):
                        # First, scan ahead to check if there's any content later
                        has_class_later = False
                        for scan_idx in range(row_idx + 1, len(rows)):
                            scan_row = rows[scan_idx]
                            scan_time = scan_row[0].strip() if scan_row[0] else ''
                            if scan_time == '时间' or '年' in scan_time:
                                break
                            if scan_time and '-' not in scan_time and '—' not in scan_time and '~' not in scan_time:
                                break
                            if col_idx < len(scan_row) and scan_row[col_idx].strip():
                                has_class_later = True
                                break
                        
                        # Set extension limit based on whether there are classes later
                        if has_class_later:
                            max_extend = 3  # 4 hours total (1 + 3)
                        else:
                            max_extend = 99  # Full day
                        
                        extend_count = 0
                        for next_row_idx in range(row_idx + 1, len(rows)):
                            if extend_count >= max_extend:
                                break
                            next_row = rows[next_row_idx]
                            next_time = next_row[0].strip() if next_row[0] else ''
                            
                            # Stop at "时间" header (new week)
                            if next_time == '时间':
                                break
                            
                            # Stop at year/month headers
                            if '年' in next_time or (next_time.endswith('月') and len(next_time) <= 5):
                                break
                            
                            # If time column has content but it's not a time slot, stop
                            if next_time and '-' not in next_time and '—' not in next_time and '~' not in next_time:
                                break
                            
                            # Stop if cell has content (merge ended early)
                            if col_idx < len(next_row) and next_row[col_idx].strip():
                                break
                            
                            # Stop if the row has no data at all and no time label
                            if not next_time:
                                has_any = any(j < len(next_row) and next_row[j].strip() for j in range(1, len(next_row)))
                                if not has_any:
                                    break
                            
                            # Determine time slots for this row
                            if next_time:
                                next_slots = parse_time_slot(next_time)
                            else:
                                # Infer time slot by looking ahead
                                inferred = None
                                for la in range(next_row_idx + 1, min(next_row_idx + 10, len(rows))):
                                    lt = rows[la][0].strip() if rows[la][0] else ''
                                    if lt and ('-' in lt or '—' in lt or '~' in lt):
                                        gap = la - next_row_idx
                                        t = lt.replace('—', '-').replace('~', '-')
                                        parts = t.split('-')
                                        try:
                                            sp = parts[0].strip().split(':')
                                            sh = int(sp[0])
                                            sm = int(sp[1]) if len(sp) > 1 and sp[1] else 0
                                            ih = sh - gap
                                            if ih >= 0:
                                                inferred = f"{ih:02d}:{sm:02d}-{ih+1:02d}:{sm:02d}"
                                        except:
                                            pass
                                        break
                                next_slots = parse_time_slot(inferred) if inferred else []

                            # Add extended rest slots
                            for ns in next_slots:
                                rest_entries.append((date_iso, ns))
                            extend_count += 1
    
    return busy_entries, rest_entries, dates_with_data


def get_weekday(date_iso):
    """Return Chinese weekday for a date string."""
    try:
        d = datetime.strptime(date_iso, '%Y-%m-%d')
        weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        return weekdays[d.weekday()]
    except:
        return ''


def format_date_display(date_iso):
    """Format date as '8月18日 周二'."""
    try:
        d = datetime.strptime(date_iso, '%Y-%m-%d')
        weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        return f"{d.month}月{d.day}日 {weekdays[d.weekday()]}"
    except:
        return date_iso


# ============ Main Processing ============

print(f"=== Parsing all {len(SHEET_MAP)} teachers' data ===\n")

all_busy = {}      # busy[date][slot] = [teacher_names]
all_rest = {}      # rest[date][slot] = [teacher_names]
all_has_data = {}  # has_data[date] = set(teacher_names)
all_dates = set()

for sheet_id, teacher_name in SHEET_MAP.items():
    filepath = f'sheet_data/{sheet_id}.json'
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        content = data.get('content', '')
        
        busy_entries, rest_entries, dates_with_data = parse_csv_content(content, teacher_name)
        
        # Record dates with data
        for date_iso in dates_with_data:
            all_dates.add(date_iso)
            if date_iso not in all_has_data:
                all_has_data[date_iso] = set()
            all_has_data[date_iso].add(teacher_name)
        
        # Record busy entries
        for date_iso, slot, cell_content in busy_entries:
            all_dates.add(date_iso)
            if date_iso not in all_busy:
                all_busy[date_iso] = {}
            if slot not in all_busy[date_iso]:
                all_busy[date_iso][slot] = []
            if teacher_name not in all_busy[date_iso][slot]:
                all_busy[date_iso][slot].append(teacher_name)
        
        # Record rest entries
        for date_iso, slot in rest_entries:
            all_dates.add(date_iso)
            if date_iso not in all_rest:
                all_rest[date_iso] = {}
            if slot not in all_rest[date_iso]:
                all_rest[date_iso][slot] = []
            if teacher_name not in all_rest[date_iso][slot]:
                all_rest[date_iso][slot].append(teacher_name)
        
        print(f"  {teacher_name:20s}: {len(busy_entries):4d} busy slots, {len(rest_entries):4d} rest slots, {len(dates_with_data):3d} dates")
    except Exception as e:
        print(f"  ERROR reading {teacher_name}: {e}")

# Sort dates
dates_sorted = sorted(all_dates)

# Build compact JSON for embedding
# Structure: {date: {slot: [busy_teachers]}}
busy_json = {}
for date in dates_sorted:
    if date in all_busy:
        busy_json[date] = all_busy[date]

# rest: {date: {slot: [rest_teachers]}}
rest_json = {}
for date in dates_sorted:
    if date in all_rest:
        rest_json[date] = all_rest[date]

# has_data: {date: [teachers_with_data]}
has_data_json = {}
for date in dates_sorted:
    if date in all_has_data:
        has_data_json[date] = sorted(all_has_data[date])

# Build date display mapping
date_displays = {}
for date in dates_sorted:
    date_displays[date] = format_date_display(date)

teachers_sorted = sorted(SHEET_MAP.values())

print(f"\n=== Summary ===")
print(f"Total dates: {len(dates_sorted)}")
print(f"Date range: {dates_sorted[0]} to {dates_sorted[-1]}")
print(f"Total teachers: {len(teachers_sorted)}")
print(f"Dates with busy data: {len(busy_json)}")
print(f"Dates with rest data: {len(rest_json)}")

# ============ Generate HTML ============

print("\n=== Generating HTML ===")

# Embed data as JSON
embed_data = json.dumps({
    'dates': dates_sorted,
    'dateDisplays': date_displays,
    'teachers': teachers_sorted,
    'timeSlots': TIME_SLOTS,
    'busy': busy_json,
    'rest': rest_json,
    'hasData': has_data_json,
}, ensure_ascii=False)

# Current timestamp for display
# 显示北京时间（CI 服务器为 UTC，需 +8）
refresh_time = (datetime.utcnow() + timedelta(hours=8)).strftime('%Y年%m月%d日 %H:%M')

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>排课空档查询</title>
<style>
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    -webkit-tap-highlight-color: transparent;
}}

body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    background: #f0f2f5;
    color: #333;
    min-height: 100vh;
    padding: 16px;
}}

.container {{
    max-width: 500px;
    margin: 0 auto;
}}

.header {{
    text-align: center;
    padding: 24px 0 20px;
}}

.header h1 {{
    font-size: 22px;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 6px;
}}

.header p {{
    font-size: 13px;
    color: #999;
}}

.card {{
    background: #fff;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}}

.form-group {{
    margin-bottom: 18px;
}}

.form-group:last-child {{
    margin-bottom: 0;
}}

label {{
    display: block;
    font-size: 14px;
    font-weight: 600;
    color: #555;
    margin-bottom: 8px;
}}

select {{
    width: 100%;
    height: 48px;
    padding: 0 14px;
    font-size: 16px;
    border: 2px solid #e8e8e8;
    border-radius: 12px;
    background: #fafafa;
    color: #333;
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath fill='%23999' d='M6 8L0 0h12z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 16px center;
    cursor: pointer;
    transition: border-color 0.2s;
}}

select:focus {{
    outline: none;
    border-color: #4a90d9;
    background: #fff;
}}

select:disabled {{
    opacity: 0.5;
    cursor: not-allowed;
}}

.btn-query {{
    width: 100%;
    height: 50px;
    background: linear-gradient(135deg, #4a90d9, #357abd);
    color: #fff;
    border: none;
    border-radius: 12px;
    font-size: 17px;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.2s, transform 0.1s;
    margin-top: 4px;
}}

.btn-query:active {{
    transform: scale(0.98);
}}

.btn-query:disabled {{
    opacity: 0.5;
    cursor: not-allowed;
}}

.result {{
    display: none;
    animation: fadeIn 0.3s ease;
}}

.result.show {{
    display: block;
}}

@keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(10px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

.result-hours {{
    text-align: center;
    padding: 28px 20px;
    border-radius: 16px;
    margin-bottom: 16px;
}}

.result-hours.has-free {{
    background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
    border: 1px solid #a5d6a7;
}}

.result-hours.no-free {{
    background: linear-gradient(135deg, #fff3e0, #ffe0b2);
    border: 1px solid #ffcc80;
}}

.result-hours .number {{
    font-size: 48px;
    font-weight: 800;
    line-height: 1.1;
}}

.result-hours.has-free .number {{
    color: #2e7d32;
}}

.result-hours.no-free .number {{
    color: #e65100;
}}

.result-hours .unit {{
    font-size: 16px;
    font-weight: 500;
    margin-top: 4px;
}}

.result-hours.has-free .unit {{
    color: #388e3c;
}}

.result-hours.no-free .unit {{
    color: #ef6c00;
}}

.result-hours .label {{
    font-size: 13px;
    color: #888;
    margin-top: 8px;
}}

.result-info {{
    font-size: 13px;
    color: #999;
    text-align: center;
    margin-bottom: 14px;
}}

.teacher-list {{
    list-style: none;
}}

.teacher-list li {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 14px;
    margin-bottom: 8px;
    border-radius: 10px;
    font-size: 15px;
}}

.teacher-list li.free {{
    background: #e8f5e9;
    color: #2e7d32;
}}

.teacher-list li.busy {{
    background: #fce4ec;
    color: #c62828;
}}

.teacher-list li.rest {{
    background: #fff3e0;
    color: #e65100;
}}

.teacher-list li.no-data {{
    background: #f5f5f5;
    color: #999;
}}

.teacher-list li .status {{
    font-size: 12px;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 20px;
}}

.teacher-list li.free .status {{
    background: #4caf50;
    color: #fff;
}}

.teacher-list li.busy .status {{
    background: #ef5350;
    color: #fff;
}}

.teacher-list li.rest .status {{
    background: #ff9800;
    color: #fff;
}}

.teacher-list li.no-data .status {{
    background: #bdbdbd;
    color: #fff;
}}

.teacher-section-title {{
    font-size: 13px;
    font-weight: 600;
    color: #888;
    margin-bottom: 10px;
    margin-top: 4px;
}}

.footer {{
    text-align: center;
    padding: 20px 0 10px;
    font-size: 12px;
    color: #bbb;
}}

.footer a {{
    color: #4a90d9;
    text-decoration: none;
}}

.hint {{
    font-size: 12px;
    color: #aaa;
    text-align: center;
    margin-top: 8px;
}}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>排课空档查询</h1>
        <p>选择日期和时段，查看老师空档</p>
    </div>
    
    <div class="card">
        <div class="form-group">
            <label for="dateSelect">日期</label>
            <select id="dateSelect">
                <option value="">请选择日期</option>
            </select>
        </div>
        
        <div class="form-group">
            <label for="timeSelect">时段</label>
            <select id="timeSelect" disabled>
                <option value="">请先选择日期</option>
            </select>
        </div>
        
        <button class="btn-query" id="queryBtn" disabled>查询空档</button>
    </div>
    
    <div class="result" id="result">
        <div class="result-hours" id="resultHours">
            <div class="number" id="resultNumber">0</div>
            <div class="unit" id="resultUnit">空档小时</div>
            <div class="label" id="resultLabel"></div>
        </div>
        
        <div class="card" id="teacherCard" style="display:none;">
            <div class="result-info" id="resultInfo"></div>
            <div class="teacher-section-title" id="freeTitle"></div>
            <ul class="teacher-list" id="freeList"></ul>
            <div class="teacher-section-title" id="restTitle" style="margin-top:16px;"></div>
            <ul class="teacher-list" id="restList"></ul>
            <div class="teacher-section-title" id="busyTitle" style="margin-top:16px;"></div>
            <ul class="teacher-list" id="busyList"></ul>
            <div class="teacher-section-title" id="noDataTitle" style="margin-top:16px;"></div>
            <ul class="teacher-list" id="noDataList"></ul>
        </div>
    </div>
    
    <div class="footer">
        <p>数据来源：总课程表在线表格</p>
        <p id="dataUpdate">数据更新时间（北京时间）：{refresh_time}</p>
    </div>
</div>

<script>
const DATA = {embed_data};

// Populate date dropdown
const dateSelect = document.getElementById('dateSelect');
const timeSelect = document.getElementById('timeSelect');
const queryBtn = document.getElementById('queryBtn');

// Sort dates, show most recent first
const sortedDates = DATA.dates.slice().sort().reverse();

// Group by month for better UX
let currentMonth = '';
sortedDates.forEach(date => {{
    const display = DATA.dateDisplays[date] || date;
    const month = date.substring(0, 7);
    if (month !== currentMonth) {{
        currentMonth = month;
        const opt = document.createElement('option');
        opt.value = month;
        opt.textContent = month.replace('-', '年') + '月';
        opt.disabled = true;
        opt.style.fontWeight = 'bold';
        dateSelect.appendChild(opt);
    }}
    const opt = document.createElement('option');
    opt.value = date;
    opt.textContent = '  ' + display;
    dateSelect.appendChild(opt);
}});

// Default to today or nearest date
const today = new Date();
const todayStr = today.getFullYear() + '-' + 
    String(today.getMonth() + 1).padStart(2, '0') + '-' + 
    String(today.getDate()).padStart(2, '0');
const hasToday = DATA.dates.includes(todayStr);
if (hasToday) {{
    dateSelect.value = todayStr;
}} else {{
    // Find nearest future date
    const futureDates = sortedDates.filter(d => d >= todayStr);
    if (futureDates.length > 0) {{
        dateSelect.value = futureDates[futureDates.length - 1]; // nearest to today
    }}
}}

if (dateSelect.value) {{
    timeSelect.disabled = false;
    queryBtn.disabled = false;
}}

// Populate time slots
DATA.timeSlots.forEach(slot => {{
    const opt = document.createElement('option');
    opt.value = slot;
    opt.textContent = slot;
    timeSelect.appendChild(opt);
}});

// Auto-trigger query on change
dateSelect.addEventListener('change', () => {{
    if (dateSelect.value) {{
        timeSelect.disabled = false;
        queryBtn.disabled = false;
    }} else {{
        timeSelect.disabled = true;
        queryBtn.disabled = true;
    }}
}});

queryBtn.addEventListener('click', query);
timeSelect.addEventListener('change', query);

function query() {{
    const date = dateSelect.value;
    const slot = timeSelect.value;
    
    if (!date || !slot) return;
    
    // Get busy and rest teachers for this date+slot
    const busyTeachers = (DATA.busy[date] && DATA.busy[date][slot]) || [];
    const restTeachers = (DATA.rest[date] && DATA.rest[date][slot]) || [];
    const teachersWithData = DATA.hasData[date] || [];
    
    const allTeachers = DATA.teachers;
    
    // Categorize teachers
    const free = [];
    const busy = [];
    const rest = [];
    const noData = [];
    
    allTeachers.forEach(teacher => {{
        if (busyTeachers.includes(teacher)) {{
            busy.push(teacher);
        }} else if (restTeachers.includes(teacher)) {{
            rest.push(teacher);
        }} else if (teachersWithData.includes(teacher)) {{
            free.push(teacher);
        }} else {{
            noData.push(teacher);
        }}
    }});
    
    // Calculate free hours (each free teacher = 0.5 hours)
    const freeHours = free.length * 0.5;
    
    // Display result
    const result = document.getElementById('result');
    const resultHours = document.getElementById('resultHours');
    const resultNumber = document.getElementById('resultNumber');
    const resultUnit = document.getElementById('resultUnit');
    const resultLabel = document.getElementById('resultLabel');
    
    result.classList.add('show');
    
    if (freeHours > 0) {{
        resultHours.className = 'result-hours has-free';
        resultNumber.textContent = freeHours % 1 === 0 ? freeHours : freeHours.toFixed(1);
        resultUnit.textContent = '空档小时';
        resultLabel.textContent = free.length + ' 位老师有空';
    }} else {{
        resultHours.className = 'result-hours no-free';
        resultNumber.textContent = '0';
        resultUnit.textContent = '空档小时';
        resultLabel.textContent = '该时段暂无空闲老师';
    }}
    
    // Show teacher list
    const teacherCard = document.getElementById('teacherCard');
    const resultInfo = document.getElementById('resultInfo');
    const dateDisplay = DATA.dateDisplays[date] || date;
    resultInfo.textContent = dateDisplay + ' ' + slot + ' - ' + slot.substring(0,2) + ':' + (parseInt(slot.substring(3)) + 30 === 60 ? (parseInt(slot.substring(0,2)) + 1) + ':00' : slot.substring(0,2) + ':' + String(parseInt(slot.substring(3)) + 30).padStart(2, '0'));
    
    // Free teachers
    const freeTitle = document.getElementById('freeTitle');
    const freeList = document.getElementById('freeList');
    freeList.innerHTML = '';
    if (free.length > 0) {{
        freeTitle.textContent = '有空档 (' + free.length + ')';
        freeTitle.style.display = 'block';
        free.forEach(t => {{
            const li = document.createElement('li');
            li.className = 'free';
            li.innerHTML = '<span>' + t + '</span><span class="status">空闲</span>';
            freeList.appendChild(li);
        }});
    }} else {{
        freeTitle.style.display = 'none';
    }}
    
    // Rest teachers
    const restTitle = document.getElementById('restTitle');
    const restList = document.getElementById('restList');
    restList.innerHTML = '';
    if (rest.length > 0) {{
        restTitle.textContent = '休息 (' + rest.length + ')';
        restTitle.style.display = 'block';
        rest.forEach(t => {{
            const li = document.createElement('li');
            li.className = 'rest';
            li.innerHTML = '<span>' + t + '</span><span class="status">休息</span>';
            restList.appendChild(li);
        }});
    }} else {{
        restTitle.style.display = 'none';
    }}
    
    // Busy teachers
    const busyTitle = document.getElementById('busyTitle');
    const busyList = document.getElementById('busyList');
    busyList.innerHTML = '';
    if (busy.length > 0) {{
        busyTitle.textContent = '有课 (' + busy.length + ')';
        busyTitle.style.display = 'block';
        busy.forEach(t => {{
            const li = document.createElement('li');
            li.className = 'busy';
            li.innerHTML = '<span>' + t + '</span><span class="status">有课</span>';
            busyList.appendChild(li);
        }});
    }} else {{
        busyTitle.style.display = 'none';
    }}
    
    // No data teachers
    const noDataTitle = document.getElementById('noDataTitle');
    const noDataList = document.getElementById('noDataList');
    noDataList.innerHTML = '';
    if (noData.length > 0) {{
        noDataTitle.textContent = '未排课 (' + noData.length + ')';
        noDataTitle.style.display = 'block';
        noData.forEach(t => {{
            const li = document.createElement('li');
            li.className = 'no-data';
            li.innerHTML = '<span>' + t + '</span><span class="status">未知</span>';
            noDataList.appendChild(li);
        }});
    }} else {{
        noDataTitle.style.display = 'none';
    }}
    
    teacherCard.style.display = 'block';
    
    // Scroll to result
    result.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
}}

// Auto-query if defaults are set
if (dateSelect.value && timeSelect.value) {{
    setTimeout(query, 300);
}}
</script>
</body>
</html>'''

output_dir = 'webapp'
import os
os.makedirs(output_dir, exist_ok=True)

output_path = os.path.join(output_dir, 'index.html')
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\nHTML saved to: {output_path}")
print(f"File size: {os.path.getsize(output_path) / 1024:.1f} KB")

# Also save the data JSON separately for reference
with open(os.path.join(output_dir, 'schedule_data.json'), 'w', encoding='utf-8') as f:
    json.dump({
        'dates': dates_sorted,
        'dateDisplays': date_displays,
        'teachers': teachers_sorted,
        'timeSlots': TIME_SLOTS,
        'busy': busy_json,
        'rest': rest_json,
        'hasData': has_data_json,
    }, f, ensure_ascii=False, indent=2)

print(f"Data JSON saved to: {os.path.join(output_dir, 'schedule_data.json')}")
print("\nDone!")
