# Core Python libraries
import sys     # Needed for Qt event loop arguments
import os      # File and directory operations
import subprocess  # Used to run pads.py as an external process
import numpy as np # For RF math operations

# scikit-rf for reading and plotting s2p networks
import skrf as rf

# PyQt6 GUI components
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLineEdit,
    QFileDialog, QVBoxLayout, QLabel, QMessageBox, QHBoxLayout, QFrame
)

# GUI styling imports
from PyQt6.QtGui import QPixmap, QPalette, QBrush, QFont
from PyQt6.QtCore import Qt

# Matplotlib for plotting S-parameters
import matplotlib.pyplot as plt


# MAIN GUI CLASS
class PadExtractorGUI(QWidget):
    def __init__(self):
        super().__init__()

        # Set window title and size
        self.setWindowTitle("RF PAD Extraction Tool")
        self.resize(800, 500)



        # Store file paths
        self.file1_path = None
        self.file2_path = None
        self.output_dir = None

        # CREATE SEMI-TRANSPARENT PANEL
        # This panel contains all buttons and inputs
        panel = QFrame(self)
        panel.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 140);  # Transparent dark background
                border-radius: 15px;
            }
        """)
        panel.setGeometry(50, 50, 330, 400)  # Position and size

        # Create vertical layout inside the panel
        layout = QVBoxLayout(panel)

        # Title text
        title = QLabel("PAD Extraction GUI")
        title.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Button styling
        btn_style = """
            QPushButton {
                background-color: #1e90ff;  # Blue button
                color: white;
                padding: 10px;
                border-radius: 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #63b3ff;  # Lighter blue when hovered
            }
        """

        # FILE 1 BUTTON
        self.btn_file1 = QPushButton("Select File 1 (.s2p)")
        self.btn_file1.setStyleSheet(btn_style)
        self.btn_file1.clicked.connect(self.load_file1)  # Click → load_file1()
        layout.addWidget(self.btn_file1)

        # FILE 2 BUTTON
        self.btn_file2 = QPushButton("Select File 2 (.s2p)")
        self.btn_file2.setStyleSheet(btn_style)
        self.btn_file2.clicked.connect(self.load_file2)
        layout.addWidget(self.btn_file2)

        # OUTPUT DIRECTORY BUTTON
        self.btn_output = QPushButton("Select Output Directory")
        self.btn_output.setStyleSheet(btn_style)
        self.btn_output.clicked.connect(self.load_output_dir)
        layout.addWidget(self.btn_output)

        # USER INPUTS FOR YEAR + LENGTH
        self.year_input = QLineEdit()
        self.year_input.setPlaceholderText("Enter Year (e.g., 2015)")
        self.year_input.setStyleSheet("padding: 8px; border-radius: 6px;")
        layout.addWidget(self.year_input)

        self.length_input = QLineEdit()
        self.length_input.setPlaceholderText("Enter Length (e.g., 600)")
        self.length_input.setStyleSheet("padding: 8px; border-radius: 6px;")
        layout.addWidget(self.length_input)

        # RUN BACKEND BUTTON
        self.btn_run = QPushButton("Run PAD Extraction")
        self.btn_run.setStyleSheet(btn_style)
        self.btn_run.clicked.connect(self.run_backend)
        layout.addWidget(self.btn_run)

        # PLOT BUTTON
        self.btn_plot = QPushButton("Plot S-Parameters of File 1")
        self.btn_plot.setStyleSheet(btn_style)
        self.btn_plot.clicked.connect(self.plot_sparameters)
        layout.addWidget(self.btn_plot)


    # FILE PICKER FUNCTIONS
    def load_file1(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Select File 1", "", "S2P Files (*.s2p *.S2P)"
        )
        if file:
            self.file1_path = file
            self.btn_file1.setText(f"File1: {os.path.basename(file)}")

    def load_file2(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Select File 2", "", "S2P Files (*.s2p *.S2P)"
        )
        if file:
            self.file2_path = file
            self.btn_file2.setText(f"File2: {os.path.basename(file)}")

    def load_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if folder:
            self.output_dir = folder
            self.btn_output.setText(f"Output: {folder}")


    # RUN BACKEND (pads.py)
    def run_backend(self):
        # Ensure user selected all required paths
        if not self.file1_path or not self.file2_path or not self.output_dir:
            QMessageBox.warning(self, "Error", "Please select both files and an output directory.")
            return

        # Validate year and length input
        try:
            year = int(self.year_input.text())
            length = int(self.length_input.text())
        except ValueError:
            QMessageBox.warning(self, "Error", "Year and Length must be numbers.")
            return

        # Run pads.py with arguments in a separate process
        result = subprocess.run(
            [
                "C:\\Users\\User\\AppData\\Local\\Programs\\Python\\Python311\\python.exe", # Python path
                "pads.py",     # Script to run
                self.file1_path,
                self.file2_path,
                str(year),
                str(length)
            ],
            capture_output=True,  # Capture stdout/stderr
            text=True             # Decode output as text
        )

        # If backend failed, show error message
        if result.returncode != 0:
            QMessageBox.warning(self, "Error", result.stderr)
            return

        # pads.py prints two filenames on two lines
        output_lines = result.stdout.strip().splitlines()
        if len(output_lines) < 2:
            QMessageBox.warning(self, "Error", "Backend did not return valid output.")
            return

        left_name = output_lines[0]   # e.g., left_pad_2015_600.s2p
        right_name = output_lines[1]  # e.g., right_pad_2015_600.s2p

        # Destination paths
        left_out = os.path.join(self.output_dir, left_name)
        right_out = os.path.join(self.output_dir, right_name)

        # Move output files into the chosen folder
        if os.path.exists(left_name):
            os.rename(left_name, left_out)
        if os.path.exists(right_name):
            os.rename(right_name, right_out)

        QMessageBox.information(
            self,
            "Success",
            f"PAD extraction completed!\nSaved to:\n{left_out}\n{right_out}"
        )


    # -----------------------------
    # PLOTTING FUNCTION
    # -----------------------------
    def plot_sparameters(self):
        # Ensure file 1 is selected
        if not self.file1_path:
            QMessageBox.warning(self, "Error", "Select File 1 first.")
            return

        # Load s2p file using scikit-rf
        ntw = rf.Network(self.file1_path)

        # Create plot window
        plt.figure(figsize=(8, 5))
        ntw.plot_s_db(m=0, n=0, label="S11")  # Plot S11 magnitude in dB
        ntw.plot_s_db(m=1, n=0, label="S21")  # Plot S21 magnitude in dB
        plt.title("S-Parameters (dB)")
        plt.legend()
        plt.grid()
        plt.show()


# -----------------------------
# RUN THE APPLICATION
# -----------------------------
app = QApplication(sys.argv)
gui = PadExtractorGUI()
gui.show()
sys.exit(app.exec())
