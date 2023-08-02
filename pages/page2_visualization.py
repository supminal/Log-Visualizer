from dash import html, dcc, callback, dash_table, Output, Input, State
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import dash
import re
from datetime import datetime
from datetime import date
import threading
from ip2geotools.databases.noncommercial import DbIpCity



dash.register_page(__name__)

#Parsing Data from Log files
def sof():
    data = []
    with open('../Dash_tut/log_samples', 'r') as file:
        logs = file.readlines()

    logs = [i.strip() for i in logs]
    # this parses the log can be changed based on the format of log
    regex = '([(\d\.)]+) - - \[(.*?)\] "(.*\s)(/.*\s)(.*?)" (\d+) (\d+) "(.*?)" "(.*?)" "(.*?)"'
    for i in logs:
        #print(i)
        x = re.match(regex, i).groups()
        #print(x)
        data.append(x)
    return data


def layout():
    global df
    data = sof()
    df = pd.DataFrame(data, columns=['UserIP', 'Time', 'Request_Type','File_Req','Protcol','Status code', 'Size', 'Unknown1',
                                     'User_Agent', 'unknown2'])
    df['Time'] = df['Time'].apply(lambda x: datetime.strptime(x, '%d/%b/%Y:%H:%M:%S %z'))
    df['Time'] = df['Time'].dt.tz_localize(None)
    a = df['User_Agent']
    b = []
    for i in range(len(a)):
        # print(a[i])
        try:
            x = re.search('(Android|Windows|Macintosh|iPhone|X11)', a[i]).groups()
            b.append(x[0])
        except AttributeError:
            b.append('-')
    # Android, Windows, Macintosh, iPhone, X11
    b = pd.Series(b)
    df['Device'] = b

    layout = html.Div(children= [
        html.H1(children='Log Visualizer', style={'textAlign': 'center'}),
        html.Br(),
    dbc.Container([ dbc.Row ([ dbc.Col( [html.H3("Parsed Data sample", style={"text-align": "center"})] ) ] ),
            dcc.Download(id="download"),
            dbc.Row([dbc.Col([ dash_table.DataTable( df[:10].to_dict("records"), [{"name": i, "id": i} for i in df.columns], page_size=10,
                                                     style_table={"overflowX": "auto"},)] )]) ,
            dbc.Row([dbc.Col([ dcc.Dropdown( options=[
                                    {"label": "Excel file", "value": "excel"},
                                    {"label": "CSV file", "value": "csv"},
                                ],
                                id="dropdown",
                                placeholder="Choose download file type. Default is CSV format!",
                            )]),
                    dbc.Col([ dbc.Button(  "Download Data", id="btn_csv"),] ),
                    ]), ]),
    dcc.DatePickerRange(
            id='my-date-picker-range',
            min_date_allowed=df['Time'].min().strftime('%Y-%m-%d'),
            max_date_allowed=df['Time'].max().strftime('%Y-%m-%d'),
            start_date=date(df['Time'].min().year,df['Time'].min().month, df['Time'].min().day),
            end_date=date(df['Time'].max().year,df['Time'].max().month, df['Time'].max().day)
        ),
       # Android, Windows, Macintosh, iPhone, X11
        dbc.Row([dbc.Col([dcc.Dropdown(options=[
            {"label": "All", "value": "All"},
            {"label": "Windows", "value": "Windows"},
            {"label": "Android", "value": "Android"},
            {"label": "Macintosh", "value": "Macintosh"},
            {"label": "iPhone", "value": "iPhone"},
            {"label": "X11", "value": "X11"},
            {"label": "Others", "value": "-"}
        ],
            value = 'All',
            id="drop_down_device",
            placeholder="Choose device type. Default is Windows !",
        )]) ]),
       dcc.Graph(id ='pie-graph'),
        html.H6(children='Number of Requests per Hour'),
        dcc.Graph(id='peak-graph'),
        html.H6(children='IP Address Locations'),
        dcc.Graph(id='ip-locations'),
        dbc.Row([dbc.Col(
            [dash_table.DataTable(id='tbl', page_size=10,
                                  style_table={"overflowX": "auto"},style_cell={
        'height': 'auto',
        'minWidth': '180px', 'width': '180px', 'maxWidth': '180px',
        'whiteSpace': 'normal'
    } )])])
    ])
    return layout


@callback(
        Output("download", "data"),
        Input("btn_csv", "n_clicks"),
        State("dropdown", "value"),
        prevent_initial_call=True,
    )
def func(n_clicks_btn, download_type):
    if download_type == "csv":
        return dcc.send_data_frame(df.to_csv, "mydf.csv")
    else:
        return dcc.send_data_frame(df.to_excel, "mydf.xlsx")

@callback(
    Output('peak-graph', 'figure'),
    Input('my-date-picker-range', 'start_date'),
    Input('my-date-picker-range', 'end_date'))
def plot_peak_times(start_date, end_date):
    group_format = '%Y-%m-%d %H:00'
    timestamps = df['Time'].loc[df['Time'].between(start_date,end_date)]
    time_groups = {}
    for timestamp in timestamps:
        group_key = timestamp.strftime(group_format)
        time_groups[group_key] = time_groups.get(group_key, 0) + 1

    x = []
    y = []
    for group_key, count in sorted(time_groups.items()):
        x.append(datetime.strptime(group_key, group_format))
        y.append(count)
    return go.Figure(data=go.Scatter(x=x, y=y))

@callback(
    Output('pie-graph', 'figure'),
    Input('my-date-picker-range', 'start_date'),
    Input('my-date-picker-range', 'end_date'),
    Input("drop_down_device", "value"))
   # prevent_initial_call=True)
def status_pie(start_date, end_date, device):
    group_format = '%Y-%m-%d %H:00'
    status_in_timeperiod = df.loc[df['Time'].between(start_date,end_date)]
    if not device == 'All':
        status_in_timeperiod = status_in_timeperiod[status_in_timeperiod['Device']==device]
    status_in_timeperiod = status_in_timeperiod['Status code']
    return px.pie(status_in_timeperiod, names='Status code', hole=.3,title = 'Request Status')

@callback(
    Output('ip-locations', 'figure'),
    Input('my-date-picker-range', 'start_date'),
    Input('my-date-picker-range', 'end_date'))
def loc_ip(start_date, end_date):
    #group_format = '%Y-%m-%d %H:00'
    ip_addresses = df['UserIP'].loc[df['Time'].between(start_date,end_date)]
    ip_addresses = ip_addresses.unique()
    ip_addresses = ip_addresses[:40]

    def func_thread(n, out):
        out.append(DbIpCity.get(n, api_key="free"))

    locations = []
    l = len(ip_addresses)
    a = 0

    while a < l:
        thread_list = []
        if a + 15 > l:
            ips = ip_addresses[a:]
        else:
            ips = ip_addresses[a:a + 15]
        for x in range(len(ips)):
            # func_thread(ip_addresses[x], locations)
            thread = threading.Thread(target=func_thread, args=(ips[x], locations))
            thread_list.append(thread)
        for thread in thread_list:
            thread.start()
        for thread in thread_list:
            thread.join()
        a += 15

    print(locations, '\n', len(locations))

    lats = [loc.latitude for loc in locations if loc is not None]
    lons = [loc.longitude for loc in locations if loc is not None]
    name = [loc.city + ', ' + loc.region for loc in locations if loc is not None]
    print(len(lats), lons)
    geo_data = []
    for i in range(len(lats)):
        geo_data.append((lons[i], lats[i], str(name[i])))
    geo_df = pd.DataFrame(geo_data, columns=['x', 'y', 'name'])
    print(len(geo_df['x'].unique()))
    # Create a scatter mapbox trace
    fig = go.Figure(data=go.Scattergeo(
        lon=geo_df['x'],
        lat=geo_df['y'],
        # name = geo_df['name']
    ))
    return fig


@callback(
    Output('tbl', 'data'),
    Input('my-date-picker-range', 'start_date'),
    Input('my-date-picker-range', 'end_date'))
def file_requested(start_date,end_date):
    files_requested = df['File_Req'].loc[df['Time'].between(start_date, end_date)]
    a = files_requested.value_counts()
    b = a.index.tolist()
    new_d = []
    for i in range(len(b)):
        new_d.append((b[i], a[i]))
    dg = pd.DataFrame(new_d, columns=['Name of File Accessed', 'Count'])
    return dg.to_dict('records')
