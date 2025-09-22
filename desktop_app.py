import sys
import pandas as pd
import numpy as np
import re

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QFileDialog, QTabWidget, QComboBox, QLabel, QFormLayout
)
from PySide6.QtCore import Qt

# Matplotlib integration for PySide6
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Import our existing data parser
from data_parser import load_and_validate_data

class MatplotlibCanvas(FigureCanvas):
    """A canvas that updates itself with a new plot."""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)

class MatplotlibCanvas3D(FigureCanvas):
    """A canvas for 3D scatter plots."""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111, projection='3d')
        super().__init__(self.fig)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Offline Flight Data Analyzer")
        self.setGeometry(100, 100, 1400, 800)

        self.df = None  # To store the loaded DataFrame

        # --- Main Layout ---
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        self.setCentralWidget(main_widget)

        # --- Left Panel: Controls ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setFixedWidth(300)

        # File selection
        self.btn_open_file = QPushButton("Open Flight Data File")
        self.btn_open_file.clicked.connect(self.open_file_dialog)
        self.lbl_file_status = QLabel("No file loaded.")
        
        # 3D Scatter Controls
        self.scatter_controls_widget = QWidget()
        scatter_layout = QFormLayout(self.scatter_controls_widget)
        self.x_axis_combo = QComboBox()
        self.y_axis_combo = QComboBox()
        self.z_axis_combo = QComboBox()
        self.color_combo = QComboBox()
        scatter_layout.addRow("X-Axis:", self.x_axis_combo)
        scatter_layout.addRow("Y-Axis:", self.y_axis_combo)
        scatter_layout.addRow("Z-Axis:", self.z_axis_combo)
        scatter_layout.addRow("Color By:", self.color_combo)
        self.scatter_controls_widget.setVisible(False)
        
        # Connect signals to update plots
        self.x_axis_combo.currentIndexChanged.connect(self.update_plots)
        self.y_axis_combo.currentIndexChanged.connect(self.update_plots)
        self.z_axis_combo.currentIndexChanged.connect(self.update_plots)
        self.color_combo.currentIndexChanged.connect(self.update_plots)

        left_layout.addWidget(self.btn_open_file)
        left_layout.addWidget(self.lbl_file_status)
        left_layout.addWidget(self.scatter_controls_widget)
        left_layout.addStretch()

        # --- Right Panel: Plots ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.tabs = QTabWidget()
        
        # Create plot canvases
        self.ground_track_canvas = MatplotlibCanvas(self)
        self.telemetry_canvas = MatplotlibCanvas(self)
        self.scatter_3d_canvas = MatplotlibCanvas3D(self)
        
        self.tabs.addTab(self.ground_track_canvas, "2D Ground Track")
        self.tabs.addTab(self.telemetry_canvas, "Telemetry Plot")
        self.tabs.addTab(self.scatter_3d_canvas, "3D Scatter Plot")
        
        right_layout.addWidget(self.tabs)
        
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)

    def open_file_dialog(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open File", "", "CSV Files (*.csv)")
        if filename:
            self.df, report = load_and_validate_data(filename)
            if self.df is not None:
                self.lbl_file_status.setText(f"Loaded: {filename.split('/')[-1]}")
                self.populate_controls()
                self.update_plots()
            else:
                self.lbl_file_status.setText("Error: Invalid data file.")

    def populate_controls(self):
        numeric_cols = self.df.select_dtypes(include=np.number).columns.tolist()
        
        # Block signals while populating to avoid premature plot updates
        self.x_axis_combo.blockSignals(True)
        self.y_axis_combo.blockSignals(True)
        self.z_axis_combo.blockSignals(True)
        self.color_combo.blockSignals(True)

        self.x_axis_combo.clear()
        self.y_axis_combo.clear()
        self.z_axis_combo.clear()
        self.color_combo.clear()
        
        self.x_axis_combo.addItems(numeric_cols)
        self.y_axis_combo.addItems(numeric_cols)
        self.z_axis_combo.addItems(numeric_cols)
        self.color_combo.addItems(numeric_cols)
        
        # Set intelligent defaults
        self.x_axis_combo.setCurrentText('POS_Longitude_deg')
        self.y_axis_combo.setCurrentText('POS_Latitude_deg')
        self.z_axis_combo.setCurrentText('POS_Altitude_ft')
        self.color_combo.setCurrentText('COMM_TCDL_Margin_dB')
        
        self.x_axis_combo.blockSignals(False)
        self.y_axis_combo.blockSignals(False)
        self.z_axis_combo.blockSignals(False)
        self.color_combo.blockSignals(False)

        self.scatter_controls_widget.setVisible(True)

    def update_plots(self):
        if self.df is None:
            return
        
        self.update_ground_track_plot()
        self.update_telemetry_plot()
        self.update_3d_scatter_plot()

    def update_ground_track_plot(self):
        canvas = self.ground_track_canvas
        canvas.axes.clear()
        df_plot = self.df.iloc[::20, :] # Downsample for performance
        scatter = canvas.axes.scatter(df_plot['POS_Longitude_deg'], df_plot['POS_Latitude_deg'],
                                     c=df_plot['POS_Altitude_ft'], cmap='viridis', s=10)
        canvas.axes.set_xlabel("Longitude (deg)")
        canvas.axes.set_ylabel("Latitude (deg)")
        canvas.axes.set_title("2D Ground Track")
        canvas.axes.grid(True)
        self.fig_colorbar(canvas, scatter, "Altitude (ft)")
        canvas.draw()
        
    def update_telemetry_plot(self):
        canvas = self.telemetry_canvas
        canvas.axes.clear()
        df_plot = self.df.iloc[::10, :] # Downsample
        canvas.axes.plot(df_plot['Timestamp'], df_plot['COMM_TCDL_Margin_dB'], label='TCDL Margin')
        canvas.axes.plot(df_plot['Timestamp'], df_plot['COMM_LOS_Margin_dB'], label='LOS Margin')
        canvas.axes.set_xlabel("Timestamp")
        canvas.axes.set_ylabel("Margin (dB)")
        canvas.axes.set_title("Communication Link Margin vs. Time")
        canvas.axes.legend()
        canvas.axes.grid(True)
        canvas.fig.autofmt_xdate()
        canvas.draw()

    def update_3d_scatter_plot(self):
        if not all([self.x_axis_combo.currentText(), self.y_axis_combo.currentText(), self.z_axis_combo.currentText(), self.color_combo.currentText()]):
            return
            
        canvas = self.scatter_3d_canvas
        canvas.axes.clear()
        df_plot = self.df.iloc[::20, :] # Downsample

        x_col = self.x_axis_combo.currentText()
        y_col = self.y_axis_combo.currentText()
        z_col = self.z_axis_combo.currentText()
        c_col = self.color_combo.currentText()

        scatter = canvas.axes.scatter(df_plot[x_col], df_plot[y_col], df_plot[z_col], 
                                     c=df_plot[c_col], cmap='viridis', s=5)
        canvas.axes.set_xlabel(x_col)
        canvas.axes.set_ylabel(y_col)
        canvas.axes.set_zlabel(z_col)
        canvas.axes.set_title(f"3D Scatter: {z_col} vs. X & Y")
        self.fig_colorbar(canvas, scatter, c_col)
        canvas.draw()
        
    def fig_colorbar(self, canvas, scatter_plot, label):
        # A helper to remove old colorbars before drawing a new one
        if hasattr(canvas, 'colorbar'):
            canvas.colorbar.remove()
        canvas.colorbar = canvas.fig.colorbar(scatter_plot, ax=canvas.axes)
        canvas.colorbar.set_label(label)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())