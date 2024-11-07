import streamlit as st
import numpy as np
import pandas as pd
import time
import os
import plotly.express as px

from labequipment.instruments.osa.AQ3675 import AQ3675
from labequipment.instruments.esa.E4440A import E4440A
from labequipment.instruments.lasers.TLB6700 import TLB6700

OSA_address1 = 'GPIB0::4::INSTR'
OSA_address2 = 'GPIB0::1::INSTR'
folder_path = './save/1003_24/temp5/27.0dBm_317mW-109mW_at_1591.98nm_-13.00+5_-27.83+25'

esa_state = 1
ESA_address = 'GPIB0::18::INSTR'

if not os.path.exists(folder_path):
    os.makedirs(folder_path)
    print(f'Folder created: {folder_path}')
else:
    print(f'Folder already exists: {folder_path}')

laser = TLB6700()
laser.on()

def trigger_on_multiple(n1, n2, threshold=0.01):

    if n2 == 0:
        raise ValueError("n2 must be non-zero.")
    
    ratio = n1 / n2
    nearest_integer = round(ratio)

    if abs(ratio - nearest_integer) < abs(threshold):
        return True
    else:
        return False

# Set page configuration
st.set_page_config(
    page_title='TE/TM OSA data collection',
    page_icon='✅',
    layout='wide'
)

# Dashboard title
st.subheader("TE/TM OSA data collection Dashboard")

# Create a compact layout for Piezo Start, Piezo Step, and buttons in a single row
col0, col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1, 1])

with col0:
    file_id_start = st.number_input("File ID", value=0, format="%.d")

with col1:
    piezo_start = st.number_input("Piezo Start", value=0.0, format="%.2f")

with col2:
    piezo_step_record = st.number_input("Piezo Step Record", value=0.1, format="%.2f")

with col3:
    piezo_step = st.number_input("Piezo Step Background", value=0.1, format="%.2f")

with col4:
    if st.button("Start Scan"):
        st.session_state.piezo = piezo_start  # Initialize piezo at the start value
        st.session_state.file_id = file_id_start
        st.session_state.scanning = True
        st.success("Scanning started")

with col5:
    if st.button("Stop Scan"):
        st.session_state.scanning = False
        # st.session_state.piezo = 0  # Reset piezo
        st.error("Scanning stopped")

# Initialize session state for dataframe and piezo value
if 'piezo' not in st.session_state:
    st.session_state.piezo = 0  # Initialization value
if 'file_id' not in st.session_state:
    st.session_state.file_id = 0  # Initialization value
if 'scanning' not in st.session_state:
    st.session_state.scanning = False  # Track scanning status

# Placeholder for the scan controls and data view
placeholder = st.empty()

# Near real-time / live feed simulation
accumulated_piezo = 0.0
while True:
    # Apply randomness to the balance_new column in every loop iteration
    with AQ3675(OSA_address1) as osa:
        data1 = osa.fetchData()

    with AQ3675(OSA_address2) as osa2:
        data2 = osa2.fetchData()

    if esa_state:
        with E4440A(ESA_address) as esa:
            data_esa = esa.fetchData()
        
        esa_dict = {"frequency": np.array(data_esa.Frequency), "intensity": np.array(data_esa.Intensity)}
        st.session_state.esa_df = pd.DataFrame(data=esa_dict)

    osa_dict1 = {"wavelength": np.array(data1.Wavelength), "intensity": np.array(data1.Intensity)}
    st.session_state.osa_df1 = pd.DataFrame(data=osa_dict1)
    osa_dict2 = {"wavelength": np.array(data2.Wavelength), "intensity": np.array(data2.Intensity)}
    st.session_state.osa_df2 = pd.DataFrame(data=osa_dict2)


    # Reading Laser data
    laser_power = laser.read_power()

    laser_wavelength = laser.read_wavelength()

    # If scanning, multiply by piezo and save to CSV
    if st.session_state.get('scanning', False):
        st.session_state.piezo += piezo_step
        laser.set_piezo(st.session_state.piezo)
        accumulated_piezo += piezo_step

        if trigger_on_multiple(accumulated_piezo, piezo_step_record, threshold=piezo_step/2):
            # Save to CSV after each update
            st.session_state.osa_df1.to_csv(folder_path+f'/{st.session_state.file_id}_piezo_{st.session_state.piezo:.2f}_1.csv', mode='a', header=False)
            st.session_state.osa_df2.to_csv(folder_path+f'/{st.session_state.file_id}_piezo_{st.session_state.piezo:.2f}_2.csv', mode='a', header=False)
            if esa_state:
                st.session_state.esa_df.to_csv(folder_path+f'/{st.session_state.file_id}_piezo_{st.session_state.piezo:.2f}_3.csv', mode='a', header=False)
            st.session_state.file_id += 1

    # Dynamically update the plots in each loop iteration
    with placeholder.container():
        # Create three columns
        kpi0, kpi1, kpi2, kpi3 = st.columns(4)

        # Fill in those three columns with respective metrics or KPIs
        # kpi1.metric(label="Age ⏳", value=round(avg_age), delta=round(avg_age) - 10)
        kpi0.metric(label="File ID", value=f"{st.session_state.file_id}")
        kpi1.metric(label="Piezo Current", value=f"{st.session_state.piezo:.2f}")
        kpi2.metric(label="Laser Power", value=laser_power)
        kpi3.metric(label="Laser Wavelength", value=laser_wavelength)

        if not esa:
        # Create two columns for charts
            fig_col1, fig_col2 = st.columns(2)
        
        else:
            fig_col1, fig_col2, fig_col3 = st.columns(3)
            
            with fig_col3:
                # st.markdown("### Second Chart")
                fig = px.line(data_frame=st.session_state.esa_df, y='intensity', x='frequency', range_y=[-100, 10])
                st.write(fig)

        with fig_col1:
            # st.markdown("### First Chart")
            fig = px.line(data_frame=st.session_state.osa_df1, y='intensity', x='wavelength', range_y=[-100, 10])
            st.write(fig)

        with fig_col2:
            # st.markdown("### Second Chart")
            fig = px.line(data_frame=st.session_state.osa_df2, y='intensity', x='wavelength', range_y=[-100, 10])
            st.write(fig)

    time.sleep(0.2)  # Delay for simulation purposes