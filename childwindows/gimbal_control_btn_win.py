import os
import sys
import struct
import datetime
from PyQt5 import QtCore,QtGui,QtWidgets


class GimbalControlBtnWin(QtWidgets.QWidget):
    _signal = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(GimbalControlBtnWin, self).__init__(parent)
        self.init_ui()

 
    def init_ui(self):

        # 窗口设置
        self.setFixedSize(480, 300)  # 设置窗体大小
        self.setWindowTitle('云台控制')  # 设置窗口标题
        self.setObjectName('gimbal_control_window')
        # 布局
        self.main_layout = QtWidgets.QGridLayout()
        self.setLayout(self.main_layout)

        # 布局
        self.gimbal_status_layout = QtWidgets.QGridLayout()
        self.gimbal_status_frame = QtWidgets.QFrame()
        self.main_layout.addWidget(self.gimbal_status_frame, 1,0,1,1, QtCore.Qt.AlignCenter)
        self.gimbal_status_frame.setLayout(self.gimbal_status_layout)

        self.gimbal_control_layout = QtWidgets.QGridLayout()
        self.gimbal_control_frame = QtWidgets.QFrame()
        self.main_layout.addWidget(self.gimbal_control_frame, 3,0,1,1, QtCore.Qt.AlignCenter)
        self.gimbal_control_frame.setLayout(self.gimbal_control_layout)


        # 创建对象
        pal = QtGui.QPalette()
        ## 吸附状态面板
        self.gimbal_status_fixed_label = QtWidgets.QLabel('云台状态')
        self.gimbal_status_fixed_label.setObjectName('gimbal_status_fixed_label')
        self.main_layout.addWidget(self.gimbal_status_fixed_label, 0, 0, 1, 1, QtCore.Qt.AlignLeft)
        pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.red)
        self.gimbal_status_fixed_label.setPalette(pal)

        self.gimbalstate_fixed_label = QtWidgets.QLabel('运行状态')
        self.gimbalstate_fixed_label.setObjectName('gimbalstate_fixed_label')
        self.gimbal_status_layout.addWidget(self.gimbalstate_fixed_label, 0, 0, 1, 1, QtCore.Qt.AlignCenter)

        self.gimbalstate_label = QtWidgets.QLabel('未开启')
        self.gimbalstate_label.setObjectName('gimbalstate_label')
        self.gimbal_status_layout.addWidget(self.gimbalstate_label, 0, 1, 1, 1, QtCore.Qt.AlignCenter)


        self.gimbal_control_fixed_label = QtWidgets.QLabel('云台控制')
        self.gimbal_control_fixed_label.setObjectName('gimbal_control_fixed_label')
        self.main_layout.addWidget(self.gimbal_control_fixed_label, 2, 0, 1, 1, QtCore.Qt.AlignLeft)
        pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.blue)
        self.gimbal_control_fixed_label.setPalette(pal)
        
        self.gimbalcc_start_button = QtWidgets.QPushButton('启动')
        self.gimbal_control_layout.addWidget(self.gimbalcc_start_button, 0, 0, 1, 3, QtCore.Qt.AlignCenter)
        self.gimbalcc_start_button.setObjectName("SET_GIMBAL_RUN")
        self.gimbalcc_start_button.setFixedSize(130, 30)

        self.gimbalcc_stop_button = QtWidgets.QPushButton('停止')
        self.gimbal_control_layout.addWidget(self.gimbalcc_stop_button, 0, 3, 1, 3, QtCore.Qt.AlignCenter)
        self.gimbalcc_stop_button.setObjectName("SET_GIMBAL_STOP")
        self.gimbalcc_stop_button.setFixedSize(130, 30)

        self.gimbalcc_zero_button = QtWidgets.QPushButton('归中')
        self.gimbal_control_layout.addWidget(self.gimbalcc_zero_button, 0, 6, 1, 3, QtCore.Qt.AlignCenter)
        self.gimbalcc_zero_button.setObjectName("SET_GIMBAL_ZERO")
        self.gimbalcc_zero_button.setFixedSize(130, 30)


        self.gimbalcc_servo_angle_label = QtWidgets.QLabel('舵机角度')
        self.gimbal_control_layout.addWidget(self.gimbalcc_servo_angle_label, 1, 0, 1, 2, QtCore.Qt.AlignLeft)
        self.gimbalcc_servo_angle_label.setFixedSize(70, 30)

        self.gimbalcc_servo_angle_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal) #水平方向
        self.gimbalcc_servo_angle_slider.setMinimum(0)#设置最小值
        self.gimbalcc_servo_angle_slider.setMaximum(180)#设置最大值
        self.gimbalcc_servo_angle_slider.setSingleStep(1)#设置步长值
        self.gimbalcc_servo_angle_slider.setValue(90)#设置当前值
        self.gimbalcc_servo_angle_slider.setFixedSize(200,20)
        self.gimbal_control_layout.addWidget(self.gimbalcc_servo_angle_slider, 1, 2, 1, 4)
        self.gimbalcc_servo_angle_slider.valueChanged.connect(self.saslider_value_change_slot)

        self.gimbalcc_servo_angle_label = QtWidgets.QLabel('90 deg')
        self.gimbal_control_layout.addWidget(self.gimbalcc_servo_angle_label, 1, 6, 1, 2)
        self.gimbalcc_servo_angle_label.setFixedSize(70, 30)

        self.gimbalcc_set_angle_button = QtWidgets.QPushButton('设置')
        self.gimbal_control_layout.addWidget(self.gimbalcc_set_angle_button, 1, 8, 1, 1, QtCore.Qt.AlignCenter)
        self.gimbalcc_set_angle_button.setObjectName("SET_GIMBAL_ANGLE")
        self.gimbalcc_set_angle_button.setFixedSize(60, 30)
        
        # 美化UI界面
        with open('qss/gimbal_control_win.qss') as f:
            qss = f.read()
        self.setStyleSheet(qss)

    def saslider_value_change_slot(self):
        self.gimbalcc_servo_angle_label.setText(str(self.gimbalcc_servo_angle_slider.value())+' deg')


    def handle_click(self):
        if not self.isVisible():
            self.show()


    def handle_close(self):
        self.close()
