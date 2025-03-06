# --------------------------------------
# Script Name: EY DASHBOARD V1
# Description: This dashboard provides an overview of water leak incidents, leak locations, findings, and the resolution process.

# Author: ONG
# Created Date: 2025-01-10
# Version: 1.0
# GitHub: https://github.com/ongaki8
# LinkedIn: https://www.linkedin.com/in/b8ongaki

# License: (Optional) MIT License, Apache License 2.0, etc.
# --------------------------------------

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
from opencage.geocoder import OpenCageGeocode
import datetime


# Set Streamlit layout to wide mode
st.set_page_config(layout="wide")

# Sidebar Navigation
st.sidebar.title("NAVIGATION")
page = st.sidebar.radio("Go to", ("DASHBOARD", "PROCESS DATA", "EDIT DATA (beta)"))

# Page 1: Data Upload
if page == "PROCESS DATA":

    # OpenCage API key 
    API_KEY = '81c369de85154de09aa3c49f4423b9a2'
    geocoder = OpenCageGeocode(API_KEY)

    # In-memory cache for airport code lookups
    airport_cache = {}

    # Function to get coordinates from airport code using OpenCage
    def get_coordinates(airport_code):
        if airport_code in airport_cache:
            return airport_cache[airport_code]  # Return from cache if already fetched

        query = f"{airport_code} airport"
        results = geocoder.geocode(query)

        if results:
            latitude = results[0]['geometry']['lat']
            longitude = results[0]['geometry']['lng']
            airport_cache[airport_code] = (latitude, longitude)  # Cache the result
            return latitude, longitude
        else:
            airport_cache[airport_code] = (None, None)  # Cache as None if not found
            return None, None

    st.title("DATA UPLOAD & PROCESSING")

    # File uploader for both Excel (.xlsx) and CSV files
    uploaded_file = st.file_uploader("Upload an Excel or CSV file", type=["xlsx", "csv"])

    if uploaded_file:
        # Step 1: Load the file
        try:
            # Determine the file type and read it accordingly
            if uploaded_file.name.endswith(".xlsx"):
                df = pd.read_excel(uploaded_file, engine="openpyxl")
            elif uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)

            # Step 2: Filter data where 'Number' starts with 'A6-B'
            df = df[df['Number'].str.startswith('A6-B', na=False)]

            # Step 3: Rename columns to match the desired format
            df.rename(columns={
                'Location': 'Location',
                'Text': 'Text',
                'Number': 'Number',
                'CreatedDate': 'Created Date',
                'ExternalReference': 'External Reference',
                'Leak location': 'Leak Location',
                'Findings': 'Findings',
                'ActionLatestSignatureDate': 'Action Latest Signature Date',
                'FlightAirportArrivalIATACode': 'Flight Airport Arrival',
                'ActionLatestText': 'Action Latest Text',
                'RegNumber': 'A/C REG'
            }, inplace=True)

            # Step 4: Add new columns for latitude and longitude based on 'Flight Airport Arrival'
            df['latitude'] = None
            df['longitude'] = None

            # Fetch coordinates in parallel or loop with caching
            for index, row in df.iterrows():
                airport_code = row['Flight Airport Arrival']
                latitude, longitude = get_coordinates(airport_code)
                df.at[index, 'latitude'] = latitude
                df.at[index, 'longitude'] = longitude

            # Step 6: Create a new column 'Resolution Time' as the time difference between 'Created Date' and 'Action Latest Signature Date'
            df['Resolution Time'] = ((pd.to_datetime(df['Action Latest Signature Date'], errors='coerce') - pd.to_datetime(df['Created Date'], errors='coerce')).dt.total_seconds() / 3600).round(1)

            # Step 7: Create a new column 'Created Date Filter' with only the date part of 'Created Date'
            df['Created Date Filter'] = pd.to_datetime(df['Created Date']).dt.date

            # Step 8: Select and rearrange columns in the desired order
            selected_columns = [
                'A/C REG', 'Flight Airport Arrival', 'Created Date', 'Number', 'Location', 'Text', 
                'Action Latest Text', 'External Reference', 'Leak Location', 'Findings', 
                'Action Latest Signature Date', 'Resolution Time', 'latitude', 'longitude'
            ]
            df = df[selected_columns]

            # # Step 9: Ensure that 'Findings', 'Leak Location', and 'External Reference' are all text fields
            # df['Findings'] = df['Findings'].astype(str)
            # df['Leak Location'] = df['Leak Location'].astype(str)
            # df['External Reference'] = df['External Reference'].astype(str)

            # Step 9: Display the dataframe
            st.dataframe(df, hide_index=True)

            # Step 10: Add a download button to export the selected data to a CSV file
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name="filtered_dataset.csv",
                mime="text/csv"
            )

        except Exception as e:
            st.error(f"An error occurred while processing the file: {e}")

# Page 2: Data Edit
elif page == "EDIT DATA (beta)":
    # Title
    st.title("EDIT DATA (beta)")

    # File uploader for CSV or Excel files
    uploaded_file = st.file_uploader("Upload CSV or Excel File", type=["csv", "xlsx"])

    #---------------------------
    st.markdown("---")
    #---------------------------

    # Initialize session state for undo, redo, and save history
    if "history" not in st.session_state:
        st.session_state.history = []  # Stack of history for undo and redo
        st.session_state.future = []  # Stack for redo
        st.session_state.current_data = None  # The current working dataframe

    # Load data if file is uploaded
    if uploaded_file is not None:
        if uploaded_file.name.endswith('.csv'):
            data = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith('.xlsx'):
            data = pd.read_excel(uploaded_file)

        # Save the initial data into session state if not already saved
        if st.session_state.current_data is None:
            st.session_state.current_data = data.copy()

        # Reset the dataframe index for display purposes (starting from 1)
        data_reset = st.session_state.current_data.reset_index(drop=True)
        data_reset.index += 1  # Adjust index to start from 1

        # Display the modified dataframe with index starting from 1
        st.write("### TABULATED DATA")
        st.dataframe(data_reset)

        #---------------------------
        st.markdown("---")
        #---------------------------

        # Dropdown to select a single row to edit, adjusting index to start from 1
        st.write("### EDIT DATA")
        selected_row = st.selectbox(
            "Select a row to edit:",
            options=range(1, len(data) + 1),  # Adjusting range to start from 1
            format_func=lambda x: f"Row {x}"  # Format to display as 'Row 1', 'Row 2', etc.
        ) - 1  # Adjust for 0-based indexing (Python index starts from 0)

        st.markdown("<br>", unsafe_allow_html=True)

        # Show the selected data for editing
        st.write(f"### Editing Row {selected_row + 1}")
        selected_data = st.session_state.current_data.iloc[selected_row]

        # Reset the index for the selected data row to start from 1 for display
        selected_data_reset = selected_data.to_frame().T.reset_index(drop=True)
        selected_data_reset.index += 1  # Adjust index to start from 1

        # Display the selected row data for editing with 1-based index
        st.write("Selected Data:")
        st.dataframe(selected_data_reset)

        # Create editable fields for the selected row
        edited_data = selected_data.copy()  # Make a copy for editing

        # Placeholder text for NaN values
        placeholder = "No data"  # Custom placeholder text for NaN values

        st.markdown("<br>", unsafe_allow_html=True)

        # Row 1: A/C REG, Number, Flight Airport Arrival
        col1, col2, col3 = st.columns(3)
        with col1:
            edited_data["A/C REG"] = st.text_input("A/C REG", value=str(edited_data["A/C REG"]), key="A/C REG")
        with col2:
            edited_data["Number"] = st.text_input("Number", value=str(edited_data["Number"]), key="Number")
        with col3:
            edited_data["Flight Airport Arrival"] = st.text_input("Flight Airport Arrival", value=str(edited_data["Flight Airport Arrival"]), key="Flight Airport Arrival")

        # Row 2: Text, Action Latest Text
        col1, col2 = st.columns(2)
        with col1:
            edited_data["Text"] = st.text_area("Text", value=str(edited_data["Text"]), key="Text")
        with col2:
            edited_data["Action Latest Text"] = st.text_area("Action Latest Text", value=str(edited_data["Action Latest Text"]), key="Action Latest Text")

        # Row 3: Created Date, Action Latest Signature Date
        col1, col2 = st.columns(2)
        with col1:
            edited_data["Created Date"] = st.date_input("Created Date", value=pd.to_datetime(edited_data["Created Date"]), key="Created Date")
        with col2:
            edited_data["Action Latest Signature Date"] = st.date_input("Action Latest Signature Date", value=pd.to_datetime(edited_data["Action Latest Signature Date"]), key="Action Latest Signature Date")

       # Row 4: Location, Leak Location
        col1, col2 = st.columns(2)
        with col1:
            edited_data["Location"] = st.text_input("Location", value=str(edited_data["Location"]), key="Location")
        with col2:
            # Dropdown for Leak Location with predefined options (No 'None' option)
            leak_location_options = ['Behind carts', 'Behind fridge', 'Behind hot beverage machine', 
                                    'Behind Oven', 'Ice Drawer', 'Other']
            selected_leak_location = st.selectbox(
                "Leak Location", 
                options=leak_location_options,  # Only predefined options
                index=leak_location_options.index(edited_data["Leak Location"]) if edited_data["Leak Location"] in leak_location_options else 0,
                key="Leak Location"
            )

            # If "Other" is selected, allow custom text entry
            if selected_leak_location == 'Other':
                edited_data["Leak Location"] = st.text_input("Custom Leak Location", value=str(edited_data["Leak Location"]), key="Custom Leak Location")
            else:
                edited_data["Leak Location"] = selected_leak_location

        # Row 5: External Reference, Findings
        col1, col2 = st.columns(2)
        with col1:
            edited_data["External Reference"] = st.text_input("External Reference", value=str(edited_data["External Reference"]), key="External Reference")
        with col2:
            # Dropdown for Findings with predefined options (No 'None' option)
            findings_options = ['Nil Leak', 'Condensation', 
                                'Bev maker reinstalled', 'Galley leak test', 
                                'Ice Drawer cleaned', 'Ice Drawer drain clogged', 
                                'Ice on chiller flaps', 'Ice on fridge port', 
                                'Overflow hose loose', 'Other']
            selected_findings = st.selectbox(
                "Findings", 
                options=findings_options,  # Only predefined options
                index=findings_options.index(edited_data["Findings"]) if edited_data["Findings"] in findings_options else 0,
                key="Findings"
            )

            # If "Other" is selected, allow custom text entry
            if selected_findings == 'Other':
                edited_data["Findings"] = st.text_input("Custom Findings", value=str(edited_data["Findings"]), key="Custom Findings")
            else:
                edited_data["Findings"] = selected_findings

        # Reset index for edited data to start from 1 for display
        edited_data_reset = edited_data.to_frame().T.reset_index(drop=True)
        edited_data_reset.index += 1  # Adjust index to start from 1

        #---------------------------
        st.markdown("---")
        #---------------------------

        # Display the edited data after user input with 1-based index
        st.write("### EDITED DATA")
        st.dataframe(edited_data_reset)

        # Row for the buttons
        col1, col2, col3, col4 = st.columns([0.2,0.2,0.2,1.04])

        with col1:
            if st.button("UNDO"):
                if st.session_state.history:
                    st.session_state.future.append(st.session_state.current_data.copy())  # Save the current state in future
                    st.session_state.current_data = st.session_state.history.pop()  # Get the last saved state from history
                    st.success("Undo Successful.")
                else:
                    st.warning("Nothing to undo.")

        with col2:
            if st.button("REDO"):
                if st.session_state.future:
                    st.session_state.history.append(st.session_state.current_data.copy())  # Save current state in history
                    st.session_state.current_data = st.session_state.future.pop()  # Get the last undone state from future
                    st.success("Redo Successful.")
                else:
                    st.warning("Nothing to redo.")

        with col3:
            if st.button("SAVE"):
                st.session_state.history.append(st.session_state.current_data.copy())  # Save current data state in history
                st.session_state.future.clear()  # Clear redo stack
                st.session_state.current_data.iloc[selected_row] = edited_data  # Update current data with edited data
                st.success("Saved Successfully.")

        with col4:
            st.download_button(
                label="DOWNLOAD CSV",
                data=st.session_state.current_data.to_csv(index=False),
                file_name="edited_data.csv",
                mime="text/csv"
            )

# Page 3: Dashboard
elif page == "DASHBOARD":

        # Dashboard title
    st.markdown("<h1 style='text-align: left;'>EY GALLEY WATER LEAK DASHBOARD</h1>", unsafe_allow_html=True)
    st.write("""
    This dashboard provides an overview of water leak incidents, leak locations, findings, and the resolution process.
    It helps to identify trends over time, root causes, and locations with higher leak 
    incident frequencies. By analyzing this data, operational improvements and corrective actions can be identified to reduce leak occurrences.
    """)
    #---------------------------
    st.markdown("---")
    #---------------------------
    st.markdown("<br>", unsafe_allow_html=True)

    # Main Page File Uploader
    uploaded_file = st.file_uploader("Upload CSV or Excel File", type=["csv", "xlsx"])

    st.markdown("<br>", unsafe_allow_html=True)

    # If a file is uploaded, load the data from it
    if uploaded_file is not None:
        if uploaded_file.name.endswith('.csv'):
            data = pd.read_csv(uploaded_file, index_col=False)
            st.write(f"Data loaded from {uploaded_file.name}")
        elif uploaded_file.name.endswith('.xlsx'):
            data = pd.read_excel(uploaded_file, index_col=False)
            st.write(f"Data loaded from {uploaded_file.name}")
    else:
        # If no file is uploaded, fall back to loading the default file
        data = pd.read_csv("master_dataset.csv", index_col=False)

    # Convert 'Created Date' to datetime and strip time (keeping only the date)
    data['Created Date'] = pd.to_datetime(data['Created Date'], errors='coerce').dt.date
    data['Action Latest Signature Date'] = pd.to_datetime(data['Action Latest Signature Date'], errors='coerce').dt.date

    # # Check values
    # oldest_date = data['Created Date'].min()  # Oldest (earliest) date
    # recent_date = data['Created Date'].max()  # Most Recent (latest) date

    # Convert the 'External Reference' column to string to remove commas in the display // Uncomment if data is displayed with commas
    # data['External Reference'] = data['External Reference'].astype(str)

    # Sidebar Filters
    st.sidebar.header("Filters")

    # Function to create a filter dropdown with checkboxes
    def create_filter_dropdown(column_name, label):
        unique_values = ['All'] + list(data[column_name].dropna().unique())
        selected_values = st.sidebar.multiselect(label, unique_values, default=['All'])
        return selected_values

    # Create filters for each field
    aircraft_filter = create_filter_dropdown('A/C REG', 'Select Aircraft Registration')
    airport_filter = create_filter_dropdown('Flight Airport Arrival', 'Select Flight Airport')
    location_filter = create_filter_dropdown('Location', 'Select Location')
    leak_location_filter = create_filter_dropdown('Leak Location', 'Select Leak Location')
    findings_filter = create_filter_dropdown('Findings', 'Select Findings')

    # Sidebar: Date Range Filter
    st.sidebar.write("### Date Range Filter")

    # Get the current system date
    current_date = datetime.date.today()

    # Check if the start_date and end_date are set in session state, otherwise use default values
    if 'start_date' not in st.session_state:
        st.session_state['start_date'] = data['Created Date'].min()
    if 'end_date' not in st.session_state:
        st.session_state['end_date'] = current_date

    # Set the date inputs with system date as the maximum value
    start_date = st.sidebar.date_input('Start date', value=st.session_state['start_date'])
    end_date = st.sidebar.date_input('End date', value=st.session_state['end_date'], max_value=current_date)

    # Add a reset button for the date range filter
    reset_date_button = st.sidebar.button("Reset Date Range")

    # If the "Reset Date Range" button is clicked, reset the date range to default
    if reset_date_button:
        st.session_state['start_date'] = data['Created Date'].min()
        st.session_state['end_date'] = current_date  # Set the end date to current system date
        st.rerun()  # Trigger a rerun to reset the filters

    # Apply filters with "AND" condition
    filtered_data = data.copy()

    # Apply the filters to the data
    if 'All' not in aircraft_filter and aircraft_filter:
        filtered_data = filtered_data[filtered_data['A/C REG'].isin(aircraft_filter)]
    if 'All' not in airport_filter and airport_filter:
        filtered_data = filtered_data[filtered_data['Flight Airport Arrival'].isin(airport_filter)]
    if 'All' not in location_filter and location_filter:
        filtered_data = filtered_data[filtered_data['Location'].isin(location_filter)]
    if 'All' not in leak_location_filter and leak_location_filter:
        filtered_data = filtered_data[filtered_data['Leak Location'].isin(leak_location_filter)]
    if 'All' not in findings_filter and findings_filter:
        filtered_data = filtered_data[filtered_data['Findings'].isin(findings_filter)]

    # Apply date range filter (using date only)
    filtered_data = filtered_data[(filtered_data['Created Date'] >= start_date) & 
                                (filtered_data['Created Date'] <= end_date)]

    # Display the filtered data without the index
    st.write("### TABULATED DATA")
    st.dataframe(filtered_data.reset_index(drop=True), use_container_width=True, hide_index=True)

    # ------------
    # Extracting the month and year from 'Created Date'
    filtered_data['Month-Year'] = pd.to_datetime(filtered_data['Created Date']).dt.to_period('M').astype(str)

    reports_over_month = filtered_data.groupby('Month-Year').size().reset_index(name='Report Count')

    # Convert Period to string for JSON serialization
    reports_over_month['Month-Year'] = reports_over_month['Month-Year'].astype(str)

    # Group data by 'A/C REG' and 'Month-Year' to count delays
    heatmap_data = filtered_data.groupby(['A/C REG', 'Month-Year']).size().reset_index(name='Delay Count')

    # Ensure 'A/C REG' and 'Month-Year' are treated as categorical variables
    heatmap_data['A/C REG'] = heatmap_data['A/C REG'].astype(str)
    heatmap_data['Month-Year'] = heatmap_data['Month-Year'].astype(str)



    # ------------
    st.markdown("<br>", unsafe_allow_html=True)

    #---------------------------
    st.markdown("---")
    #---------------------------

    # LEAK DISTRIBUTION SECTION ------
    with st.expander("LEAK DISTRIBUTION"):
        # Leak Distribution by Aircraft
        # st.write("### LEAK DISTRIBUTION")
        # Group by aircraft registration and leak location
        aircraft_leak_counts = filtered_data.groupby(['A/C REG', 'Leak Location']).size().reset_index(name='Leak Count')

        # Create bar chart showing the number of leaks per aircraft
        aircraft_leak_chart = px.bar(aircraft_leak_counts, x='A/C REG', y='Leak Count', color='Leak Location', 
                                    title='LEAK DISTRIBUTION BY AIRCRAFT REGISTRATION')

        # Update the layout to make the legend horizontal and position it below the chart
        aircraft_leak_chart.update_layout(
            legend=dict(
                orientation='h',  # Horizontal legend
                yanchor='top',  # Position the legend at the bottom
                y=-0.4,  # Adjust the vertical position (below the chart)
                xanchor='center',  # Center the legend horizontally
                x=0.5,  # Center the legend horizontally
                title=None
            )
        )


        # Update the layout to center the title
        aircraft_leak_chart.update_layout(
            title={
                'text': 'LEAK DISTRIBUTION BY AIRCRAFT REGISTRATION',  # Title text
                'x': 0.5,  # x=0.5 will center the title
                'xanchor': 'center'  # Anchor the title in the center
            }
        )
        st.plotly_chart(aircraft_leak_chart)

        # Add space between charts
        st.markdown("<br>", unsafe_allow_html=True)  

        # Group by 'A/C REG' and 'Leak Location' to count the number of leaks
        aircraft_leak_counts = filtered_data.groupby(['A/C REG', 'Leak Location']).size().reset_index(name='Leak Count')

        # Create a treemap showing leaks by aircraft registration and leak location
        treemap = px.treemap(aircraft_leak_counts, path=['A/C REG', 'Leak Location'], values='Leak Count',
                            title='TREEMAP OF LEAKS BY AIRCRAFT REGISTRATION AND LEAK LOCATION')
        # Update the hover template to show "A/C REG" and "Leak Count"
        treemap.update_traces(
            hovertemplate="Leak Count: %{value}<extra></extra>"
        )
        
        # Update the layout to center the title
        treemap.update_layout(
            title={
                'text': 'TREEMAP OF LEAKS BY AIRCRAFT REGISTRATION AND LEAK LOCATION',  # Title text
                'x': 0.5,  # x=0.5 will center the title
                'xanchor': 'center'  # Anchor the title in the center
            }
        )

        # Adjust the height of the treemap
        treemap.update_layout(
            height=600  # Set the desired height for the treemap
        )
        st.plotly_chart(treemap)

    #---------------------------
    st.markdown("---")
    #---------------------------

    # GALLEYS AND LEAK LOCATION ANALYSIS SECTION ------
    with st.expander("GALLEYS AND LEAK LOCATION ANALYSIS"):
        # Location-Specific Issues
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)

        # Pie chart for distribution of reports by location
        with col1:
            location_counts = filtered_data.groupby('Location').size().reset_index(name='Report Count')
            pie_chart_location = px.pie(location_counts, names='Location', values='Report Count', 
                                        title='LOCATION')
            
            # Update the layout to center the title
            pie_chart_location.update_layout(
                title={'x': 0.5, 'xanchor': 'center'}  # Center title
            )

            # Update the layout to move the legend to the left side
            pie_chart_location.update_layout(
                legend=dict(
                    orientation="v",  # Vertical orientation
                    x=-0.2,  # Position legend outside the plot area to the left
                    y=0.5,
                )
            )
            
            # Display the pie chart
            st.plotly_chart(pie_chart_location)

        # Histogram in the second column
        with col2:
            leak_location_counts = filtered_data.groupby('Leak Location').size().reset_index(name='Leak Count')
            pie_chart_leak_location = px.pie(leak_location_counts, names='Leak Location', values='Leak Count', title='LEAK LOCATION DISTRIBUTION')
            # Update the layout to center the title
            pie_chart_leak_location.update_layout(
            title={'x': 0.5, 'xanchor': 'center'}  # Center title
                    )
            pie_chart_leak_location.update_layout(
            legend=dict(
            orientation="v",  # Vertical orientation
            x=1.2,  # Position legend outside the plot area to the right
            y=0.5,  # Center the legend vertically
            yanchor='middle'  # Anchor the legend vertically to its middle
                    )
                )
            st.plotly_chart(pie_chart_leak_location)

        st.markdown("---")

        # Group by location and leak location
        location_leak_counts = filtered_data.groupby(['Location', 'Leak Location']).size().reset_index(name='Leak Count')

        # Create a side-by-side bar chart
        location_leak_chart = px.bar(location_leak_counts, 
                                    x='Location', 
                                    y='Leak Count', 
                                    color='Leak Location', 
                                    title='Location - Specific Leak Issues'.upper(),
                                    barmode='group')  # This makes the bars side by side

        # Update the layout to center the title
        location_leak_chart.update_layout(
            title={'x': 0.5, 'xanchor': 'center'},  # Center title
            legend=dict(
                orientation='h',  # Horizontal legend
                yanchor='top',  # Position the legend at the bottom
                y=-0.3,  # Adjust the vertical position (below the chart)
                xanchor='center',  # Center the legend horizontally
                x=0.5,  # Center the legend horizontally
                title=None
            )
        )

        # Display the chart
        st.plotly_chart(location_leak_chart)

        st.markdown("<br>", unsafe_allow_html=True)

    #---------------------------
    st.markdown("---")
    #---------------------------

    # FREQUENCY OF OCCURRENCES SECTION -----
    with st.expander("FREQUENCY OF OCCURRENCES"):
        # Frequency of Occurrences (Leaks over time)
        # Count the number of leaks per month
        monthly_leak_counts = filtered_data.groupby('Month-Year').size().reset_index(name='Leak Count')

        # Simplify data if there are too many points
        if len(monthly_leak_counts) > 100:  # Adjust threshold based on your dataset size
            monthly_leak_counts = monthly_leak_counts.iloc[::1, :]  # Take every 2nd row to reduce data size

        # Create line chart showing leak counts over time
        leak_frequency_chart = px.line(monthly_leak_counts, x='Month-Year', y='Leak Count', title='FREQUENCY OF LEAKS OVER TIME')

        # Update the layout to center the title
        leak_frequency_chart.update_layout(
            title={'x': 0.5, 'xanchor': 'center'},  # Center title
            xaxis=dict(
            tickmode='auto',  # Let Plotly decide the best tick positions
            nticks=len(monthly_leak_counts) // 1,  # Approximate tick interval to every 2 months
            tickangle=45,  # Rotate the ticks for better readability
            )
        )
        st.plotly_chart(leak_frequency_chart)

        st.markdown("---")

        # Space below
        st.markdown("<br>", unsafe_allow_html=True) 

        # Center Title
        st.markdown("<h3 style='text-align: center;'>LEAK TRENDS POST-CORRECTIVE ACTIONS</h3>", unsafe_allow_html=True)
        
        # Space below
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Calculate the recurrence data for the entire dataset
        data = data.sort_values(by=['A/C REG', 'Findings', 'Created Date'])
        data['Reccurrence Count'] = data.groupby(['A/C REG', 'Findings']).cumcount()
        data['Cumulative Reccurrence Count'] = data.groupby('Findings').cumcount()

        # Store this recurrence data in an independent DataFrame
        recurrence_data = data[['A/C REG', 'Findings', 'Leak Location', 'Created Date', 'Reccurrence Count', 'Cumulative Reccurrence Count']].copy()

        # Continue with the existing process for filtered data
        col1, col2 = st.columns([0.3, 0.7])

        with col1:
            # Create a filter for Findings with 'All' option
            findings_options = ['All'] + list(recurrence_data['Findings'].unique())
            default_index = findings_options.index('Nil Leak') if 'Nil Leak' in findings_options else 0
            selected_finding = st.selectbox('SELECT FINDING', findings_options, index=default_index)

            # Filter recurrence_data based on the selected finding
            filtered_recurrence_data = recurrence_data if selected_finding == 'All' else recurrence_data[recurrence_data['Findings'] == selected_finding].copy()

            # Calculate the maximum recurrence count for the finding
            max_reccurrence_finding = filtered_recurrence_data['Cumulative Reccurrence Count'].max()

            # Calculate the maximum recurrence per aircraft and for the selected finding
            aircraft_max_reccurrence = filtered_recurrence_data.groupby('A/C REG')['Reccurrence Count'].max().reset_index()
            aircraft_max_reccurrence = aircraft_max_reccurrence.rename(columns={'Reccurrence Count': 'Max Reccurrence'})

            # Merge max recurrence back to the filtered_recurrence_data and sort by 'Created Date'
            filtered_recurrence_data = filtered_recurrence_data.merge(aircraft_max_reccurrence, on='A/C REG', how='left')
            filtered_recurrence_data = filtered_recurrence_data.sort_values(by='Created Date', ascending=True)

            # Find the first occurrence of the selected finding
            first_occurrence = filtered_recurrence_data.iloc[0]

            st.markdown("<h4 style='text-align: center;'>RECURRENCE PER AIRCRAFT</h4>", unsafe_allow_html=True)
            st.dataframe(aircraft_max_reccurrence, hide_index=True, use_container_width=True, height=330)

        with col2:
            # Recurrence over time using the Recurrence Count
            reccurrence_chart = px.line(
            filtered_recurrence_data, 
            x='Created Date', 
            y='Reccurrence Count', 
            color='A/C REG', 
            title=f'RECURRENCE OF {selected_finding} OVER TIME (Recurrence: {max_reccurrence_finding} Instances)'.upper()
            )
            reccurrence_chart.update_traces(mode='lines+markers', marker=dict(size=6))
            reccurrence_chart.add_scatter(
                x=[first_occurrence['Created Date']], 
                y=[first_occurrence['Reccurrence Count']], 
                mode='markers+text', 
                textposition='top center',
                marker=dict(color=reccurrence_chart['data'][0]['line']['color'], size=10, symbol='bowtie'),
                name='First Occurrence'
            )
            reccurrence_chart.update_layout(
                title={'x': 0.5, 'xanchor': 'center'}  # Center title
            )
            reccurrence_chart.add_annotation(
                x=first_occurrence['Created Date'], 
                y=first_occurrence['Reccurrence Count'],
                text=f"First Occurrence: {first_occurrence['A/C REG']}",
                showarrow=True,
                arrowhead=3,
                ax=0,  
                ay=-60,  
                arrowcolor=reccurrence_chart['data'][0]['line']['color'],
                font=dict(size=12, color="White")
            )
            reccurrence_chart.update_layout(height=520)
            st.plotly_chart(reccurrence_chart)

        st.markdown("---")

        # Calculate the recurrence data for the entire dataset
        data = data.sort_values(by=['A/C REG', 'Findings', 'Created Date'])
        data['Reccurrence Count'] = data.groupby(['A/C REG', 'Findings']).cumcount() - 1
        data['Cumulative Reccurrence Count'] = data.groupby('Findings').cumcount() - 1
        

        # Store this reoccurrence data in an independent DataFrame
        reccurrence_dataset = data[['A/C REG', 'Findings', 'Leak Location', 'Created Date', 'Reccurrence Count', 'Cumulative Reccurrence Count']].copy()
        
        # Store the final filtered data in a variable for further use
        recurrence_filtered_data = filtered_data.copy()

        # Recurrence Tabulated Data
        # st.dataframe(reccurrence_dataset, hide_index=True, use_container_width=True)

        # Create two columns for the pie chart and bar chart
        col1, col2 = st.columns([0.5, 0.5])

        # Pie chart for cumulative recurrences by leak location in the left column
        with col1:
            # Group by 'Findings' to get the cumulative number of recurrences by type
            findings_recurrence = recurrence_data.groupby('Findings')['Cumulative Reccurrence Count'].max().reset_index(name='Cumulative Recurrence Count')

            # Sort the findings_recurrence DataFrame by 'Cumulative Recurrence Count' in descending order
            findings_recurrence = findings_recurrence.sort_values(by='Cumulative Recurrence Count', ascending=False)

            # Create bar chart for cumulative recurrences by findings
            bar_chart_findings = px.bar(findings_recurrence, x='Findings', y='Cumulative Recurrence Count', title='RECURRENCES BY FINDINGS')

            bar_chart_findings.update_layout(
                title={'x': 0.5, 'xanchor': 'center'}  # Center title
            )

            # Update the title alignment for the bar chart
            bar_chart_findings.update_layout(title_x=0.5)

            # Display the bar chart
            st.plotly_chart(bar_chart_findings)
            
        # Bar chart for cumulative recurrences by findings in the right column
        with col2:
            # Group by 'Leak Location' to count the number of instances
            leak_location_instances = recurrence_data.groupby('Leak Location').size().reset_index(name='Instance Count')

            # Sort the leak_location_instances DataFrame by 'Instance Count' in descending order
            leak_location_instances = leak_location_instances.sort_values(by='Instance Count', ascending=False)

            # Create a pie chart for instances by leak location
            pie_chart_leak_location = px.pie(leak_location_instances, names='Leak Location', values='Instance Count', title='RECURRENCES BY LEAK LOCATION')

            pie_chart_leak_location.update_layout(
                title={'x': 0.35, 'xanchor': 'center'}  # Center title
            )

            pie_chart_leak_location.update_layout(
            legend=dict(
                orientation='h',  # Horizontal legend
                yanchor='top',  # Position the legend at the bottom
                y=-0.1,  # Adjust the vertical position (below the chart)
                xanchor='center',  # Center the legend horizontally
                x=0.45,  # Center the legend horizontally
                title=None
            )
        )

            # Update the title alignment for the pie chart
            pie_chart_leak_location.update_layout(title_x=0.5)

            # Display the pie chart
            st.plotly_chart(pie_chart_leak_location)

        st.markdown("---")
        
        st.markdown("<br>", unsafe_allow_html=True) 

        # Root Cause Analysis
        st.markdown("<h3 style='text-align: center;'>ROOT CAUSE ANALYSIS</h3>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True) 

        # Create a two-column layout
        col1, col2 = st.columns([0.4, 0.6])

        with col1:
            # Group by 'Findings' and 'Leak Location' to get independent counts
            findings_leak_counts = data.groupby(['Findings', 'Leak Location', 'Location']).size().reset_index(name='Leak Count')
            # Create sunburst chart showing the correlation between findings and leak locations
            findings_leak_chart = px.sunburst(
                findings_leak_counts, 
                path=['Leak Location', 'Findings'], 
                values='Leak Count', 
                title='LEAK LOCATION INSIGHTS'
            )

            # Update hover template to show only "Leak Count" and "Location"
            findings_leak_chart.update_traces(
                hovertemplate="Leak Count: %{value}<br>%{label}<extra></extra>"
            )

            # Update the layout to center the title
            findings_leak_chart.update_layout(
                title={'x': 0.5, 'xanchor': 'center'}  # Center title
            )

            # Display the sunburst chart
            st.plotly_chart(findings_leak_chart)

            
        with col2:
            # Treemap chart showing the distribution of leaks by findings and leak location
            findings_treemap = px.treemap(
                findings_leak_counts, 
                path=['Location', 'Findings', 'Leak Location'], 
                values='Leak Count', 
                title='FINDINGS DISTRIBUTION'
            )

            # Update hover template to show only "Leak Count" and "Location"
            findings_treemap.update_traces(
                hovertemplate="Leak Count: %{value}<br>%{label}<extra></extra>"
            )

            # Center the title for the treemap chart
            findings_treemap.update_layout(
                title={'x': 0.5, 'xanchor': 'center'}  # This centers the title
            )

            # Display the treemap chart
            st.plotly_chart(findings_treemap)
            
    #---------------------------
    st.markdown("---")
    #---------------------------

    # REPORT TO RESOLUTION TIME SECTION -----
    with st.expander("REPORT TO RESOLUTION TIME"):
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>TIME FROM REPORTING TO RESOLUTION</h3>", unsafe_allow_html=True)

        # Load and preprocess data
        # time_data = pd.read_csv("edited_data.csv")  # Ensure you load data from the updated CSV
        time_data = pd.read_csv("master_dataset.csv")  # Ensure you load data from the updated CSV
        time_data['Resolution Time'] = time_data['Resolution Time'].round(2)

        # Remove rows with NaN in 'Findings', 'Leak Location', or 'Location'
        time_data_cleaned = time_data.dropna(subset=['Findings', 'Leak Location', 'Location'])

        # Aggregate data for fastest, slowest, and average resolution times
        fastest_and_slowest = time_data.groupby('Findings')['Resolution Time'].agg(
            fastest='min',
            slowest='max'
        ).reset_index()

        findings_avg_resolution = time_data.groupby('Findings')['Resolution Time'].mean().reset_index(name='avg_resolution_time')

        metrics_data = time_data.groupby(['Leak Location', 'Findings'])['Resolution Time'].mean().reset_index()
        metrics_data['avg_resolution_time'] = metrics_data['Resolution Time'].round(2)

        # Create layout for charts
        col1, col2 = st.columns([0.3, 0.7])

        with col1:
            sunburst_chart = px.sunburst(
                time_data_cleaned,  # Use the cleaned data without NaN values
                path=['Findings', 'Leak Location', 'Location'],
                values='Resolution Time',
                title='FINDINGS BREAKDOWN'
            )
            sunburst_chart.update_traces(
                hovertemplate="<b>%{label}</b><br>Avg Resolution Time: %{value:.2f} Hours<extra></extra>"
            )
            sunburst_chart.update_layout(
                title={'x': 0.5, 'xanchor': 'center'},
                legend=dict(
                    orientation='h',
                    yanchor='top',
                    y=-0.3,
                    xanchor='center',
                    x=0.5,
                    title=None
                )
            )
            st.plotly_chart(sunburst_chart, use_container_width=True)

        with col2:
            tree_map_chart = px.treemap(
                metrics_data,
                path=['Leak Location', 'Findings'],
                values='avg_resolution_time',
                title='LOCATION BREAKDOWN'
            )
            tree_map_chart.update_traces(
                hovertemplate="<b>%{label}</b><br>Avg Resolution Time: %{value:.2f} Hours<extra></extra>"
            )
            tree_map_chart.update_layout(
                title={'x': 0.5, 'xanchor': 'center'},
                legend=dict(
                    orientation='h',
                    yanchor='top',
                    y=-0.3,
                    xanchor='center',
                    x=0.5,
                    title=None
                )
            )
            st.plotly_chart(tree_map_chart, use_container_width=True)

        st.markdown("---")

        # Scatter and bar chart for resolution times
        resolution_data = time_data[['Resolution Time', 'Findings']].dropna()
        max_resolution_time = resolution_data.groupby('Findings')['Resolution Time'].max().reset_index()
        avg_resolution_time = resolution_data.groupby('Findings')['Resolution Time'].mean().reset_index()

        scatter_plot = go.Scatter(
            x=resolution_data['Findings'],
            y=resolution_data['Resolution Time'],
            mode='markers',
            name='Resolution Time',
            marker=dict(color='#0068c9', size=10)
        )

        bar_chart = go.Bar(
            x=max_resolution_time['Findings'],
            y=max_resolution_time['Resolution Time'],
            name='Max Resolution Time',
            marker=dict(color='#84c9ff', opacity=1)
        )

        avg_marker = go.Scatter(
            x=avg_resolution_time['Findings'],
            y=avg_resolution_time['Resolution Time'],
            mode='markers',
            name='Average Resolution Time',
            marker=dict(color='#ff2a2b', size=12, symbol='bowtie-open')
        )

        fig = go.Figure(data=[scatter_plot, bar_chart, avg_marker])
        fig.update_layout(
            title='RESOLUTION TIME (HOURS) BY FINDINGS',
            title_x=0.4,
            xaxis={'categoryorder': 'array', 'categoryarray': max_resolution_time['Findings'].tolist()},
            yaxis=dict(range=[0, 6450]),
            legend=dict(
                orientation='h',
                yanchor='top',
                y=-0.3,
                xanchor='center',
                x=0.5,
                title=None
            ),
            xaxis_title="Finding",
            yaxis_title="Resolution Time (Hours)"
        )
        st.plotly_chart(fig)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("---")

        # Box plot for resolution time distribution
        grouped_data = time_data.groupby(['Location', 'Leak Location'])['Resolution Time'].agg(
            count='size',
            mean='mean'
        ).reset_index()
        time_data_with_stats = time_data.merge(grouped_data, on=['Location', 'Leak Location'], how='left')

        box_plot_chart = px.box(
            time_data_with_stats,
            x='Location',
            y='Resolution Time',
            color='Leak Location',
            title='RESOLUTION TIME DISTRIBUTION BY LOCATION AND LEAK LOCATION',
            hover_data={
                'Location': True,
                'Leak Location': True,
                'Resolution Time': True,
                'count': True,
                'mean': True
            }
        )
        box_plot_chart.update_layout(
            title={'x': 0.5, 'xanchor': 'center'},
            legend=dict(
                orientation='h',
                yanchor='top',
                y=-0.3,
                xanchor='center',
                x=0.5,
                title=None
            )
        )
        st.plotly_chart(box_plot_chart)

    #---------------------------
    st.markdown("---")
    #---------------------------

    # AIRCRAFT REPORT SUMMARY SECTION -----
    with st.expander("AIRCRAFT REPORT SUMMARY"):

        # Calculate cumulative report count
        cumulative_report = reports_over_month.copy()
        cumulative_report['Cumulative Report Count'] = cumulative_report['Report Count'].cumsum()

        # Plot cumulative reports as an area chart
        area_chart = px.area(
            cumulative_report, 
            x='Month-Year', 
            y='Cumulative Report Count', 
            title='CUMULATIVE AIRCRAFT REPORTS'
        )
        area_chart.update_layout(
            title={'x': 0.5, 'xanchor': 'center'},  # Center title
            legend=dict(
                orientation='h',  
                yanchor='top',
                y=-0.3, 
                xanchor='center', 
                x=0.5,
                title=None
            )
        )
        st.plotly_chart(area_chart)

        st.markdown("<br>", unsafe_allow_html=True) 

        # Group data by 'Flight Airport Arrival' to get report counts
        airport_counts = (
            filtered_data.groupby('Flight Airport Arrival').size().reset_index(name='Report Count')
            .merge(
                filtered_data[['Flight Airport Arrival', 'latitude', 'longitude']].drop_duplicates(),
                on='Flight Airport Arrival', 
                how='left'
            )
        )

        # Data for the PyDeck chart
        deck_data = airport_counts[['latitude', 'longitude', 'Report Count', 'Flight Airport Arrival']]

        # PyDeck scatterplot layer
        deck = pdk.Deck(
            initial_view_state=pdk.ViewState(
                latitude=20.0, 
                longitude=0.0,
                zoom=3,
                pitch=60,  
                bearing=0  
            ),
            layers=[
                pdk.Layer(
                    "ScatterplotLayer",
                    deck_data,
                    get_position=["longitude", "latitude"],
                    get_radius="Report Count",
                    get_fill_color=[255, 0, 0, 140],  
                    radius_scale=10,
                    radius_min_pixels=5,
                    radius_max_pixels=50,
                    pickable=True,
                    auto_highlight=True,
                    get_elevation="Report Count",  
                    elevation_scale=50  
                )
            ],
            tooltip={"html": "<b>Airport:</b> {Flight Airport Arrival} <br><b>Reports:</b> {Report Count}"}
        )

        st.markdown("---")
        # st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("<h3 style='text-align: center;'>AIRCRAFT REPORTS</h3>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Layout for side-by-side charts
        col1, col2 = st.columns([0.4, 0.6])

        # Sunburst Chart (Reports by Airport and Aircraft)
        with col1:
            sunburst_data = filtered_data[['Flight Airport Arrival', 'A/C REG']].dropna()
            sunburst_chart = px.sunburst(sunburst_data, path=['Flight Airport Arrival', 'A/C REG'], title='Reports by Airport and Aircraft')
            sunburst_chart.update_layout(title_text='', margin=dict(t=50, b=10, l=50, r=50))
            st.plotly_chart(sunburst_chart)

        # PyDeck Chart (Reports by Airport Location)
        with col2:
            st.pydeck_chart(deck)

        st.markdown("---")
        st.markdown("<br>", unsafe_allow_html=True)

        # Section: Reports by Airport and Aircraft
        col1, col2 = st.columns(2)

        # Bar Chart: Number of reports per aircraft
        with col1:
            report_counts = filtered_data.groupby('A/C REG').size().reset_index(name='Report Count')
            bar_chart = px.bar(report_counts, x='A/C REG', y='Report Count', title='Number of Reports per Aircraft'.upper())
            bar_chart.update_layout(title={'x': 0.5, 'xanchor': 'center'})
            st.plotly_chart(bar_chart)

        # Pie Chart: Proportion of reports per aircraft
        with col2:
            pie_chart = px.pie(report_counts, names='A/C REG', values='Report Count', title='Proportion of Reports per Aircraft'.upper())
            pie_chart.update_layout(
            margin=dict(t=100, b=50, l=50, r=50),  # Top, bottom, left, right margins
            title={'x': 0.05, 'xanchor': 'left'},
            legend=dict(orientation='v', x=1, y=0.5, yanchor='middle')  # Adjust legend position if needed
        )
            st.plotly_chart(pie_chart)

        # Add space between charts
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
