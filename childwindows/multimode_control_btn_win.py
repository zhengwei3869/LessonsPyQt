import os
import sys
import struct
import datetime
from PyQt5 import QtCore,QtGui,QtWidgets


class MultiModeControlBtnWin(QtWidgets.QWidget):
    _signal = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(MultiModeControlBtnWin, self).__init__(parent)
        self.pectfin_motion_mode = 0
        self.init_ui()

 
    def init_ui(self):

        # 窗口设置
        self.setFixedSize(800, 750)  # 设置窗体大小
        self.setWindowTitle('多模态控制')  # 设置窗口标题
        self.setObjectName('multimode_control_window')
        # 布局
        self.main_layout = QtWidgets.QGridLayout()
        self.setLayout(self.main_layout)

        # 布局
        ## 尾部运动
        row_cnt = 0
        self.multimode_tail_control_label = QtWidgets.QLabel("尾鳍运动")
        self.multimode_tail_control_label.setObjectName("tail_mode_label")
        self.main_layout.addWidget(self.multimode_tail_control_label, row_cnt,0,1,1, QtCore.Qt.AlignLeft)
        row_cnt = row_cnt + 1
        self.multimode_tail_oscillate_mode_checkbox = QtWidgets.QCheckBox("摆动模态")
        self.main_layout.addWidget(self.multimode_tail_oscillate_mode_checkbox, row_cnt,0,1,1, QtCore.Qt.AlignCenter)
        self.multimode_tail_oscillate_mode_checkbox.setChecked(True)
        self.multimode_tail_offset_mode_checkbox = QtWidgets.QCheckBox("偏置模态")
        self.main_layout.addWidget(self.multimode_tail_offset_mode_checkbox, row_cnt,1,1,1, QtCore.Qt.AlignCenter)
        row_cnt = row_cnt + 1
        self.multimode_tail_cpg_label = QtWidgets.QLabel('摆动CPG参数(频率、幅值、偏移):')
        self.main_layout.addWidget(self.multimode_tail_cpg_label, row_cnt,0,1,3, QtCore.Qt.AlignLeft)
        row_cnt = row_cnt + 1
        self.multimode_tail_cpgfreq_editor = QtWidgets.QLineEdit()
        self.main_layout.addWidget(self.multimode_tail_cpgfreq_editor, row_cnt,0,1,1, QtCore.Qt.AlignCenter)
        self.multimode_tail_cpgfreq_button = QtWidgets.QPushButton("写入频率")
        self.main_layout.addWidget(self.multimode_tail_cpgfreq_button, row_cnt,1,1,1, QtCore.Qt.AlignCenter)
        self.multimode_tail_cpgfreq_button.setObjectName("SET_TAIL_CPG_FREQ")
        self.multimode_tail_cpgamp_editor = QtWidgets.QLineEdit()
        self.main_layout.addWidget(self.multimode_tail_cpgamp_editor, row_cnt,2,1,1, QtCore.Qt.AlignCenter)
        self.multimode_tail_cpgamp_button = QtWidgets.QPushButton("写入幅值")
        self.main_layout.addWidget(self.multimode_tail_cpgamp_button, row_cnt,3,1,1, QtCore.Qt.AlignCenter)
        self.multimode_tail_cpgamp_button.setObjectName("SET_TAIL_CPG_AMP")
        self.multimode_tail_cpgoffset_editor = QtWidgets.QLineEdit()
        self.main_layout.addWidget(self.multimode_tail_cpgoffset_editor, row_cnt,4,1,1, QtCore.Qt.AlignCenter)
        self.multimode_tail_cpgoffset_button = QtWidgets.QPushButton("写入偏移")
        self.main_layout.addWidget(self.multimode_tail_cpgoffset_button, row_cnt,5,1,1, QtCore.Qt.AlignCenter)
        self.multimode_tail_cpgoffset_button.setObjectName("SET_TAIL_CPG_OFFSET")
        self.multimode_tail_oscillate_start_button = QtWidgets.QPushButton("启动")
        self.main_layout.addWidget(self.multimode_tail_oscillate_start_button, row_cnt,6,1,1, QtCore.Qt.AlignCenter)
        self.multimode_tail_oscillate_start_button.setObjectName("SET_TAIL_RUN")
        self.multimode_tail_oscillate_stop_button = QtWidgets.QPushButton("停止")
        self.main_layout.addWidget(self.multimode_tail_oscillate_stop_button, row_cnt,7,1,1, QtCore.Qt.AlignCenter)
        self.multimode_tail_oscillate_stop_button.setObjectName("SET_TAIL_STOP")
        row_cnt = row_cnt + 1
        self.multimode_tail_offset_label = QtWidgets.QLabel('偏置角度:')
        self.main_layout.addWidget(self.multimode_tail_offset_label, row_cnt,0,1,1, QtCore.Qt.AlignCenter)
        self.multimode_tail_offset_slider =  QtWidgets.QSlider(QtCore.Qt.Horizontal) #水平方向
        self.main_layout.addWidget(self.multimode_tail_offset_slider, row_cnt, 1, 1, 5)
        self.multimode_tail_offset_slider.setMinimum(-60)    #设置最小值
        self.multimode_tail_offset_slider.setMaximum(60)   #设置最大值
        self.multimode_tail_offset_slider.setSingleStep(1) #设置步长值
        self.multimode_tail_offset_slider.setValue(0)     #设置当前值
        self.multimode_tail_offset_value_label = QtWidgets.QLabel('0')
        self.main_layout.addWidget(self.multimode_tail_offset_value_label, row_cnt,6,1,1, QtCore.Qt.AlignCenter)
        self.multimode_tail_offset_set_button = QtWidgets.QPushButton("设置")
        self.main_layout.addWidget(self.multimode_tail_offset_set_button, row_cnt,7,1,1, QtCore.Qt.AlignCenter)
        self.multimode_tail_offset_set_button.setObjectName("SET_TAIL_ANGLE")
        ## 胸鳍运动
        row_cnt = row_cnt + 2
        self.multimode_pectfin_control_label = QtWidgets.QLabel('胸鳍运动')
        self.multimode_pectfin_control_label.setObjectName("pectfin_mode_label")
        self.main_layout.addWidget(self.multimode_pectfin_control_label, row_cnt,0,1,1, QtCore.Qt.AlignLeft)
        row_cnt = row_cnt + 1
        self.multimode_pectfin_oscillate_mode_checkbox = QtWidgets.QCheckBox("摆动模态")
        self.main_layout.addWidget(self.multimode_pectfin_oscillate_mode_checkbox, row_cnt,0,1,1, QtCore.Qt.AlignCenter)
        self.multimode_pectfin_oscillate_mode_checkbox.setChecked(True)
        self.multimode_pectfin_backward_mode_checkbox = QtWidgets.QCheckBox("倒游模态")
        self.main_layout.addWidget(self.multimode_pectfin_backward_mode_checkbox, row_cnt,1,1,1, QtCore.Qt.AlignCenter)
        self.multimode_pectfin_upward_mode_checkbox = QtWidgets.QCheckBox("上游模态")
        self.main_layout.addWidget(self.multimode_pectfin_upward_mode_checkbox, row_cnt,2,1,1, QtCore.Qt.AlignCenter)
        self.multimode_pectfin_leftsteer_mode_checkbox = QtWidgets.QCheckBox("差动左转")
        self.main_layout.addWidget(self.multimode_pectfin_leftsteer_mode_checkbox, row_cnt,3,1,1, QtCore.Qt.AlignCenter)
        self.multimode_pectfin_rightsteer_mode_checkbox = QtWidgets.QCheckBox("差动右转")
        self.main_layout.addWidget(self.multimode_pectfin_rightsteer_mode_checkbox, row_cnt,4,1,1, QtCore.Qt.AlignCenter)
        self.multimode_pectfin_offset_mode_checkbox = QtWidgets.QCheckBox("偏置模态")
        self.main_layout.addWidget(self.multimode_pectfin_offset_mode_checkbox, row_cnt,5,1,1, QtCore.Qt.AlignCenter)
        self.multimode_pectfin_independent_mode_checkbox = QtWidgets.QCheckBox("独立控制")
        self.main_layout.addWidget(self.multimode_pectfin_independent_mode_checkbox, row_cnt,6,1,1, QtCore.Qt.AlignCenter)
        self.multimode_pectfin_set_mode_button = QtWidgets.QPushButton("设置模态")
        self.main_layout.addWidget(self.multimode_pectfin_set_mode_button, row_cnt,7,1,1, QtCore.Qt.AlignCenter)
        self.multimode_pectfin_set_mode_button.setObjectName("SET_PECTFIN_MODE")
        row_cnt = row_cnt + 1
        self.multimode_pectfin_cpg_label = QtWidgets.QLabel('胸鳍摆动CPG参数(频率、幅值、偏移):')
        self.main_layout.addWidget(self.multimode_pectfin_cpg_label, row_cnt,0,1,4, QtCore.Qt.AlignLeft)
        row_cnt = row_cnt + 1
        self.multimode_pectfin_cpgfreq_editor = QtWidgets.QLineEdit()
        self.main_layout.addWidget(self.multimode_pectfin_cpgfreq_editor, row_cnt,0,1,1, QtCore.Qt.AlignCenter)
        self.multimode_pectfin_cpgfreq_button = QtWidgets.QPushButton("写入频率")
        self.multimode_pectfin_cpgfreq_button.setObjectName("SET_PECTFIN_CPG_FREQ")
        self.main_layout.addWidget(self.multimode_pectfin_cpgfreq_button, row_cnt,1,1,1, QtCore.Qt.AlignCenter)
        self.multimode_pectfin_cpgamp_editor = QtWidgets.QLineEdit()
        self.main_layout.addWidget(self.multimode_pectfin_cpgamp_editor, row_cnt,2,1,1, QtCore.Qt.AlignCenter)
        self.multimode_pectfin_cpgamp_button = QtWidgets.QPushButton("写入幅值")
        self.main_layout.addWidget(self.multimode_pectfin_cpgamp_button, row_cnt,3,1,1, QtCore.Qt.AlignCenter)
        self.multimode_pectfin_cpgamp_button.setObjectName("SET_PECTFIN_CPG_AMP")
        self.multimode_pectfin_cpgoffset_editor = QtWidgets.QLineEdit()
        self.main_layout.addWidget(self.multimode_pectfin_cpgoffset_editor, row_cnt,4,1,1, QtCore.Qt.AlignCenter)
        self.multimode_pectfin_cpgoffset_button = QtWidgets.QPushButton("写入偏移")
        self.main_layout.addWidget(self.multimode_pectfin_cpgoffset_button, row_cnt,5,1,1, QtCore.Qt.AlignCenter)
        self.multimode_pectfin_cpgoffset_button.setObjectName("SET_PECTFIN_CPG_OFFSET")
        self.multimode_pectfin_oscillate_start_button = QtWidgets.QPushButton("启动")
        self.main_layout.addWidget(self.multimode_pectfin_oscillate_start_button, row_cnt,6,1,1, QtCore.Qt.AlignCenter)
        self.multimode_pectfin_oscillate_start_button.setObjectName("SET_PECTFIN_RUN")
        self.multimode_pectfin_oscillate_stop_button = QtWidgets.QPushButton("停止")
        self.main_layout.addWidget(self.multimode_pectfin_oscillate_stop_button, row_cnt,7,1,1, QtCore.Qt.AlignCenter)
        self.multimode_pectfin_oscillate_stop_button.setObjectName("SET_PECTFIN_STOP")
        row_cnt = row_cnt + 1
        self.multimode_pectfin_offset_label = QtWidgets.QLabel('偏置角度:')
        self.main_layout.addWidget(self.multimode_pectfin_offset_label, row_cnt,0,1,1, QtCore.Qt.AlignCenter)
        self.multimode_pectfin_offset_slider =  QtWidgets.QSlider(QtCore.Qt.Horizontal) #水平方向
        self.main_layout.addWidget(self.multimode_pectfin_offset_slider, row_cnt, 1, 1, 5)
        self.multimode_pectfin_offset_slider.setMinimum(-90)    #设置最小值
        self.multimode_pectfin_offset_slider.setMaximum(90)   #设置最大值
        self.multimode_pectfin_offset_slider.setSingleStep(1) #设置步长值
        self.multimode_pectfin_offset_slider.setValue(0)     #设置当前值
        self.multimode_pectfin_offset_value_label = QtWidgets.QLabel('0')
        self.main_layout.addWidget(self.multimode_pectfin_offset_value_label, row_cnt,6,1,1, QtCore.Qt.AlignCenter)
        self.multimode_pectfin_offset_set_button = QtWidgets.QPushButton("设置")
        self.main_layout.addWidget(self.multimode_pectfin_offset_set_button, row_cnt,7,1,1, QtCore.Qt.AlignCenter)
        self.multimode_pectfin_offset_set_button.setObjectName("SET_PECTFIN_ANGLE")
        row_cnt = row_cnt + 1
        self.multimode_leftpectfin_cpg_label = QtWidgets.QLabel('左胸鳍摆动CPG参数(频率、幅值、偏移):')
        self.main_layout.addWidget(self.multimode_leftpectfin_cpg_label, row_cnt,0,1,4, QtCore.Qt.AlignLeft)
        row_cnt = row_cnt + 1
        self.multimode_leftpectfin_cpgfreq_editor = QtWidgets.QLineEdit()
        self.main_layout.addWidget(self.multimode_leftpectfin_cpgfreq_editor, row_cnt,0,1,1, QtCore.Qt.AlignCenter)
        self.multimode_leftpectfin_cpgfreq_button = QtWidgets.QPushButton("写入频率")
        self.multimode_leftpectfin_cpgfreq_button.setObjectName("SET_LEFTPECTFIN_CPG_FREQ")
        self.main_layout.addWidget(self.multimode_leftpectfin_cpgfreq_button, row_cnt,1,1,1, QtCore.Qt.AlignCenter)
        self.multimode_leftpectfin_cpgamp_editor = QtWidgets.QLineEdit()
        self.main_layout.addWidget(self.multimode_leftpectfin_cpgamp_editor, row_cnt,2,1,1, QtCore.Qt.AlignCenter)
        self.multimode_leftpectfin_cpgamp_button = QtWidgets.QPushButton("写入幅值")
        self.main_layout.addWidget(self.multimode_leftpectfin_cpgamp_button, row_cnt,3,1,1, QtCore.Qt.AlignCenter)
        self.multimode_leftpectfin_cpgamp_button.setObjectName("SET_LEFTPECTFIN_CPG_AMP")
        self.multimode_leftpectfin_cpgoffset_editor = QtWidgets.QLineEdit()
        self.main_layout.addWidget(self.multimode_leftpectfin_cpgoffset_editor, row_cnt,4,1,1, QtCore.Qt.AlignCenter)
        self.multimode_leftpectfin_cpgoffset_button = QtWidgets.QPushButton("写入偏移")
        self.main_layout.addWidget(self.multimode_leftpectfin_cpgoffset_button, row_cnt,5,1,1, QtCore.Qt.AlignCenter)
        self.multimode_leftpectfin_cpgoffset_button.setObjectName("SET_LEFTPECTFIN_CPG_OFFSET")
        self.multimode_leftpectfin_oscillate_start_button = QtWidgets.QPushButton("启动")
        self.main_layout.addWidget(self.multimode_leftpectfin_oscillate_start_button, row_cnt,6,1,1, QtCore.Qt.AlignCenter)
        self.multimode_leftpectfin_oscillate_start_button.setObjectName("SET_LEFTPECTFIN_RUN")
        self.multimode_leftpectfin_oscillate_stop_button = QtWidgets.QPushButton("停止")
        self.main_layout.addWidget(self.multimode_leftpectfin_oscillate_stop_button, row_cnt,7,1,1, QtCore.Qt.AlignCenter)
        self.multimode_leftpectfin_oscillate_stop_button.setObjectName("SET_LEFTPECTFIN_STOP")
        row_cnt = row_cnt + 1
        self.multimode_leftpectfin_offset_label = QtWidgets.QLabel('偏置角度:')
        self.main_layout.addWidget(self.multimode_leftpectfin_offset_label, row_cnt,0,1,1, QtCore.Qt.AlignCenter)
        self.multimode_leftpectfin_offset_slider =  QtWidgets.QSlider(QtCore.Qt.Horizontal) #水平方向
        self.main_layout.addWidget(self.multimode_leftpectfin_offset_slider, row_cnt, 1, 1, 5)
        self.multimode_leftpectfin_offset_slider.setMinimum(-90)    #设置最小值
        self.multimode_leftpectfin_offset_slider.setMaximum(90)   #设置最大值
        self.multimode_leftpectfin_offset_slider.setSingleStep(1) #设置步长值
        self.multimode_leftpectfin_offset_slider.setValue(0)     #设置当前值
        self.multimode_leftpectfin_offset_value_label = QtWidgets.QLabel('0')
        self.main_layout.addWidget(self.multimode_leftpectfin_offset_value_label, row_cnt,6,1,1, QtCore.Qt.AlignCenter)
        self.multimode_leftpectfin_offset_set_button = QtWidgets.QPushButton("设置")
        self.main_layout.addWidget(self.multimode_leftpectfin_offset_set_button, row_cnt,7,1,1, QtCore.Qt.AlignCenter)
        self.multimode_leftpectfin_offset_set_button.setObjectName("SET_LEFTPECTFIN_ANGLE")
        row_cnt = row_cnt + 1
        self.multimode_rightpectfin_cpg_label = QtWidgets.QLabel('右胸鳍摆动CPG参数(频率、幅值、偏移):')
        self.main_layout.addWidget(self.multimode_rightpectfin_cpg_label, row_cnt,0,1,4, QtCore.Qt.AlignLeft)
        row_cnt = row_cnt + 1
        self.multimode_rightpectfin_cpgfreq_editor = QtWidgets.QLineEdit()
        self.main_layout.addWidget(self.multimode_rightpectfin_cpgfreq_editor, row_cnt,0,1,1, QtCore.Qt.AlignCenter)
        self.multimode_rightpectfin_cpgfreq_button = QtWidgets.QPushButton("写入频率")
        self.main_layout.addWidget(self.multimode_rightpectfin_cpgfreq_button, row_cnt,1,1,1, QtCore.Qt.AlignCenter)
        self.multimode_rightpectfin_cpgfreq_button.setObjectName("SET_RIGHTPECTFIN_CPG_FREQ")
        self.multimode_rightpectfin_cpgamp_editor = QtWidgets.QLineEdit()
        self.main_layout.addWidget(self.multimode_rightpectfin_cpgamp_editor, row_cnt,2,1,1, QtCore.Qt.AlignCenter)
        self.multimode_rightpectfin_cpgamp_button = QtWidgets.QPushButton("写入幅值")
        self.main_layout.addWidget(self.multimode_rightpectfin_cpgamp_button, row_cnt,3,1,1, QtCore.Qt.AlignCenter)
        self.multimode_rightpectfin_cpgamp_button.setObjectName("SET_RIGHTPECTFIN_CPG_AMP")
        self.multimode_rightpectfin_cpgoffset_editor = QtWidgets.QLineEdit()
        self.main_layout.addWidget(self.multimode_rightpectfin_cpgoffset_editor, row_cnt,4,1,1, QtCore.Qt.AlignCenter)
        self.multimode_rightpectfin_cpgoffset_button = QtWidgets.QPushButton("写入偏移")
        self.main_layout.addWidget(self.multimode_rightpectfin_cpgoffset_button, row_cnt,5,1,1, QtCore.Qt.AlignCenter)
        self.multimode_rightpectfin_cpgoffset_button.setObjectName("SET_RIGHTPECTFIN_CPG_OFFSET")
        self.multimode_rightpectfin_oscillate_start_button = QtWidgets.QPushButton("启动")
        self.main_layout.addWidget(self.multimode_rightpectfin_oscillate_start_button, row_cnt,6,1,1, QtCore.Qt.AlignCenter)
        self.multimode_rightpectfin_oscillate_start_button.setObjectName("SET_RIGHTPECTFIN_RUN")
        self.multimode_rightpectfin_oscillate_stop_button = QtWidgets.QPushButton("停止")
        self.main_layout.addWidget(self.multimode_rightpectfin_oscillate_stop_button, row_cnt,7,1,1, QtCore.Qt.AlignCenter)
        self.multimode_rightpectfin_oscillate_stop_button.setObjectName("SET_RIGHTPECTFIN_STOP")
        row_cnt = row_cnt + 1
        self.multimode_rightpectfin_offset_label = QtWidgets.QLabel('偏置角度:')
        self.main_layout.addWidget(self.multimode_rightpectfin_offset_label, row_cnt,0,1,1, QtCore.Qt.AlignCenter)
        self.multimode_rightpectfin_offset_slider =  QtWidgets.QSlider(QtCore.Qt.Horizontal) #水平方向
        self.main_layout.addWidget(self.multimode_rightpectfin_offset_slider, row_cnt, 1, 1, 5)
        self.multimode_rightpectfin_offset_slider.setMinimum(-90)    #设置最小值
        self.multimode_rightpectfin_offset_slider.setMaximum(90)   #设置最大值
        self.multimode_rightpectfin_offset_slider.setSingleStep(1) #设置步长值
        self.multimode_rightpectfin_offset_slider.setValue(0)     #设置当前值
        self.multimode_rightpectfin_offset_value_label = QtWidgets.QLabel('0')
        self.main_layout.addWidget(self.multimode_rightpectfin_offset_value_label, row_cnt,6,1,1, QtCore.Qt.AlignCenter)
        self.multimode_rightpectfin_offset_set_button = QtWidgets.QPushButton("设置")
        self.main_layout.addWidget(self.multimode_rightpectfin_offset_set_button, row_cnt,7,1,1, QtCore.Qt.AlignCenter)
        self.multimode_rightpectfin_offset_set_button.setObjectName("SET_RIGHTPECTFIN_ANGLE")
        # 浮力调节
        row_cnt = row_cnt + 2
        self.multimode_ballast_control_label = QtWidgets.QLabel('浮力调节')
        self.multimode_ballast_control_label.setObjectName("ballast_mode_label")
        self.main_layout.addWidget(self.multimode_ballast_control_label, row_cnt,0,1,1, QtCore.Qt.AlignLeft)
        row_cnt = row_cnt + 1
        self.multimode_ballast_combine_mode_checkbox = QtWidgets.QCheckBox("联合控制")
        self.main_layout.addWidget(self.multimode_ballast_combine_mode_checkbox, row_cnt,0,1,1, QtCore.Qt.AlignCenter)
        self.multimode_ballast_combine_mode_checkbox.setChecked(True)    
        self.multimode_ballast_independent_mode_checkbox = QtWidgets.QCheckBox("独立控制")
        self.main_layout.addWidget(self.multimode_ballast_independent_mode_checkbox, row_cnt,1,1,1, QtCore.Qt.AlignCenter)
        row_cnt = row_cnt + 1
        self.multimode_ballast_position_label = QtWidgets.QLabel('滑块位置:')
        self.main_layout.addWidget(self.multimode_ballast_position_label, row_cnt,0,1,1, QtCore.Qt.AlignCenter)
        self.multimode_ballast_position_slider =  QtWidgets.QSlider(QtCore.Qt.Horizontal) #水平方向
        self.main_layout.addWidget(self.multimode_ballast_position_slider, row_cnt, 1, 1, 5)
        self.multimode_ballast_position_slider.setMinimum(-15)    #设置最小值
        self.multimode_ballast_position_slider.setMaximum(15)   #设置最大值
        self.multimode_ballast_position_slider.setSingleStep(1) #设置步长值
        self.multimode_ballast_position_slider.setValue(0)     #设置当前值
        self.multimode_ballast_position_value_label = QtWidgets.QLabel('0')
        self.main_layout.addWidget(self.multimode_ballast_position_value_label, row_cnt,6,1,1, QtCore.Qt.AlignCenter)
        self.multimode_ballast_position_set_button = QtWidgets.QPushButton("设置")
        self.main_layout.addWidget(self.multimode_ballast_position_set_button, row_cnt,7,1,1, QtCore.Qt.AlignCenter)
        self.multimode_ballast_position_set_button.setObjectName("SET_BALLAST_POS")
        row_cnt = row_cnt + 1
        self.multimode_leftballast_position_label = QtWidgets.QLabel('左侧滑块位置:')
        self.main_layout.addWidget(self.multimode_leftballast_position_label, row_cnt,0,1,1, QtCore.Qt.AlignCenter)
        self.multimode_leftballast_position_slider =  QtWidgets.QSlider(QtCore.Qt.Horizontal) #水平方向
        self.main_layout.addWidget(self.multimode_leftballast_position_slider, row_cnt, 1, 1, 5)
        self.multimode_leftballast_position_slider.setMinimum(-15)    #设置最小值
        self.multimode_leftballast_position_slider.setMaximum(15)   #设置最大值
        self.multimode_leftballast_position_slider.setSingleStep(1) #设置步长值
        self.multimode_leftballast_position_slider.setValue(0)     #设置当前值
        self.multimode_leftballast_position_value_label = QtWidgets.QLabel('0')
        self.main_layout.addWidget(self.multimode_leftballast_position_value_label, row_cnt,6,1,1, QtCore.Qt.AlignCenter)
        self.multimode_leftballast_position_set_button = QtWidgets.QPushButton("设置")
        self.main_layout.addWidget(self.multimode_leftballast_position_set_button, row_cnt,7,1,1, QtCore.Qt.AlignCenter)
        self.multimode_leftballast_position_set_button.setObjectName("SET_LEFTBALLAST_POS")
        row_cnt = row_cnt + 1
        self.multimode_rightballast_position_label = QtWidgets.QLabel('右侧滑块位置:')
        self.main_layout.addWidget(self.multimode_rightballast_position_label, row_cnt,0,1,1, QtCore.Qt.AlignCenter)
        self.multimode_rightballast_position_slider =  QtWidgets.QSlider(QtCore.Qt.Horizontal) #水平方向
        self.main_layout.addWidget(self.multimode_rightballast_position_slider, row_cnt, 1, 1, 5)
        self.multimode_rightballast_position_slider.setMinimum(-15)    #设置最小值
        self.multimode_rightballast_position_slider.setMaximum(15)   #设置最大值
        self.multimode_rightballast_position_slider.setSingleStep(1) #设置步长值
        self.multimode_rightballast_position_slider.setValue(0)     #设置当前值
        self.multimode_rightballast_position_value_label = QtWidgets.QLabel('0')
        self.main_layout.addWidget(self.multimode_rightballast_position_value_label, row_cnt,6,1,1, QtCore.Qt.AlignCenter)
        self.multimode_rightballast_position_set_button = QtWidgets.QPushButton("设置")
        self.main_layout.addWidget(self.multimode_rightballast_position_set_button, row_cnt,7,1,1, QtCore.Qt.AlignCenter)
        self.multimode_rightballast_position_set_button.setObjectName("SET_RIGHTBALLAST_POS")

        # 相机运动
        row_cnt = row_cnt + 2
        self.multimode_camera_control_label = QtWidgets.QLabel('相机运动')
        self.multimode_camera_control_label.setObjectName("camera_mode_label")
        self.main_layout.addWidget(self.multimode_camera_control_label, row_cnt,0,1,1, QtCore.Qt.AlignLeft)
        row_cnt = row_cnt + 1
        self.multimode_camera_angle_label = QtWidgets.QLabel('相机偏转角度:')
        self.main_layout.addWidget(self.multimode_camera_angle_label, row_cnt,0,1,1, QtCore.Qt.AlignCenter)
        self.multimode_camera_angle_slider =  QtWidgets.QSlider(QtCore.Qt.Horizontal) #水平方向
        self.main_layout.addWidget(self.multimode_camera_angle_slider, row_cnt, 1, 1, 5)
        self.multimode_camera_angle_slider.setMinimum(-90)    #设置最小值
        self.multimode_camera_angle_slider.setMaximum(90)   #设置最大值
        self.multimode_camera_angle_slider.setSingleStep(1) #设置步长值
        self.multimode_camera_angle_slider.setValue(0)     #设置当前值
        self.multimode_camera_angle_value_label = QtWidgets.QLabel('0')
        self.main_layout.addWidget(self.multimode_camera_angle_value_label, row_cnt,6,1,1, QtCore.Qt.AlignCenter)
        self.multimode_camera_angle_set_button = QtWidgets.QPushButton("设置")
        self.main_layout.addWidget(self.multimode_camera_angle_set_button, row_cnt,7,1,1, QtCore.Qt.AlignCenter)
        self.multimode_camera_angle_set_button.setObjectName("SET_CAMERA_ANGLE")
        # 吸附控制
        row_cnt = row_cnt + 2
        self.multimode_adhesive_control_label = QtWidgets.QLabel('吸附运动')
        self.multimode_adhesive_control_label.setObjectName("adhesive_mode_label")
        self.main_layout.addWidget(self.multimode_adhesive_control_label, row_cnt,0,1,1, QtCore.Qt.AlignLeft)
        row_cnt = row_cnt + 1
        self.multimode_pumpon_button = QtWidgets.QPushButton("水泵开启")
        self.main_layout.addWidget(self.multimode_pumpon_button, row_cnt,0,1,1, QtCore.Qt.AlignCenter)
        self.multimode_pumpon_button.setObjectName("SET_PUMP_ON")
        self.multimode_pumpoff_button = QtWidgets.QPushButton("水泵关闭")
        self.main_layout.addWidget(self.multimode_pumpoff_button, row_cnt,1,1,1, QtCore.Qt.AlignCenter)
        self.multimode_pumpoff_button.setObjectName("SET_PUMP_OFF")
        self.multimode_valveon_button = QtWidgets.QPushButton("电磁阀开启")
        self.main_layout.addWidget(self.multimode_valveon_button, row_cnt,2,1,1, QtCore.Qt.AlignCenter)
        self.multimode_valveon_button.setObjectName("SET_VALVE_ON")
        self.multimode_valveoff_button = QtWidgets.QPushButton("电磁阀关闭")
        self.main_layout.addWidget(self.multimode_valveoff_button, row_cnt,3,1,1, QtCore.Qt.AlignCenter)
        self.multimode_valveoff_button.setObjectName("SET_VALVE_OFF")

        # 连接
        self.multimode_tail_oscillate_mode_checkbox.stateChanged.connect(self.tail_oscillate_mode_checkbox_ctl)
        self.multimode_tail_offset_mode_checkbox.stateChanged.connect(self.tail_offset_mode_checkbox_ctl)
        self.multimode_pectfin_oscillate_mode_checkbox.stateChanged.connect(self.pectfin_oscillate_mode_checkbox_ctl)
        self.multimode_pectfin_backward_mode_checkbox.stateChanged.connect(self.pectfin_backward_mode_checkbox_ctl)
        self.multimode_pectfin_upward_mode_checkbox.stateChanged.connect(self.pectfin_upward_mode_checkbox_ctl)
        self.multimode_pectfin_leftsteer_mode_checkbox.stateChanged.connect(self.pectfin_leftsteer_mode_checkbox_ctl)
        self.multimode_pectfin_rightsteer_mode_checkbox.stateChanged.connect(self.pectfin_rightsteer_mode_checkbox_ctl)
        self.multimode_pectfin_offset_mode_checkbox.stateChanged.connect(self.pectfin_offset_mode_checkbox_ctl)
        self.multimode_pectfin_independent_mode_checkbox.stateChanged.connect(self.pectfin_independent_mode_checkbox_ctl)
        self.multimode_ballast_combine_mode_checkbox.stateChanged.connect(self.ballast_combine_mode_checkbox_ctl)
        self.multimode_ballast_independent_mode_checkbox.stateChanged.connect(self.ballast_independent_mode_checkbox_ctl)
        self.multimode_tail_offset_slider.valueChanged.connect(self.tail_offset_slider_slot)
        self.multimode_pectfin_offset_slider.valueChanged.connect(self.pectfin_offset_slider_slot)
        self.multimode_leftpectfin_offset_slider.valueChanged.connect(self.leftpectfin_offset_slider_slot)
        self.multimode_rightpectfin_offset_slider.valueChanged.connect(self.rightpectfin_offset_slider_slot)
        self.multimode_ballast_position_slider.valueChanged.connect(self.ballast_position_slider_slot)
        self.multimode_leftballast_position_slider.valueChanged.connect(self.leftballast_position_slider_slot)
        self.multimode_rightballast_position_slider.valueChanged.connect(self.rightballast_position_slider_slot)
        self.multimode_camera_angle_slider.valueChanged.connect(self.camera_angle_slider_slot)
        self.tail_offset_slider_slot()
        self.pectfin_offset_slider_slot()
        self.leftpectfin_offset_slider_slot()
        self.rightpectfin_offset_slider_slot()
        self.ballast_position_slider_slot()
        self.leftballast_position_slider_slot()
        self.rightballast_position_slider_slot()
        self.camera_angle_slider_slot()
        self.tail_oscillate_mode_checkbox_ctl()
        self.pectfin_oscillate_mode_checkbox_ctl()
        self.ballast_combine_mode_checkbox_ctl()

        # 美化UI界面
        with open('qss/multimode_control_btn_win.qss') as f:
            qss = f.read()
        self.setStyleSheet(qss)

    # 下面的代码都不用看，毫无意义，只是一些简单的逻辑
    def tail_offset_slider_slot(self):
        self.multimode_tail_offset_value_label.setText(str(self.multimode_tail_offset_slider.value()) + ' deg')

    def pectfin_offset_slider_slot(self):
        self.multimode_pectfin_offset_value_label.setText(str(self.multimode_pectfin_offset_slider.value()) + ' deg')
    
    def leftpectfin_offset_slider_slot(self):
        self.multimode_leftpectfin_offset_value_label.setText(str(self.multimode_leftpectfin_offset_slider.value()) + ' deg')
    
    def rightpectfin_offset_slider_slot(self):
        self.multimode_rightpectfin_offset_value_label.setText(str(self.multimode_rightpectfin_offset_slider.value()) + ' deg')

    def ballast_position_slider_slot(self):
        self.multimode_ballast_position_value_label.setText(str(self.multimode_ballast_position_slider.value()) + ' mm')

    def leftballast_position_slider_slot(self):
        self.multimode_leftballast_position_value_label.setText(str(self.multimode_leftballast_position_slider.value()) + ' mm')

    def rightballast_position_slider_slot(self):
        self.multimode_rightballast_position_value_label.setText(str(self.multimode_rightballast_position_slider.value()) + ' mm')

    def camera_angle_slider_slot(self):
        self.multimode_camera_angle_value_label.setText(str(self.multimode_camera_angle_slider.value()) + ' deg')

    # 下面的代码都不用看，毫无意义，只是一些简单的逻辑
    def tail_oscillate_mode_checkbox_ctl(self):
        if self.multimode_tail_oscillate_mode_checkbox.isChecked():
            self.multimode_tail_offset_mode_checkbox.setChecked(False)
            self.multimode_tail_cpgfreq_editor.setEnabled(True)
            self.multimode_tail_cpgfreq_button.setEnabled(True)
            self.multimode_tail_cpgamp_editor.setEnabled(True)
            self.multimode_tail_cpgamp_button.setEnabled(True)
            self.multimode_tail_cpgoffset_editor.setEnabled(True)
            self.multimode_tail_cpgoffset_button.setEnabled(True)
            self.multimode_tail_oscillate_start_button.setEnabled(True)
            self.multimode_tail_oscillate_stop_button.setEnabled(True)
            self.multimode_tail_offset_slider.setEnabled(False)
            self.multimode_tail_offset_set_button.setEnabled(False)

    def tail_offset_mode_checkbox_ctl(self):
        if self.multimode_tail_offset_mode_checkbox.isChecked():
            self.multimode_tail_oscillate_mode_checkbox.setChecked(False)
            self.multimode_tail_cpgfreq_editor.setEnabled(False)
            self.multimode_tail_cpgfreq_button.setEnabled(False)
            self.multimode_tail_cpgamp_editor.setEnabled(False)
            self.multimode_tail_cpgamp_button.setEnabled(False)
            self.multimode_tail_cpgoffset_editor.setEnabled(False)
            self.multimode_tail_cpgoffset_button.setEnabled(False)
            self.multimode_tail_oscillate_start_button.setEnabled(False)
            self.multimode_tail_oscillate_stop_button.setEnabled(False)
            self.multimode_tail_offset_slider.setEnabled(True)
            self.multimode_tail_offset_set_button.setEnabled(True)

    def pectfin_oscillate_mode_checkbox_ctl(self):
        if self.multimode_pectfin_oscillate_mode_checkbox.isChecked():
            self.pectfin_motion_mode = 0
            self.multimode_pectfin_backward_mode_checkbox.setChecked(False)
            self.multimode_pectfin_upward_mode_checkbox.setChecked(False)
            self.multimode_pectfin_leftsteer_mode_checkbox.setChecked(False)
            self.multimode_pectfin_rightsteer_mode_checkbox.setChecked(False)
            self.multimode_pectfin_offset_mode_checkbox.setChecked(False)
            self.pectfin_independent_mode_checkbox_ctl()
      
    def pectfin_backward_mode_checkbox_ctl(self):
        if self.multimode_pectfin_backward_mode_checkbox.isChecked():
            self.pectfin_motion_mode = 1
            self.multimode_pectfin_oscillate_mode_checkbox.setChecked(False)
            self.multimode_pectfin_upward_mode_checkbox.setChecked(False)
            self.multimode_pectfin_leftsteer_mode_checkbox.setChecked(False)
            self.multimode_pectfin_rightsteer_mode_checkbox.setChecked(False)
            self.multimode_pectfin_offset_mode_checkbox.setChecked(False)
            self.pectfin_independent_mode_checkbox_ctl()

    def pectfin_upward_mode_checkbox_ctl(self):
        if self.multimode_pectfin_upward_mode_checkbox.isChecked():
            self.pectfin_motion_mode = 2
            self.multimode_pectfin_oscillate_mode_checkbox.setChecked(False)
            self.multimode_pectfin_leftsteer_mode_checkbox.setChecked(False)
            self.multimode_pectfin_rightsteer_mode_checkbox.setChecked(False)
            self.multimode_pectfin_backward_mode_checkbox.setChecked(False)
            self.multimode_pectfin_offset_mode_checkbox.setChecked(False)
            self.pectfin_independent_mode_checkbox_ctl()

    def pectfin_leftsteer_mode_checkbox_ctl(self):
        if self.multimode_pectfin_leftsteer_mode_checkbox.isChecked():
            self.pectfin_motion_mode = 3
            self.multimode_pectfin_oscillate_mode_checkbox.setChecked(False)
            self.multimode_pectfin_upward_mode_checkbox.setChecked(False)
            self.multimode_pectfin_backward_mode_checkbox.setChecked(False)
            self.multimode_pectfin_offset_mode_checkbox.setChecked(False)
            self.multimode_pectfin_rightsteer_mode_checkbox.setChecked(False)
            self.pectfin_independent_mode_checkbox_ctl()

    def pectfin_rightsteer_mode_checkbox_ctl(self):
        if self.multimode_pectfin_rightsteer_mode_checkbox.isChecked():
            self.pectfin_motion_mode = 4
            self.multimode_pectfin_oscillate_mode_checkbox.setChecked(False)
            self.multimode_pectfin_upward_mode_checkbox.setChecked(False)
            self.multimode_pectfin_backward_mode_checkbox.setChecked(False)
            self.multimode_pectfin_offset_mode_checkbox.setChecked(False)
            self.multimode_pectfin_leftsteer_mode_checkbox.setChecked(False)
            self.pectfin_independent_mode_checkbox_ctl()

    def pectfin_offset_mode_checkbox_ctl(self):
        if self.multimode_pectfin_offset_mode_checkbox.isChecked():
            self.pectfin_motion_mode = 5
            self.multimode_pectfin_oscillate_mode_checkbox.setChecked(False)
            self.multimode_pectfin_upward_mode_checkbox.setChecked(False)
            self.multimode_pectfin_backward_mode_checkbox.setChecked(False)
            self.multimode_pectfin_leftsteer_mode_checkbox.setChecked(False)
            self.multimode_pectfin_rightsteer_mode_checkbox.setChecked(False)
            self.pectfin_independent_mode_checkbox_ctl()

    def pectfin_independent_mode_checkbox_ctl(self):
        if self.multimode_pectfin_independent_mode_checkbox.isChecked():
            self.multimode_pectfin_cpgfreq_editor.setEnabled(False)
            self.multimode_pectfin_cpgfreq_button.setEnabled(False)
            self.multimode_pectfin_cpgamp_editor.setEnabled(False)
            self.multimode_pectfin_cpgamp_button.setEnabled(False)
            self.multimode_pectfin_cpgoffset_editor.setEnabled(False)
            self.multimode_pectfin_cpgoffset_button.setEnabled(False)
            self.multimode_pectfin_oscillate_start_button.setEnabled(False)
            self.multimode_pectfin_oscillate_stop_button.setEnabled(False)
            self.multimode_pectfin_offset_slider.setEnabled(False)
            self.multimode_pectfin_offset_set_button.setEnabled(False)
            self.multimode_leftpectfin_cpgfreq_editor.setEnabled(True)
            self.multimode_leftpectfin_cpgfreq_button.setEnabled(True)
            self.multimode_leftpectfin_cpgamp_editor.setEnabled(True)
            self.multimode_leftpectfin_cpgamp_button.setEnabled(True)
            self.multimode_leftpectfin_cpgoffset_editor.setEnabled(True)
            self.multimode_leftpectfin_cpgoffset_button.setEnabled(True)
            self.multimode_leftpectfin_oscillate_start_button.setEnabled(True)
            self.multimode_leftpectfin_oscillate_stop_button.setEnabled(True)
            self.multimode_leftpectfin_offset_slider.setEnabled(True)
            self.multimode_leftpectfin_offset_set_button.setEnabled(True)
            self.multimode_rightpectfin_cpgfreq_editor.setEnabled(True)
            self.multimode_rightpectfin_cpgfreq_button.setEnabled(True)
            self.multimode_rightpectfin_cpgamp_editor.setEnabled(True)
            self.multimode_rightpectfin_cpgamp_button.setEnabled(True)
            self.multimode_rightpectfin_cpgoffset_editor.setEnabled(True)
            self.multimode_rightpectfin_cpgoffset_button.setEnabled(True)
            self.multimode_rightpectfin_oscillate_start_button.setEnabled(True)
            self.multimode_rightpectfin_oscillate_stop_button.setEnabled(True)
            self.multimode_rightpectfin_offset_slider.setEnabled(True)
            self.multimode_rightpectfin_offset_set_button.setEnabled(True)
        else:
            self.multimode_pectfin_cpgfreq_editor.setEnabled(True)
            self.multimode_pectfin_cpgfreq_button.setEnabled(True)
            self.multimode_pectfin_cpgamp_editor.setEnabled(True)
            self.multimode_pectfin_cpgamp_button.setEnabled(True)
            self.multimode_pectfin_cpgoffset_editor.setEnabled(True)
            self.multimode_pectfin_cpgoffset_button.setEnabled(True)
            self.multimode_pectfin_oscillate_start_button.setEnabled(True)
            self.multimode_pectfin_oscillate_stop_button.setEnabled(True)
            self.multimode_pectfin_offset_slider.setEnabled(True)
            self.multimode_pectfin_offset_set_button.setEnabled(True)
            self.multimode_leftpectfin_cpgfreq_editor.setEnabled(False)
            self.multimode_leftpectfin_cpgfreq_button.setEnabled(False)
            self.multimode_leftpectfin_cpgamp_editor.setEnabled(False)
            self.multimode_leftpectfin_cpgamp_button.setEnabled(False)
            self.multimode_leftpectfin_cpgoffset_editor.setEnabled(False)
            self.multimode_leftpectfin_cpgoffset_button.setEnabled(False)
            self.multimode_leftpectfin_oscillate_start_button.setEnabled(False)
            self.multimode_leftpectfin_oscillate_stop_button.setEnabled(False)
            self.multimode_leftpectfin_offset_slider.setEnabled(False)
            self.multimode_leftpectfin_offset_set_button.setEnabled(False)
            self.multimode_rightpectfin_cpgfreq_editor.setEnabled(False)
            self.multimode_rightpectfin_cpgfreq_button.setEnabled(False)
            self.multimode_rightpectfin_cpgamp_editor.setEnabled(False)
            self.multimode_rightpectfin_cpgamp_button.setEnabled(False)
            self.multimode_rightpectfin_cpgoffset_editor.setEnabled(False)
            self.multimode_rightpectfin_cpgoffset_button.setEnabled(False)
            self.multimode_rightpectfin_oscillate_start_button.setEnabled(False)
            self.multimode_rightpectfin_oscillate_stop_button.setEnabled(False)
            self.multimode_rightpectfin_offset_slider.setEnabled(False)
            self.multimode_rightpectfin_offset_set_button.setEnabled(False)

        if self.multimode_pectfin_offset_mode_checkbox.isChecked():
            self.multimode_pectfin_cpgfreq_editor.setEnabled(False)
            self.multimode_pectfin_cpgfreq_button.setEnabled(False)
            self.multimode_pectfin_cpgamp_editor.setEnabled(False)
            self.multimode_pectfin_cpgamp_button.setEnabled(False)
            self.multimode_pectfin_cpgoffset_editor.setEnabled(False)
            self.multimode_pectfin_cpgoffset_button.setEnabled(False)
            self.multimode_pectfin_oscillate_start_button.setEnabled(False)
            self.multimode_pectfin_oscillate_stop_button.setEnabled(False)
            self.multimode_leftpectfin_cpgfreq_editor.setEnabled(False)
            self.multimode_leftpectfin_cpgfreq_button.setEnabled(False)
            self.multimode_leftpectfin_cpgamp_editor.setEnabled(False)
            self.multimode_leftpectfin_cpgamp_button.setEnabled(False)
            self.multimode_leftpectfin_cpgoffset_editor.setEnabled(False)
            self.multimode_leftpectfin_cpgoffset_button.setEnabled(False)
            self.multimode_leftpectfin_oscillate_start_button.setEnabled(False)
            self.multimode_leftpectfin_oscillate_stop_button.setEnabled(False)
            self.multimode_rightpectfin_cpgfreq_editor.setEnabled(False)
            self.multimode_rightpectfin_cpgfreq_button.setEnabled(False)
            self.multimode_rightpectfin_cpgamp_editor.setEnabled(False)
            self.multimode_rightpectfin_cpgamp_button.setEnabled(False)
            self.multimode_rightpectfin_cpgoffset_editor.setEnabled(False)
            self.multimode_rightpectfin_cpgoffset_button.setEnabled(False)
            self.multimode_rightpectfin_oscillate_start_button.setEnabled(False)
            self.multimode_rightpectfin_oscillate_stop_button.setEnabled(False)
        else:
            self.multimode_pectfin_offset_slider.setEnabled(False)
            self.multimode_pectfin_offset_set_button.setEnabled(False)
            self.multimode_leftpectfin_offset_slider.setEnabled(False)
            self.multimode_leftpectfin_offset_set_button.setEnabled(False)
            self.multimode_rightpectfin_offset_slider.setEnabled(False)
            self.multimode_rightpectfin_offset_set_button.setEnabled(False)

    def ballast_combine_mode_checkbox_ctl(self):
        if self.multimode_ballast_combine_mode_checkbox.isChecked():
            self.multimode_ballast_independent_mode_checkbox.setChecked(False)
            self.multimode_ballast_position_slider.setEnabled(True)
            self.multimode_ballast_position_set_button.setEnabled(True)
            self.multimode_leftballast_position_slider.setEnabled(False)
            self.multimode_leftballast_position_set_button.setEnabled(False)
            self.multimode_rightballast_position_slider.setEnabled(False)
            self.multimode_rightballast_position_set_button.setEnabled(False)

    def ballast_independent_mode_checkbox_ctl(self):
        if self.multimode_ballast_independent_mode_checkbox.isChecked():
            self.multimode_ballast_combine_mode_checkbox.setChecked(False)
            self.multimode_ballast_position_slider.setEnabled(False)
            self.multimode_ballast_position_set_button.setEnabled(False)
            self.multimode_leftballast_position_slider.setEnabled(True)
            self.multimode_leftballast_position_set_button.setEnabled(True)
            self.multimode_rightballast_position_slider.setEnabled(True)
            self.multimode_rightballast_position_set_button.setEnabled(True)
        
    def handle_click(self):
        if not self.isVisible():
            self.show()

    def handle_close(self):
        self.close()
