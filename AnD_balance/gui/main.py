# AnD_balance/gui/balance_gui.py
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QLineEdit, QFileDialog, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QHBoxLayout, QShortcut, QVBoxLayout
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QPainter, QIcon

from sqlmodel import SQLModel, create_engine, Session
from .db import BuoyantWeight

import os
import pkg_resources
import json
import pandas as pd
import numpy as np
from datetime import datetime

from AnD_balance.balance import FX_Balance

class DummyBalance:
    def get_weight(self):
        return 1.2345, 'g', 'Stable'
    
class DummyTemp:
    # def __init__(self):
    #     raise ValueError
    def read(self):
        return np.random.normal(22,1)

class StatusLED(QWidget):
    clicked = pyqtSignal()  # Define a custom signal
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.off()
        self.status = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setBrush(self.color)
        
        x = int(self.width() * 0.1)
        width = int(self.width() * 0.8)
        y = int(self.height() * 0.1)
        height = int(self.height() * 0.8)
        
        painter.drawEllipse(x, y, width, height)

    def setColor(self, color):
        self.color = color
        self.update()  # Trigger a repaint
    
    def on(self):
        self.setColor(QColor(0,255,0))  # set green
        self.status = True
        
    def off(self):
        self.setColor(QColor(255, 0, 0))  # set red
        self.status = False
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()  # Emit the custom signal

    def isOn(self):
        return self.status

class BalanceGUI(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle('Buoyant Weights')
        self.resize(800, 600)
        self.setWindowIcon(QIcon(pkg_resources.resource_filename('AnD_balance', 'gui/icon.png')))
        
        self._temp_file = pkg_resources.resource_filename('AnD_balance', 'gui/temp.json')
        with open(self._temp_file, 'r') as f:
            self._temp_data = json.load(f)

        self.layout = QVBoxLayout()
        # self.layout = QGridLayout()
        # self.layout.setRowStretch(1, 1)
        self.setLayout(self.layout)
        
        self.db_path = None
        self.data_table = None
        self.data = None
        
        self.data_model = BuoyantWeight
       
        self.make_fields()
        
        self.select_db_file()

        self.balance = None
        self.temp_probe = None
        
        self.balance_timer = QTimer()
        self.balance_timer.timeout.connect(self.init_balance)
        self.balance_timer.start(1000)  # Run init_balance every 1000 milliseconds
        
        self.temp_probe_timer = QTimer()
        self.temp_probe_timer.timeout.connect(self.init_temp_probe)
        self.temp_probe_timer.start(1000)
        
        self.init_balance()
        self.init_temp_probe()
        
    def init_balance(self):
        try:
            self.balance = FX_Balance()
            self.balance_LED.on()
            self.balance_timer.stop()
            print('balance initialized')
            return
        except:
            pass
        
    def init_temp_probe(self):
        try:
            self.temp_probe = DummyTemp()
            self.temp_LED.on()
            self.temp_probe_timer.stop()
            print('temp probe initialized')
            return
        except:
            print('temp failed')
            self.temperature_checkbox.setChecked(False)
            self.temperature_checkbox.setEnabled(False)
            self.toggle_auto_temp()
            pass
    
    def make_fields(self):
        # first row: database selection
        col = 0
        row_layout = QHBoxLayout()
        
        self.recent_db_files = self._temp_data['recent_db_files']
        self.db_dropdown = QComboBox()
        self.db_dropdown.addItems(self.recent_db_files)
        self.db_dropdown.currentIndexChanged.connect(self.select_db_file)
        row_layout.addWidget(self.db_dropdown)
        row_layout.setStretchFactor(self.db_dropdown, 1)
        col += 3

        self.new_db_button = QPushButton('Open')
        self.new_db_button.clicked.connect(self.choose_db_file)
        row_layout.addWidget(self.new_db_button)
        col += 1
        
        self.new_db_button = QPushButton('New')
        self.new_db_button.clicked.connect(self.new_db_file)
        row_layout.addWidget(self.new_db_button)
        col += 1
        
        self.layout.addLayout(row_layout)
        
        # second row - salinity and temperature
        row_layout = QHBoxLayout()
        self.salinity_label = QLabel('Salinity:')
        self.salinity_field = QLineEdit('35.0')
        self.temperature_label = QLabel('Temperature:')
        self.temperature_field = QLineEdit('20.0')
        self.temperature_checkbox = QCheckBox('auto temp.')
        
        self.temperature_checkbox.setChecked(True)
        self.temperature_field.setEnabled(False)
        self.temperature_checkbox.clicked.connect(self.toggle_auto_temp)   
        
        row_layout.addWidget(self.salinity_label)
        row_layout.addWidget(self.salinity_field)
        row_layout.addWidget(self.temperature_label)
        row_layout.addWidget(self.temperature_field)
        row_layout.addWidget(self.temperature_checkbox)
        
        self.layout.addLayout(row_layout)
        
        # third row: table of measurements
        row_layout = QHBoxLayout()
        self.data_table = QTableWidget()
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        row_layout.addWidget(self.data_table)
        self.layout.addLayout(row_layout)
        self.populate_data_table()


        # # fourth row: measure button
        row_layout = QHBoxLayout()
        
        self.read_button = QPushButton('Read [Ctrl+Space]')
        self.read_button.clicked.connect(self.read)
        self.read_shortcut = QShortcut('Ctrl+Space', self)
        self.read_shortcut.activated.connect(self.read)
        row_layout.addWidget(self.read_button)
        
        self.tare_button = QPushButton('Tare [Ctrl+z]')
        self.tare_button.clicked.connect(self.tare_balance)
        row_layout.addWidget(self.tare_button)
        self.tare_shortcut = QShortcut('Ctrl+z', self)
        self.tare_shortcut.activated.connect(self.tare_balance)
        
        self.layout.addLayout(row_layout)
        
        # # bottom bar: status LEDs
        self.status_bar = QHBoxLayout()
        self.status_bar.addStretch()
        
        self.temp_LED_label = QLabel('Temperature Probe:')
        self.temp_LED = StatusLED()
        self.temp_LED.clicked.connect(self.init_temp_probe)
        self.temp_LED.setFixedSize(10,10)
        self.status_bar.addWidget(self.temp_LED_label)
        self.status_bar.addWidget(self.temp_LED)
        
        self.balance_LED_label = QLabel('Balance:')
        self.balance_LED = StatusLED()
        self.balance_LED.clicked.connect(self.init_balance)
        self.balance_LED.setFixedSize(10,10)
        self.status_bar.addWidget(self.balance_LED_label)
        self.status_bar.addWidget(self.balance_LED)
        
        self.layout.addLayout(self.status_bar)
        

    @pyqtSlot()
    def read(self):
        if self.balance is None:
            return
        
        sample_name = self.get_sample_name()
        timestamp = datetime.now().isoformat()
        
        try:
            mass, unit, status = self.balance.get_weight()
        except:
            self.balance_LED.off()
            return
        
        temperature = self.read_temp()
        
        new_data = {
            'sample': sample_name,
            'mass': mass,
            'unit': unit,
            'status': status,
            'salinity': float(self.salinity_field.text()),
            'temperature': temperature,
            'notes': '',
            'timestamp': timestamp,
        }
    
        if sample_name != '' and mass is not None:
            self.fill_line(new_data)
                        
            self.data.loc[self.id_current] = new_data
            
            with Session(self.db_engine) as db:
                db.add(self.data_model(**new_data))
                db.commit()
            
            self.id_current += 1
            
            self.insert_row()

    @pyqtSlot()
    def tare_balance(self):
        if self.balance is None:
            return
        self.balance.tare()

    @pyqtSlot()
    def read_temp(self):
        if self.temp_probe is None:
            return
        
        if self.temperature_checkbox.isChecked():
            try:
                temperature = self.temp_probe.read()
            except:
                self.temp_LED.off()
                self.toggle_auto_temp()
                return
        else:
            temperature = float(self.temperature_field.text())
        
        print(temperature)
        self.temperature_field.setText(f'{temperature:.2f}')
        return temperature
    
    def toggle_auto_temp(self):
        self.temperature_field.setEnabled(not self.temperature_checkbox.isChecked())
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return:
            self.read()
        else:
            super().keyPressEvent(event)
    
    def fill_line(self, data):
        self.data_table.setItem(0, 0, QTableWidgetItem(data['sample']))
        self.data_table.setItem(0, 1, QTableWidgetItem(str(data['mass'])))
        self.data_table.setItem(0, 2, QTableWidgetItem(data['unit']))
        self.data_table.setItem(0, 3, QTableWidgetItem(data['status']))
        self.data_table.setItem(0, 4, QTableWidgetItem(f"{data['salinity']:.2f}"))
        self.data_table.setItem(0, 5, QTableWidgetItem(f"{data['temperature']:.2f}"))
        self.data_table.setItem(0, 6, QTableWidgetItem(data['timestamp']))
    
    def get_sample_name(self):
        sample_name = self.data_table.item(0, 0)
        if sample_name is not None:
            value = sample_name.text()
            return value
        else:
            return None
    
    def populate_data_table(self):
        if self.data is None:
            return

        nrow, _ = self.data.shape
        colNames = ['sample'] + [c for c in self.data.columns if c not in ['notes', 'sample']]
        ncol = len(colNames)

        self.data_table.setRowCount(nrow)
        self.data_table.setColumnCount(ncol)

        # self.data_table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        self.data_table.setHorizontalHeaderLabels(colNames)
        
        # add data to the table
        prow = 0
        if nrow > 0:
            for i, row_data in self.data.iloc[::-1].iterrows():
                for j, c in enumerate(colNames):
                    self.data_table.setItem(prow, j, QTableWidgetItem(str(row_data[c])))
                prow += 1
        self.data_table.setVerticalHeaderLabels(self.data.index[::-1].astype(str))
        
        self.insert_row()
        
    
    def insert_row(self):
        self.data_table.insertRow(0)
        self.data_table.setVerticalHeaderLabels([str(self.id_current)])
        
        item = QTableWidgetItem()
        item.setBackground(QColor(255, 255, 0))  # RGB color for yellow
        self.data_table.setItem(0, 0, item)
        
        self.data_table.setCurrentCell(0, 0)
    
    def choose_db_file(self):
        self.db_path, _ = QFileDialog.getOpenFileName(self, 'Create File', filter='SQLite Database (*.sqlite)')
        self._new_db_file()
        
    def new_db_file(self):
        self.db_path, _ = QFileDialog.getSaveFileName(self, 'Select File', filter='SQLite Database (*.sqlite)')
        self._new_db_file()

    def _new_db_file(self):
        if self.db_path and self.db_path not in self.recent_db_files:
            self.recent_db_files.append(self.db_path)
            self.db_dropdown.addItem(self.db_path)
            
            self._temp_data['recent_db_files'] = self.recent_db_files
            with open(self._temp_file, 'w') as f:
                json.dump(self._temp_data, f)
            
            self.db_dropdown.setCurrentIndex(self.db_dropdown.count() - 1)
        
        if os.path.exists(self.db_path):
            self.select_db_file()
        else:
            self.connect_db()
    
    def select_db_file(self):
        self.db_path = os.path.expanduser(self.db_dropdown.currentText())
        self.connect_db()
    
    def connect_db(self):
        if self.db_path:            
            self.db_uri = f'sqlite:///{self.db_path}'
            print(self.db_uri)
            self.db_engine = create_engine(self.db_uri)
            SQLModel.metadata.create_all(self.db_engine)
            self.data = pd.read_sql_table('BuoyantWeightData', self.db_engine, parse_dates=False)
            self.data.set_index('id', inplace=True)
            self.id_current = self.data.index.max() + 1
            if np.isnan(self.id_current):
                self.id_current = 0

        else:
            self.data = None
        
        self.populate_data_table()
 
    def disconnectDB(self):
        self.db_engine.disconnect()
        self.data = None        
    
def run():
    app = QApplication([])
    gui = BalanceGUI()
    gui.show()
    app.exec_()

if __name__ == "__main__":
    run()