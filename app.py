import base64
import io
import pandas as pd

import dash
from dash import dcc, html, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import re

# Import our custom data parser
from data_parser import load_and_validate_data

# --- Your Mapbox Access Token ---
mapbox_access_token = "pk.eyJ1IjoicXlyb3dyZW4iLCJhIjoiY21mcGg4cjVpMGY1dTJrcjRuYmo1YWl3ZCJ9.YlqTfqH9P954mOz6C1lLDA"

# --- App Initialization ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server

# --- Reusable Components ---
def card(children, **kwargs):
    return dbc.Card(dbc.CardBody(children), **kwargs)

# --- App Layout ---
app.layout = dbc.Container(fluid=True, children=[
    dcc.Store(id='dataframe-store'),
    html.H1("Aerospace Flight Data Analyzer", className="text-center my-4 text-primary"),
    dbc.Row([
        # Left Column: Control Panel
        dbc.Col(width=4, children=[
            card([
                html.H4("Control Panel", className="card-title"),
                dcc.Upload(
                    id='upload-data',
                    children=html.Div(['Drag and Drop or ', html.A('Select a Flight Data File')]),
                    style={'width': '100%','height': '60px','lineHeight': '60px','borderWidth': '1px','borderStyle': 'dashed','borderRadius': '5px','textAlign': 'center','margin': '10px 0'},
                    multiple=False
                ),
                html.Div(id='upload-status')
            ]),
            card(id='parser-report-card', className="mt-4", style={'display': 'none'}, children=[
                html.H4("Data Validation Report", className="card-title"),
                html.Div(id='parser-report-output')
            ]),
            card(id='plot-controls-card', className="mt-4", style={'display': 'none'}, children=[
                html.H4("Plotting Controls", className="card-title"),
                html.Label("Select Subsystems for 2D Plot:"),
                dcc.Checklist(id='subsystem-checklist', options=[], value=[], labelStyle={'display': 'block'})
            ]),
            card(id='comm-outage-card', className="mt-4", style={'display': 'none'}, children=[
                html.H4("Comm Link Analysis", className="card-title"),
                html.Label("Show outages for link:"),
                dcc.Dropdown(id='comm-link-selector', options=[], value=None, clearable=True, placeholder="Select a link..."),
                html.Label("Outage Threshold (dB):", className="mt-2"),
                dcc.Input(id='outage-threshold-input', type='number', value=3, step=0.5, className="w-100")
            ])
        ]),
        # Right Column: Visualization Area with Tabs
        dbc.Col(width=8, children=[
            card([
                dbc.Tabs(id="tabs", active_tab="tab-map", children=[
                    dbc.Tab(label="Telemetry Plots", tab_id="tab-2d", children=[
                        dcc.Graph(id='main-graph', style={'height': '80vh'})
                    ]),
                    dbc.Tab(label="Flight Path Map", tab_id="tab-map", children=[
                        dcc.Graph(id='map-graph', style={'height': '80vh'})
                    ]),
                ])
            ])
        ])
    ])
])

# --- Callbacks ---
@app.callback(
    [Output('dataframe-store', 'data'),
     Output('upload-status', 'children'),
     Output('parser-report-card', 'style'),
     Output('parser-report-output', 'children'),
     Output('plot-controls-card', 'style'),
     Output('subsystem-checklist', 'options'),
     Output('comm-outage-card', 'style'),
     Output('comm-link-selector', 'options')],
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def process_upload(contents, filename):
    no_update_list = [no_update] * 8
    if contents is None: return no_update_list
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        df, report = load_and_validate_data(io.StringIO(decoded.decode('utf-8')))
        if df is None or df.empty:
            status_msg = html.Div([f"Error: Parser returned no data for {filename}. ", html.Pre(str(report['warnings']))], className="text-danger")
            return no_update, status_msg, {'display': 'none'}, "", {'display': 'none'}, [], {'display': 'none'}, []
        status_msg = html.Div(f"Loaded: {filename}", className="text-success")
        report_children = [
            html.P(f"Status: {report['status'].title()}", className=f"text-{'success' if report['status']=='success' else 'danger'}"),
            html.P(f"Subsystems: {', '.join(report['subsystems_found'])}"),
            html.P(f"Payloads: {', '.join(report['payloads_found'])}"),
        ]
        if report['warnings']: report_children.append(html.P("Warnings:", className="text-warning")); report_children.append(html.Ul([html.Li(w) for w in report['warnings']]))
        if report['redacted_cols_found']: report_children.append(html.P("Redacted:", className="text-info")); report_children.append(html.Ul([html.Li(c) for c in report['redacted_cols_found']]))
        subsystem_options = [{'label': s, 'value': s} for s in report['subsystems_found']]
        comm_link_cols = [col for col in df.columns if col.startswith('COMM_') and col.endswith('_dB')]
        comm_link_options = [{'label': re.search('COMM_(.*)_Margin_dB', col).group(1), 'value': col} for col in comm_link_cols]
        return (df.to_json(date_format='iso', orient='split'), status_msg, {'display': 'block'}, report_children, {'display': 'block'}, subsystem_options, {'display': 'block', 'marginTop': '1rem'}, comm_link_options)
    except Exception as e:
        return no_update, html.Div(f"An error occurred: {e}", className="text-danger"), {'display': 'none'},"",{'display': 'none'},[],{'display': 'none'},[]

@app.callback(
    Output('main-graph', 'figure'),
    Input('subsystem-checklist', 'value'),
    State('dataframe-store', 'data')
)
def update_2d_graph(selected_subsystems, json_data):
    if not selected_subsystems or not json_data:
        fig = go.Figure()
        fig.update_layout(template="plotly_dark", title_text="Select a subsystem to begin analysis")
        return fig
    df = pd.read_json(io.StringIO(json_data), orient='split')
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    fig = go.Figure()
    for subsystem in selected_subsystems:
        subsystem_cols = [col for col in df.columns if col.startswith(f"{subsystem}_")]
        for col in subsystem_cols:
            fig.add_trace(go.Scatter(x=df['Timestamp'], y=df[col], mode='lines', name=col))
    fig.update_layout(title="Subsystem Telemetry Over Time", template="plotly_dark")
    return fig

# --- UPDATED MAP CALLBACK WITH SEGMENTED COLORS ---
@app.callback(
    Output('map-graph', 'figure'),
    [Input('dataframe-store', 'data'),
     Input('comm-link-selector', 'value'),
     Input('outage-threshold-input', 'value')]
)
def update_map_graph(json_data, selected_comm_link, outage_threshold):
    if mapbox_access_token == "YOUR_MAPBOX_ACCESS_TOKEN_HERE" or mapbox_access_token == "":
        fig = go.Figure()
        fig.update_layout(template="plotly_dark", title_text="ERROR: Mapbox Token is not set in app.py")
        return fig

    default_fig = go.Figure(go.Scattermapbox())
    default_fig.update_layout(
        title_text="Upload Data to See Flight Path", template="plotly_dark",
        mapbox_style="dark", mapbox_accesstoken=mapbox_access_token,
        mapbox_center_lon=10.75, mapbox_center_lat=59.9, mapbox_zoom=5
    )
    if not json_data: return default_fig

    try:
        df = pd.read_json(io.StringIO(json_data), orient='split')
        if df.empty: return default_fig
            
        map_traces = []
        
        # --- NEW LOGIC: Plot outage segments and good segments separately ---
        if selected_comm_link and outage_threshold is not None:
            # Create a boolean column for outages
            df['is_outage'] = df[selected_comm_link] < outage_threshold
            
            # Create a trace for the segments with good comms
            df_good = df[~df['is_outage']]
            good_trace = go.Scattermapbox(
                name="Link OK",
                mode="lines",
                lon=df_good['POS_Longitude_deg'],
                lat=df_good['POS_Latitude_deg'],
                line=dict(width=4, color='#1F77B4'), # Blue for good signal
                hovertemplate="<b>Lon:</b> %{lon:.4f}<br><b>Lat:</b> %{lat:.4f}<br><b>Altitude:</b> %{text:,} ft<extra></extra>",
                text=df_good['POS_Altitude_ft'],
            )
            map_traces.append(good_trace)
            
            # Create a trace for the outage segments
            df_bad = df[df['is_outage']]
            bad_trace = go.Scattermapbox(
                name="Link Outage",
                mode="lines",
                lon=df_bad['POS_Longitude_deg'],
                lat=df_bad['POS_Latitude_deg'],
                line=dict(width=5, color='#DC3545'), # Thicker, bright red for outages
                hovertemplate="<b>OUTAGE</b><br>" + f"<b>{selected_comm_link.replace('_', ' ')}:</b> %{{text:.2f}} dB<br>" + "<b>Lon:</b> %{lon:.4f}<br>" + "<b>Lat:</b> %{lat:.4f}<extra></extra>",
                text=df_bad[selected_comm_link]
            )
            map_traces.append(bad_trace)

        else:
            # Default case: No link selected, show the whole path in orange
            full_path_trace = go.Scattermapbox(
                name="Flight Path",
                mode="lines",
                lon=df['POS_Longitude_deg'],
                lat=df['POS_Latitude_deg'],
                line=dict(width=4, color='#FF851B'),
                hovertemplate="<b>Lon:</b> %{lon:.4f}<br><b>Lat:</b> %{lat:.4f}<br><b>Altitude:</b> %{text:,} ft<extra></extra>",
                text=df['POS_Altitude_ft'],
            )
            map_traces.append(full_path_trace)
        
        fig = go.Figure(data=map_traces)
        fig.update_layout(
            title="Flight Path Visualization", template="plotly_dark",
            mapbox_style="satellite-streets", mapbox_accesstoken=mapbox_access_token,
            mapbox_center_lon=df['POS_Longitude_deg'].mean(),
            mapbox_center_lat=df['POS_Latitude_deg'].mean(),
            mapbox_zoom=6, margin={"r":0,"t":40,"l":0,"b":0},
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
        )
        return fig
    except Exception as e:
        print(f"AN ERROR OCCURRED IN update_map_graph: {e}")
        return default_fig

# --- Run the App ---
if __name__ == '__main__':
    app.run(debug=True)

