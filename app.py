import math
import pandas as pd
import time
import io
import streamlit as st

# Set page config
st.set_page_config(
    page_title="Rwanda Coordinate Translation Engine",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =====================================================
# SAFELY TARGETED CSS OVERRIDES
# =====================================================
st.markdown("""
<style>
    /* Main Title Styling */
    .main-title {
        font-size: 32px !important;
        font-weight: 700 !important;
        color: #1E293B !important;
        letter-spacing: -0.5px !important;
        margin-bottom: 4px !important;
    }
    
    /* Subtitle Styling */
    .sub-title {
        font-size: 15px !important;
        color: #64748B !important;
        margin-bottom: 24px !important;
    }
    
    /* Upload Section Title Styling */
    .upload-title {
        color: #FFFFFF !important;
        text-transform: uppercase !important;
        font-weight: 800 !important;
        font-size: 26px !important;
        margin-bottom: 12px !important;
        background-color: #1E293B; /* Background added so white font remains visible on light themes */
        padding: 8px 12px;
        border-radius: 4px;
        display: inline-block;
    }
    
    /* Strict File Uploader Sizing Constraints */
    [data-testid="stFileUploader"] {
        max-width: 160px !important;
        min-width: 160px !important;
    }
    
    /* Safely target only the specific sub-labels inside the uploader dropzone */
    [data-testid="stFileUploaderDropzone"] [data-testid="stTypography"] {
        display: none !important;
    }
    [data-testid="stFileUploaderDropzone"] button::after {
        content: " Choose File" !important;
    }
    
    /* Suppress Header Hover Anchor Icons Completely */
    .stApp h1 a, .stApp h2 a, .stApp h3 a, .stApp h4 a, .stApp h5 a, .stApp h6 a {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# =====================================================
# TM RWANDA PARAMETERS (WGS84) - Kept Exactly Intact
# =====================================================
a = 6378137.0
f = 1 / 298.257223563
e2 = 2 * f - f**2
ep2 = e2 / (1 - e2)
E0 = 500000.0
N0 = 5000000.0
k0 = 0.9996
lam0 = math.radians(30.0)

# =====================================================
# INVERSE TM RWANDA -> WGS84 - Kept Exactly Intact
# =====================================================
def tm_to_geographic(E, N):
    x = E - E0
    y = N - N0
    M = y / k0
    mu = M / (
        a * (1 - e2/4 - 3*e2**2/64 - 5*e2**3/256)
    )
    e1 = (1 - math.sqrt(1-e2)) / (1 + math.sqrt(1-e2))
    phi1 = (
        mu
        + (3*e1/2 - 27*e1**3/32) * math.sin(2*mu)
        + (21*e1**2/16 - 55*e1**4/32) * math.sin(4*mu)
        + (151*e1**3/96) * math.sin(6*mu)
        + (1097*e1**4/512) * math.sin(8*mu)
    )
    N1 = a / math.sqrt(
        1 - e2 * math.sin(phi1)**2
    )
    R1 = (
        a*(1-e2)
        /
        (1-e2*math.sin(phi1)**2)**1.5
    )
    T1 = math.tan(phi1)**2
    C1 = ep2 * math.cos(phi1)**2
    D = x / N1
    lat = phi1 - (
        N1 * math.tan(phi1) / R1
    ) * (
        D**2/2
        -
        (5+3*T1+10*C1-4*C1**2-9*ep2)
        *D**4/24
        +
        (61+90*T1+298*C1+45*T1**2
         -252*ep2-3*C1**2)
        *D**6/720
    )
    lon = lam0 + (
        D
        -
        (1+2*T1+C1)*D**3/6
        +
        (5-2*C1+28*T1-3*C1**2
         +8*ep2+24*T1**2)
        *D**5/120
    ) / math.cos(phi1)
    return math.degrees(lat), math.degrees(lon)

# =====================================================
# CACHED TEMPLATE GENERATION
# =====================================================
@st.cache_data
def generate_template_bytes():
    output_buffer = io.BytesIO()
    columns = ["STATIONS", "EASTING (E)", "NORTHING(N)", "HDOP (m)", "VDOP(m)"]
    df_template = pd.DataFrame(columns=columns)
    with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
        df_template.to_excel(writer, index=False)
    return output_buffer.getvalue()

# =====================================================
# SESSION STATE INITIALIZATION
# =====================================================
if "file_bytes" not in st.session_state:
    st.session_state.file_bytes = None
if "processed_data" not in st.session_state:
    st.session_state.processed_data = None
if "metrics" not in st.session_state:
    st.session_state.metrics = None
if "output_excel_bytes" not in st.session_state:
    st.session_state.output_excel_bytes = None

# =====================================================
# FRONTEND UI PRESENTATION
# =====================================================
st.markdown('<h1 class="main-title">Rwanda Coordinate Translation Engine</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Enterprise geodetic translation utility optimized for TM Rwanda (WGS84) vector alignment.</p>', unsafe_allow_html=True)

if st.session_state.file_bytes is None:
    # 1. Blueprint Layout Framework
    st.markdown("### Expected Input Template Format Blueprint")
    preview_cols = ["STATIONS", "EASTING (E)", "NORTHING(N)", "HDOP (m)", "VDOP(m)"]
    preview_data = [["", "", "", "", ""]]
    df_preview = pd.DataFrame(preview_data, columns=preview_cols)
    st.table(df_preview)
    
    template_bytes = generate_template_bytes()
    st.download_button(
        label="Download Sample Format Excel Template",
        data=template_bytes,
        file_name="TM_Warm_Template_Format.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.markdown("---")
    
    # 2. Upload Panel Display
    st.markdown('<p class="upload-title">CLICK BELOW TO UPLOAD EXCEL FILE</p>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        label="Excel File Entry Node",
        label_visibility="collapsed",
        type=["xlsx"]
    )
    
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        st.session_state.file_bytes = file_bytes
        
        try:
            start_time = time.time()
            data = pd.read_excel(io.BytesIO(file_bytes))
            data.columns = data.columns.str.strip()
            
            results = []
            for _, row in data.iterrows():
                station = row["STATIONS"]
                E = float(row["EASTING (E)"])
                N = float(row["NORTHING(N)"])
                lat, lon = tm_to_geographic(E, N)
                
                results.append([
                    station,
                    E,
                    N,
                    round(lat, 8),
                    round(lon, 8),
                    row["HDOP (m)"],
                    row["VDOP(m)"]
                ])
                
            output_df = pd.DataFrame(results, columns=[
                "Station",
                "Easting (m)",
                "Northing (m)",
                "Latitude",
                "Longitude",
                "HDOP (m)",
                "VDOP (m)"
            ])
            
            end_time = time.time()
            exec_time = round(end_time - start_time, 4)
            
            output_buffer = io.BytesIO()
            with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
                output_df.to_excel(writer, index=False)
                
            st.session_state.processed_data = output_df
            st.session_state.output_excel_bytes = output_buffer.getvalue()
            st.session_state.metrics = {
                "nodes": len(output_df),
                "datum": "WGS84 Sphere",
                "time": f"{exec_time}s"
            }
            st.rerun()
            
        except Exception as e:
            st.error(f"Error during calculations parsing logic: {str(e)}")
            st.session_state.file_bytes = None

else:
    # 3. Dynamic Transformation Dashboard Display Panel
    st.success("TM Rwanda to WGS84 processing engine completed successfully.")
    
    m1, m2, m3 = st.columns(3)
    metrics = st.session_state.metrics
    m1.metric(label="Calculated Nodes", value=metrics["nodes"])
    m2.metric(label="Reference Datum", value=metrics["datum"])
    m3.metric(label="Execution Time", value=metrics["time"])
    
    st.markdown("### Processed Vector Alignment Data Records")
    
    config_map = {col: st.column_config.Column(disabled=True) for col in st.session_state.processed_data.columns}
    
    st.dataframe(
        st.session_state.processed_data,
        use_container_width=True,
        column_config=config_map,
        hide_index=True
    )
    
    st.download_button(
        label="Download Processed Coordinates (Excel)",
        data=st.session_state.output_excel_bytes,
        file_name="TM_Rwanda_WGS84_Result.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.markdown("---")
    
    if st.button("Clear and Convert Another File"):
        st.session_state.file_bytes = None
        st.session_state.processed_data = None
        st.session_state.metrics = None
        st.session_state.output_excel_bytes = None
        st.rerun()
