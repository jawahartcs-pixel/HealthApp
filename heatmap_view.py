import streamlit as st
import pandas as pd
import json
import io
from investigation_standards import InvestigationStandards
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def render_heatmap_view(db, selected_patient, user_id, edit_df, key_prefix="manage", editable=True):
    patient_profile = db.get_patient_profile(selected_patient, user_id)
    patient_gender = patient_profile.get('gender', '').lower() if patient_profile else ''

    investigation_standards = InvestigationStandards(db)
    all_standards = investigation_standards.get_all_standards()

    test_info = {}
    categories_dict = {}

    for standard in all_standards:
        if isinstance(standard, dict):
            category = standard.get('category', 'Other')
            test_name = standard.get('standard_name', '').strip()
            aliases = standard.get('aliases', '')

            if patient_gender == 'male':
                range_min = standard.get('male_range_min')
                range_max = standard.get('male_range_max')
                unit = standard.get('male_unit', '')
            elif patient_gender == 'female':
                range_min = standard.get('female_range_min')
                range_max = standard.get('female_range_max')
                unit = standard.get('female_unit', '')
            else:
                range_min = standard.get('male_range_min')
                range_max = standard.get('male_range_max')
                unit = standard.get('male_unit', '')
        else:
            if len(standard) > 4:
                category = standard[4] if standard[4] else 'Other'
                test_name = standard[1] if len(standard) > 1 else ''
                aliases = standard[5] if len(standard) > 5 and standard[5] else ""
                range_min = standard[6] if len(standard) > 6 else None
                range_max = standard[7] if len(standard) > 7 else None
                unit = standard[8] if len(standard) > 8 else ''
            else:
                continue

        if category and test_name:
            if category not in categories_dict:
                categories_dict[category] = []
            categories_dict[category].append(test_name)

            test_info[test_name] = {
                'category': category,
                'min': range_min,
                'max': range_max,
                'unit': unit
            }

            if aliases:
                for alias in aliases.split(','):
                    alias = alias.strip()
                    if alias:
                        test_info[alias] = test_info[test_name]
                        if alias not in categories_dict[category]:
                            categories_dict[category].append(alias)

    col1, col2 = st.columns([1, 1])
    with col1:
        date_format = st.selectbox(
            "Date Format:",
            options=["UK (DD/MM/YYYY)", "US (MM/DD/YYYY)"],
            key=f"{key_prefix}_heatmap_date_format"
        )
    with col2:
        sort_tests = st.selectbox(
            "Sort Tests:",
            options=["Alphabetically", "By Category"],
            key=f"{key_prefix}_heatmap_sort_tests"
        )

    st.divider()

    all_patient_tests = edit_df['Test Type'].unique().tolist()

    patient_tests_by_category = {}
    uncategorized_tests = []
    for test in all_patient_tests:
        info = test_info.get(test)
        if info:
            cat = info['category']
            if cat not in patient_tests_by_category:
                patient_tests_by_category[cat] = []
            patient_tests_by_category[cat].append(test)
        else:
            uncategorized_tests.append(test)

    if uncategorized_tests:
        patient_tests_by_category['Other'] = uncategorized_tests

    filter_key = f"{key_prefix}_heatmap_filter_{selected_patient}"
    if filter_key not in st.session_state:
        saved_tests_json = db.get_user_preference(user_id, selected_patient, f'{key_prefix}_heatmap_selected_tests')
        if not saved_tests_json and key_prefix == 'manage':
            saved_tests_json = db.get_user_preference(user_id, selected_patient, 'heatmap_selected_tests')
        if saved_tests_json:
            try:
                saved_tests = json.loads(saved_tests_json)
                st.session_state[filter_key] = {'groups': {}, 'tests': {t: True for t in saved_tests if t in all_patient_tests}}
            except:
                st.session_state[filter_key] = {'groups': {}, 'tests': {t: True for t in all_patient_tests}}
        else:
            st.session_state[filter_key] = {'groups': {}, 'tests': {t: True for t in all_patient_tests}}

    st.write("**Filter by Test Groups:**")

    selected_tests = []

    with st.expander("📋 Select Test Groups and Tests", expanded=True):
        btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 2])
        with btn_col1:
            if st.button("✅ Select All", key=f"{key_prefix}_select_all_tests"):
                for cat in patient_tests_by_category:
                    st.session_state[filter_key]['groups'][cat] = True
                    for test in patient_tests_by_category[cat]:
                        st.session_state[filter_key]['tests'][test] = True
                st.rerun()
        with btn_col2:
            if st.button("❌ Deselect All", key=f"{key_prefix}_deselect_all_tests"):
                st.session_state[filter_key]['groups'] = {}
                st.session_state[filter_key]['tests'] = {}
                st.rerun()
        with btn_col3:
            if st.button("💾 Save Filter Selection", key=f"{key_prefix}_save_filter_selection"):
                tests_to_save = [t for t, selected in st.session_state[filter_key]['tests'].items() if selected]
                if db.save_user_preference(user_id, selected_patient, f'{key_prefix}_heatmap_selected_tests', json.dumps(tests_to_save)):
                    st.success("Filter selection saved! It will be restored next time.")
                else:
                    st.error("Failed to save filter selection.")

        for category in sorted(patient_tests_by_category.keys()):
            tests_in_cat = sorted(patient_tests_by_category[category], key=lambda x: x.lower())

            all_selected = all(st.session_state[filter_key]['tests'].get(t, False) for t in tests_in_cat)
            any_selected = any(st.session_state[filter_key]['tests'].get(t, False) for t in tests_in_cat)

            group_checked = st.checkbox(
                f"**{category}** ({len(tests_in_cat)} tests)",
                value=all_selected,
                key=f"{key_prefix}_group_{category}"
            )

            prev_group_state = st.session_state[filter_key]['groups'].get(category, all_selected)
            if group_checked != prev_group_state:
                st.session_state[filter_key]['groups'][category] = group_checked
                for test in tests_in_cat:
                    st.session_state[filter_key]['tests'][test] = group_checked
                st.rerun()

            with st.container():
                cols = st.columns([0.05, 0.95])
                with cols[1]:
                    for test in tests_in_cat:
                        test_checked = st.checkbox(
                            test,
                            value=st.session_state[filter_key]['tests'].get(test, False),
                            key=f"{key_prefix}_test_{category}_{test}"
                        )
                        if test_checked:
                            selected_tests.append(test)
                        st.session_state[filter_key]['tests'][test] = test_checked

    if not selected_tests:
        st.warning("No tests selected. Please select at least one test to view the heat map.")
        selected_tests = []

    heatmap_df = edit_df[edit_df['Test Type'].isin(selected_tests)].copy()
    heatmap_df['Date_dt'] = pd.to_datetime(heatmap_df['Date'])

    if date_format == "UK (DD/MM/YYYY)":
        heatmap_df['Date_Formatted'] = heatmap_df['Date_dt'].dt.strftime('%d/%m/%Y')
    else:
        heatmap_df['Date_Formatted'] = heatmap_df['Date_dt'].dt.strftime('%m/%d/%Y')

    if heatmap_df.empty:
        st.warning("No data available for the selected tests.")
    else:
        unique_dates = heatmap_df.sort_values('Date_dt', ascending=False)['Date_Formatted'].unique().tolist()

        unique_tests = heatmap_df['Test Type'].unique().tolist()

        if sort_tests == "Alphabetically":
            unique_tests = sorted(unique_tests, key=lambda x: x.lower())
        else:
            def get_category_sort_key(test):
                info = test_info.get(test)
                cat = info['category'] if info else 'ZZZ_Other'
                return (cat, test.lower())
            unique_tests = sorted(unique_tests, key=get_category_sort_key)

        pivot_data = {}
        reference_ranges = {}
        value_ids = {}
        units_map = {}

        for test in unique_tests:
            pivot_data[test] = {}
            value_ids[test] = {}
            test_rows = heatmap_df[heatmap_df['Test Type'] == test]

            info = test_info.get(test)
            if info and info.get('min') is not None and info.get('max') is not None:
                try:
                    reference_ranges[test] = {'min': float(info['min']), 'max': float(info['max'])}
                    units_map[test] = info.get('unit', '')
                except (ValueError, TypeError):
                    reference_ranges[test] = None
                    units_map[test] = ''
            else:
                std_name, std_match = investigation_standards.standardize_test_name(test, source_text=test)
                if std_match:
                    if patient_gender == 'male':
                        range_min = std_match.get('male_range_min')
                        range_max = std_match.get('male_range_max')
                        unit = std_match.get('male_unit', '')
                    elif patient_gender == 'female':
                        range_min = std_match.get('female_range_min')
                        range_max = std_match.get('female_range_max')
                        unit = std_match.get('female_unit', '')
                    else:
                        range_min = std_match.get('male_range_min')
                        range_max = std_match.get('male_range_max')
                        unit = std_match.get('male_unit', '')

                    if range_min is not None and range_max is not None:
                        try:
                            reference_ranges[test] = {'min': float(range_min), 'max': float(range_max)}
                            units_map[test] = unit
                        except (ValueError, TypeError):
                            reference_ranges[test] = None
                            units_map[test] = ''
                    else:
                        reference_ranges[test] = None
                        units_map[test] = ''
                else:
                    if not test_rows.empty:
                        ref_str = test_rows.iloc[0]['Reference Range']
                        units_map[test] = test_rows.iloc[0]['Unit'] or ''
                        if ref_str and '-' in str(ref_str):
                            try:
                                parts = str(ref_str).replace(' ', '').split('-')
                                if len(parts) >= 2:
                                    low = float(parts[0])
                                    high_part = parts[1].split()[0] if ' ' in parts[1] else parts[1]
                                    high = float(''.join(c for c in high_part if c.isdigit() or c == '.'))
                                    reference_ranges[test] = {'min': low, 'max': high}
                                else:
                                    reference_ranges[test] = None
                            except:
                                reference_ranges[test] = None
                        else:
                            reference_ranges[test] = None
                    else:
                        reference_ranges[test] = None
                        units_map[test] = ''

            for date in unique_dates:
                date_rows = test_rows[test_rows['Date_Formatted'] == date]
                if not date_rows.empty:
                    pivot_data[test][date] = date_rows.iloc[0]['Value']
                    value_ids[test][date] = date_rows.iloc[0]['ID']
                else:
                    pivot_data[test][date] = None
                    value_ids[test][date] = None

        pivot_df = pd.DataFrame(pivot_data).T
        pivot_df.index.name = 'Test Name'

        def get_deviation_color(value, ref_info):
            if value is None or pd.isna(value):
                return ""

            try:
                value = float(value)
            except (ValueError, TypeError):
                return ""

            low, high = None, None

            if isinstance(ref_info, dict) and ref_info:
                low = ref_info.get('min')
                high = ref_info.get('max')

            if low is None or high is None:
                return ""

            try:
                low, high = float(low), float(high)
            except (ValueError, TypeError):
                return ""

            if high <= low:
                return ""

            range_size = high - low

            if low <= value <= high:
                mid = (low + high) / 2
                deviation = abs(value - mid) / (range_size / 2)
                deviation = min(max(deviation, 0), 1)
                r = int(144 - deviation * 110)
                g = int(238 - deviation * 99)
                b = int(144 - deviation * 110)
                return f"background-color: rgb({r}, {g}, {b})"
            elif value < low:
                deviation = (low - value) / range_size
                deviation = min(max(deviation, 0), 2)
                intensity = min(deviation / 2, 1)
                r = int(173 - intensity * 173)
                g = int(216 - intensity * 216)
                b = int(230 - intensity * 91)
                return f"background-color: rgb({r}, {g}, {b})"
            else:
                deviation = (value - high) / range_size
                deviation = min(max(deviation, 0), 2)
                intensity = min(deviation / 2, 1)
                r = int(255 - intensity * 116)
                g = int(204 - intensity * 204)
                b = int(203 - intensity * 203)
                return f"background-color: rgb({r}, {g}, {b})"

        st.markdown("""
        <style>
        .legend-container {
            display: flex;
            align-items: center;
            gap: 20px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 8px;
            margin-bottom: 10px;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .legend-gradient {
            width: 80px;
            height: 20px;
            border-radius: 4px;
            border: 1px solid #ccc;
        }
        .blue-gradient {
            background: linear-gradient(to right, #00008B, #ADD8E6);
        }
        .green-gradient {
            background: linear-gradient(to right, #228B22, #90EE90, #228B22);
        }
        .red-gradient {
            background: linear-gradient(to right, #FFCCCB, #8B0000);
        }
        </style>
        <div class="legend-container">
            <strong>Color Legend:</strong>
            <div class="legend-item">
                <div class="legend-gradient blue-gradient"></div>
                <span>Below Normal</span>
            </div>
            <div class="legend-item">
                <div class="legend-gradient green-gradient"></div>
                <span>Normal Range</span>
            </div>
            <div class="legend-item">
                <div class="legend-gradient red-gradient"></div>
                <span>Above Normal</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if patient_gender:
            st.info(f"Using {patient_gender.title()} reference ranges")
        st.write(f"**{len(unique_tests)} tests × {len(unique_dates)} dates** (Latest date first)")

        stats_data = {}
        for test in unique_tests:
            values = [v for v in pivot_data[test].values() if v is not None and not pd.isna(v)]
            if values:
                try:
                    float_values = [float(v) for v in values]
                    stats_data[test] = {
                        'Count': len(float_values),
                        'Sum': round(sum(float_values), 2),
                        'Average': round(sum(float_values) / len(float_values), 2)
                    }
                except:
                    stats_data[test] = {'Count': 0, 'Sum': 0, 'Average': 0}
            else:
                stats_data[test] = {'Count': 0, 'Sum': 0, 'Average': 0}

        st.markdown("**Statistics Summary:**")
        stats_cols = st.columns(3)
        total_count = sum(s['Count'] for s in stats_data.values())
        total_sum = sum(s['Sum'] for s in stats_data.values())
        overall_avg = total_sum / total_count if total_count > 0 else 0
        with stats_cols[0]:
            st.metric("Total Values", total_count)
        with stats_cols[1]:
            st.metric("Total Sum", f"{total_sum:.2f}")
        with stats_cols[2]:
            st.metric("Overall Average", f"{overall_avg:.2f}")

        range_column = {}
        for test in unique_tests:
            ref = reference_ranges.get(test)
            if ref and isinstance(ref, dict):
                unit = units_map.get(test, '')
                range_column[test] = f"{ref['min']}-{ref['max']} {unit}".strip()
            else:
                range_column[test] = "N/A"

        enhanced_pivot_df = pivot_df.copy()
        enhanced_pivot_df.insert(0, 'Range', [range_column.get(t, 'N/A') for t in enhanced_pivot_df.index])
        enhanced_pivot_df['Avg'] = [stats_data.get(t, {}).get('Average', 0) for t in enhanced_pivot_df.index]
        enhanced_pivot_df['Count'] = [stats_data.get(t, {}).get('Count', 0) for t in enhanced_pivot_df.index]
        enhanced_pivot_df['Sum'] = [stats_data.get(t, {}).get('Sum', 0) for t in enhanced_pivot_df.index]

        summary_row = {'Range': 'SUMMARY'}
        for date_col in unique_dates:
            date_values = []
            for test in unique_tests:
                val = pivot_data.get(test, {}).get(date_col)
                if val is not None and not pd.isna(val):
                    try:
                        date_values.append(float(val))
                    except:
                        pass
            if date_values:
                summary_row[date_col] = round(sum(date_values) / len(date_values), 2)
            else:
                summary_row[date_col] = None
        summary_row['Avg'] = overall_avg
        summary_row['Count'] = total_count
        summary_row['Sum'] = total_sum

        summary_df = pd.DataFrame([summary_row], index=['Average Per Date'])
        enhanced_pivot_df = pd.concat([enhanced_pivot_df, summary_df])

        date_columns = unique_dates.copy()

        def apply_row_style(row):
            test_name = row.name
            if test_name == 'Average Per Date':
                return ['background-color: #e8e8e8; font-weight: bold'] * len(row)
            ref_info = reference_ranges.get(test_name, "")
            styles = []
            for col in row.index:
                if col in date_columns:
                    color = get_deviation_color(row[col], ref_info)
                    styles.append(color if color else "")
                else:
                    styles.append("")
            return styles

        styled_display = enhanced_pivot_df.style.apply(apply_row_style, axis=1)
        styled_display = styled_display.format(precision=2, na_rep="")

        st.markdown("""
        <style>
        /* Auto-fit column widths for st.dataframe */
        div[data-testid="stDataFrame"] > div {
            overflow-x: auto !important;
        }
        div[data-testid="stDataFrame"] table {
            width: auto !important;
            table-layout: auto !important;
        }
        div[data-testid="stDataFrame"] table th,
        div[data-testid="stDataFrame"] table td {
            white-space: nowrap !important;
            padding: 4px 8px !important;
        }
        /* Sticky header for st.dataframe */
        div[data-testid="stDataFrame"] table thead tr th {
            position: sticky !important;
            top: 0 !important;
            background-color: #f0f2f6 !important;
            z-index: 100 !important;
        }
        /* Freeze first column for st.dataframe */
        div[data-testid="stDataFrame"] table tbody tr td:first-child,
        div[data-testid="stDataFrame"] table thead tr th:first-child {
            position: sticky !important;
            left: 0 !important;
            background-color: #f0f2f6 !important;
            z-index: 99 !important;
        }
        div[data-testid="stDataFrame"] table thead tr th:first-child {
            z-index: 101 !important;
        }
        
        /* Auto-fit column widths for st.data_editor */
        div[data-testid="stDataEditor"] > div {
            overflow-x: auto !important;
        }
        div[data-testid="stDataEditor"] table {
            width: auto !important;
            table-layout: auto !important;
        }
        div[data-testid="stDataEditor"] table th,
        div[data-testid="stDataEditor"] table td {
            white-space: nowrap !important;
            padding: 4px 8px !important;
        }
        /* Sticky header for st.data_editor */
        div[data-testid="stDataEditor"] table thead tr th {
            position: sticky !important;
            top: 0 !important;
            background-color: #f0f2f6 !important;
            z-index: 100 !important;
        }
        /* Freeze first column for st.data_editor */
        div[data-testid="stDataEditor"] table tbody tr td:first-child,
        div[data-testid="stDataEditor"] table thead tr th:first-child {
            position: sticky !important;
            left: 0 !important;
            background-color: #f0f2f6 !important;
            z-index: 99 !important;
        }
        div[data-testid="stDataEditor"] table thead tr th:first-child {
            z-index: 101 !important;
        }
        </style>
        """, unsafe_allow_html=True)
        st.caption("Tip: Scroll horizontally to see all dates. Test name column and header row stay fixed when scrolling.")

        with st.expander("📊 Heat Map View (Color-Coded)", expanded=True):
            st.dataframe(styled_display, use_container_width=False, height=min(600, len(unique_tests) * 35 + 80))

        def get_deviation_color_rgb(value, ref_info):
            if value is None or pd.isna(value):
                return None
            try:
                value = float(value)
            except (ValueError, TypeError):
                return None
            low, high = None, None
            if isinstance(ref_info, dict) and ref_info:
                low = ref_info.get('min')
                high = ref_info.get('max')
            if low is None or high is None:
                return None
            try:
                low, high = float(low), float(high)
            except (ValueError, TypeError):
                return None
            if high <= low:
                return None
            range_size = high - low
            if low <= value <= high:
                mid = (low + high) / 2
                deviation = abs(value - mid) / (range_size / 2)
                deviation = min(max(deviation, 0), 1)
                r = int(144 - deviation * 110)
                g = int(238 - deviation * 99)
                b = int(144 - deviation * 110)
                return (r, g, b)
            elif value < low:
                deviation = (low - value) / range_size
                deviation = min(max(deviation, 0), 2)
                intensity = min(deviation / 2, 1)
                r = int(173 - intensity * 173)
                g = int(216 - intensity * 216)
                b = int(230 - intensity * 91)
                return (r, g, b)
            else:
                deviation = (value - high) / range_size
                deviation = min(max(deviation, 0), 2)
                intensity = min(deviation / 2, 1)
                r = int(255 - intensity * 116)
                g = int(204 - intensity * 204)
                b = int(203 - intensity * 203)
                return (r, g, b)

        def generate_excel_heatmap():
            wb = Workbook()
            ws = wb.active
            ws.title = "Heat Map"

            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF", size=11)
            summary_fill = PatternFill(start_color="E8E8E8", end_color="E8E8E8", fill_type="solid")
            summary_font = Font(bold=True, size=11)
            thin_border = Border(
                left=Side(style='thin', color='D9D9D9'),
                right=Side(style='thin', color='D9D9D9'),
                top=Side(style='thin', color='D9D9D9'),
                bottom=Side(style='thin', color='D9D9D9')
            )
            center_align = Alignment(horizontal='center', vertical='center')

            headers = ['Test Name', 'Category', 'Range'] + list(unique_dates) + ['Avg', 'Count', 'Sum']
            for col_idx, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col_idx, value=header)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = center_align
                cell.border = thin_border

            for row_idx, test in enumerate(unique_tests, 2):
                info = test_info.get(test)
                category = info['category'] if info else 'Other'
                range_str = range_column.get(test, 'N/A')

                ws.cell(row=row_idx, column=1, value=test).border = thin_border
                ws.cell(row=row_idx, column=1).font = Font(bold=True, size=10)
                ws.cell(row=row_idx, column=2, value=category).border = thin_border
                ws.cell(row=row_idx, column=3, value=range_str).border = thin_border
                ws.cell(row=row_idx, column=3).alignment = center_align

                ref_info = reference_ranges.get(test)
                for date_idx, date_col in enumerate(unique_dates):
                    col_num = 4 + date_idx
                    val = pivot_data.get(test, {}).get(date_col)
                    cell = ws.cell(row=row_idx, column=col_num)
                    cell.border = thin_border
                    cell.alignment = center_align
                    if val is not None and not pd.isna(val):
                        try:
                            cell.value = round(float(val), 2)
                        except:
                            cell.value = val
                        rgb = get_deviation_color_rgb(val, ref_info)
                        if rgb:
                            hex_color = f"{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
                            cell.fill = PatternFill(start_color=hex_color, end_color=hex_color, fill_type="solid")
                            lum = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2])
                            text_color = "FFFFFF" if lum < 128 else "000000"
                            cell.font = Font(color=text_color, size=10)

                stats = stats_data.get(test, {})
                stats_start = 4 + len(unique_dates)
                for si, sv in enumerate([stats.get('Average', 0), stats.get('Count', 0), stats.get('Sum', 0)]):
                    cell = ws.cell(row=row_idx, column=stats_start + si, value=sv)
                    cell.border = thin_border
                    cell.alignment = center_align

            summary_row = len(unique_tests) + 2
            ws.cell(row=summary_row, column=1, value="Average Per Date").font = summary_font
            ws.cell(row=summary_row, column=1).fill = summary_fill
            ws.cell(row=summary_row, column=1).border = thin_border
            ws.cell(row=summary_row, column=2, value="").fill = summary_fill
            ws.cell(row=summary_row, column=2).border = thin_border
            ws.cell(row=summary_row, column=3, value="SUMMARY").fill = summary_fill
            ws.cell(row=summary_row, column=3).border = thin_border
            ws.cell(row=summary_row, column=3).alignment = center_align

            for date_idx, date_col in enumerate(unique_dates):
                col_num = 4 + date_idx
                date_values = []
                for test in unique_tests:
                    val = pivot_data.get(test, {}).get(date_col)
                    if val is not None and not pd.isna(val):
                        try:
                            date_values.append(float(val))
                        except:
                            pass
                cell = ws.cell(row=summary_row, column=col_num)
                cell.fill = summary_fill
                cell.font = summary_font
                cell.border = thin_border
                cell.alignment = center_align
                if date_values:
                    cell.value = round(sum(date_values) / len(date_values), 2)

            stats_start = 4 + len(unique_dates)
            for si, sv in enumerate([overall_avg, total_count, total_sum]):
                cell = ws.cell(row=summary_row, column=stats_start + si, value=round(sv, 2) if isinstance(sv, float) else sv)
                cell.fill = summary_fill
                cell.font = summary_font
                cell.border = thin_border
                cell.alignment = center_align

            ws.column_dimensions['A'].width = 25
            ws.column_dimensions['B'].width = 18
            ws.column_dimensions['C'].width = 18
            for col_idx in range(4, 4 + len(unique_dates)):
                ws.column_dimensions[get_column_letter(col_idx)].width = 14
            for col_idx in range(4 + len(unique_dates), 4 + len(unique_dates) + 3):
                ws.column_dimensions[get_column_letter(col_idx)].width = 12

            ws.freeze_panes = 'D2'

            legend_ws = wb.create_sheet("Color Legend")
            legend_ws.cell(row=1, column=1, value="Color Legend").font = Font(bold=True, size=14)
            legend_ws.cell(row=3, column=1, value="Below Normal Range").font = Font(bold=True, size=11)
            legend_ws.cell(row=3, column=2).fill = PatternFill(start_color="ADD8E6", end_color="ADD8E6", fill_type="solid")
            legend_ws.cell(row=3, column=3, value="Light Blue → Dark Blue (further below)")
            legend_ws.cell(row=4, column=2).fill = PatternFill(start_color="0000A0", end_color="0000A0", fill_type="solid")
            legend_ws.cell(row=5, column=1, value="Normal Range").font = Font(bold=True, size=11)
            legend_ws.cell(row=5, column=2).fill = PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid")
            legend_ws.cell(row=5, column=3, value="Light Green → Dark Green (closer to boundary)")
            legend_ws.cell(row=6, column=2).fill = PatternFill(start_color="228B22", end_color="228B22", fill_type="solid")
            legend_ws.cell(row=7, column=1, value="Above Normal Range").font = Font(bold=True, size=11)
            legend_ws.cell(row=7, column=2).fill = PatternFill(start_color="FFCCCB", end_color="FFCCCB", fill_type="solid")
            legend_ws.cell(row=7, column=3, value="Light Red → Dark Red (further above)")
            legend_ws.cell(row=8, column=2).fill = PatternFill(start_color="8B0000", end_color="8B0000", fill_type="solid")
            legend_ws.column_dimensions['A'].width = 25
            legend_ws.column_dimensions['B'].width = 10
            legend_ws.column_dimensions['C'].width = 45
            if patient_gender:
                legend_ws.cell(row=10, column=1, value=f"Reference ranges: {patient_gender.title()}").font = Font(italic=True, size=11)

            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            return output

        dl_col1, dl_col2 = st.columns([1, 3])
        with dl_col1:
            excel_data = generate_excel_heatmap()
            safe_name = selected_patient.replace(' ', '_')
            st.download_button(
                label="📥 Download as Excel",
                data=excel_data,
                file_name=f"heatmap_{safe_name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"{key_prefix}_download_heatmap_excel"
            )

        if editable:
            with st.expander("✏️ Editable Table", expanded=True):
                st.caption("Edit values directly in the table below. Click 'Save All Changes' to persist your edits. Stats columns (Avg, Count, Sum) are read-only.")

                editable_df = pivot_df.copy()
                editable_df.insert(0, 'Range', [range_column.get(t, 'N/A') for t in editable_df.index])
                editable_df['Avg'] = [stats_data.get(t, {}).get('Average', 0) for t in editable_df.index]
                editable_df['Count'] = [stats_data.get(t, {}).get('Count', 0) for t in editable_df.index]
                editable_df['Sum'] = [stats_data.get(t, {}).get('Sum', 0) for t in editable_df.index]
                editable_df = editable_df.reset_index()
                editable_df = editable_df.rename(columns={'index': 'Test Name'})

                column_config = {
                    'Test Name': st.column_config.TextColumn('Test Name', disabled=True),
                    'Range': st.column_config.TextColumn('Range', disabled=True),
                    'Avg': st.column_config.NumberColumn('Avg', disabled=True, format="%.2f"),
                    'Count': st.column_config.NumberColumn('Count', disabled=True),
                    'Sum': st.column_config.NumberColumn('Sum', disabled=True, format="%.2f")
                }

                edited_df = st.data_editor(
                    editable_df,
                    use_container_width=False,
                    hide_index=True,
                    num_rows="fixed",
                    column_config=column_config,
                    key=f"{key_prefix}_heatmap_editor"
                )

            col_save1, col_save2 = st.columns([1, 3])
            with col_save1:
                save_btn = st.button("💾 Save All Changes", key=f"{key_prefix}_save_heatmap_changes", type="primary")
            with col_save2:
                if st.button("🔄 Refresh Data", key=f"{key_prefix}_refresh_heatmap"):
                    editor_key = f"{key_prefix}_heatmap_editor"
                    if editor_key in st.session_state:
                        del st.session_state[editor_key]
                    st.rerun()

            if save_btn:
                changes_made = 0
                errors = 0
                new_entries = 0
                deleted_entries = 0
                changes_list = []

                with st.expander("🔍 Debug: Finding Differences", expanded=True):
                    st.write("**Scanning for differences between Editor and DB:**")
                    diff_count = 0
                    for idx, row in edited_df.iterrows():
                        test_name = row['Test Name']
                        for date_col in unique_dates:
                            if date_col in row.index:
                                edit_val = row[date_col]
                                db_val = pivot_data.get(test_name, {}).get(date_col)
                                edit_empty = pd.isna(edit_val) or (isinstance(edit_val, str) and str(edit_val).strip() == '')
                                db_empty = db_val is None or pd.isna(db_val)
                                if not edit_empty and not db_empty:
                                    try:
                                        if abs(float(edit_val) - float(db_val)) > 0.001:
                                            st.success(f"✅ DIFF FOUND: **{test_name}** @ {date_col}: Editor={edit_val}, DB={db_val}")
                                            diff_count += 1
                                    except:
                                        pass
                    if diff_count == 0:
                        st.warning("No differences found between Editor values and Database values")

                save_attempts = []
                for idx, row in edited_df.iterrows():
                    test_name = row['Test Name']
                    for date_col in unique_dates:
                        if date_col not in row.index:
                            continue

                        new_value = row[date_col]
                        original_value = pivot_data.get(test_name, {}).get(date_col)
                        result_id = value_ids.get(test_name, {}).get(date_col)

                        new_is_empty = pd.isna(new_value) or (isinstance(new_value, str) and str(new_value).strip() == '')
                        orig_is_empty = original_value is None or pd.isna(original_value)

                        if new_is_empty and orig_is_empty:
                            continue

                        value_changed = False
                        if new_is_empty != orig_is_empty:
                            value_changed = True
                        elif not new_is_empty and not orig_is_empty:
                            try:
                                new_float = float(new_value)
                                orig_float = float(original_value)
                                if abs(new_float - orig_float) > 0.001:
                                    value_changed = True
                                    changes_list.append(f"{test_name} ({date_col}): {orig_float} → {new_float}")
                                    save_attempts.append(f"{test_name}@{date_col}: new={new_float}, old={orig_float}, id={result_id}")
                            except (ValueError, TypeError):
                                if str(new_value) != str(original_value):
                                    value_changed = True
                                    changes_list.append(f"{test_name} ({date_col}): {original_value} → {new_value}")

                        if not value_changed:
                            continue

                        try:
                            try:
                                if date_format == "UK (DD/MM/YYYY)":
                                    parsed_date = pd.to_datetime(date_col, format='%d/%m/%Y').date()
                                else:
                                    parsed_date = pd.to_datetime(date_col, format='%m/%d/%Y').date()
                            except:
                                try:
                                    parsed_date = pd.to_datetime(date_col).date()
                                except Exception as date_err:
                                    st.error(f"Date parse error for {date_col}: {date_err}")
                                    errors += 1
                                    continue

                            unit = units_map.get(test_name, '')
                            ref_info = reference_ranges.get(test_name, '')
                            ref_str = f"{ref_info['min']}-{ref_info['max']}" if isinstance(ref_info, dict) else str(ref_info)

                            if not new_is_empty:
                                try:
                                    numeric_value = float(new_value)
                                except (ValueError, TypeError):
                                    errors += 1
                                    st.error(f"Invalid number '{new_value}' for {test_name}")
                                    continue

                            st.write(f"🔧 Saving: {test_name}, id={result_id}, value={numeric_value}, date={parsed_date}")

                            if result_id is not None:
                                if new_is_empty:
                                    if db.delete_test_result(result_id):
                                        deleted_entries += 1
                                        st.success(f"Deleted {test_name}")
                                else:
                                    update_result = db.update_test_result(
                                        result_id=result_id,
                                        test_type=test_name,
                                        value=numeric_value,
                                        unit=unit,
                                        test_date=parsed_date,
                                        reference_range=ref_str
                                    )
                                    if update_result:
                                        changes_made += 1
                                        st.success(f"Updated {test_name} to {numeric_value}")
                                    else:
                                        st.error(f"Update failed for {test_name} (id={result_id}) - returned False")
                            else:
                                if not new_is_empty:
                                    patient_id = db.get_patient_id(selected_patient, user_id)
                                    if not patient_id:
                                        st.error(f"Could not find patient '{selected_patient}' - cannot add new test result")
                                        errors += 1
                                    elif db.add_test_result(
                                        patient_id=patient_id,
                                        test_date=parsed_date,
                                        test_type=test_name,
                                        test_value=numeric_value,
                                        unit=unit,
                                        reference_range=ref_str,
                                        user_id=user_id
                                    ):
                                        new_entries += 1
                                        st.success(f"Added {test_name}")
                                    else:
                                        st.error(f"Failed to add {test_name}")
                                        errors += 1
                        except Exception as e:
                            errors += 1
                            st.error(f"Error saving {test_name}: {e}")

                total_changes = changes_made + new_entries + deleted_entries
                if total_changes > 0:
                    msg_parts = []
                    if changes_made > 0:
                        msg_parts.append(f"{changes_made} updated")
                    if new_entries > 0:
                        msg_parts.append(f"{new_entries} added")
                    if deleted_entries > 0:
                        msg_parts.append(f"{deleted_entries} deleted")
                    st.success(f"✅ {total_changes} change(s) saved: {', '.join(msg_parts)}")
                    if changes_list and len(changes_list) <= 10:
                        with st.expander("View changes"):
                            for change in changes_list:
                                st.write(f"• {change}")
                    elif changes_list:
                        with st.expander(f"View first 10 of {len(changes_list)} changes"):
                            for change in changes_list[:10]:
                                st.write(f"• {change}")
                    editor_key = f"{key_prefix}_heatmap_editor"
                    if editor_key in st.session_state:
                        del st.session_state[editor_key]
                    st.rerun()
                elif errors > 0:
                    st.error(f"❌ {errors} errors occurred while saving")
                else:
                    st.info("No changes detected. Edit values in the table above and click Save.")
                    if save_attempts:
                        st.warning(f"Debug: {len(save_attempts)} changes were detected but not saved:")
                        for attempt in save_attempts[:5]:
                            st.write(f"• {attempt}")
                    if changes_list:
                        st.warning(f"Debug: changes_list has {len(changes_list)} items but total_changes={total_changes}")
