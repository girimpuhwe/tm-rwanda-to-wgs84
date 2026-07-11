import streamlit as st
import pandas as pd
import math
import io
import time

# ==============================================================================
# SECTION 1: TM RWANDA PARAMETERS (WGS84) & CACHED MATH BACKEND
# ==============================================================================
a = 6378137.0
f = 1 / 298.257223563
e2 = 2 * f - f**2
ep2 = e2 / (1 - e2)

E0 = 500000.0
N0 = 5000000.0
k0 = 0.9996
lam0 = math.radians(30.0)

@st.cache_data(show_spinner=False)
def tm_to_geographic(E, N):
    x = E - E0
    y = N - N0
    M = y / k0
    mu = M / (a * (1 - e2/4 - 3*e2**2/64 - 5*e2**3/256))
    e1 = (1 - math.sqrt(1-e2)) / (1 + math.sqrt(1-e2))
    phi1 = (
        mu
        + (3*e1/2 - 27*e1**3/32) * math.sin(2*mu)
        + (21*e1**2/16 - 55*e1**4/32) * math.sin(4*mu)
        + (151*e1**3/96) * math.sin(6*mu)
        + (1097*e1**4/512) * math.sin(8*mu)
    )
    N1 = a / math.sqrt(1 - e2 * math.sin(phi1)**2)
    R1 = (a*(1-e2) / (1-e2*math.sin(phi1)**2)**1.5)
    T1 = math.tan(phi1)**2
    C1 = ep2 * math.cos(phi1)**2
    D = x / N1
    lat = phi1 - (N1 * math.tan(phi1) / R1) * (
        D**2/2
        - (5+3*T1+10*C1-4*C1**2-9*ep2) * D**4/24
        + (61+90*T1+298*C1+45*T1**2 - 252*ep2-3*C1**2) * D**6/720
    )
    lon = lam0 + (
        D
        - (1+2*T1+C1)*D**3/6
        + (5-2*C1+28*T1-3*C1**2 + 8*ep2+24*T1**2) * D**5/120
    ) / math.cos(phi1)
    return math.degrees(lat), math.degrees(lon)


# ==============================================================================
# SECTION 2: SINGLE-PASS STATIC FRONTEND CONFIGURATION & CSS
# ==============================================================================
st.set_page_config(
    page_title="Rwanda Geospatial Engine",
    page_icon="🌐",
    layout="centered"
)

st.markdown("""
    <style>
        .main-title {
            font-size: 32px !important;
            font-weight: 700 !important;
            color: #1E293B !important;
            margin-bottom: 2px;
            letter-spacing: -0.5px;
        }
        .sub-title {
            font-size: 15px !important;
            color: #64748B !important;
            margin-bottom: 25px;
        }
        .upload-instruction {
            font-size: 26px !important;
            font-weight: 800 !important;
            color: #FFFFFF !important;
            text-transform: uppercase !important;
            margin-bottom: 12px !important;
            margin-top: 25px !important;
            letter-spacing: -0.5px;
        }
        .stFileUploader {
            border: 1px solid #E2E8F0 !important;
            border-radius: 8px !important;
            background-color: #F8FAFC !important;
            padding: 5px !important;
            max-width: 160px !important;
            min-width: 160px !important;
        }
        
        [data-testid="stFileUploadDropzone"] {
            padding: 0px !important;
            border: none !important;
            pointer-events: none !important;
        }
        div[data-testid="stFileUploader"] section button {
            display: inline-flex !important;
            margin: 0px !important;
            pointer-events: auto !important;
        }
        
        [data-testid="stFileUploadDropzoneInstructions"],
        [data-testid="stFileUploadDropzone"] small,
        [data-testid="stFileUploadDropzone"] span,
        div[data-testid="stFileUploader"] section div div {
            display: none !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 24px !important;
            color: #0F766E !important;
            font-weight: 600;
        }
        
        h1 a, h2 a, h3 a, h4 a, h5 a, h6 a, .stMarkdown a.header-anchor, a.header-anchor {
            display: none !important;
            visibility: hidden !important;
            pointer-events: none !important;
        }
    </style>
    
    <h1 class="main-title">Rwanda Coordinate Translation Engine</h1>
    <p class="sub-title">Enterprise geodetic translation utility optimized for TM Rwanda (WGS84) vector alignment.</p>
""", unsafe_allow_html=True)


# ==============================================================================
# SECTION 3: MAIN APP LAYOUT (CACHED TEMPLATE FORMAT)
# ==============================================================================
st.markdown("### 📋 Required Spreadsheet Format Structure")
st.write("Your uploaded Excel file must strictly match this layout:")

blueprint_df = pd.DataFrame({
    "STATIONS": ["ST1", "ST2", ".", "ST(n)"],
    "EASTING (E)": ["", "", "", ""],
    "NORTHING(N)": ["", "", "", ""],
    "HDOP (m)": ["", "", "", ""],
    "VDOP(m)": ["", "", "", ""]
})
st.table(blueprint_df)

@st.cache_data(show_spinner=False)
def generate_static_template():
    template_buffer = io.BytesIO()
    with pd.ExcelWriter(template_buffer, engine='openpyxl') as writer:
        pd.DataFrame({
            "STATIONS": ["ST1", "ST2", ".", "ST(n)"],
            "EASTING (E)": [None, None, None, None],
            "NORTHING(N)": [None, None, None, None],
            "HDOP (m)": [None, None, None, None],
            "VDOP(m)": [None, None, None, None]
        }).to_excel(writer, index=False)
    return template_buffer.getvalue()

st.download_button(
    label="📥 Download Template Format",
    data=generate_static_template(),
    file_name="TM_Rwanda_Template_Format.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.markdown("---")

# Initialize state memory pipelines to isolate data from cloud refresh crashes
if 'file_bytes' not in st.session_state:
    st.session_state.file_bytes = None
if 'output_df' not in st.session_state:
    st.session_state.output_df = None
if 'metrics_data' not in st.session_state:
    st.session_state.metrics_data = None

# Step 1: Handle File Upload State
if st.session_state.file_bytes is None:
    st.markdown('<p class="upload-instruction">CLICK BELOW TO UPLOAD EXCEL FILE</p>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("", type=["xlsx"], accept_multiple_files=False)
    if uploaded_file is not None:
        st.session_state.file_bytes = uploaded_file.read()
        st.rerun()


# ==============================================================================
# SECTION 4: BATCH DATA EXECUTION PIPELINE (CLOUD STATE PROOF)
# ==============================================================================
if st.session_state.file_bytes is not None and st.session_state.output_df is None:
    st.info("ℹ️ File loaded successfully. Click the button below to process the conversion.")
    
    if st.button("Convert", type="primary", use_container_width=True):
        start_time = time.time()
        
        try:
            # Memory-isolated internal data stream handler
            with io.BytesIO(st.session_state.file_bytes) as file_stream:
                data = pd.read_excel(file_stream)
            
            data.columns = [str(col).strip() for col in data.columns]
            
            easting_col = next((col for col in data.columns if 'EAST' in col.upper()), None)
            northing_col = next((col for col in data.columns if 'NORTH' in col.upper()), None)
            station_col = next((col for col in data.columns if 'STAT' in col.upper()), None)
            hdop_col = next((col for col in data.columns if 'HDOP' in col.upper()), None)
            vdop_col = next((col for col in data.columns if 'VDOP' in col.upper()), None)
            
            if not easting_col or not northing_col:
                st.error("🚨 Processing Error: File Structure Misaligned. Columns must contain 'EASTING' and 'NORTHING'.")
                st.session_state.file_bytes = None  # Clear broken state data
            else:
                results = []
                for _, row in data.iterrows():
                    station = row[station_col] if station_col else "Unknown"
                    
                    try:
                        if pd.isna(row[easting_col]) or pd.isna(row[northing_col]):
                            continue
                        E = float(row[easting_col])
                        N = float(row[northing_col])
                    except (ValueError, TypeError):
                        continue
                        
                    hdop_val = row[hdop_col] if hdop_col else 0.0
                    vdop_val = row[vdop_col] if vdop_col else 0.0
                    
                    lat, lon = tm_to_geographic(E, N)
                    results.append([station, E, N, round(lat, 8), round(lon, 8), hdop_val, vdop_val])
                    
                if not results:
                    st.warning("⚠️ Data Insight: Valid numeric coordinates could not be processed inside the file.")
                    st.session_state.file_bytes = None
                else:
                    output = pd.DataFrame(results, columns=[
                        "Station", "Easting (m)", "Northing (m)", "Latitude", "Longitude", "HDOP (m)", "VDOP (m)"
                    ])
                    
                    # Store variables globally into the safe state pipeline memory
                    st.session_state.output_df = output
                    st.session_state.metrics_data = {
                        "count": len(output),
                        "runtime": round(time.time() - start_time, 4)
                    }
                    st.rerun()
                    
        except Exception as container_exception:
            st.error(f"🚨 Cloud Container Operational Error: {str(container_exception)}")
            st.session_state.file_bytes = None


# ==============================================================================
# SECTION 5: STATIC OUTPUT RENDERING (ZERO MEMORY BLOAT SELECTORS)
# ==============================================================================
if st.session_state.output_df is not None:
    st.success("🎉 TM RWANDA TO WGS84 COMPLETED SUCCESSFULLY")
    
    m_data = st.session_state.metrics_data
    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric(label="Calculated Nodes", value=f"{m_data['count']} Stations")
    m_col2.metric(label="Reference Datum", value="WGS84 Sphere")
    m_col3.metric(label="Execution Time", value=f"{m_data['runtime']} sec")
    
    # Renders the large table data safely without memory blowups or sorting buttons
    st.dataframe(
        st.session_state.output_df, 
        use_container_width=True,
        column_config={col: st.column_config.Column(disabled=True) for col in st.session_state.output_df.columns}
    )
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        st.session_state.output_df.to_excel(writer, index=False)
    
    st.download_button(
        label="📥 Download Converted TM_Rwanda_WGS84_Result.xlsx",
        data=buffer.getvalue(),
        file_name="TM_Rwanda_WGS84_Result.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    
    # State reset key to restart loop process cleanly
    if st.button("🔄 Clear and Convert Another File", use_container_width=True):
        st.session_state.file_bytes = None
        st.session_state.output_df = None
        st.session_state.metrics_data = None
        st.rerun()
