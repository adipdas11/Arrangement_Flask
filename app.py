from flask import Flask, render_template, request, Markup, make_response
import pandas as pd
from datetime import datetime
import webview


app = Flask(__name__, template_folder='Renders')
webview.create_window('Arrangement Application', app)

excel_file = 'Data\TeacherTimeTable.xlsx'

@app.route('/')
def home():
    excel_data = pd.ExcelFile(excel_file)
    teacher_names = excel_data.sheet_names
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('home.html', teachers=teacher_names, today=today)

def create_dropdown(free_teachers, present_teachers_free_periods):
    """Generates HTML for a dropdown with given teacher options."""
    options_html = '<option value="">Select Teacher</option>'
    for teacher in free_teachers:
        free_count = len(present_teachers_free_periods[teacher])
        options_html += f'<option value="{teacher}" data-free-count="{free_count}" data-initial-free-count="{free_count}">{teacher} - {free_count}</option>'
    dropdown_html = f'<select class="custom-select" onchange="updateFreePeriodCount(this)">{options_html}</select>'
    return dropdown_html


@app.route('/arrangement', methods=['POST'])
def arrangement():
    selected_teachers = request.form.getlist('absent_teacher')
    selected_date = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
    weekday = datetime.strptime(selected_date, '%Y-%m-%d').strftime('%A')
    excel_data = pd.ExcelFile(excel_file)
    
    # Determine present teachers
    all_teacher_names = excel_data.sheet_names
    present_teachers = [teacher for teacher in all_teacher_names if teacher not in selected_teachers]

    # Calculate free periods for present teachers
    present_teachers_free_periods = {teacher: [] for teacher in present_teachers}
    for teacher in present_teachers:
        df = excel_data.parse(teacher).fillna('')
        day_df = df[df['DAYS'] == weekday]
        if not day_df.empty:
            for period in ['1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th']:
                if day_df.iloc[0][period] == '':
                    present_teachers_free_periods[teacher].append(period)

    # Generate the combined DataFrame for absent teachers' schedules
    combined_df = pd.DataFrame()
    for teacher in selected_teachers:
        df = excel_data.parse(teacher).fillna('')
        day_df = df[df['DAYS'] == weekday].copy()
        absence_type = request.form.get(f'absence_{teacher}')

        # Determine periods to block based on absence type
        if absence_type == 'first_half':
            periods_to_block = ['5th', '6th', '7th', '8th']  # Block second half
            
        elif absence_type == 'second_half':
            periods_to_block = ['1st', '2nd', '3rd', '4th']  # Block first half
            
        else:
            periods_to_block = []  # Do not block any periods

        # Block the appropriate periods
        for period in periods_to_block:
            day_df[period] = 'Blocked'

        # Set the teacher's name and weekday
        day_df['Teacher'] = teacher
        day_df['DAYS'] = weekday
        combined_df = pd.concat([combined_df, day_df], ignore_index=True)

        # Create a row for dropdowns
        dropdown_row = {col: '' for col in combined_df.columns}
        for period in ['1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th']:
            cell_value = day_df.iloc[0][period]
            if cell_value not in ['Blocked', '']:
                free_teachers = [t for t, free_periods in present_teachers_free_periods.items() if period in free_periods]
                dropdown_row[period] = create_dropdown(free_teachers, present_teachers_free_periods) if free_teachers else ''
            else:
                dropdown_row[period] = 'Blocked' if cell_value == 'Blocked' else ''

        combined_df = pd.concat([combined_df, pd.DataFrame([dropdown_row])], ignore_index=True)

    # Reorder columns and convert to HTML
    column_order = ['Teacher', 'DAYS', '1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th']
    combined_df = combined_df[column_order]
    table_html = combined_df.to_html(classes='table table-striped', border=0, index=False, escape=False)

    # Generate the table for present teachers and their free period counts
    present_teachers_table = pd.DataFrame(
        [(teacher, len(periods)) for teacher, periods in present_teachers_free_periods.items()],
        columns=['Teacher', 'Free Periods']
    )
    present_teachers_table_html = present_teachers_table.to_html(classes='table table-striped', border=0, index=False)

    # ... [Rest of the code to generate the main arrangement table]

    return render_template('arrangement.html', table=Markup(table_html), present_teachers_table=Markup(present_teachers_table_html))

@app.route('/generate_csv', methods=['POST'])
def generate_csv():
    data = request.get_json().get('tableData')
    # Convert the JSON data to DataFrame
    df = pd.DataFrame(data[1:], columns=data[0])  # The first row is the header

    # Generate CSV from DataFrame
    csv_str = df.to_csv(index=False)
    
    # Create the response
    response = make_response(csv_str)
    response.headers['Content-Disposition'] = f'attachment; filename=arrangement_{datetime.now().strftime("%Y-%m-%d")}.csv'
    response.headers['Content-Type'] = 'text/csv'

    return response

@app.route('/timetable', methods=['GET', 'POST'])
def timetable():
    excel_data = pd.ExcelFile(excel_file)
    teacher_names = excel_data.sheet_names
    selected_teacher = request.form.get('teacher') if request.method == 'POST' else None

    table_html = ""
    if selected_teacher:
        timetable_data = excel_data.parse(selected_teacher).fillna('')
        table_html = timetable_data.to_html(classes='table table-striped', border=0, index=False)

    return render_template('table.html', teachers=teacher_names, table=Markup(table_html), selected_teacher=selected_teacher)



if __name__ == '__main__':
    # app.run(debug=True)
    webview.start()

