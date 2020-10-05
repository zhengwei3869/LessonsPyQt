import os
import sys
import struct
import datetime
from PyQt5 import QtCore,QtGui,QtWidgets


class AttachControlBtnWin(QtWidgets.QWidget):
    _signal = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(AttachControlBtnWin, self).__init__(parent)
        self.init_ui()

 
    def init_ui(self):

        # 窗口设置
        self.setFixedSize(640, 280)  # 设置窗体大小
        self.setWindowTitle('吸附控制')  # 设置窗口标题

        self.main_layout = QtWidgets.QGridLayout()
        self.setLayout(self.main_layout)

        # 布局
        self.attach_status_layout = QtWidgets.QGridLayout()
        self.attach_status_frame = QtWidgets.QFrame()
        self.main_layout.addWidget(self.attach_status_frame, 1,0,1,1, QtCore.Qt.AlignCenter)
        self.attach_status_frame.setLayout(self.attach_status_layout)
        self.attach_status_frame.setFrameShape(QtWidgets.QFrame.Box)
        self.attach_status_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.attach_status_frame.setLineWidth(1)

        self.attach_control_layout = QtWidgets.QGridLayout()
        self.attach_control_frame = QtWidgets.QFrame()
        self.main_layout.addWidget(self.attach_control_frame, 3,0,1,1, QtCore.Qt.AlignCenter)
        self.attach_control_frame.setLayout(self.attach_control_layout)
        self.attach_control_frame.setFrameShape(QtWidgets.QFrame.Box)
        self.attach_control_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.attach_control_frame.setLineWidth(1)
    
        # 创建对象
        button_width = 100
        button_height = 25
        pal = QtGui.QPalette()
        ## 吸附状态面板
        self.attach_status_fixed_label = QtWidgets.QLabel('吸附状态')
        self.attach_status_fixed_label.setFont(QtGui.QFont('Microsoft YaHei', 14, QtGui.QFont.Bold))
        self.main_layout.addWidget(self.attach_status_fixed_label, 0, 0, 1, 1, QtCore.Qt.AlignLeft)
        pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.red)
        self.attach_status_fixed_label.setPalette(pal)

        self.pumpstate_fixed_label = QtWidgets.QLabel('水泵状态')
        self.pumpstate_fixed_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.attach_status_layout.addWidget(self.pumpstate_fixed_label, 1, 0, 1, 1, QtCore.Qt.AlignCenter)
        self.pumpstate_fixed_label.setFixedSize(button_width, button_height)

        self.pumpstate_label = QtWidgets.QLabel('关闭')
        self.pumpstate_label.setFont(QtGui.QFont('SimSun', 12))
        self.attach_status_layout.addWidget(self.pumpstate_label, 1, 1, 1, 1, QtCore.Qt.AlignCenter)
        self.pumpstate_label.setFixedSize(button_width, button_height)

        self.pumpinstate_fixed_label = QtWidgets.QLabel('吸水泵')
        self.pumpinstate_fixed_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.attach_status_layout.addWidget(self.pumpinstate_fixed_label, 1, 2, 1, 1, QtCore.Qt.AlignCenter)
        self.pumpinstate_fixed_label.setFixedSize(button_width, button_height)

        self.pumpinstate_label = QtWidgets.QLabel('关闭')
        self.pumpinstate_label.setFont(QtGui.QFont('SimSun', 12))
        self.attach_status_layout.addWidget(self.pumpinstate_label, 1, 3, 1, 1, QtCore.Qt.AlignCenter)
        self.pumpinstate_label.setFixedSize(button_width, button_height)

        self.pumpoutstate_fixed_label = QtWidgets.QLabel('排水泵')
        self.pumpoutstate_fixed_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.attach_status_layout.addWidget(self.pumpoutstate_fixed_label, 1, 4, 1, 1, QtCore.Qt.AlignCenter)
        self.pumpoutstate_fixed_label.setFixedSize(button_width, button_height)

        self.pumpoutstate_label = QtWidgets.QLabel('关闭')
        self.pumpoutstate_label.setFont(QtGui.QFont('SimSun', 12))
        self.attach_status_layout.addWidget(self.pumpoutstate_label, 1, 5, 1, 1, QtCore.Qt.AlignCenter)
        self.pumpoutstate_label.setFixedSize(button_width, button_height)

        self.valvestate_fixed_label = QtWidgets.QLabel('磁阀状态')
        self.valvestate_fixed_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.attach_status_layout.addWidget(self.valvestate_fixed_label, 2, 0, 1, 2, QtCore.Qt.AlignLeft)
        self.valvestate_fixed_label.setFixedSize(button_width, button_height)

        self.valve1state_fixed_label = QtWidgets.QLabel('电磁阀1')
        self.valve1state_fixed_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.attach_status_layout.addWidget(self.valve1state_fixed_label, 2, 2, 1, 1, QtCore.Qt.AlignRight)
        self.valve1state_fixed_label.setFixedSize(button_width, button_height)

        self.valve1state_label = QtWidgets.QLabel('关闭')
        self.valve1state_label.setFont(QtGui.QFont('SimSun', 12))
        self.attach_status_layout.addWidget(self.valve1state_label, 2, 3, 1, 1, QtCore.Qt.AlignCenter)
        self.valve1state_label.setFixedSize(button_width, button_height)

        self.valve2state_fixed_label = QtWidgets.QLabel('电磁阀2')
        self.valve2state_fixed_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.attach_status_layout.addWidget(self.valve2state_fixed_label, 2, 4, 1, 1, QtCore.Qt.AlignRight)
        self.valve2state_fixed_label.setFixedSize(button_width, button_height)

        self.valve2state_label = QtWidgets.QLabel('关闭')
        self.valve2state_label.setFont(QtGui.QFont('SimSun', 12))
        self.attach_status_layout.addWidget(self.valve2state_label, 2, 5, 1, 1, QtCore.Qt.AlignCenter)
        self.valve2state_label.setFixedSize(button_width, button_height)


        ## 吸附控制面板

        self.attach_control_fixed_label = QtWidgets.QLabel('吸附控制')
        self.attach_control_fixed_label.setFont(QtGui.QFont('Microsoft YaHei', 14, QtGui.QFont.Bold))
        self.main_layout.addWidget(self.attach_control_fixed_label, 2, 0, 1, 1, QtCore.Qt.AlignLeft)
        pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.blue)
        self.attach_control_fixed_label.setPalette(pal)

        self.attachcc_attach_button = QtWidgets.QPushButton('吸附')
        self.attach_control_layout.addWidget(self.attachcc_attach_button, 1, 0, 1, 1, QtCore.Qt.AlignCenter)
        self.attachcc_attach_button.setObjectName("GOTO_ATTACH")

        self.attachcc_detach_button = QtWidgets.QPushButton('脱附')
        self.attach_control_layout.addWidget(self.attachcc_detach_button, 1, 1, 1, 1, QtCore.Qt.AlignCenter)
        self.attachcc_detach_button.setObjectName("GOTO_DETACH")

        self.attachcc_v1open_button = QtWidgets.QPushButton('开启阀1')
        self.attach_control_layout.addWidget(self.attachcc_v1open_button, 1, 2, 1, 1, QtCore.Qt.AlignCenter)
        self.attachcc_v1open_button.setObjectName("SET_VALVE1_ON")

        self.attachcc_v1close_button = QtWidgets.QPushButton('关闭阀1')
        self.attach_control_layout.addWidget(self.attachcc_v1close_button, 1, 3, 1, 1, QtCore.Qt.AlignCenter)
        self.attachcc_v1close_button.setObjectName("SET_VALVE1_OFF")

        self.attachcc_v2open_button = QtWidgets.QPushButton('开启阀2')
        self.attach_control_layout.addWidget(self.attachcc_v2open_button, 1, 4, 1, 1, QtCore.Qt.AlignCenter)
        self.attachcc_v2open_button.setObjectName("SET_VALVE2_ON")

        self.attachcc_v2close_button = QtWidgets.QPushButton('关闭阀2')
        self.attach_control_layout.addWidget(self.attachcc_v2close_button, 1, 5, 1, 1, QtCore.Qt.AlignCenter)
        self.attachcc_v2close_button.setObjectName("SET_VALVE2_OFF")

        self.attachcc_pumpopen_button = QtWidgets.QPushButton('开启水泵')
        self.attach_control_layout.addWidget(self.attachcc_pumpopen_button, 2, 0, 1, 1, QtCore.Qt.AlignCenter)
        self.attachcc_pumpopen_button.setObjectName("SET_PUMP_ON")

        self.attachcc_pumpclose_button = QtWidgets.QPushButton('关闭水泵')
        self.attach_control_layout.addWidget(self.attachcc_pumpclose_button, 2, 1, 1, 1, QtCore.Qt.AlignCenter)
        self.attachcc_pumpclose_button.setObjectName("SET_PUMP_OFF")

        self.attachcc_pumpinopen_button = QtWidgets.QPushButton('开启吸水')
        self.attach_control_layout.addWidget(self.attachcc_pumpinopen_button, 2, 2, 1, 1, QtCore.Qt.AlignCenter)
        self.attachcc_pumpinopen_button.setObjectName("SET_PUMP_IN_ON")

        self.attachcc_pumpinclose_button = QtWidgets.QPushButton('关闭吸水')
        self.attach_control_layout.addWidget(self.attachcc_pumpinclose_button, 2, 3, 1, 1, QtCore.Qt.AlignCenter)
        self.attachcc_pumpinclose_button.setObjectName("SET_PUMP_IN_OFF")

        self.attachcc_pumpoutopen_button = QtWidgets.QPushButton('开启排水')
        self.attach_control_layout.addWidget(self.attachcc_pumpoutopen_button, 2, 4, 1, 1, QtCore.Qt.AlignCenter)
        self.attachcc_pumpoutopen_button.setObjectName("SET_PUMP_OUT_ON")

        self.attachcc_pumpoutclose_button = QtWidgets.QPushButton('关闭排水')
        self.attach_control_layout.addWidget(self.attachcc_pumpoutclose_button, 2, 5, 1, 1, QtCore.Qt.AlignCenter)
        self.attachcc_pumpoutclose_button.setObjectName("SET_PUMP_OUT_OFF")


    def handle_click(self):
        if not self.isVisible():
            self.show()


    def handle_close(self):
        self.close()
