import os
import sys
import struct
import datetime
from PyQt5 import QtCore,QtGui,QtWidgets


class DepthControlBtnWin(QtWidgets.QWidget):
    _signal = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(DepthControlBtnWin, self).__init__(parent)
        self.init_ui()

 
    def init_ui(self):

        button_width = 100
        button_height = 25

        # 窗口设置
        self.setFixedSize(600, 320)  # 设置窗体大小
        self.setWindowTitle('深度控制')  # 设置窗口标题
        self.setObjectName('depth_control_window')

        self.main_layout = QtWidgets.QGridLayout()
        self.setLayout(self.main_layout)

        # 布局
        self.depth_mannual_control_fixed_label = QtWidgets.QLabel('手动控制区')
        self.depth_mannual_control_fixed_label.setObjectName('manual_cotrol_label')
        self.main_layout.addWidget(self.depth_mannual_control_fixed_label, 0, 0, 1, 1, QtCore.Qt.AlignLeft)

        self.depth_mannual_control_layout = QtWidgets.QGridLayout()
        self.depth_mannual_control_frame = QtWidgets.QFrame()
        self.main_layout.addWidget(self.depth_mannual_control_frame, 1,0,1,1, QtCore.Qt.AlignCenter)
        self.depth_mannual_control_frame.setLayout(self.depth_mannual_control_layout)

        #
        self.dmctl_both_ballast_fixed_label = QtWidgets.QLabel('两侧Ballast位移: ')
        self.depth_mannual_control_layout.addWidget(self.dmctl_both_ballast_fixed_label, 0, 0, 1, 1, QtCore.Qt.AlignCenter)

        self.dmctl_both_ballast_silder = QtWidgets.QSlider(QtCore.Qt.Horizontal) #水平方向
        self.dmctl_both_ballast_silder.setMinimum(0)#设置最小值
        self.dmctl_both_ballast_silder.setMaximum(50)#设置最大值
        self.dmctl_both_ballast_silder.setSingleStep(1)#设置步长值
        self.dmctl_both_ballast_silder.setValue(25)#设置当前值
        # self.dmctl_both_ballast_silder.setTickPosition(QtWidgets.QSlider.TicksBelow)#设置刻度位置，在下方
        # self.dmctl_both_ballast_silder.setTickInterval(5)#设置刻度间隔
        self.dmctl_both_ballast_silder.setFixedSize(200,20)
        self.depth_mannual_control_layout.addWidget(self.dmctl_both_ballast_silder, 0, 1, 1, 4)
        self.dmctl_both_ballast_silder.valueChanged.connect(self.bslider_value_change_slot)

        self.dmctl_both_ballast_value_label = QtWidgets.QLabel('位移: '+str(self.dmctl_both_ballast_silder.value())+'mm')
        self.depth_mannual_control_layout.addWidget(self.dmctl_both_ballast_value_label, 0, 5, 1, 2, QtCore.Qt.AlignCenter)
        self.dmctl_both_ballast_value_label.setFixedSize(110,30)

        self.dmctl_both_ballast_button = QtWidgets.QPushButton('发送数据')
        self.depth_mannual_control_layout.addWidget(self.dmctl_both_ballast_button, 0, 7, 1, 1, QtCore.Qt.AlignCenter)
        self.dmctl_both_ballast_button.setFixedSize(80,30)
        self.dmctl_both_ballast_button.setObjectName('SET_BALLAST_POS')
 
        #
        self.dmctl_left_ballast_fixed_label = QtWidgets.QLabel('左侧Ballast位移: ')
        self.depth_mannual_control_layout.addWidget(self.dmctl_left_ballast_fixed_label, 1, 0, 1, 1, QtCore.Qt.AlignCenter)

        self.dmctl_left_ballast_silder =  QtWidgets.QSlider(QtCore.Qt.Horizontal) #水平方向
        self.dmctl_left_ballast_silder.setMinimum(0)#设置最小值
        self.dmctl_left_ballast_silder.setMaximum(50)#设置最大值
        self.dmctl_left_ballast_silder.setSingleStep(1)#设置步长值
        self.dmctl_left_ballast_silder.setValue(25)#设置当前值
        # self.dmctl_left_ballast_silder.setTickPosition(QtWidgets.QSlider.TicksBelow)#设置刻度位置，在下方
        # self.dmctl_left_ballast_silder.setTickInterval(5)#设置刻度间隔
        self.dmctl_left_ballast_silder.setFixedSize(200,20)
        self.depth_mannual_control_layout.addWidget(self.dmctl_left_ballast_silder, 1, 1, 1, 4)
        self.dmctl_left_ballast_silder.valueChanged.connect(self.lslider_value_change_slot)

        self.dmctl_left_ballast_value_label = QtWidgets.QLabel('位移: '+str(self.dmctl_left_ballast_silder.value())+'mm')
        self.depth_mannual_control_layout.addWidget(self.dmctl_left_ballast_value_label, 1, 5, 1, 2, QtCore.Qt.AlignCenter)
        self.dmctl_left_ballast_value_label.setFixedSize(110,30)

        self.dmctl_left_ballast_button = QtWidgets.QPushButton('发送数据')
        self.depth_mannual_control_layout.addWidget(self.dmctl_left_ballast_button, 1, 7, 1, 1, QtCore.Qt.AlignCenter)
        self.dmctl_left_ballast_button.setFixedSize(80,30)
        self.dmctl_left_ballast_button.setObjectName('SET_LEFTBALLAST_POS')
        #
        self.dmctl_right_ballast_fixed_label = QtWidgets.QLabel('右侧Ballast位移: ')
        self.depth_mannual_control_layout.addWidget(self.dmctl_right_ballast_fixed_label, 2, 0, 1, 1, QtCore.Qt.AlignCenter)

        self.dmctl_right_ballast_silder =  QtWidgets.QSlider(QtCore.Qt.Horizontal) #水平方向
        self.dmctl_right_ballast_silder.setMinimum(0)#设置最小值
        self.dmctl_right_ballast_silder.setMaximum(50)#设置最大值
        self.dmctl_right_ballast_silder.setSingleStep(1)#设置步长值
        self.dmctl_right_ballast_silder.setValue(25)#设置当前值
        # self.dmctl_right_ballast_silder.setTickPosition(QtWidgets.QSlider.TicksBelow)#设置刻度位置，在下方
        # self.dmctl_right_ballast_silder.setTickInterval(5)#设置刻度间隔
        self.dmctl_right_ballast_silder.setFixedSize(200,20)
        self.depth_mannual_control_layout.addWidget(self.dmctl_right_ballast_silder, 2, 1, 1, 4)
        self.dmctl_right_ballast_silder.valueChanged.connect(self.rslider_value_change_slot)

        self.dmctl_right_ballast_value_label = QtWidgets.QLabel('位移: '+str(self.dmctl_right_ballast_silder.value())+'mm')
        self.depth_mannual_control_layout.addWidget(self.dmctl_right_ballast_value_label, 2, 5, 1, 2, QtCore.Qt.AlignCenter)
        self.dmctl_right_ballast_value_label.setFixedSize(110,30)

        self.dmctl_right_ballast_button = QtWidgets.QPushButton('发送数据')
        self.depth_mannual_control_layout.addWidget(self.dmctl_right_ballast_button, 2, 7, 1, 1, QtCore.Qt.AlignCenter)
        self.dmctl_right_ballast_button.setFixedSize(80,30)
        self.dmctl_right_ballast_button.setObjectName("SET_RIGHTTBALLAST_POS")


        self.depth_auto_control_fixed_label = QtWidgets.QLabel('自动控制区')
        self.depth_auto_control_fixed_label.setObjectName('auto_cotrol_label')
        self.main_layout.addWidget(self.depth_auto_control_fixed_label, 2, 0, 1, 1, QtCore.Qt.AlignLeft)

        self.depth_auto_control_layout = QtWidgets.QGridLayout()
        self.depth_auto_control_frame = QtWidgets.QFrame()
        self.main_layout.addWidget(self.depth_auto_control_frame, 3,0,1,1, QtCore.Qt.AlignCenter)
        self.depth_auto_control_frame.setLayout(self.depth_auto_control_layout)

        # 美化UI界面
        with open('qss/depth_control_win.qss') as f:
            qss = f.read()
        self.setStyleSheet(qss)

    def bslider_value_change_slot(self):
        self.dmctl_both_ballast_value_label.setText('位移: '+str(self.dmctl_both_ballast_silder.value())+'mm')

    def lslider_value_change_slot(self):
        self.dmctl_left_ballast_value_label.setText('位移: '+str(self.dmctl_left_ballast_silder.value())+'mm')

    def rslider_value_change_slot(self):
        self.dmctl_right_ballast_value_label.setText('位移: '+str(self.dmctl_right_ballast_silder.value())+'mm')

    def handle_click(self):
        if not self.isVisible():
            self.show()


    def handle_close(self):
        self.close()
