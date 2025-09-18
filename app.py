import base64
import io
import pandas as pd

import dash
from dash import dcc, html, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go

# Import our custom data parser
from data_parser import load_and_validate_data, discover_subsystems

# --- App Initialization ---
# Use a nice Bootstrap theme for a professional look
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server

# --- Reusable Components ---
# Card component for styling sections
def card(children, **kwargs):
    return dbc.Card(dbc.CardBody(children), **kwargs)

# --- App Layout ---
app.layout = dbc.Container(fluid=True, children=[
    # Hidden store for sharing data between callbacks
    dcc.Store(id='dataframe-store'),

    # --- Header ---
    html.H1("Aerospace Flight Data Analyzer", className="text-center my-4 text-primary"),

    # --- Main Content Row ---
    dbc.Row([
        # --- Left Column: Control Panel ---
        dbc.Col(width=4, children=[
            card([
                html.H4("Control Panel", className="card-title"),
                dcc.Upload(
                    id='upload-data',
                    children=html.Div([
                        'Drag and Drop or ',
                        html.A('Select a Flight Data File')
                    ]),
                    style={
                        'width': '100%', 'height': '60px', 'lineHeight': '60px',
                        'borderWidth': '1px', 'borderStyle': 'dashed',
                        'borderRadius': '5px', 'textAlign': 'center', 'margin': '10px 0'
                    },
                    multiple=False # Allow only a single file
                ),
                html.Div(id='upload-status') # To show filename or errors
            ]),
            
            card(id='parser-report-card', className="mt-4", style={'display': 'none'}, children=[
                html.H4("Data Validation Report", className="card-title"),
                html.Div(id='parser-report-output')
            ]),

            card(id='plot-controls-card', className="mt-4", style={'display': 'none'}, children=[
                html.H4("Plotting Controls", className="card-title"),
                html.Label("Select Subsystems to Plot:"),
                dcc.Checklist(id='subsystem-checklist', options=[], value=[], labelStyle={'display': 'block'})
            ])
        ]),

        # --- Right Column: Visualization Area ---
        dbc.Col(width=8, children=[
            card([
                dcc.Graph(id='main-graph', style={'height': '80vh'})
            ])
        ])
    ])
])

# --- Callbacks ---

# Callback 1: Process uploaded file and update stores & UI
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
    if contents is None:
        return no_update # No file uploaded, do nothing

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    try:
        # Use our robust parser
        df, report = load_and_validate_data(io.StringIO(decoded.decode('utf-8')))

        if df is None:
            # Parser failed, show error
            status_msg = html.Div([f"Error processing {filename}:", html.Pre(str(report['warnings']))], className="text-danger")
            return no_update, status_msg, {'display': 'none'}, "", {'display': 'none'}, [], []

        # Parser succeeded
        status_msg = html.Div(f"Loaded: {filename}", className="text-success")
        
        # Format the report for display
        report_children = [
            html.P(f"Status: {report['status'].title()}", className=f"text-{'success' if report['status']=='success' else 'danger'}"),
            html.P(f"Subsystems Found: {', '.join(report['subsystems_found'])}"),
            html.P(f"Payloads Found: {', '.join(report['payloads_found'])}"),
        ]
        if report['warnings']:
            report_children.append(html.P("Warnings:"))
            report_children.append(html.Ul([html.Li(w) for w in report['warnings']]))
        if report['redacted_cols_found']:
             report_children.append(html.P("Redacted Columns (handled):"))
             report_children.append(html.Ul([html.Li(c) for c in report['redacted_cols_found']]))

        # Create checklist options from found subsystems
        subsystem_options = [{'label': s, 'value': s} for s in report['subsystems_found']]
        
        return (df.to_json(date_format='iso', orient='split'), 
                status_msg, 
                {'display': 'block', 'marginTop': '1rem'}, 
                report_children, 
                {'display': 'block', 'marginTop': '1rem'},
                subsystem_options,
                []) # Return empty list for checklist value initially

    except Exception as e:
        status_msg = html.Div(f"An unexpected error occurred: {e}", className="text-danger")
        return no_update, status_msg, {'display': 'none'}, "", {'display': 'none'}, [], []


# Callback 2: Update graph based on checklist selection
@app.callback(
    Output('main-graph', 'figure'),
    Input('subsystem-checklist', 'value'),
    State('dataframe-store', 'data')
)
def update_graph(selected_subsystems, json_data):
    if not selected_subsystems or not json_data:
        # No data or no selection, show an empty graph
        fig = go.Figure()
        fig.update_layout(
            template="plotly_dark",
            title="Select a subsystem to begin analysis",
            xaxis_title="Time",
            yaxis_title="Value"
        )
        return fig

    df = pd.read_json(json_data, orient='split')
    
    # Create a figure to plot on
    fig = go.Figure()
    
    for subsystem in selected_subsystems:
        # Find all columns related to this subsystem
        subsystem_cols = [col for col in df.columns if col.startswith(f"{subsystem}_")]
        
        for col in subsystem_cols:
            # Add a trace (a line) for each parameter
            fig.add_trace(go.Scatter(x=df['Timestamp'], y=df[col], mode='lines', name=col))

    fig.update_layout(
        title="Subsystem Telemetry Over Time",
        xaxis_title="Timestamp",
        yaxis_title="Sensor Value",
        template="plotly_dark",
        legend_title="Parameters"
    )
    
    return fig

# --- Run the App ---
if __name__ == '__main__':
    app.run(debug=True)