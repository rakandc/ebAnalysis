import streamlit as st
import pandas as pd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import geodatasets
import geopandas
import plotly.graph_objects as go



from urllib.request import urlopen
import json

import datetime 
import copy 




allPlotlyFigs = []


allMatplotlibFigs = []

st.write(f"""# Battery Analysis
         
         Current as of {pd.Timestamp.now().date()}""")




def read_in_battery_report(filepath):
    sheet_names = {'Co-located with Solar':"solar",
 'Co-located with Wind':"wind",
 'Co-located with Thermal':"thermal",
 'Stand-Alone':"standalone",
#  'Co-located Operational':"operational",
 }
    
    
    sheet_list = []

    for sheet in sheet_names.keys():
        tempSheetRead = pd.read_excel(filepath,sheet_name=sheet,skiprows=13,header=1)
        tempSheetRead.rename(columns={'Unnamed: 12':'Financial Security and Notice to Proceed Provided'},inplace=True)
        tempSheetRead = tempSheetRead.drop(index=range(0, 5))
        tempSheetRead = tempSheetRead.assign(colocated=sheet_names[sheet])
        tempSheetRead['Projected COD'] = pd.to_datetime(tempSheetRead['Projected COD'])
        sheet_list.append(tempSheetRead)
    
    temp = pd.concat(sheet_list)

    
    operationaldf = pd.read_excel(filepath,sheet_name='Co-located Operational',header=13)

    operationaldf.dropna(inplace=True,how='all')
    operationaldf['Capacity (MW)*'].replace(0,np.nan,inplace=True)
    operationaldf['In Service'] = pd.to_datetime(operationaldf['In Service'],format='%Y')
    # operationaldf['In Service'] = operationaldf['In Service'].dt.year
    operationaldf = operationaldf.iloc[:-1]
    return temp, operationaldf.reset_index(drop=True)


filename = './resources/RPT.00015933.0000000000000000.20240810.080547317.Co-located_Battery_Identification_Report_July_2024 (1).xlsx'
planned, operational = read_in_battery_report(filename)
#
operational_cumsum = operational.groupby(by=['In Service','Fuel'])['Capacity (MW)*'].sum().unstack().fillna(0).cumsum(axis=0).resample('Y').ffill().reset_index()




# plt1 = plt.figure(figsize=(15,7))
# sns.scatterplot(data=planned.loc[planned['Fuel']=='OTH'], x='Projected COD',y='Capacity (MW)',s=70,hue='colocated',alpha=0.7,palette=sns.color_palette("husl", 4))
# plt.title('Projected Commercial Operations Date vs Capacity (MW) for Co-located Batteries',fontsize=20)

# st.pyplot(plt1)



def plot_by_finance(kf,tohtml=False):
    fig = px.scatter(data_frame=kf.loc[kf['Fuel']=='OTH'], x='Projected COD',y='Capacity (MW)',color='Financial Security and Notice to Proceed Provided',custom_data=['Project Name','Financial Security and Notice to Proceed Provided','Interconnecting Entity'])
    fig.update_layout(title='Projected Commercial Operations Date vs Capacity (MW) for Co-located Batteries',legend_title='Finance and Notice Provided',xaxis_title='Projected Commercial Operations Date',yaxis_title='Capacity (MW)')
    fig.update_traces(
        hovertemplate="<br>".join([
            "Project Name: %{customdata[0]}",
            "Interconnecting Entity: %{customdata[2]}",
            "Projected Commerical Operations Date: %{x}",
            "Capacity (MW): %{y}",
            "Financial Security and<br> Notice to Proceed Provided: %{customdata[1]}",
        ]),marker=dict(size=10),opacity=0.7)


    allMatplotlibFigs.append(copy.deepcopy(plt.gcf()))

    if tohtml:
        fig.write_html('battery_report.html')
        return
    st.plotly_chart(fig)

plot_by_finance(planned)



fig = px.area(operational_cumsum,
              x='In Service',
              y=['GAS','OTH','SOL','WIN'],
              labels={'value':'Capacity (MW)','variable':'Fuel Type'},
              title='Total operational Capacity (MW) over Time by Fuel Type')



fig.update_layout(
    xaxis=dict(rangeslider=dict(visible=True),dtick="M12"),
    title='Total operational Capacity (MW) over Time by Fuel Type',
    hovermode='x unified',
)
st.plotly_chart(fig)







startYear = 2000
fig=px.bar(operational_cumsum.loc[operational_cumsum['In Service']> datetime.datetime(startYear,1,1)],x='In Service',y=['GAS','OTH','SOL','WIN'],title='Operational Cumulative Capacity (MW) by Fuel Type and Year')
fig.update_xaxes(rangeslider=dict(visible=True),dtick="M12",title='Year')

fig.update_yaxes(title='Cumulative Capacity (MW)')
fig.update_yaxes(title='Cumulative Capacity (MW)', tickformat="d")
fig.update_traces(hovertemplate="<br>".join([
    "Year: %{x}",
    "Capacity (MW): %{y}",
]))

st.plotly_chart(fig)











yearToUse = 2000

fipsdf = pd.read_csv('./resources/state_and_county_fips_master.csv')
dfWithFips = planned.merge(fipsdf.loc[fipsdf['state']=='TX'][['name', 'fips']], left_on='County', right_on='name', how='left')
dfWithFips.drop(columns='name', inplace=True)
fipValues = dfWithFips.loc[dfWithFips['Projected COD'].dt.year>yearToUse].groupby(by=['fips','County'])['Capacity (MW)'].sum().reset_index()
txFipsList = fipsdf.loc[fipsdf['state']=="TX"]
fipValues = dfWithFips.loc[dfWithFips['Projected COD'].dt.year < yearToUse].groupby(by=['fips','County'])['Capacity (MW)'].sum().reset_index()
txFipsList = dfWithFips[['fips']].drop_duplicates()  # Assuming you have a list of TX FIPS codes
# txFipsList.merge(fipValues, on='fips', how='left').fillna(0)


with urlopen('https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json') as response:
    counties = json.load(response)

colorMap = ['rgb(255, 255, 255)',
 'rgb(62, 82, 143)',
 'rgb(64, 60, 115)',
 'rgb(59, 48, 93)',
 'rgb(54, 43, 77)',
 'rgb(39, 26, 44)']

fig = go.Figure()

colorscale = [
[0, 'rgb(38, 53, 113)'], 
[0.5, 'rgb(57, 162, 225)'],
[1, 'rgb(234, 32, 41)']
]
counties['features'] = [i for i in counties['features'] if i['properties']['STATE']=="48"]




def create_choropleth(yearToUse):
    fipValues = dfWithFips.loc[dfWithFips['Projected COD'].dt.year < yearToUse].groupby(by=['fips'])['Capacity (MW)'].sum().reset_index()
    txFipsList = fipsdf.loc[fipsdf['state']=="TX"]
    # txFipsList.merge(fipValues, on='fips', how='left').drop(columns='County').fillna(0)


    # txFipsList = dfWithFips[['fips']].drop_duplicates()  # Assuming you have a list of TX FIPS codes
    merged_df = txFipsList.merge(fipValues, on='fips', how='left').fillna(0)
    
    fig = px.choropleth(merged_df,
                        geojson=counties,
                        locations='fips',
                        color='Capacity (MW)',
                        color_continuous_scale=colorMap,
                        range_color=(0,10000),
                        scope="usa",
                        hover_name='name',
                        labels={'fips': 'County Fip Code'}
                       )
    fig.update_geos(fitbounds="geojson")
    fig.update_layout(title="Currently Planned Battery Capacity Expansion by County")
    return fig



minYear = int(dfWithFips['Projected COD'].dt.year.min())
maxYear = int(dfWithFips['Projected COD'].dt.year.max() + 1)

fig = create_choropleth(minYear)

# Add slider
steps = []
for year in range(minYear, maxYear):
    step = {
        'args': [[year], {'frame': {'duration': 300, 'redraw': True}, 'mode': 'immediate'}],
        'label': str(year),
        'method': 'animate'
    }
    steps.append(step)

sliders = [dict(
    active=0,
    currentvalue={"prefix": "Projected COD up to: "},
    pad={"t": 50},
    steps=steps
)]

fig.update_layout(sliders=sliders)

# Create frames for each year
frames = []
for year in range(minYear, maxYear):
    frame = go.Frame(
        data=create_choropleth(year).data,
        name=str(year)
    )
    frames.append(frame)

fig.frames = frames


# Show the figure
# pyo.plot(fig, filename='plotly_figure_new.html')
st.plotly_chart(fig)
# Show the figure




combined = (pd.concat([planned
                      .rename(columns={'Projected COD' : "Date"
                          
                      }), 
                      operational.rename(columns={'In Service' : "Date", 
                                                  'Unit Name':'Project Name',
                                                  'Capacity (MW)*':'Capacity (MW)'})])
                    #  .drop(columns=['Fuel','County','Interconnecting Entity','Financial Security and Notice to Proceed Provided','colocated']
                    .reset_index(drop=True))

combined['Project Status'] = combined['Project Status'].fillna('Operational')
combined['Date']= pd.to_datetime(combined['Date'])














yearToUse = 2020

fipsdf = pd.read_csv('./resources/state_and_county_fips_master.csv')
dfWithFips = combined.merge(fipsdf.loc[fipsdf['state']=='TX'][['name', 'fips']], left_on='County', right_on='name', how='left')
dfWithFips.drop(columns='name', inplace=True)
fipValues = dfWithFips.loc[dfWithFips['Date'].dt.year>yearToUse].groupby(by=['fips','County'])['Capacity (MW)'].sum().reset_index()
txFipsList = fipsdf.loc[fipsdf['state']=="TX"]
fipValues = dfWithFips.loc[dfWithFips['Date'].dt.year < yearToUse].groupby(by=['fips','County'])['Capacity (MW)'].sum().reset_index()
txFipsList = dfWithFips[['fips']].drop_duplicates()  # Assuming you have a list of TX FIPS codes
# txFipsList.merge(fipValues, on='fips', how='left').fillna(0)


with urlopen('https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json') as response:
    counties = json.load(response)

colorMap = ['rgb(255, 255, 255)',
 'rgb(62, 82, 143)',
 'rgb(64, 60, 115)',
 'rgb(59, 48, 93)',
 'rgb(54, 43, 77)',
 'rgb(39, 26, 44)']

fig = go.Figure()

colorscale = [
[0, 'rgb(38, 53, 113)'], 
[0.5, 'rgb(57, 162, 225)'],
[1, 'rgb(234, 32, 41)']
]
counties['features'] = [i for i in counties['features'] if i['properties']['STATE']=="48"]




def create_choropleth(yearToUse):
    fipValues = dfWithFips.loc[dfWithFips['Date'].dt.year < yearToUse].groupby(by=['fips'])['Capacity (MW)'].sum().reset_index()
    txFipsList = fipsdf.loc[fipsdf['state']=="TX"]
    # txFipsList.merge(fipValues, on='fips', how='left').drop(columns='County').fillna(0)


    # txFipsList = dfWithFips[['fips']].drop_duplicates()  # Assuming you have a list of TX FIPS codes
    merged_df = txFipsList.merge(fipValues, on='fips', how='left').fillna(0)
    
    fig = px.choropleth(merged_df,
                        geojson=counties,
                        locations='fips',
                        color='Capacity (MW)',
                        color_continuous_scale=colorMap,
                        range_color=(0,10000),
                        scope="usa",
                        hover_name='name',
                        labels={'fips': 'County Fip Code'}
                       )
    fig.update_geos(fitbounds="geojson")
    fig.update_layout(title="Existing and Planned Battery Capacity Expansion by County")
    return fig



minYear = int(dfWithFips['Date'].dt.year.min())
maxYear = int(dfWithFips['Date'].dt.year.max() + 1)

fig = create_choropleth(minYear)

# Add slider
steps = []
for year in range(yearToUse, maxYear):
    step = {
        'args': [[year], {'frame': {'duration': 300, 'redraw': True}, 'mode': 'immediate'}],
        'label': str(year),
        'method': 'animate'
    }
    steps.append(step)

sliders = [dict(
    active=0,
    currentvalue={"prefix": "Date up to: "},
    pad={"t": 50},
    steps=steps
)]

fig.update_layout(sliders=sliders)

# Create frames for each year
frames = []
for year in range(minYear, maxYear):
    frame = go.Frame(
        data=create_choropleth(year).data,
        name=str(year)
    )
    frames.append(frame)

fig.frames = frames


# Show the figure
# pyo.plot(fig, filename='plotly_figure_new.html')
st.plotly_chart(fig)


# Show the figure






startYear = 2000
fig=px.bar(operational_cumsum.loc[operational_cumsum['In Service']> datetime.datetime(startYear,1,1)],x='In Service',y=['GAS','OTH','SOL','WIN'],title='Operational Cumulative Capacity (MW) by Fuel Type and Year')
fig.update_xaxes(rangeslider=dict(visible=True),dtick="M12",title='Year')

fig.update_yaxes(title='Cumulative Capacity (MW)')
fig.update_yaxes(title='Cumulative Capacity (MW)', tickformat="d")
fig.update_traces(hovertemplate="<br>".join([
    "Year: %{x}",
    "Capacity (MW): %{y}",
]))
st.plotly_chart(fig)



combined_cumsum = combined.groupby(by=['Date','Fuel'])['Capacity (MW)'].sum().unstack().fillna(0).cumsum(axis=0).resample('Y').ffill().reset_index()


startYear = 2000
fig=px.bar(combined_cumsum.loc[combined_cumsum['Date']> datetime.datetime(startYear,1,1)],x='Date',y=['GAS','OTH','SOL','WIN'],title='Operational and planned Cumulative Capacity (MW) by Fuel Type and Year')
fig.update_xaxes(rangeslider=dict(visible=True),dtick="M12",title='Year')

# fig.update_yaxes(type='log', title='Cumulative Capacity (MW)')
fig.update_yaxes(title='Cumulative Capacity (MW)', tickformat="d")
fig.update_traces(hovertemplate="<br>".join([
    "Year: %{x}",
    "Capacity (MW): %{y}",
]))


st.plotly_chart(fig)




startYear = 2000
fig=px.bar(combined_cumsum.loc[combined_cumsum['Date']> datetime.datetime(startYear,1,1)],x='Date',y=['GAS','OTH','SOL','WIN'],title='Operational and planned Cumulative Capacity (MW) by Fuel Type and Year LOG SCALE')
fig.update_xaxes(rangeslider=dict(visible=True),dtick="M12",title='Year')

fig.update_yaxes(type='log', title='Cumulative Capacity (MW)')
fig.update_yaxes(type='log', title='Cumulative Capacity (MW)', tickformat="d")
fig.update_traces(hovertemplate="<br>".join([
    "Year: %{x}",
    "Capacity (MW): %{y}",
]))


st.plotly_chart(fig)






startYear = 2000
fig=px.bar(combined_cumsum.loc[combined_cumsum['Date']> datetime.datetime(startYear,1,1)],x='Date',y=['GAS','OTH','SOL','WIN'],title='Operational and planned Cumulative Capacity (MW) by Fuel Type and Year')
fig.update_xaxes(rangeslider=dict(visible=True),dtick="M12",title='Year')

# fig.update_yaxes(type='log', title='Cumulative Capacity (MW)')
fig.update_yaxes(title='Cumulative Capacity (MW)', tickformat="d")
fig.update_traces(hovertemplate="<br>".join([
    "Year: %{x}",
    "Capacity (MW): %{y}",
]))


st.plotly_chart(fig)







fig = px.scatter(data_frame=combined.loc[combined['Fuel']=='OTH'], x='Date',y='Capacity (MW)',color='Project Status',custom_data=['Project Name','Project Status','Interconnecting Entity'])
fig.update_layout(title='Projected Commercial Operations Date vs Capacity (MW) for Co-located Batteries',legend_title='Finance and Notice Provided',xaxis_title='Projected Commercial Operations Date',yaxis_title='Capacity (MW)')
fig.update_traces(
    hovertemplate="<br>".join([
        "Project Name: %{customdata[0]}",
        "Interconnecting Entity: %{customdata[2]}",
        "Projected Commerical Operations Date: %{x}",
        "Capacity (MW): %{y}",
        "Financial Security and<br> Notice to Proceed Provided: %{customdata[1]}",
    ]),marker=dict(size=10),opacity=0.7)


st.plotly_chart(fig)




