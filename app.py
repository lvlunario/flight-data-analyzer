import base64
import io
import pandas as pd

import dash
from dash import dcc, html, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

# Import our custom data parser
from data_parser import load_and_validate_data

# mapbox.com api token
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
     Output('subsystem-checklist', 'value')],
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def process_upload(contents, filename):
    if contents is None: return no_update
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        df, report = load_and_validate_data(io.StringIO(decoded.decode('utf-8')))
        if df is None or df.empty:
            status_msg = html.Div([f"Error: Parser returned no data for {filename}. ", html.Pre(str(report['warnings']))], className="text-danger")
            return no_update, status_msg, {'display': 'none'}, "", {'display': 'none'}, [], []
        
        status_msg = html.Div(f"Loaded: {filename}", className="text-success")
        report_children = [
            html.P(f"Status: {report['status'].title()}", className=f"text-{'success' if report['status']=='success' else 'danger'}"),
            html.P(f"Subsystems: {', '.join(report['subsystems_found'])}"),
            html.P(f"Payloads: {', '.join(report['payloads_found'])}"),
        ]
        if report['warnings']: report_children.append(html.P("Warnings:", className="text-warning")); report_children.append(html.Ul([html.Li(w) for w in report['warnings']]))
        if report['redacted_cols_found']: report_children.append(html.P("Redacted:", className="text-info")); report_children.append(html.Ul([html.Li(c) for c in report['redacted_cols_found']]))
        subsystem_options = [{'label': s, 'value': s} for s in report['subsystems_found']]
        return df.to_json(date_format='iso', orient='split'), status_msg, {'display': 'block'}, report_children, {'display': 'block'}, subsystem_options, []
    except Exception as e:
        return no_update, html.Div(f"An error occurred during file processing: {e}", className="text-danger"), {'display': 'none'}, "", {'display': 'none'}, [], []

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

@app.callback(
    Output('map-graph', 'figure'),
    Input('dataframe-store', 'data')
)
def update_map_graph(json_data):
    if mapbox_access_token == "YOUR_MAPBOX_ACCESS_TOKEN_HERE" or mapbox_access_token == "":
        fig = go.Figure()
        fig.update_layout(template="plotly_dark", title_text="ERROR: Mapbox Token is not set in app.py")
        return fig

    default_fig = go.Figure(go.Scattermapbox())
    default_fig.update_layout(
        title_text="Upload Data to See Flight Path", template="plotly_dark",
        mapbox_style="dark", mapbox_accesstoken=mapbox_access_token,
        mapbox_center_lon=121.05, mapbox_center_lat=14.33, mapbox_zoom=5
    )
    if not json_data: return default_fig

    try:
        df = pd.read_json(io.StringIO(json_data), orient='split')
        if df.empty: return default_fig
            
        df_map = df.iloc[::15, :].copy()

        # --- VISIBILITY ENHANCEMENTS ARE HERE ---
        fig = go.Figure(go.Scattermapbox(
            mode="lines",
            lon=df_map['POS_Longitude_deg'],
            lat=df_map['POS_Latitude_deg'],
            # Set a thick, bright, solid-color line for high visibility
            line=dict(width=4, color='#FF851B'), # A bright orange color
            hovertemplate="<b>Lon:</b> %{lon:.4f}<br><b>Lat:</b> %{lat:.4f}<br><b>Altitude:</b> %{text:,} ft<extra></extra>",
            # We still pass altitude data, but just for the hover text
            text=df_map['POS_Altitude_ft'],
        ))
        
        fig.update_layout(
            title="Flight Path Visualization", template="plotly_dark",
            mapbox_style="satellite-streets", mapbox_accesstoken=mapbox_access_token,
            mapbox_center_lon=df_map['POS_Longitude_deg'].mean(),
            mapbox_center_lat=df_map['POS_Latitude_deg'].mean(),
            mapbox_zoom=7, margin={"r":0,"t":40,"l":0,"b":0}
        )
        return fig
    except Exception as e:
        print(f"AN ERROR OCCURRED IN update_map_graph: {e}")
        return default_fig

# --- Run the App ---
if __name__ == '__main__':
    app.run(debug=True)