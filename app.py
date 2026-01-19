import streamlit as st
import pandas as pd
from datetime import datetime, date

# Page config
st.set_page_config(page_title="Attendance Tracker", page_icon="📋")

# Initialize session state
if 'students' not in st.session_state:
    st.session_state.students = []

if 'attendance' not in st.session_state:
    st.session_state.attendance = []

# Title
st.title("📋 Attendance Tracker")

# Sidebar menu
menu = st.sidebar.selectbox("Menu", [
    "Dashboard",
    "Add Student", 
    "Mark Attendance",
    "View Records"
])

# ============ DASHBOARD ============
if menu == "Dashboard":
    st.header("🏠 Dashboard")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Students", len(st.session_state.students))
    with col2:
        st.metric("Total Records", len(st.session_state.attendance))
    
    st.subheader("Today's Date")
    st.write(date.today().strftime("%B %d, %Y"))

# ============ ADD STUDENT ============
elif menu == "Add Student":
    st.header("➕ Add New Student")
    
    with st.form("student_form"):
        student_id = st.text_input("Student ID")
        student_name = st.text_input("Student Name")
        department = st.selectbox("Department", [
            "Computer Science",
            "Engineering",
            "Business",
            "Arts"
        ])
        
        submit = st.form_submit_button("Add Student")
        
        if submit:
            if student_id and student_name:
                # Check if ID exists
                existing_ids = [s['id'] for s in st.session_state.students]
                if student_id in existing_ids:
                    st.error("❌ Student ID already exists!")
                else:
                    st.session_state.students.append({
                        'id': student_id,
                        'name': student_name,
                        'department': department
                    })
                    st.success(f"✅ Added {student_name}!")
            else:
                st.warning("Please fill all fields!")
    
    # Show students list
    st.subheader("📋 Student List")
    if st.session_state.students:
        df = pd.DataFrame(st.session_state.students)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No students added yet.")

# ============ MARK ATTENDANCE ============
elif menu == "Mark Attendance":
    st.header("✅ Mark Attendance")
    
    if not st.session_state.students:
        st.warning("⚠️ Please add students first!")
    else:
        st.write(f"**Date:** {date.today().strftime('%Y-%m-%d')}")
        
        with st.form("attendance_form"):
            # Create selection
            student_options = {s['id']: f"{s['id']} - {s['name']}" for s in st.session_state.students}
            
            selected_id = st.selectbox(
                "Select Student",
                options=list(student_options.keys()),
                format_func=lambda x: student_options[x]
            )
            
            status = st.radio("Status", ["Present", "Absent", "Late"], horizontal=True)
            
            submit = st.form_submit_button("Mark Attendance")
            
            if submit:
                # Find student name
                student_name = next(s['name'] for s in st.session_state.students if s['id'] == selected_id)
                
                st.session_state.attendance.append({
                    'id': selected_id,
                    'name': student_name,
                    'date': date.today().strftime('%Y-%m-%d'),
                    'time': datetime.now().strftime('%H:%M:%S'),
                    'status': status
                })
                st.success(f"✅ Marked {student_name} as {status}")

# ============ VIEW RECORDS ============
elif menu == "View Records":
    st.header("📊 Attendance Records")
    
    if st.session_state.attendance:
        df = pd.DataFrame(st.session_state.attendance)
        
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            filter_status = st.selectbox("Filter by Status", ["All", "Present", "Absent", "Late"])
        with col2:
            if st.session_state.students:
                filter_student = st.selectbox("Filter by Student", ["All"] + [s['id'] for s in st.session_state.students])
        
        # Apply filters
        filtered_df = df.copy()
        if filter_status != "All":
            filtered_df = filtered_df[filtered_df['status'] == filter_status]
        if filter_student != "All":
            filtered_df = filtered_df[filtered_df['id'] == filter_student]
        
        st.dataframe(filtered_df, use_container_width=True)
        
        # Statistics
        st.subheader("📈 Statistics")
        col1, col2, col3 = st.columns(3)
        with col1:
            present = len(df[df['status'] == 'Present'])
            st.metric("Present", present)
        with col2:
            absent = len(df[df['status'] == 'Absent'])
            st.metric("Absent", absent)
        with col3:
            late = len(df[df['status'] == 'Late'])
            st.metric("Late", late)
    else:
        st.info("No attendance records yet.")

# Footer
st.sidebar.markdown("---")
st.sidebar.write("📋 Attendance Tracker v1.0")
print("Streamlit app is running")
