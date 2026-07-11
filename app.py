import streamlit as st
import pandas as pd
import math
import io
import time

# ==============================================================================
# SECTION 1: TM RWANDA PARAMETERS (WGS84) & EXACT MATH BACKEND
# ==============================================================================
a = 6378137.0
f = 1 / 298.257223563
e2 = 2 * f - f**2
ep2 = e2 / (1 - e2)

E0 = 500000.0
N0 = 5000000.0
k0 = 0.9996
lam0 = math.radians(30.0)

# INVERSE TM RWANDA -> WGS84
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


# ==============================================================================
# SECTION 2: FRONTEND CONFIGURATION & PROFESSIONAL CSS INJECTION
# ==============================================================================
st.set_page_config(
    page_title="Rwanda Geospatial Engine",
    page_icon="🌐",
    layout="centered"
)

# Aggressive CSS to enforce UI rules and hide Streamlit's default subtexts
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
        .stFileUploader {
            border: 1px solid #E2E8F0 !important;
            border-radius: 8px !important;
            background-color: #F8FAFC !important;
            padding: 5px !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 24px !important;
            color: #0F766E !important;
            font-weight: 600;
        }
        
        /* FORCIBLY HIDE THE 'upload Excel file' EXTRA DRAWERS CLEANLY */
        [data-testid="stFileUploadDropzone"] small {
            display: none !important;
        }
        [data-testid="stFileUploadDropzone"] > div > span {
            display: none !important;
        }
    </style>
""", unsafe_allow_html=True)


# ==============================================================================
# SECTION 3: MAIN APP LAYOUT (BATCH FILE UPLOAD & EXECUTION)
# ==============================================================================
st.markdown('<h1 class="main-title">Rwanda Coordinate Translation Engine</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Enterprise geodetic translation utility optimized for TM Rwanda (WGS84) vector alignment.</p>', unsafe_allow_html=True)

st.markdown("### 📋 Required Spreadsheet Format Structure")
st.write("Your uploaded Excel file columns must contain these keywords in the header row:")

# Display expected format safely
blueprint_df = pd.DataFrame({
    "Required Header Column Label": ["STATIONS", "EASTING (E)", "NORTHING(N)", "HDOP (m) *Optional*", "VDOP(m) *Optional*"],
    "Expected Format Example": ["ST01", 456746.11, 4834101.23, 0.013, 0.023]
})
st.dataframe(blueprint_df, hide_index=True, use_container_width=True)

st.markdown("---")

# Safe structural visibility flag avoids empty label core engine vulnerabilities
uploaded_file = st.file_uploader(
    "Excel Data Source Stream", 
    type=["xlsx"], 
    accept_multiple_files=False, 
    label_visibility="collapsed"
)

# ==============================================================================
# SECTION 4: DYNAMIC UI & PROCESSING LOOP
# ==============================================================================
if uploaded_file is not None:
    
    # DYNAMIC CSS TRICK: Hide the "+" dropzone completely once a file is inside
    st.markdown("""
        <style>
            [data-testid="stFileUploadDropzone"] {
                display: none !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.info("ℹ️ File loaded successfully. Click the button below to process the conversion.")
    
    if st.button("Convert", type="primary", use_container_width=True):
        
        start = time.time()
        
        # Read the Excel file instantly
        data = pd.read_excel(uploaded_file)
            
        data.columns = [str(col).strip() for col in data.columns]
        
        # Smart column detection
        easting_col = next((col for col in data.columns if 'EAST' in col.upper()), None)
        northing_col = next((col for col in data.columns if 'NORTH' in col.upper()), None)
        station_col = next((col for col in data.columns if 'STAT' in col.upper()), None)
        hdop_col = next((col for col in data.columns if 'HDOP' in col.upper()), None)
        vdop_col = next((col for col in data.columns if 'VDOP' in col.upper()), None)
        
        # Validation Check
        if not easting_col or not northing_col:
            st.error("🚨 Processing Error: File Structure Misaligned")
            st.markdown("#### 🔍 Structural Audit Logs:")
            st.markdown(f"""
            * **Easting Column Target Status:** {"✅ Linked" if easting_col else "❌ MISSING OR MISSPELLED"}
            * **Northing Column Target Status:** {"✅ Linked" if northing_col else "❌ MISSING OR MISSING"}
            """)
            st.info("💡 Modify your column headers so that they contain the words **EASTING** and **NORTHING**.")
            st.write("**Headers found inside your file:**", list(data.columns))
        else:
            results = []
            
            # CORE CONVERSION LOOP
            for _, row in data.iterrows():
                station = row[station_col] if station_col else "Unknown"
                E = float(row[easting_col])
                N = float(row[northing_col])
                hdop_val = row[hdop_col] if hdop_col else 0.0
                vdop_val = row[vdop_col] if vdop_col else 0.0
                
                lat, lon = tm_to_geographic(E, N)
                
                results.append([
                    station, E, N, round(lat, 8), round(lon, 8), hdop_val, vdop_val
                ])
                
            # Compile final dataframe
            output = pd.DataFrame(results, columns=[
                "Station", "Easting (m)", "Northing (m)", "Latitude", "Longitude", "HDOP (m)", "VDOP (m)"
            ])
            
            end = time.time()
            exec_time = round(end - start, 4)
            
            st.success("🎉 TM RWANDA TO WGS84 COMPLETED SUCCESSFULLY")
            
            m_col1, m_col2, m_col3 = st.columns(3)
            with m_col1:
                st.metric(label="Calculated Nodes", value=f"{len(output)} Stations")
            with m_col2:
                st.metric(label="Reference Datum", value="WGS84 Sphere")
            with m_col3:
                st.metric(label="Execution Time", value=f"{exec_time} sec")
            
            st.dataframe(output, use_container_width=True)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                output.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Download Converted TM_Rwanda_WGS84_Result.xlsx",
                data=buffer.getvalue(),
                file_name="TM_Rwanda_WGS84_Result.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
