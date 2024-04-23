# AnD_balance/gui/balance_gui.py
from PyQt5.QtWidgets import QApplication, QWidget, QGridLayout, QPushButton, QLabel, QLineEdit, QFileDialog, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QColor, QKeyEvent

from sqlmodel import SQLModel, create_engine, Session
from .db import Weight

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

class BalanceGUI(QWidget):
    def __init__(self):
        super().__init__()
        
        self.resize(800, 600)
        
        self._temp_file = pkg_resources.resource_filename('AnD_balance', 'gui/temp.json')
        with open(self._temp_file, 'r') as f:
            self._temp_data = json.load(f)

        # self.balance = DummyBalance()
        self.balance = FX_Balance()

        self.layout = QGridLayout()
        self.layout.setRowStretch(1, 1)
        self.setLayout(self.layout)
        
        self.db_path = None
        self.data_table = None
        
        self.data_model = Weight
        
        # first row: database selection
        row = 0
        col = 0
        self.recent_db_files = self._temp_data['recent_db_files']
        self.db_dropdown = QComboBox()
        self.db_dropdown.addItems(self.recent_db_files)
        self.db_dropdown.currentIndexChanged.connect(self.select_db_file)
        self.layout.addWidget(self.db_dropdown, row, col, 1, 3)
        col += 3

        self.new_db_button = QPushButton('Choose new file')
        self.new_db_button.clicked.connect(self.choose_db_file)
        self.layout.addWidget(self.new_db_button, row, col, 1, 1)
        col += 1
        
        # third row: table of measurements
        row = 1


        # self.make_data_table(row)

        # last row: measure button
        row = 2
        col = 0
        self.read_button = QPushButton('Read')
        self.read_button.clicked.connect(self.read)
        self.layout.addWidget(self.read_button, row, 0, 1, 4)
        col += 4
        
        self.select_db_file()

    @pyqtSlot()
    def read(self):
        sample_name = self.get_sample_name()
        timestamp = datetime.now().isoformat()
        mass, unit, status = self.balance.get_weight()
        
        new_data = {
            'sample': sample_name,
            'mass': mass,
            'unit': unit,
            'status': status,
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
        self.data_table.setItem(0, 4, QTableWidgetItem(data['timestamp']))
    
    def get_sample_name(self):
        sample_name = self.data_table.item(0, 0)
        if sample_name is not None:
            value = sample_name.text()
            return value
        else:
            return None
    
    def make_data_table(self, row=1):
        if self.data is None:
            return

        nrow, _ = self.data.shape
        colNames = ['sample'] + [c for c in self.data.columns if c not in ['notes', 'sample']]
        ncol = len(colNames)

        col = 0
        
        self.data_table = QTableWidget()
        
        self.data_table.setRowCount(nrow)
        self.data_table.setColumnCount(ncol)

        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # self.data_table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.layout.addWidget(self.data_table, row, col, 1, 4)
        
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
        self.db_path, _ = QFileDialog.getSaveFileName(self, 'Select or Create File', filter='SQLite Database (*.sqlite)')
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
            self.db_engine = create_engine(self.db_uri)
            SQLModel.metadata.create_all(self.db_engine)
            self.data = pd.read_sql_table('WeightData', self.db_engine, parse_dates=False)
            self.data.set_index('id', inplace=True)
            self.id_current = self.data.index.max() + 1
            if np.isnan(self.id_current):
                self.id_current = 0

        else:
            self.data = None
        
        self.make_data_table()
 
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