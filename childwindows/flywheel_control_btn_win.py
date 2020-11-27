import os
import sys
import struct
import datetime
from PyQt5 import QtCore,QtGui,QtWidgets


class FlywheelControlBtnWin(QtWidgets.QWidget):
    _signal = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(FlywheelControlBtnWin, self).__init__(parent)
        self.init_ui()

 
    def init_ui(self):

        # 窗口设置
        self.setFixedSize(380, 220)  # 设置窗体大小
        self.setWindowTitle('飞轮控制')  # 设置窗口标题

        # 布局
        self.main_layout = QtWidgets.QGridLayout()
        self.setLayout(self.main_layout)

         # 布局
        self.flywheel_status_layout = QtWidgets.QGridLayout()
        self.flywheel_status_frame = QtWidgets.QFrame()
        self.main_layout.addWidget(self.flywheel_status_frame, 1,0,1,1, QtCore.Qt.AlignCenter)
        self.flywheel_status_frame.setLayout(self.flywheel_status_layout)
        self.flywheel_status_frame.setFrameShape(QtWidgets.QFrame.Box)
        self.flywheel_status_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.flywheel_status_frame.setLineWidth(1)
        self.flywheel_status_frame.setFixedSize(320, 50)

        self.flywheel_control_layout = QtWidgets.QGridLayout()
        self.flywheel_control_frame = QtWidgets.QFrame()
        self.main_layout.addWidget(self.flywheel_control_frame, 3,0,1,1, QtCore.Qt.AlignCenter)
        self.flywheel_control_frame.setLayout(self.flywheel_control_layout)
        self.flywheel_control_frame.setFrameShape(QtWidgets.QFrame.Box)
        self.flywheel_control_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.flywheel_control_frame.setLineWidth(1)
        self.flywheel_control_frame.setFixedSize(320, 50)

         # 创建对象
        pal = QtGui.QPalette()
        ## 吸附状态面板
        self.flywheel_status_fixed_label = QtWidgets.QLabel('飞轮状态')
        self.flywheel_status_fixed_label.setFont(QtGui.QFont('Microsoft YaHei', 14, QtGui.QFont.Bold))
        self.main_layout.addWidget(self.flywheel_status_fixed_label, 0, 0, 1, 1, QtCore.Qt.AlignLeft)
        pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.red)
        self.flywheel_status_fixed_label.setPalette(pal)

        self.flywheelstate_fixed_label = QtWidgets.QLabel('运行状态')
        self.flywheelstate_fixed_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.flywheel_status_layout.addWidget(self.flywheelstate_fixed_label, 0, 0, 1, 1, QtCore.Qt.AlignCenter)

        self.flywheelstate_label = QtWidgets.QLabel('施工中')
        self.flywheelstate_label.setFont(QtGui.QFont('SimSun', 12))
        self.flywheel_status_layout.addWidget(self.flywheelstate_label, 0, 1, 1, 1, QtCore.Qt.AlignCenter)


        self.flywheel_control_fixed_label = QtWidgets.QLabel('飞轮控制')
        self.flywheel_control_fixed_label.setFont(QtGui.QFont('Microsoft YaHei', 14, QtGui.QFont.Bold))
        self.main_layout.addWidget(self.flywheel_control_fixed_label, 2, 0, 1, 1, QtCore.Qt.AlignLeft)
        pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.blue)
        self.flywheel_control_fixed_label.setPalette(pal)

        self.flywheelcc_start_button = QtWidgets.QPushButton('启动')
        self.flywheel_control_layout.addWidget(self.flywheelcc_start_button, 0, 0, 1, 1, QtCore.Qt.AlignCenter)
        self.flywheelcc_start_button.setObjectName("SET_FLYWHEEL_RUN")

        self.flywheelcc_stop_button = QtWidgets.QPushButton('停止')
        self.flywheel_control_layout.addWidget(self.flywheelcc_stop_button, 0, 1, 1, 1, QtCore.Qt.AlignCenter)
        self.flywheelcc_stop_button.setObjectName("SET_FLYWHEEL_STOP")
        

    def handle_click(self):
        if not self.isVisible():
            self.show()


    def handle_close(self):
        self.close()
