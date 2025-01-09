# EY DASHBOARD v1.0

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk


# Set Streamlit layout to wide mode
st.set_page_config(layout="wide")

# Load the data from the CSV file
data = pd.read_csv("master_dataset.csv", index_col=False)

# Convert 'Created Date' to datetime and strip time (keeping only the date)
data['Created Date'] = pd.to_datetime(data['Created Date'], errors='coerce').dt.date
data['Action Latest Signature Date'] = pd.to_datetime(data['Action Latest Signature Date'], errors='coerce').dt.date

# Check values
oldest_date = data['Created Date'].min()  # Oldest (earliest) date
recent_date = data['Created Date'].max()  # Most recent (latest) date

# Dashboard title
st.markdown("<h1 style='text-align: left;'>EY GALLEY WATER LEAK DASHBOARD</h1>", unsafe_allow_html=True)
st.write("""
This dashboard provides an overview of water leak incidents, leak locations, findings, and the resolution process.
It helps to identify trends over time, root causes, and locations with higher leak 
incident frequencies. By analyzing this data, operational improvements and corrective actions can be identified to reduce leak occurrences.
""")

st.markdown("<br>", unsafe_allow_html=True)

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

# Check if the start_date and end_date are set in session state, otherwise use default values
if 'start_date' not in st.session_state:
    st.session_state['start_date'] = data['Created Date'].min()
if 'end_date' not in st.session_state:
    st.session_state['end_date'] = data['Created Date'].max()

start_date = st.sidebar.date_input('Start date', min_value=data['Created Date'].min(),
                                  max_value=data['Created Date'].max(), value=st.session_state['start_date'])
end_date = st.sidebar.date_input('End date', min_value=data['Created Date'].min(),
                                max_value=data['Created Date'].max(), value=st.session_state['end_date'])

# Add a reset button for the date range filter
reset_date_button = st.sidebar.button("Reset Date Range")

# If the "Reset Date Range" button is clicked, reset the date range to default
if reset_date_button:
    st.session_state['start_date'] = oldest_date
    st.session_state['end_date'] = recent_date
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
st.write("### Tabulated Data")
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

# Analysis Sections
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

# SECTION ------
with st.expander("GALLEYS AND LEAK LOCATION ANALYSIS"):
    # Location-Specific Issues
    # st.write("### LOCATION-SPECIFIC ISSUES")

    # Create a two-column layout
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
                y=1
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
        st.plotly_chart(pie_chart_leak_location)

    # Group by location and leak location
    location_leak_counts = filtered_data.groupby(['Location', 'Leak Location']).size().reset_index(name='Leak Count')


    st.markdown("<br>", unsafe_allow_html=True)

    # Create a side-by-side bar chart
    location_leak_chart = px.bar(location_leak_counts, 
                                x='Location', 
                                y='Leak Count', 
                                color='Leak Location', 
                                title='Location - Specific Leak Issues',
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

#---------------------------
st.markdown("---")
#---------------------------

# SECTION -----
with st.expander("FREQUENCY OF OCCURRENCES"):
    # Frequency of Occurrences (Leaks over time)
    # st.write("### FREQUENCY OF OCCURRENCES")
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
        findings_options = ['All'] + list(data['Findings'].unique())
        default_index = findings_options.index('Nil Leak') if 'Nil Leak' in findings_options else 0
        selected_finding = st.selectbox('SELECT FINDING', findings_options, index=default_index)

        # Filter data based on the selected finding
        filtered_data = data if selected_finding == 'All' else data[data['Findings'] == selected_finding].copy()

        # Calculate the maximum reccurrence count for the finding
        max_reccurrence_finding = filtered_data['Cumulative Reccurrence Count'].max()

        # Calculate the maximum recurrence per aircraft and for the selected finding
        aircraft_max_reccurrence = filtered_data.groupby('A/C REG')['Reccurrence Count'].max().reset_index()
        aircraft_max_reccurrence = aircraft_max_reccurrence.rename(columns={'Reccurrence Count': 'Max Reccurrence'})

        # Merge max recurrence back to the filtered data and sort by 'Created Date'
        filtered_data = filtered_data.merge(aircraft_max_reccurrence, on='A/C REG', how='left')
        filtered_data = filtered_data.sort_values(by='Created Date', ascending=True)

        # Find the first occurrence of the selected finding
        first_occurrence = filtered_data.iloc[0]

        st.write("### Recurrence per Aircraft")
        st.dataframe(aircraft_max_reccurrence, hide_index=True, use_container_width=True)

    with col2:
        # Plot the recurrence over time using the Recurrence Count
        reccurrence_chart = px.line(filtered_data, x='Created Date', y='Reccurrence Count', 
                                    color='A/C REG', 
                                    title=f'Recurrence of {selected_finding} Over Time (Recurrence: {max_reccurrence_finding} Instances)')
        # reccurrence_chart.update_layout(
        #     title='<b>RECURRENCE OF <span style="color:#FF3333;">{}</span> OVER TIME</b>'.format(selected_finding.upper()),
        #     title_x=0.35,  # This centers the title
        #     height=600 
        # )
        reccurrence_chart.update_traces(mode='lines+markers', marker=dict(size=6))
        reccurrence_chart.add_scatter(
            x=[first_occurrence['Created Date']], 
            y=[first_occurrence['Reccurrence Count']], 
            mode='markers+text', 
            textposition='top center',
            marker=dict(color=reccurrence_chart['data'][0]['line']['color'], size=10, symbol='bowtie'),
            name='First Occurrence'
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

        st.plotly_chart(reccurrence_chart)


    # Calculate the recurrence data for the entire dataset
    data = data.sort_values(by=['A/C REG', 'Findings', 'Created Date'])
    data['Reccurrence Count'] = data.groupby(['A/C REG', 'Findings']).cumcount() - 1
    data['Cumulative Reccurrence Count'] = data.groupby('Findings').cumcount() - 1
    

    # Store this reoccurrence data in an independent DataFrame
    reccurrence_dataset = data[['A/C REG', 'Findings', 'Leak Location', 'Created Date', 'Reccurrence Count', 'Cumulative Reccurrence Count']].copy()
    
    # Store the final filtered data in a variable for further use
    recurrence_filtered_data = filtered_data.copy()

    # Independent Recurrence Data
    # st.write("### Full Recurrence Data (Independent)")
    st.dataframe(reccurrence_dataset, hide_index=True, use_container_width=True)

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

# SECTION -----
with st.expander("REPORT TO RESOLUTION TIME"):

    # Add space between charts
    st.markdown("<br>", unsafe_allow_html=True) 

    # Time Between Reporting and Resolution
    st.markdown("<h3 style='text-align: center;'>TIME FROM REPORTING TO RESOLUTION</h3>", unsafe_allow_html=True)

    # Load the data from the CSV file
    time_data = pd.read_csv("resolved_issues_data.csv")

    # Calculate time difference in hours (assuming 'Resolution Time' is in hours)
    time_data['Resolution Time (hours)'] = time_data['Resolution Time'].round(2)

    # Group data by Findings and calculate the fastest (min) and slowest (max) resolution times
    fastest_and_slowest = time_data.groupby('Findings').agg(
        fastest_resolution_time=('Resolution Time (hours)', 'min'),
        slowest_resolution_time=('Resolution Time (hours)', 'max')
    ).reset_index()
    
    # Group data by Findings and calculate the average resolution time (hours)
    findings_avg_resolution = time_data.groupby('Findings').agg({'Resolution Time (hours)': 'mean'}).reset_index()

    # Group by Leak Location and Findings to calculate the average resolution time
    metrics_data = time_data.groupby(['Leak Location', 'Findings']).agg(
        avg_resolution_time=('Resolution Time', 'mean')
    ).reset_index()

    # Round the average resolution time for display
    metrics_data['avg_resolution_time'] = metrics_data['avg_resolution_time'].round(2)

    # Create the Sunburst chart in the first column
    col1, col2 = st.columns([0.3, 0.7])  # Create two columns for side-by-side layout

    with col1:
        # Create Sunburst Chart with Location added to the path hierarchy
        sunburst_chart = px.sunburst(time_data, 
                                    path=['Findings', 'Leak Location', 'Location'],  # Added Location to the path
                                    title='FINDINGS BREAKDOWN',
                                    values='Resolution Time',  # Use resolution time as the values
                                    # color='Resolution Time',  # Use resolution time for color
                                    # color_continuous_scale='Viridis'  # Set continuous color scale
                                    )

        # Simplify the hovertemplate for Sunburst Chart
        sunburst_chart.update_traces(
            hovertemplate="<b>%{label}</b><br>Avg Resolution Time: %{value:.2f} Hours<extra></extra>"
        )

        # Update layout and remove the legend
        sunburst_chart.update_layout(
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


        # Display the Sunburst chart
        st.plotly_chart(sunburst_chart, use_container_width=True)

    # Create the Tree Map in the second column
    with col2:
        # Create Tree Map
        tree_map_chart = px.treemap(metrics_data, 
                                    path=['Leak Location', 'Findings'],  # Removed Location here
                                    values='avg_resolution_time', 
                                    title='LOCATION BREAKDOWN',
                                    # color='avg_resolution_time',  # Use average resolution time for color
                                    # color_continuous_scale='Viridis'  # Set continuous color scale
                                    )
        tree_map_chart.update_layout(
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
        # Simplify the hovertemplate for Tree Map
        tree_map_chart.update_traces(
            hovertemplate="<b>%{label}</b><br>Avg Resolution Time: %{value:.2f} Hours<extra></extra>"
        )

        # Display the Tree Map
        st.plotly_chart(tree_map_chart, use_container_width=True)

    # Sort the data by 'Resolution Time (hours)' in descending order
    findings_avg_resolution_sorted = findings_avg_resolution.sort_values(by='Resolution Time (hours)', ascending=False)


    # Filter the dataset to get the relevant columns
    # Assuming 'Resolution Time (hours)' and 'Findings' are present in the dataset
    resolution_data = time_data[['Resolution Time (hours)', 'Findings']]

    # Ensure there are no missing values
    resolution_data = resolution_data.dropna(subset=['Resolution Time (hours)', 'Findings'])

    # Calculate maximum resolution time for each Finding
    max_resolution_time = resolution_data.groupby('Findings')['Resolution Time (hours)'].max().reset_index()

    # Calculate average resolution time for each Finding
    avg_resolution_time = resolution_data.groupby('Findings')['Resolution Time (hours)'].mean().reset_index()

    # Sort the data in descending order
    max_resolution_time = max_resolution_time.sort_values(by='Resolution Time (hours)', ascending=False)
    avg_resolution_time = avg_resolution_time.sort_values(by='Resolution Time (hours)', ascending=False)
    resolution_data = resolution_data.sort_values(by='Resolution Time (hours)', ascending=False)

    # Create a scatter plot showing the resolution time for each finding
    scatter_plot = go.Scatter(
        x=resolution_data['Findings'],
        y=resolution_data['Resolution Time (hours)'],
        mode='markers',
        name='Resolution Time',
        marker=dict(color='#0068c9', size=10)
    )

    # Bar chart for the maximum resolution time
    bar_chart = go.Bar(
        x=max_resolution_time['Findings'],
        y=max_resolution_time['Resolution Time (hours)'],
        name='Max Resolution Time',
        marker=dict(color='#84c9ff', opacity=1)
    )

    # Markers for the average resolution time
    avg_marker = go.Scatter(
        x=avg_resolution_time['Findings'],
        y=avg_resolution_time['Resolution Time (hours)'],
        mode='markers',
        name='Average Resolution Time',
        marker=dict(color='#ff2a2b', size=12, symbol='bowtie-open', 
                    # line=dict(color='green', width=2)
                    )
    )

    # Combined figure with scatter plot, bar chart, and average markers
    fig = go.Figure(data=[scatter_plot, bar_chart, avg_marker])

    # Update the layout
    fig.update_layout(
        title='RESOLUTION TIME BY FINDINGS',
        title_x=0.4,  # Center title
        xaxis={'categoryorder': 'array', 'categoryarray': max_resolution_time['Findings'].tolist()},  # Sort the x-axis in descending order
        yaxis=dict(
            range=[0, 6450],  # Set the minimum and maximum values for the y-axis
        ),
        legend=dict(
            orientation='h',  # Horizontal legend
            yanchor='top',  # Position the legend at the bottom
            y=-0.3,  # Adjust the vertical position (below the chart)
            xanchor='center',  # Center the legend horizontally
            x=0.5,  # Center the legend horizontally
            title=None
        ),
        xaxis_title="Finding",  # Label for x-axis
        yaxis_title="Resolution Time (hours)"  # Label for y-axis
    )

    # Display the combined chart
    st.plotly_chart(fig)

    # Add space between charts
    st.markdown("<br>", unsafe_allow_html=True) 


    # Group by Location and Leak Location to calculate count and mean resolution time
    grouped_data = time_data.groupby(['Location', 'Leak Location'])['Resolution Time (hours)'].agg(
        count='size',
        mean='mean'
    ).reset_index()

    # Merge the calculated values back to the original dataset
    time_data_with_stats = time_data.merge(grouped_data, on=['Location', 'Leak Location'], how='left')

    # Create the box plot with custom hover data
    box_plot_chart = px.box(time_data_with_stats, 
                            x='Location', 
                            y='Resolution Time (hours)', 
                            color='Leak Location', 
                            title='Resolution Time Distribution by Location and Leak Location'.upper(),
                            hover_data={
                                'Location': True,  # Show Location on hover
                                'Leak Location': True,  # Show Leak Location on hover
                                'Resolution Time (hours)': True,  # Show Resolution Time (hours)
                                'count': True,  # Show count of records for each group
                                'mean': True  # Show mean resolution time for each group
                            })

    # Customize chart layout
    box_plot_chart.update_layout(
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
    # Display the box plot
    st.plotly_chart(box_plot_chart)


#---------------------------
st.markdown("---")
#---------------------------

# SECTION -----
with st.expander("AIRCRAFT REPORT SUMMARY"):

    cumulative_report = reports_over_month.copy()
    cumulative_report['Cumulative Report Count'] = cumulative_report['Report Count'].cumsum()

    area_chart = px.area(cumulative_report, x='Month-Year', y='Cumulative Report Count', title='CUMULATIVE AIRCRAFT REPORTS')
    area_chart.update_layout(
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

    st.plotly_chart(area_chart)

    st.markdown("<br>", unsafe_allow_html=True) 
    
    # Airport code to get report counts
    airport_counts = filtered_data.groupby('Flight Airport Arrival').size().reset_index(name='Report Count')

    # Airport counts with latitude and longitude
    airport_counts = airport_counts.merge(filtered_data[['Flight Airport Arrival', 'latitude', 'longitude']].drop_duplicates(),
                                        left_on='Flight Airport Arrival', right_on='Flight Airport Arrival', how='left')

    # Prepare data for the PyDeck chart
    deck_data = airport_counts[['latitude', 'longitude', 'Report Count', 'Flight Airport Arrival']]

    # 3D PyDeck map with a scatterplot layer
    deck = pdk.Deck(
        initial_view_state=pdk.ViewState(
            latitude=20.0,  # Centering on the globe (you can adjust the zoom)
            longitude=0.0,
            zoom=1,
            pitch=60,  # Adjust the pitch for a better 3D view
            bearing=0  # The rotation angle of the map
        ),
        layers=[
            pdk.Layer(
                "ScatterplotLayer",
                deck_data,
                get_position=["longitude", "latitude"],
                get_radius="Report Count",
                get_fill_color=[255, 0, 0, 140],  # Red color with transparency
                radius_scale=10,
                radius_min_pixels=5,
                radius_max_pixels=50,
                pickable=True,
                auto_highlight=True,
                get_elevation="Report Count",  # Use Report Count as the elevation (3D effect)
                elevation_scale=50  # Adjust the scale of elevation
            )
        ],
        tooltip={"html": "<b>Airport:</b> {Flight Airport Arrival} <br><b>Reports:</b> {Report Count}"}
    )

    st.markdown("<h3 style='text-align: center;'>AIRCRAFT REPORTS</h3>", unsafe_allow_html=True)
    # Creating a layout for multiple sections (side-by-side charts)
    col1, col2 = st.columns([0.4,0.6])

    # Sunburst Chart (Reports by Airport and Aircraft)
    with col1:

        # Check if there are any missing values in the columns used for the Sunburst path
        sunburst_data = filtered_data[['Flight Airport Arrival', 'A/C REG']].dropna()

        # Create the Sunburst chart (without 'Findings')
        sunburst_chart = px.sunburst(sunburst_data, path=['Flight Airport Arrival', 'A/C REG'], 
                                    title='Reports by Airport and Aircraft')
        sunburst_chart.update_layout(title_text='')

        # Display the Sunburst chart
        st.plotly_chart(sunburst_chart)

    # PyDeck Chart (Reports by Airport Location)
    with col2:
        st.pydeck_chart(deck)


    #---------------------------
    st.markdown("---")
    #---------------------------



    #---------------------------
    st.markdown("---")
    #---------------------------

    # Section: Reports by Airport and Aircraft
 
    col1, col2 = st.columns(2)

    # Card 1: Number of reports per aircraft
    with col1:
        report_counts = filtered_data.groupby('A/C REG').size().reset_index(name='Report Count')
        bar_chart = px.bar(report_counts, x='A/C REG', y='Report Count', title='Number of Reports per Aircraft'.upper())
        bar_chart.update_layout(
            title={'x': 0.5, 'xanchor': 'center'}  # This centers the title
        )
        st.plotly_chart(bar_chart)

    # Card 2: Proportion of reports per aircraft
    with col2:
        pie_chart = px.pie(report_counts, names='A/C REG', values='Report Count', title='Proportion of Reports per Aircraft'.upper())
        st.plotly_chart(pie_chart)


    # Add space between charts
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True) 

    # ------------
    # SECTION
    # Area Chart (Cumulative Reports Over Month)
    # st.markdown("<h3 style='text-align: center;'>CUMULATIVE REPORTS</h3>", unsafe_allow_html=True)
