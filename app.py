import base64
import io
import pandas as pd
import numpy as np

import dash
from dash import dcc, html, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import re

from data_parser import load_and_validate_data

# PDF + Word generation
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from docx import Document
import tempfile

mapbox_access_token = "pk.eyJ1IjoicXlyb3dyZW4iLCJhIjoiY21mcGg4cjVpMGY1dTJrcjRuYmo1YWl3ZCJ9.YlqTfqH9P954mOz6C1lLDA"

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG], suppress_callback_exceptions=True)
server = app.server

def card(children, **kwargs):
    return dbc.Card(dbc.CardBody(children), **kwargs)

app.layout = dbc.Container(fluid=True, children=[
    dcc.Store(id='dataframe-store'),
    html.H1("Aerospace Flight Data Analyzer", className="text-center my-4 text-primary"),
    dbc.Row([
        dbc.Col(width=4, children=[
            card([
                html.H4("Control Panel", className="card-title"),
                dcc.Upload(
                    id='upload-data',
                    children=html.Div(['Drag and Drop or ', html.A('Select a Flight Data File')]),
                    style={
                        'width': '100%','height': '60px','lineHeight': '60px',
                        'borderWidth': '1px','borderStyle': 'dashed',
                        'borderRadius': '5px','textAlign': 'center','margin': '10px 0'
                    }
                ),
                html.Div(id='upload-status'),
                html.Div([
                    html.Button("Download PDF Report", id="download-pdf-btn", className="btn btn-primary mt-2 me-2"),
                    dcc.Download(id="download-pdf"),
                    html.Button("Download Word Report", id="download-word-btn", className="btn btn-secondary mt-2"),
                    dcc.Download(id="download-word")
                ])
            ]),
            card([], id='parser-report-card', className="mt-4", style={'display': 'none'}),
            card([], id='summary-report-card', className="mt-4", style={'display': 'none'}),
            card([], id='plot-controls-card', className="mt-4", style={'display': 'none'}),
            card([], id='comm-outage-card', className="mt-4", style={'display': 'none'}),
            
            card(id='scatter-3d-controls-card', className="mt-4", style={'display': 'none'}, children=[
                html.H4("3D Scatter Plot Controls", className="card-title"),
                html.Label("X-Axis:"),
                dcc.Dropdown(id='x-axis-selector', value='POS_Longitude_deg'),
                html.Label("Y-Axis:", className="mt-2"),
                dcc.Dropdown(id='y-axis-selector', value='POS_Latitude_deg'),
                html.Label("Z-Axis:", className="mt-2"),
                dcc.Dropdown(id='z-axis-selector', value='POS_Altitude_ft'),
                html.Label("Color By:", className="mt-2"),
                dcc.Dropdown(id='color-selector', value='COMM_TCDL_Margin_dB'),
            ])
        ]),
        dbc.Col(width=8, children=[
            card([
                dbc.Tabs(id="tabs", active_tab="tab-map", children=[
                    dbc.Tab(dcc.Graph(id='main-graph', style={'height': '80vh'}), label="Telemetry Plots", tab_id="tab-2d"),
                    dbc.Tab(dcc.Graph(id='map-graph', style={'height': '80vh'}), label="Flight Path Map", tab_id="tab-map"),
                    dbc.Tab(dcc.Graph(id='scatter-3d-graph', style={'height': '80vh'}), label="3D Scatter Plot", tab_id="tab-3d"),
                ])
            ])
        ])
    ])
])

def generate_summary_report(df, outage_threshold_db=3.0):
    """Analyzes the dataframe to produce a summary report on links and subsystems."""
    
    # --- 1. Communication Link Analysis ---
    comm_cols = [col for col in df.columns if col.startswith('COMM_') and col.endswith('_dB')]
    link_rows = []
    if comm_cols:
        for link in comm_cols:
            link_name = re.search('COMM_(.*)_dB', link).group(1).replace('_', ' ')
            outages = df[link] < outage_threshold_db
            outage_duration_sec = df['Timestamp'][outages].diff().dt.total_seconds().sum()
            
            link_rows.append(html.Tr([
                html.Td(link_name),
                html.Td(f"{df[link].mean():.2f} dB"),
                html.Td(f"{df[link].min():.2f} dB"),
                html.Td(f"{outage_duration_sec:.1f} sec")
            ]))
    
    comm_table = dbc.Table([
        html.Thead(html.Tr([html.Th("Link"), html.Th("Avg Margin"), html.Th("Min Margin"), html.Th("Outage Time")])),
        html.Tbody(link_rows)
    ], bordered=True, striped=True, hover=True, responsive=True)

    # --- 2. Subsystem Health (based on data availability) ---
    subsystems, _ = discover_subsystems(df.columns)
    subsystem_rows = []
    if subsystems:
        for sys in subsystems:
            sys_cols = [col for col in df.columns if col.startswith(f"{sys}_")]
            data_availability = df[sys_cols].notna().mean().mean() * 100
            subsystem_rows.append(html.Tr([
                html.Td(sys),
                html.Td(f"{data_availability:.1f}%")
            ]))

    subsystem_table = dbc.Table([
        html.Thead(html.Tr([html.Th("Subsystem"), html.Th("Data Availability")])),
        html.Tbody(subsystem_rows)
    ], bordered=True, striped=True, hover=True, responsive=True, className="mt-3")

    report_children = [
        html.H4("Flight Summary Report", className="card-title"),
        html.H5("Communication Links", className="mt-3"),
        comm_table,
        html.H5("Subsystem Health", className="mt-3"),
        subsystem_table
    ]
    
    return report_children

def discover_subsystems(df_columns):
    """Dynamically identifies subsystems from column prefixes."""
    subsystems = set()
    prefix_pattern = re.compile(r'^([A-Z0-9]+)_')
    for col in df_columns:
        match = prefix_pattern.match(col)
        if match:
            prefix = match.group(1)
            if prefix not in ['COMM', 'POS']:
                 subsystems.add(prefix)
    return sorted(list(subsystems)), []


# --- Combined Callback for all UI updates on file upload ---
@app.callback(
    [Output('dataframe-store', 'data'), Output('upload-status', 'children'),
     Output('parser-report-card', 'children'), Output('parser-report-card', 'style'),
     Output('summary-report-card', 'children'), Output('summary-report-card', 'style'),
     Output('plot-controls-card', 'children'), Output('plot-controls-card', 'style'),
     Output('comm-outage-card', 'children'), Output('comm-outage-card', 'style'),
     Output('scatter-3d-controls-card', 'style'),
     Output('x-axis-selector', 'options'), Output('y-axis-selector', 'options'),
     Output('z-axis-selector', 'options'), Output('color-selector', 'options')],
    Input('upload-data', 'contents'), State('upload-data', 'filename')
)
def process_upload_and_update_ui(contents, filename):
    if contents is None:
        return [no_update] * 15

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        df, report = load_and_validate_data(io.StringIO(decoded.decode('utf-8')))
        
        if df is None or df.empty:
            status = html.Div(f"Error: Parser failed for {filename}.", className="text-danger")
            return (
                no_update, status,
                [], {'display': 'none'},
                [], {'display': 'none'},
                [], {'display': 'none'},
                [], {'display': 'none'},
                {'display': 'none'},
                [], [], [], []
            )

        status = html.Div(f"Loaded: {filename}", className="text-success")
        
        report_children = [html.H4("Data Validation Report", className="card-title"),
                           html.P(f"Status: {report['status']}")]
        
        summary_report_children = generate_summary_report(df)

        plot_controls_children = [
            html.H4("Plotting Controls", className="card-title"),
            html.Label("Select Subsystems:"),
            dcc.Checklist(
                id='subsystem-checklist',
                options=[{'label': s, 'value': s} for s in report.get('subsystems_found', [])],
                labelStyle={'display': 'block'}
            )
        ]
        
        comm_link_cols = [col for col in df.columns if col.startswith('COMM_') and col.endswith('_dB')]
        comm_link_options = [{'label': col, 'value': col} for col in comm_link_cols]
        comm_outage_children = [
            html.H4("Comm Link Analysis", className="card-title"),
            html.Label("Show outages for link:"),
            dcc.Dropdown(id='comm-link-selector', options=comm_link_options, placeholder="Select a link..."),
            html.Label("Outage Threshold (dB):", className="mt-2"),
            dcc.Input(id='outage-threshold-input', type='number', value=3, step=0.5, className="w-100")
        ]
        
        numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
        axis_options = [{'label': col, 'value': col} for col in numeric_cols]

        return (
            df.to_json(orient='split'), status,
            report_children, {'display': 'block', 'marginTop': '1rem'},
            summary_report_children, {'display': 'block', 'marginTop': '1rem'},
            plot_controls_children, {'display': 'block', 'marginTop': '1rem'},
            comm_outage_children, {'display': 'block', 'marginTop': '1rem'},
            {'display': 'block', 'marginTop': '1rem'},
            axis_options, axis_options, axis_options, axis_options
        )

    except Exception as e:
        status = html.Div(f"An error occurred: {e}", className="text-danger")
        return (
            no_update, status,
            [], {'display': 'none'},
            [], {'display': 'none'},
            [], {'display': 'none'},
            [], {'display': 'none'},
            {'display': 'none'},
            [], [], [], []
        )


# --- PDF Report Generator ---
@app.callback(
    Output("download-pdf", "data"),
    Input("download-pdf-btn", "n_clicks"),
    State("dataframe-store", "data"),
    State("comm-link-selector", "value"),
    State("outage-threshold-input", "value"),
    prevent_initial_call=True
)
def generate_pdf_report(n_clicks, json_data, selected_comm_link, outage_threshold):
    if not json_data:
        return no_update

    df = pd.read_json(io.StringIO(json_data), orient="split")

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(tmp_file.name)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Flight Data Report", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Rows: {len(df)}, Columns: {len(df.columns)}", styles["Normal"]))

    if selected_comm_link and selected_comm_link in df.columns:
        outages = df[selected_comm_link] < outage_threshold if outage_threshold else pd.Series([False]*len(df))
        outage_time = df['Timestamp'][outages].diff().dt.total_seconds().sum()

        table_data = [
            ["Link", "Avg Margin (dB)", "Min Margin (dB)", "Outage Time (sec)"],
            [selected_comm_link,
             f"{df[selected_comm_link].mean():.2f}",
             f"{df[selected_comm_link].min():.2f}",
             f"{outage_time:.1f}"]
        ]
        t = Table(table_data, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.grey),
            ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("GRID", (0,0), (-1,-1), 0.5, colors.black)
        ]))
        story.append(t)

    doc.build(story)
    return dcc.send_file(tmp_file.name)


# --- Word Report Generator ---
@app.callback(
    Output("download-word", "data"),
    Input("download-word-btn", "n_clicks"),
    State("dataframe-store", "data"),
    State("comm-link-selector", "value"),
    State("outage-threshold-input", "value"),
    prevent_initial_call=True
)
def generate_word_report(n_clicks, json_data, selected_comm_link, outage_threshold):
    if not json_data:
        return no_update

    df = pd.read_json(io.StringIO(json_data), orient="split")

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    doc = Document()

    doc.add_heading("Flight Data Report", 0)
    doc.add_paragraph(f"Rows: {len(df)}, Columns: {len(df.columns)}")

    if selected_comm_link and selected_comm_link in df.columns:
        doc.add_heading("Comm Link Analysis", level=1)
        outages = df[selected_comm_link] < outage_threshold if outage_threshold else pd.Series([False]*len(df))
        outage_time = df['Timestamp'][outages].diff().dt.total_seconds().sum()

        table = doc.add_table(rows=1, cols=4)
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text, hdr_cells[1].text, hdr_cells[2].text, hdr_cells[3].text = \
            "Link", "Avg Margin (dB)", "Min Margin (dB)", "Outage Time (sec)"
        
        row_cells = table.add_row().cells
        row_cells[0].text = selected_comm_link
        row_cells[1].text = f"{df[selected_comm_link].mean():.2f}"
        row_cells[2].text = f"{df[selected_comm_link].min():.2f}"
        row_cells[3].text = f"{outage_time:.1f}"

    doc.save(tmp_file.name)
    return dcc.send_file(tmp_file.name)


# --- Callbacks for each graph ---
@app.callback(Output('main-graph', 'figure'),
              Input('subsystem-checklist', 'value'), State('dataframe-store', 'data'))
def update_2d_graph(selected_subsystems, json_data):
    if not selected_subsystems or not json_data:
        return go.Figure().update_layout(template="plotly_dark", title_text="Select a subsystem to begin analysis")
    df = pd.read_json(io.StringIO(json_data), orient='split')
    fig = go.Figure()
    for subsystem in selected_subsystems:
        subsystem_cols = [col for col in df.columns if col.startswith(f"{subsystem}_")]
        for col in subsystem_cols:
            fig.add_trace(go.Scatter(x=df['Timestamp'], y=df[col], mode='lines', name=col))
    return fig.update_layout(title="Subsystem Telemetry Over Time", template="plotly_dark")

@app.callback(Output('map-graph', 'figure'),
              [Input('dataframe-store', 'data'), Input('comm-link-selector', 'value'), Input('outage-threshold-input', 'value')])
def update_map_graph(json_data, selected_comm_link, outage_threshold):
    if not json_data:
        return go.Figure(go.Scattermapbox()).update_layout(template="plotly_dark", mapbox_style="dark", mapbox_accesstoken=mapbox_access_token, mapbox_center_lon=10.75, mapbox_center_lat=59.9)
    df = pd.read_json(io.StringIO(json_data), orient='split')
    map_traces = []
    if selected_comm_link and outage_threshold is not None:
        df['is_outage'] = df[selected_comm_link] < outage_threshold
        map_traces.append(go.Scattermapbox(
            name="Link OK", mode="lines",
            lon=df[~df['is_outage']]['POS_Longitude_deg'],
            lat=df[~df['is_outage']]['POS_Latitude_deg'],
            line=dict(width=4, color='#1F77B4')))
        map_traces.append(go.Scattermapbox(
            name="Link Outage", mode="lines",
            lon=df[df['is_outage']]['POS_Longitude_deg'],
            lat=df[df['is_outage']]['POS_Latitude_deg'],
            line=dict(width=5, color='#DC3545')))
    else:
        map_traces.append(go.Scattermapbox(
            name="Flight Path", mode="lines",
            lon=df['POS_Longitude_deg'], lat=df['POS_Latitude_deg'],
            line=dict(width=4, color='#FF851B')))
    return go.Figure(data=map_traces).update_layout(
        template="plotly_dark", mapbox_style="satellite-streets",
        mapbox_accesstoken=mapbox_access_token,
        mapbox_center_lon=df['POS_Longitude_deg'].mean(),
        mapbox_center_lat=df['POS_Latitude_deg'].mean(),
        mapbox_zoom=6)

@app.callback(
    Output('scatter-3d-graph', 'figure'),
    [Input('x-axis-selector', 'value'), Input('y-axis-selector', 'value'),
     Input('z-axis-selector', 'value'), Input('color-selector', 'value')],
    State('dataframe-store', 'data')
)
def update_3d_scatter(x_axis, y_axis, z_axis, color_axis, json_data):
    if not all([x_axis, y_axis, z_axis, color_axis, json_data]):
        return go.Figure().update_layout(template="plotly_dark", title_text="Select axes and color parameters to generate a 3D plot")

    df = pd.read_json(io.StringIO(json_data), orient='split')
    df_scatter = df.iloc[::20, :].copy()

    fig = go.Figure(data=[go.Scatter3d(
        x=df_scatter[x_axis],
        y=df_scatter[y_axis],
        z=df_scatter[z_axis],
        mode='markers',
        marker=dict(
            size=4,
            color=df_scatter[color_axis],
            colorscale='Viridis',
            showscale=True,
            colorbar_title_text=color_axis.replace('_', ' ')
        )
    )])

    fig.update_layout(
        template="plotly_dark",
        title=f"3D Analysis: {z_axis} vs. {x_axis} and {y_axis}",
        scene=dict(
            xaxis_title=x_axis.replace('_', ' '),
            yaxis_title=y_axis.replace('_', ' '),
            zaxis_title=z_axis.replace('_', ' ')
        ),
        margin=dict(l=0, r=0, b=0, t=40)
    )
    return fig

if __name__ == '__main__':
    app.run(debug=True)
