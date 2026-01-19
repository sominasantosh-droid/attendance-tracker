import streamlit as st
import pandas as pd
import psycopg2
from psycopg2 import sql
from datetime import datetime, date
from contextlib import contextmanager

# ============ PAGE CONFIGURATION ============
st.set_page_config(
    page_title="Attendance Tracker",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============ DATABASE CONNECTION ============

def get_connection():
    """Create database connection using Streamlit secrets"""
    try:
        conn = psycopg2.connect(
            host=st.secrets["postgres"]["host"],
            database=st.secrets["postgres"]["database"],
            user=st.secrets["postgres"]["user"],
            password=st.secrets["postgres"]["password"],
            port=st.secrets["postgres"]["port"]
        )
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

@contextmanager
def get_db_cursor():
    """Context manager for database operations"""
    conn = get_connection()
    if conn is None:
        yield None
    else:
        try:
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            st.error(f"Database error: {e}")
        finally:
            cursor.close()
            conn.close()

# ============ DATABASE FUNCTIONS ============

def init_database():
    """Initialize database tables if they don't exist"""
    with get_db_cursor() as cursor:
        if cursor:
            # Create students table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    department TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Create attendance table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    id SERIAL PRIMARY KEY,
                    student_id TEXT REFERENCES students(id) ON DELETE CASCADE,
                    student_name TEXT NOT NULL,
                    date DATE NOT NULL,
                    time TIME NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

def load_students():
    """Load all students from database"""
    with get_db_cursor() as cursor:
        if cursor:
            cursor.execute("SELECT id, name, department FROM students ORDER BY name")
            columns = ['ID', 'Name', 'Department']
            data = cursor.fetchall()
            return pd.DataFrame(data, columns=columns)
    return pd.DataFrame(columns=['ID', 'Name', 'Department'])

def add_student(student_id, name, department):
    """Add new student to database"""
    with get_db_cursor() as cursor:
        if cursor:
            try:
                cursor.execute(
                    "INSERT INTO students (id, name, department) VALUES (%s, %s, %s)",
                    (student_id, name, department)
                )
                return True, "Student added successfully!"
            except psycopg2.errors.UniqueViolation:
                return False, "Student ID already exists!"
            except Exception as e:
                return False, f"Error: {e}"
    return False, "Database connection failed"

def delete_student(student_id):
    """Delete student from database"""
    with get_db_cursor() as cursor:
        if cursor:
            cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))
            return True
    return False

def load_attendance(date_filter=None, student_filter=None, status_filter=None):
    """Load attendance records with optional filters"""
    with get_db_cursor() as cursor:
        if cursor:
            query = """
                SELECT student_id, student_name, date, time, status 
                FROM attendance 
                WHERE 1=1
            """
            params = []
            
            if date_filter:
                query += " AND date = %s"
                params.append(date_filter)
            
            if student_filter and student_filter != "All":
                query += " AND student_id = %s"
                params.append(student_filter)
            
            if status_filter and status_filter != "All":
                query += " AND status = %s"
                params.append(status_filter)
            
            query += " ORDER BY date DESC, time DESC"
            
            cursor.execute(query, params)
            columns = ['ID', 'Name', 'Date', 'Time', 'Status']
            data = cursor.fetchall()
            return pd.DataFrame(data, columns=columns)
    return pd.DataFrame(columns=['ID', 'Name', 'Date', 'Time', 'Status'])

def save_attendance(student_id, student_name, status):
    """Save attendance record to database"""
    with get_db_cursor() as cursor:
        if cursor:
            current_date = date.today()
            current_time = datetime.now().time()
            
            cursor.execute(
                """INSERT INTO attendance (student_id, student_name, date, time, status) 
                   VALUES (%s, %s, %s, %s, %s)""",
                (student_id, student_name, current_date, current_time, status)
            )
            return True
    return False

def get_today_attendance():
    """Get today's attendance records"""
    with get_db_cursor() as cursor:
        if cursor:
            cursor.execute(
                """SELECT student_id, student_name, date, time, status 
                   FROM attendance WHERE date = %s ORDER BY time DESC""",
                (date.today(),)
            )
            columns = ['ID', 'Name', 'Date', 'Time', 'Status']
            data = cursor.fetchall()
            return pd.DataFrame(data, columns=columns)
    return pd.DataFrame(columns=['ID', 'Name', 'Date', 'Time', 'Status'])

def get_attendance_stats():
    """Get attendance statistics"""
    with get_db_cursor() as cursor:
        if cursor:
            # Total records
            cursor.execute("SELECT COUNT(*) FROM attendance")
            total = cursor.fetchone()[0]
            
            # Status counts
            cursor.execute("""
                SELECT status, COUNT(*) 
                FROM attendance 
                GROUP BY status
            """)
            status_counts = dict(cursor.fetchall())
            
            # Today's counts
            cursor.execute("""
                SELECT status, COUNT(*) 
                FROM attendance 
                WHERE date = %s 
                GROUP BY status
            """, (date.today(),))
            today_counts = dict(cursor.fetchall())
            
            return {
                'total': total,
                'present': status_counts.get('Present', 0),
                'absent': status_counts.get('Absent', 0),
                'late': status_counts.get('Late', 0),
                'today_present': today_counts.get('Present', 0),
                'today_absent': today_counts.get('Absent', 0),
                'today_late': today_counts.get('Late', 0)
            }
    return None

def get_student_report(student_id):
    """Get individual student attendance report"""
    with get_db_cursor() as cursor:
        if cursor:
            cursor.execute("""
                SELECT status, COUNT(*) 
                FROM attendance 
                WHERE student_id = %s 
                GROUP BY status
            """, (student_id,))
            return dict(cursor.fetchall())
    return {}

# ============ INITIALIZE DATABASE ============
init_database()

# ============ CUSTOM CSS ============
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border-radius: 5px;
        border-left: 5px solid #28a745;
    }
    .warning-box {
        padding: 1rem;
        background-color: #fff3cd;
        border-radius: 5px;
        border-left: 5px solid #ffc107;
    }
    .stButton > button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ============ MAIN APP ============

st.markdown('<h1 class="main-header">📋 Attendance Tracker</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: gray;">Powered by PostgreSQL Database</p>', unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("📌 Navigation")
page = st.sidebar.radio("Go to", [
    "🏠 Dashboard",
    "👤 Add Student",
    "✅ Mark Attendance",
    "📊 View Records",
    "📈 Reports"
])

# ============ DASHBOARD PAGE ============
if page == "🏠 Dashboard":
    st.header("🏠 Dashboard")
    
    students_df = load_students()
    stats = get_attendance_stats()
    today_df = get_today_attendance()
    
    # Metrics row
    st.subheader("📊 Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👥 Total Students", len(students_df))
    
    with col2:
        st.metric("📝 Total Records", stats['total'] if stats else 0)
    
    with col3:
        st.metric("✅ Present Today", stats['today_present'] if stats else 0)
    
    with col4:
        st.metric("❌ Absent Today", stats['today_absent'] if stats else 0)
    
    st.divider()
    
    # Today's attendance
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"📅 Today's Attendance ({date.today().strftime('%B %d, %Y')})")
        if not today_df.empty:
            st.dataframe(today_df, use_container_width=True, hide_index=True)
        else:
            st.info("📭 No attendance marked for today yet.")
    
    with col2:
        st.subheader("📈 Quick Stats")
        if stats and stats['total'] > 0:
            attendance_rate = (stats['present'] / stats['total']) * 100
            st.metric("Overall Attendance Rate", f"{attendance_rate:.1f}%")
            
            st.write("**All Time:**")
            st.write(f"✅ Present: {stats['present']}")
            st.write(f"❌ Absent: {stats['absent']}")
            st.write(f"⏰ Late: {stats['late']}")
        else:
            st.info("No data available")

# ============ ADD STUDENT PAGE ============
elif page == "👤 Add Student":
    st.header("👤 Add New Student")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📝 Student Registration")
        
        with st.form("add_student_form", clear_on_submit=True):
            student_id = st.text_input(
                "Student ID *", 
                placeholder="e.g., STU001",
                help="Unique identifier for the student"
            )
            
            name = st.text_input(
                "Full Name *", 
                placeholder="Enter student's full name"
            )
            
            department = st.selectbox(
                "Department *",
                options=[
                    "Computer Science",
                    "Electrical Engineering",
                    "Mechanical Engineering",
                    "Civil Engineering",
                    "Business Administration",
                    "Arts & Humanities",
                    "Medical Sciences",
                    "Other"
                ]
            )
            
            submitted = st.form_submit_button("➕ Add Student", type="primary")
            
            if submitted:
                if student_id and name:
                    success, message = add_student(student_id.strip(), name.strip(), department)
                    if success:
                        st.success(f"✅ {message}")
                        st.balloons()
                    else:
                        st.error(f"❌ {message}")
                else:
                    st.warning("⚠️ Please fill in all required fields!")
    
    with col2:
        st.subheader("📋 Registered Students")
        students_df = load_students()
        
        if not students_df.empty:
            st.dataframe(students_df, use_container_width=True, hide_index=True)
            
            st.divider()
            
            # Delete student section
            st.subheader("🗑️ Remove Student")
            student_to_delete = st.selectbox(
                "Select student to remove",
                options=students_df['ID'].tolist(),
                format_func=lambda x: f"{x} - {students_df[students_df['ID']==x]['Name'].values[0]}"
            )
            
            col_del1, col_del2 = st.columns(2)
            with col_del1:
                if st.button("🗑️ Delete Student", type="secondary", use_container_width=True):
                    if delete_student(student_to_delete):
                        st.success("✅ Student deleted!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to delete student")
        else:
            st.info("📭 No students registered yet.")

# ============ MARK ATTENDANCE PAGE ============
elif page == "✅ Mark Attendance":
    st.header("✅ Mark Attendance")
    
    students_df = load_students()
    
    if students_df.empty:
        st.warning("⚠️ No students registered! Please add students first.")
        st.page_link("👤 Add Student", label="Go to Add Student", icon="👤")
    else:
        st.info(f"📅 **Date:** {date.today().strftime('%A, %B %d, %Y')} | ⏰ **Time:** {datetime.now().strftime('%H:%M:%S')}")
        
        tab1, tab2 = st.tabs(["📝 Individual Attendance", "📋 Bulk Attendance"])
        
        # Individual attendance tab
        with tab1:
            st.subheader("Mark Individual Attendance")
            
            with st.form("individual_attendance"):
                col1, col2 = st.columns(2)
                
                with col1:
                    selected_student = st.selectbox(
                        "Select Student",
                        options=students_df['ID'].tolist(),
                        format_func=lambda x: f"{x} - {students_df[students_df['ID']==x]['Name'].values[0]}"
                    )
                
                with col2:
                    status = st.radio(
                        "Attendance Status",
                        options=["Present", "Absent", "Late"],
                        horizontal=True
                    )
                
                if st.form_submit_button("✅ Mark Attendance", type="primary", use_container_width=True):
                    student_name = students_df[students_df['ID'] == selected_student]['Name'].values[0]
                    if save_attendance(selected_student, student_name, status):
                        st.success(f"✅ Marked **{student_name}** as **{status}**")
                    else:
                        st.error("❌ Failed to save attendance")
        
        # Bulk attendance tab
        with tab2:
            st.subheader("Mark Attendance for All Students")
            
            with st.form("bulk_attendance"):
                attendance_records = {}
                
                # Create columns for better layout
                for idx, (_, student) in enumerate(students_df.iterrows()):
                    col1, col2 = st.columns([3, 2])
                    
                    with col1:
                        st.write(f"**{student['ID']}** - {student['Name']}")
                        st.caption(f"Department: {student['Department']}")
                    
                    with col2:
                        attendance_records[student['ID']] = st.selectbox(
                            "Status",
                            options=["Present", "Absent", "Late"],
                            key=f"bulk_{student['ID']}",
                            label_visibility="collapsed"
                        )
                    
                    if idx < len(students_df) - 1:
                        st.divider()
                
                if st.form_submit_button("✅ Submit All Attendance", type="primary", use_container_width=True):
                    success_count = 0
                    for student_id, status in attendance_records.items():
                        student_name = students_df[students_df['ID'] == student_id]['Name'].values[0]
                        if save_attendance(student_id, student_name, status):
                            success_count += 1
                    
                    if success_count == len(attendance_records):
                        st.success(f"✅ Successfully marked attendance for all {success_count} students!")
                        st.balloons()
                    else:
                        st.warning(f"⚠️ Marked {success_count}/{len(attendance_records)} records")

# ============ VIEW RECORDS PAGE ============
elif page == "📊 View Records":
    st.header("📊 Attendance Records")
    
    students_df = load_students()
    
    # Filters
    st.subheader("🔍 Filters")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        date_filter = st.date_input("Filter by Date", value=None)
    
    with col2:
        student_options = ["All"] + students_df['ID'].tolist() if not students_df.empty else ["All"]
        student_filter = st.selectbox("Filter by Student", options=student_options)
    
    with col3:
        status_filter = st.selectbox("Filter by Status", options=["All", "Present", "Absent", "Late"])
    
    with col4:
        st.write("")
        st.write("")
        refresh = st.button("🔄 Refresh", use_container_width=True)
    
    st.divider()
    
    # Load and display records
    attendance_df = load_attendance(
        date_filter=date_filter if date_filter else None,
        student_filter=student_filter,
        status_filter=status_filter
    )
    
    if not attendance_df.empty:
        st.subheader(f"📋 Records ({len(attendance_df)} entries)")
        
        # Display dataframe
        st.dataframe(
            attendance_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                "Time": st.column_config.TimeColumn("Time", format="HH:mm:ss"),
                "Status": st.column_config.TextColumn("Status")
            }
        )
        
        # Download button
        csv = attendance_df.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name=f"attendance_records_{date.today()}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("📭 No records found matching the filters.")

# ============ REPORTS PAGE ============
elif page == "📈 Reports":
    st.header("📈 Attendance Reports")
    
    students_df = load_students()
    stats = get_attendance_stats()
    
    if not stats or stats['total'] == 0:
        st.info("📭 No attendance data available for reports.")
    else:
        # Overall statistics
        st.subheader("📊 Overall Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📝 Total Records", stats['total'])
        
        with col2:
            rate = (stats['present'] / stats['total'] * 100) if stats['total'] > 0 else 0
            st.metric("📈 Attendance Rate", f"{rate:.1f}%")
        
        with col3:
            st.metric("✅ Total Present", stats['present'])
        
        with col4:
            st.metric("❌ Total Absent", stats['absent'])
        
        st.divider()
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Status Distribution")
            chart_data = pd.DataFrame({
                'Status': ['Present', 'Absent', 'Late'],
                'Count': [stats['present'], stats['absent'], stats['late']]
            })
            st.bar_chart(chart_data.set_index('Status'))
        
        with col2:
            st.subheader("📅 Today's Summary")
            today_data = pd.DataFrame({
                'Status': ['Present', 'Absent', 'Late'],
                'Count': [stats['today_present'], stats['today_absent'], stats['today_late']]
            })
            st.bar_chart(today_data.set_index('Status'))
        
        st.divider()
        
        # Individual student report
        st.subheader("👤 Individual Student Report")
        
        if not students_df.empty:
            selected_student = st.selectbox(
                "Select Student",
                options=students_df['ID'].tolist(),
                format_func=lambda x: f"{x} - {students_df[students_df['ID']==x]['Name'].values[0]}"
            )
            
            student_stats = get_student_report(selected_student)
            student_name = students_df[students_df['ID'] == selected_student]['Name'].values[0]
            
            if student_stats:
                st.write(f"**Student:** {student_name}")
                
                col1, col2, col3, col4 = st.columns(4)
                
                total = sum(student_stats.values())
                present = student_stats.get('Present', 0)
                absent = student_stats.get('Absent', 0)
                late = student_stats.get('Late', 0)
                
                with col1:
                    st.metric("Total Days", total)
                
                with col2:
                    st.metric("Present", present)
                
                with col3:
                    st.metric("Absent", absent)
                
                with col4:
                    rate = (present / total * 100) if total > 0 else 0
                    st.metric("Attendance %", f"{rate:.1f}%")
            else:
                st.info(f"📭 No attendance records for {student_name}")
        else:
            st.warning("⚠️ No students registered.")

# ============ SIDEBAR FOOTER ============
st.sidebar.divider()
st.sidebar.success("✅ Connected to PostgreSQL")
st.sidebar.caption(f"📅 {date.today().strftime('%B %d, %Y')}")
st.sidebar.caption("Version 1.0")
