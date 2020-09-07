import sys
import time
import serial
import struct
import copy
import platform

from PyQt5 import QtCore,QtGui,QtWidgets

import matplotlib
matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

###
### 自定义模块
import analysis_btn_win # 解析数据窗口
import storage_btn_win # 储存数据窗口
import sendback_btn_win # 回传数据窗口
import rflink # Robotic Fish 通讯协议
import serctl # 串口控制工具
import remorastate # 机器人状态
import sensor_data_canvas

###
### 类对象
# 机器人状态
roboremora = remorastate.RoboRemoraState()
# 串口类
send_sertool = serctl.RemoraSerial()
recv_sertool = serctl.RemoraSerial()
# rf通讯协议类
rftool = rflink.RFLink()



###
### 多线程变量
# 机器人状态线程锁
rm_mutex = QtCore.QMutex()
# 串口线程锁
ser_mutex = QtCore.QMutex()
# 通讯线程锁
rf_mutex = QtCore.QMutex()
rf_cond = QtCore.QWaitCondition()
# 绘图线程锁
plt_mutex = QtCore.QMutex()


#########################################################################################################
def analysis_data(databytes,datalen): # 分析串口接收到的rflink数据,更新roboremora的状态
    """
    本函数将串口接收到的rflink数据进行分析,解码出收到的Command,更新roboremora的状态
    :param databytes: byte类型数据串
    :param datalen: 数据串长度
    :return: 收到Command的ID
    """
    global roboremora

    try:
        command_id = databytes[0]
    except IndexError:
        return rflink.Command.LAST_COMMAND_FLAG.value

    command = rflink.Command(command_id)
    if command is rflink.Command.READ_ROBOT_STATUS:
        roboremora.swim_state = remorastate.SwimState((databytes[1]>>6)&3)
        roboremora.valve1_state = remorastate.ValveState((databytes[1]>>5)&1)
        roboremora.valve2_state = remorastate.ValveState((databytes[1]>>4)&1)
        roboremora.pumpin_state = remorastate.PumpState((databytes[1]>>3)&1)
        roboremora.pumpout_state = remorastate.PumpState((databytes[1]>>2)&1)
        roboremora.gimbal_state = remorastate.GimbalState((databytes[1])&3)
        roboremora.flywheel_state = remorastate.FlywheelState((databytes[2]>>7)&1)

    elif command is rflink.Command.READ_SINE_MOTION_PARAM:
        datatuple = struct.unpack('fff', databytes[1:])
        roboremora.motion_amp = datatuple[0]
        roboremora.motion_freq = datatuple[1]
        roboremora.motion_offset = datatuple[2]

    return command_id

#########################################################################################################
class PollingStateThread(QtCore.QThread): # 轮询线程
    """
    本类创建一个轮询线程,每隔一段时间,通过串口发送获取机器人状态的指令
    """
    def __init__(self,parent=None):
        super(PollingStateThread, self).__init__(parent)
        self.is_running = False
        self.is_pause = False
        self._sync = QtCore.QMutex()
        self._pause_cond = QtCore.QWaitCondition()
        self._count = 0

    def run(self):
        """
        本线程运行的主要循环
        """
        self.is_running = True
        while self.is_running == True:

            self._sync.lock()
            if self.is_pause:
                self._pause_cond.wait(self._sync)
            self._sync.unlock()

            # 这段代码就是在轮询,获取下位机信息,注释掉就没有了
            datapack = rftool.RFLink_packdata(rflink.Command.READ_ROBOT_STATUS.value, 0)

            # 通过串口发送数据
            ser_mutex.lock()
            send_sertool.write_cmd(datapack)
            ser_mutex.unlock()

            # 间隔1s,轮询一次
            self.sleep(1)

    def pause(self):
        """
        暂停线程
        """
        self._sync.lock()
        self.is_pause = True
        self._sync.unlock()

    def resume(self):
        """
        恢复线程
        """
        self._sync.lock()
        self.is_pause = False
        self._sync.unlock()
        self._pause_cond.wakeAll()

    def stop(self):
        """
        终止线程,一旦调用,本线程将无法再打开
        """
        self.is_running = False
        self.terminate()

#########################################################################################################
class ReceiveDataThread(QtCore.QThread): # 数据接收线程
    """
    本类创建一个数据接收线程
    通过串口等待数据,每接收到一个数据,就使用RFLink的接收状态机RFLink_receivedata进行分析
    每次接收到一帧完整的消息后,唤醒AnalysisDataThread线程
    """
    def __init__(self,parent=None):
        super(ReceiveDataThread, self).__init__(parent)
        self.is_running = False
        self.is_pause = False
        self._sync = QtCore.QMutex()
        self._pause_cond = QtCore.QWaitCondition()

    def run(self):
        """
        本线程运行的主要循环
        """
        self.is_running = True
        global rftool
        while self.is_running == True:

            self._sync.lock()
            if self.is_pause:
                self._pause_cond.wait(self._sync)
            self._sync.unlock()

            # 接收数据
            rx_data = recv_sertool.read_data()

            # 数据送入状态机
            rf_mutex.lock()
            if rftool.RFLink_receivedata(rx_data): # 如果返回True,那么通知数据分析线程
                rf_cond.wakeAll() # 通知等待rf_cond的线程
            rf_mutex.unlock()


    def pause(self):
        """
        暂停线程
        """
        self._sync.lock()
        self.is_pause = True
        self._sync.unlock()

    def resume(self):
        """
        恢复线程
        """
        self._sync.lock()
        self.is_pause = False
        self._sync.unlock()
        self._pause_cond.wakeAll()

    def stop(self):
        """
        终止线程,一旦调用,本线程将无法再打开
        """
        self.is_running = False
        self.terminate()

#########################################################################################################
class AnalysisDataThread(QtCore.QThread): # 数据分析线程
    """
    本类创建一个数据分析线程
    每当ReceiveDataThread接收到一帧完整消息后,本线程被唤醒
    本线程分析消息中的Command以及机器人的数据
    """
    # 信号量,用于传递Command的ID
    command_id_out = QtCore.pyqtSignal(int)

    def __init__(self,parent=None):
        super(AnalysisDataThread, self).__init__(parent)
        self.command_id = 0
        self.is_running = False
        self.is_pause = False
        self._sync = QtCore.QMutex()
        self._pause_cond = QtCore.QWaitCondition()

    def run(self):
        """
        本线程运行的主要循环
        """
        self.is_running = True
        global rftool
        while self.is_running == True:

            self._sync.lock()
            if self.is_pause:
                self._pause_cond.wait(self._sync)
            self._sync.unlock()

            # 获取消息
            rf_mutex.lock()
            rf_cond.wait(rf_mutex) # 等待数据接收线程唤醒,一旦唤醒,说明rftool已经接收到了一帧完整的消息
            # 拿到数据
            databytes = rftool.message
            datalen = rftool.length
            rf_mutex.unlock()

            # 分析消息,更新机器人状态
            rm_mutex.lock()
            self.command_id = analysis_data(databytes,datalen)
            rm_mutex.unlock()

            # 通知Main Window
            self.command_id_out.emit(self.command_id)

    def pause(self):
        """
        暂停线程
        """
        self._sync.lock()
        self.is_pause = True
        self._sync.unlock()

    def resume(self):
        """
        恢复线程
        """
        self._sync.lock()
        self.is_pause = False
        self._sync.unlock()
        self._pause_cond.wakeAll()

    def stop(self):
        """
        终止线程,一旦调用,本线程将无法再打开
        """
        self.is_running = False
        self.terminate()

#########################################################################################################
class RobotRemoraWindow(QtWidgets.QMainWindow): # 主窗口
    """
    Roboremora Qt 主窗口
    函数大致分为四块:
    第一部分:关于UI定义
    第二部分:关于Slot和Signal的
    第三部分:下位机数据处理
    """
    close_signal = QtCore.pyqtSignal() # 同步关闭主窗口和子窗口
    
    # 初始化
    def __init__(self):
        """
        初始化
        创建三大线程
        初始化UI
        初始化信号和槽的连接
        """
        super(RobotRemoraWindow, self).__init__()
        # 创建线程
        self.receive_data_thread = ReceiveDataThread()
        self.polling_state_thread = PollingStateThread()
        self.analysis_data_thread = AnalysisDataThread()

        # 初始化UI
        self.init_ui()

        # 初始化控件间信号和槽的连接
        self.widgets_connect()
        self.analysis_data_thread.command_id_out.connect(self.newdata_comming_slot) # 处理下位机数据

        # 子窗口初始化
        ## 储存数据子窗口
        self.STBW = storage_btn_win.StorageBtnWin()
        self.datashow_storage_button.clicked.connect(self.STBW.handle_click)
        self.STBW._signal.connect(self.datashow_storage_button_clicked)
        self.close_signal.connect(self.STBW.handle_close)
        ## 回传数据子窗口
        self.SBBW = sendback_btn_win.SendbackBtnWin()
        self.datashow_save_button.clicked.connect(self.SBBW.handle_click)
        self.SBBW._signal.connect(self.datashow_save_button_clicked)
        self.close_signal.connect(self.SBBW.handle_close)

        # 绘图部分变量初始化
        self.showtime = 0
        self.timelist = [] # x轴数据,时间
        self.datalist = [] # y轴数据,传感器数据

        self.datashow_running_flag = False

        self.datashow_sensor_type = 1 # 选择显示哪个传感器
        self.datashow_sensor_id = 1
        self.datashow_sensor_datatype = 1
        self.datashow_sensor_dataaxis = 1

        # 保存数据的文件名
        self.savefile_name = "data.bin"

    #####################################################################################################
    #####################################################################################################
    ## 第一部分:关于UI定义
    #####################################################################################################
    #####################################################################################################
    # 初始化UI界面
    def init_ui(self):
        """
        初始化UI
        :return:
        """
        self.init_layout()
        self.statusBar().showMessage('串口未打开')
        self.setFixedSize(1680,1008)# 设置窗体大小
        self.setWindowTitle('Robot Remora')  # 设置窗口标题
        self.show()  # 窗口显示

    # 初始化layout界面
    def init_layout(self):
        """
        初始化UI界面布局
        UI界面主要分为三个部分:
        self.stateshow_frame:状态显示区
        self.datashow_frame:传感器数据显示区
        self.console_frame:控制台
        self.cmdshell_frame:指令shell区
        :return:
        """

        self.main_widget = QtWidgets.QWidget()
        self.main_layout = QtWidgets.QGridLayout()
        self.main_widget.setLayout(self.main_layout)

        # 状态显示区
        self.stateshow_frame = QtWidgets.QFrame()
        self.stateshow_layout = QtWidgets.QGridLayout()
        self.stateshow_frame.setLayout(self.stateshow_layout)
        self.stateshow_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.stateshow_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.stateshow_frame.setLineWidth(1)

        # 传感器数据显示区
        self.datashow_frame = QtWidgets.QFrame()
        self.datashow_layout = QtWidgets.QGridLayout()
        self.datashow_frame.setLayout(self.datashow_layout)
        self.datashow_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.datashow_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.datashow_frame.setLineWidth(1)

        # 控制台
        self.console_frame = QtWidgets.QFrame()
        self.console_layout = QtWidgets.QGridLayout()
        self.console_frame.setLayout(self.console_layout)
        self.console_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.console_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.console_frame.setLineWidth(1)

        # shell区
        self.cmdshell_frame = QtWidgets.QFrame()
        #self.cmdshell_frame.setStyleSheet('''background-color:rgb(255,255,255);''')
        self.cmdshell_layout = QtWidgets.QGridLayout()
        self.cmdshell_frame.setLayout(self.cmdshell_layout)
        self.cmdshell_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.cmdshell_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.cmdshell_frame.setLineWidth(1)

        # 布局,15行17列
        self.main_layout.addWidget(self.stateshow_frame, 0, 0, 10, 2)
        self.main_layout.addWidget(self.datashow_frame, 0, 2, 10, 13)
        self.main_layout.addWidget(self.console_frame, 10, 0, 5, 15)
        self.main_layout.addWidget(self.cmdshell_frame, 0, 16, 15, 10)

        self.setCentralWidget(self.main_widget)  # 设置窗口主部件

        self.init_stateshow_panel()
        self.init_console_panel()
        self.init_datashow_panel()
        self.init_cmdshell_panel()

    # 初始化状态显示区面板
    def init_stateshow_panel(self):
        """
        初始化状态显示区面板
        :return:
        """

        self.stateshow_title_label = QtWidgets.QLabel('状态显示区')
        self.stateshow_title_label.setFont(QtGui.QFont('Microsoft YaHei', 20 ,QtGui.QFont.Bold))
        self.stateshow_layout.addWidget(self.stateshow_title_label, 0, 0, 1, 2, QtCore.Qt.AlignCenter)

        self.swimstate_fixed_label = QtWidgets.QLabel('游动状态')
        self.swimstate_fixed_label.setFont(QtGui.QFont('SimSun', 12 ,QtGui.QFont.Bold))
        self.stateshow_layout.addWidget(self.swimstate_fixed_label, 1, 0, 1, 1, QtCore.Qt.AlignLeft)

        self.swimstate_label = QtWidgets.QLabel('停止')
        self.swimstate_label.setFont(QtGui.QFont('SimSun', 12))
        self.stateshow_layout.addWidget(self.swimstate_label, 1, 1, 1, 1, QtCore.Qt.AlignCenter)

        self.cpgstate_fixed_label = QtWidgets.QLabel('运动参数（正弦）')
        self.cpgstate_fixed_label.setFont(QtGui.QFont('SimSun', 12 ,QtGui.QFont.Bold))
        self.stateshow_layout.addWidget(self.cpgstate_fixed_label, 2, 0, 1, 2, QtCore.Qt.AlignLeft)

        self.cpgamp_fixed_label = QtWidgets.QLabel('幅度')
        self.cpgamp_fixed_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.stateshow_layout.addWidget(self.cpgamp_fixed_label, 3, 0, 1, 1, QtCore.Qt.AlignRight)

        self.cpgamp_label = QtWidgets.QLabel('0.0')
        self.cpgamp_label.setFont(QtGui.QFont('SimSun', 12))
        self.stateshow_layout.addWidget(self.cpgamp_label, 3, 1, 1, 1, QtCore.Qt.AlignCenter)

        self.cpgfreq_fixed_label = QtWidgets.QLabel('频率')
        self.cpgfreq_fixed_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.stateshow_layout.addWidget(self.cpgfreq_fixed_label, 4, 0, 1, 1, QtCore.Qt.AlignRight)

        self.cpgfreq_label = QtWidgets.QLabel('0.0')
        self.cpgfreq_label.setFont(QtGui.QFont('SimSun', 12))
        self.stateshow_layout.addWidget(self.cpgfreq_label, 4, 1, 1, 1, QtCore.Qt.AlignCenter)

        self.cpgoffset_fixed_label = QtWidgets.QLabel('偏移')
        self.cpgoffset_fixed_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.stateshow_layout.addWidget(self.cpgoffset_fixed_label, 5, 0, 1, 1, QtCore.Qt.AlignRight)

        self.cpgoffset_label = QtWidgets.QLabel('0.0')
        self.cpgoffset_label.setFont(QtGui.QFont('SimSun', 12))
        self.stateshow_layout.addWidget(self.cpgoffset_label, 5, 1, 1, 1, QtCore.Qt.AlignCenter)

        self.pumpstate_fixed_label = QtWidgets.QLabel('水泵状态')
        self.pumpstate_fixed_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.stateshow_layout.addWidget(self.pumpstate_fixed_label, 6, 0, 1, 1, QtCore.Qt.AlignCenter)

        self.pumpinstate_fixed_label = QtWidgets.QLabel('吸水泵')
        self.pumpinstate_fixed_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.stateshow_layout.addWidget(self.pumpinstate_fixed_label, 7, 0, 1, 1, QtCore.Qt.AlignCenter)

        self.pumpinstate_label = QtWidgets.QLabel('关闭')
        self.pumpinstate_label.setFont(QtGui.QFont('SimSun', 12))
        self.stateshow_layout.addWidget(self.pumpinstate_label, 7, 1, 1, 1, QtCore.Qt.AlignCenter)

        self.pumpoutstate_fixed_label = QtWidgets.QLabel('排水泵')
        self.pumpoutstate_fixed_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.stateshow_layout.addWidget(self.pumpoutstate_fixed_label, 8, 0, 1, 1, QtCore.Qt.AlignCenter)

        self.pumpoutstate_label = QtWidgets.QLabel('关闭')
        self.pumpoutstate_label.setFont(QtGui.QFont('SimSun', 12))
        self.stateshow_layout.addWidget(self.pumpoutstate_label, 8, 1, 1, 1, QtCore.Qt.AlignCenter)

        self.valvestate_fixed_label = QtWidgets.QLabel('磁阀状态')
        self.valvestate_fixed_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.stateshow_layout.addWidget(self.valvestate_fixed_label, 9, 0, 1, 2, QtCore.Qt.AlignLeft)

        self.valve1state_fixed_label = QtWidgets.QLabel('阀1')
        self.valve1state_fixed_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.stateshow_layout.addWidget(self.valve1state_fixed_label, 10, 0, 1, 1, QtCore.Qt.AlignRight)

        self.valve1state_label = QtWidgets.QLabel('关闭')
        self.valve1state_label.setFont(QtGui.QFont('SimSun', 12))
        self.stateshow_layout.addWidget(self.valve1state_label, 10, 1, 1, 1, QtCore.Qt.AlignCenter)

        self.valve2state_fixed_label = QtWidgets.QLabel('阀2')
        self.valve2state_fixed_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.stateshow_layout.addWidget(self.valve2state_fixed_label, 11, 0, 1, 1, QtCore.Qt.AlignRight)

        self.valve2state_label = QtWidgets.QLabel('关闭')
        self.valve2state_label.setFont(QtGui.QFont('SimSun', 12))
        self.stateshow_layout.addWidget(self.valve2state_label, 11, 1, 1, 1, QtCore.Qt.AlignCenter)

        self.gimbalstate_fixed_label = QtWidgets.QLabel('云台状态')
        self.gimbalstate_fixed_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.stateshow_layout.addWidget(self.gimbalstate_fixed_label, 12, 0, 1, 1, QtCore.Qt.AlignCenter)

        self.gimbalstate_label = QtWidgets.QLabel('施工中')
        self.gimbalstate_label.setFont(QtGui.QFont('SimSun', 12))
        self.stateshow_layout.addWidget(self.gimbalstate_label, 12, 1, 1, 1, QtCore.Qt.AlignCenter)

        self.flywheelstate_fixed_label = QtWidgets.QLabel('飞轮状态')
        self.flywheelstate_fixed_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.stateshow_layout.addWidget(self.flywheelstate_fixed_label, 13, 0, 1, 1, QtCore.Qt.AlignCenter)

        self.flywheelstate_label = QtWidgets.QLabel('施工中')
        self.flywheelstate_label.setFont(QtGui.QFont('SimSun', 12))
        self.stateshow_layout.addWidget(self.flywheelstate_label, 13, 1, 1, 1, QtCore.Qt.AlignCenter)

    # 初始化控制台面板
    def init_console_panel(self):
        """
        初始化控制台面板
        控制台面板分为五大板块
        self.swimcc_frame:游动控制
        self.cpgcc_frame:CPG参数控制
        self.attachcc_frame:吸附控制
        self.gimbalcc_frame:云台控制
        self.flywheelcc_frame:飞轮控制
        :return:
        """
        self.console_title_label = QtWidgets.QLabel('RoboRemora控制台')
        self.console_title_label.setFont(QtGui.QFont('Microsoft YaHei', 20, QtGui.QFont.Bold))
        self.console_layout.addWidget(self.console_title_label, 0, 0, 1, 15, QtCore.Qt.AlignCenter)

        # 游动控制
        self.swimcc_frame = QtWidgets.QFrame()
        self.swimcc_layout = QtWidgets.QGridLayout()
        self.swimcc_frame.setLayout(self.swimcc_layout)
        self.swimcc_frame.setFrameShape(QtWidgets.QFrame.Box)
        self.swimcc_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.swimcc_frame.setLineWidth(1)
        self.console_layout.addWidget(self.swimcc_frame, 1, 0, 10, 4)

        self.swimcc_fixed_label = QtWidgets.QLabel('游动状态')
        self.swimcc_fixed_label.setFont(QtGui.QFont('Microsoft YaHei', 15, QtGui.QFont.Bold))
        self.swimcc_layout.addWidget(self.swimcc_fixed_label, 1, 0, 1, 4, QtCore.Qt.AlignCenter)

        self.swimcc_start_button = QtWidgets.QPushButton('启动')
        self.swimcc_layout.addWidget(self.swimcc_start_button, 2, 0, 1, 1, QtCore.Qt.AlignCenter)
        self.swimcc_start_button.setObjectName("SET_SWIM_RUN")

        self.swimcc_stop_button = QtWidgets.QPushButton('暂停')
        self.swimcc_layout.addWidget(self.swimcc_stop_button, 2, 1, 1, 1, QtCore.Qt.AlignCenter)
        self.swimcc_stop_button.setObjectName("SET_SWIM_STOP")

        self.swimcc_forcestop_button = QtWidgets.QPushButton('停止')
        self.swimcc_layout.addWidget(self.swimcc_forcestop_button, 2, 2, 1,  1, QtCore.Qt.AlignCenter)
        self.swimcc_forcestop_button.setObjectName("SET_SWIM_FORCESTOP")

        self.swimcc_turnleft_button = QtWidgets.QPushButton('左转')
        self.swimcc_layout.addWidget(self.swimcc_turnleft_button, 3, 0, 1, 1, QtCore.Qt.AlignCenter)
        self.swimcc_turnleft_button.setObjectName("SET_SWIM_LEFT")

        self.swimcc_straight_button = QtWidgets.QPushButton('直游')
        self.swimcc_layout.addWidget(self.swimcc_straight_button, 3, 1, 1, 1, QtCore.Qt.AlignCenter)
        self.swimcc_straight_button.setObjectName("SET_SWIM_STRAIGHT")

        self.swimcc_turnright_button = QtWidgets.QPushButton('右转')
        self.swimcc_layout.addWidget(self.swimcc_turnright_button, 3, 2, 1, 1, QtCore.Qt.AlignCenter)
        self.swimcc_turnright_button.setObjectName("SET_SWIM_RIGHT")

        self.swimcc_speedup_button = QtWidgets.QPushButton('加速')
        self.swimcc_layout.addWidget(self.swimcc_speedup_button, 4, 0, 1, 1, QtCore.Qt.AlignCenter)
        self.swimcc_speedup_button.setObjectName("SET_SWIM_SPEEDUP")

        self.swimcc_speeddown_button = QtWidgets.QPushButton('减速')
        self.swimcc_layout.addWidget(self.swimcc_speeddown_button, 5, 0, 1, 1, QtCore.Qt.AlignCenter)
        self.swimcc_speeddown_button.setObjectName("SET_SWIM_SPEEDDOWN")

        self.swimcc_raise_button = QtWidgets.QPushButton('上浮')
        self.swimcc_layout.addWidget(self.swimcc_raise_button, 2, 3, 1, 1, QtCore.Qt.AlignCenter)
        self.swimcc_raise_button.setObjectName("SET_SWIM_UP")

        self.swimcc_dive_button = QtWidgets.QPushButton('下潜')
        self.swimcc_layout.addWidget(self.swimcc_dive_button, 3, 3, 1, 1, QtCore.Qt.AlignCenter)
        self.swimcc_dive_button.setObjectName("SET_SWIM_DOWN")

        self.swimcc_leftfinzero_button = QtWidgets.QPushButton('左胸鳍回中')
        self.swimcc_layout.addWidget(self.swimcc_leftfinzero_button, 4, 2, 1, 1, QtCore.Qt.AlignCenter)
        self.swimcc_leftfinzero_button.setObjectName("SET_LEFTPECFIN_ZERO")

        self.swimcc_rightfinzero_button = QtWidgets.QPushButton('右胸鳍回中')
        self.swimcc_layout.addWidget(self.swimcc_rightfinzero_button, 5, 2, 1, 1, QtCore.Qt.AlignCenter)
        self.swimcc_rightfinzero_button.setObjectName("SET_RIGHTPECFIN_ZERO")

        self.swimcc_leftfinup_button = QtWidgets.QPushButton('左胸鳍+')
        self.swimcc_layout.addWidget(self.swimcc_leftfinup_button, 4, 1, 1, 1, QtCore.Qt.AlignCenter)
        self.swimcc_leftfinup_button.setObjectName("SET_LEFTPECFIN_UP")

        self.swimcc_leftfindown_button = QtWidgets.QPushButton('左胸鳍-')
        self.swimcc_layout.addWidget(self.swimcc_leftfindown_button, 4, 3, 1, 1, QtCore.Qt.AlignCenter)
        self.swimcc_leftfindown_button.setObjectName("SET_LEFTPECFIN_DOWN")

        self.swimcc_rightfinup_button = QtWidgets.QPushButton('右胸鳍+')
        self.swimcc_layout.addWidget(self.swimcc_rightfinup_button, 5, 1, 1, 1, QtCore.Qt.AlignCenter)
        self.swimcc_rightfinup_button.setObjectName("SET_RIGHTPECFIN_UP")

        self.swimcc_rightfindown_button = QtWidgets.QPushButton('右胸鳍-')
        self.swimcc_layout.addWidget(self.swimcc_rightfindown_button, 5, 3, 1, 1, QtCore.Qt.AlignCenter)
        self.swimcc_rightfindown_button.setObjectName("SET_RIGHTPECFIN_DOWN")

        # CPG参数设置
        self.cpgcc_frame = QtWidgets.QFrame()
        self.cpgcc_layout = QtWidgets.QGridLayout()
        self.cpgcc_frame.setLayout(self.cpgcc_layout)
        self.cpgcc_frame.setFrameShape(QtWidgets.QFrame.Box)
        self.cpgcc_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.cpgcc_frame.setLineWidth(1)
        self.console_layout.addWidget(self.cpgcc_frame, 1, 4, 10, 3)

        self.cpgcc_fixed_label = QtWidgets.QLabel('运动参数设置')
        self.cpgcc_fixed_label.setFont(QtGui.QFont('Microsoft YaHei', 15, QtGui.QFont.Bold))
        self.cpgcc_layout.addWidget(self.cpgcc_fixed_label, 1, 0, 1, 3, QtCore.Qt.AlignCenter)

        self.cpgcc_amp_label = QtWidgets.QLabel('幅度')
        self.cpgcc_amp_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.cpgcc_layout.addWidget(self.cpgcc_amp_label, 2, 0, 1, 1, QtCore.Qt.AlignCenter)

        self.cpgcc_amp_edit = QtWidgets.QLineEdit()
        self.cpgcc_amp_edit.setFixedSize(70,30)
        self.cpgcc_amp_edit.setPlaceholderText('0~0.7')
        double_validator1 = QtGui.QDoubleValidator()
        double_validator1.setRange(0, 0.7)
        double_validator1.setNotation(QtGui.QDoubleValidator.StandardNotation)
        double_validator1.setDecimals(3)
        self.cpgcc_amp_edit.setValidator(double_validator1)
        self.cpgcc_layout.addWidget(self.cpgcc_amp_edit, 2, 1, 1, 1, QtCore.Qt.AlignCenter)

        self.cpgcc_amp_button = QtWidgets.QPushButton('写入')
        self.cpgcc_layout.addWidget(self.cpgcc_amp_button, 2, 2, 1, 1, QtCore.Qt.AlignCenter)
        self.cpgcc_amp_button.setObjectName("SET_SINE_MOTION_AMP")

        self.cpgcc_freq_label = QtWidgets.QLabel('频率')
        self.cpgcc_freq_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.cpgcc_layout.addWidget(self.cpgcc_freq_label, 3, 0, 1, 1, QtCore.Qt.AlignCenter)

        self.cpgcc_freq_edit = QtWidgets.QLineEdit()
        self.cpgcc_freq_edit.setFixedSize(70, 30)
        self.cpgcc_freq_edit.setPlaceholderText('0~2.0')
        double_validator2 = QtGui.QDoubleValidator()
        double_validator2.setRange(0, 2.0)
        double_validator2.setNotation(QtGui.QDoubleValidator.StandardNotation)
        double_validator2.setDecimals(2)
        self.cpgcc_freq_edit.setValidator(double_validator2)
        self.cpgcc_layout.addWidget(self.cpgcc_freq_edit, 3, 1, 1, 1, QtCore.Qt.AlignCenter)

        self.cpgcc_freq_button = QtWidgets.QPushButton('写入')
        self.cpgcc_layout.addWidget(self.cpgcc_freq_button, 3, 2, 1, 1, QtCore.Qt.AlignCenter)
        self.cpgcc_freq_button.setObjectName("SET_SINE_MOTION_FREQ")

        self.cpgcc_offset_label = QtWidgets.QLabel('偏移')
        self.cpgcc_offset_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.cpgcc_layout.addWidget(self.cpgcc_offset_label, 4, 0, 1, 1, QtCore.Qt.AlignCenter)

        self.cpgcc_offset_edit = QtWidgets.QLineEdit()
        self.cpgcc_offset_edit.setFixedSize(70, 30)
        self.cpgcc_offset_edit.setPlaceholderText('-0.8~0.8')
        double_validator3 = QtGui.QDoubleValidator()
        double_validator3.setRange(-0.8, 0.8)
        double_validator3.setNotation(QtGui.QDoubleValidator.StandardNotation)
        double_validator3.setDecimals(2)
        self.cpgcc_offset_edit.setValidator(double_validator3)
        self.cpgcc_layout.addWidget(self.cpgcc_offset_edit, 4, 1, 1, 1, QtCore.Qt.AlignCenter)

        self.cpgcc_offset_button = QtWidgets.QPushButton('写入')
        self.cpgcc_layout.addWidget(self.cpgcc_offset_button, 4, 2, 1, 1, QtCore.Qt.AlignCenter)
        self.cpgcc_offset_button.setObjectName("SET_SINE_MOTION_OFFSET")

        self.cpgcc_readparam_button = QtWidgets.QPushButton('读取参数')
        self.cpgcc_layout.addWidget(self.cpgcc_readparam_button, 5, 0, 1, 3, QtCore.Qt.AlignCenter)
        self.cpgcc_readparam_button.setObjectName("READ_SINE_MOTION_PARAM")

        # 吸附控制
        self.attachcc_frame = QtWidgets.QFrame()
        self.attachcc_layout = QtWidgets.QGridLayout()
        self.attachcc_frame.setLayout(self.attachcc_layout)
        self.attachcc_frame.setFrameShape(QtWidgets.QFrame.Box)
        self.attachcc_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.attachcc_frame.setLineWidth(1)
        self.console_layout.addWidget(self.attachcc_frame, 1, 7, 10, 3)

        self.attachcc_fixed_label = QtWidgets.QLabel('吸附控制')
        self.attachcc_fixed_label.setFont(QtGui.QFont('Microsoft YaHei', 15, QtGui.QFont.Bold))
        self.attachcc_layout.addWidget(self.attachcc_fixed_label, 1, 0, 1, 3, QtCore.Qt.AlignCenter)

        self.attachcc_attach_button = QtWidgets.QPushButton('吸附')
        self.attachcc_layout.addWidget(self.attachcc_attach_button, 2, 0, 1, 1, QtCore.Qt.AlignCenter)
        self.attachcc_attach_button.setObjectName("GOTO_ATTACH")

        self.attachcc_detach_button = QtWidgets.QPushButton('脱附')
        self.attachcc_layout.addWidget(self.attachcc_detach_button, 3, 0, 1, 1, QtCore.Qt.AlignCenter)
        self.attachcc_detach_button.setObjectName("GOTO_DETACH")

        # self.attachcc_valve1_label = QtWidgets.QLabel('阀1')
        # self.attachcc_valve1_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        # self.attachcc_layout.addWidget(self.attachcc_valve1_label, 3, 0, 1, 1, QtCore.Qt.AlignCenter)

        self.attachcc_v1open_button = QtWidgets.QPushButton('开启阀1')
        self.attachcc_layout.addWidget(self.attachcc_v1open_button, 2, 1, 1, 1, QtCore.Qt.AlignCenter)
        self.attachcc_v1open_button.setObjectName("SET_VALVE1_ON")

        self.attachcc_v1close_button = QtWidgets.QPushButton('关闭阀1')
        self.attachcc_layout.addWidget(self.attachcc_v1close_button, 3, 1, 1, 1, QtCore.Qt.AlignCenter)
        self.attachcc_v1close_button.setObjectName("SET_VALVE1_OFF")

        # self.attachcc_valve2_label = QtWidgets.QLabel('阀2')
        # self.attachcc_valve2_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        # self.attachcc_layout.addWidget(self.attachcc_valve2_label, 4, 0, 1, 1, QtCore.Qt.AlignCenter)

        self.attachcc_v2open_button = QtWidgets.QPushButton('开启阀2')
        self.attachcc_layout.addWidget(self.attachcc_v2open_button, 2, 2, 1, 1, QtCore.Qt.AlignCenter)
        self.attachcc_v2open_button.setObjectName("SET_VALVE2_ON")

        self.attachcc_v2close_button = QtWidgets.QPushButton('关闭阀2')
        self.attachcc_layout.addWidget(self.attachcc_v2close_button, 3, 2, 1, 1, QtCore.Qt.AlignCenter)
        self.attachcc_v2close_button.setObjectName("SET_VALVE2_OFF")

        # self.attachcc_pump_label = QtWidgets.QLabel('水泵')
        # self.attachcc_pump_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        # self.attachcc_layout.addWidget(self.attachcc_pump_label, 5, 0, 1, 1, QtCore.Qt.AlignCenter)

        self.attachcc_pumpinopen_button = QtWidgets.QPushButton('开启吸水')
        self.attachcc_layout.addWidget(self.attachcc_pumpinopen_button, 4, 1, 1, 1, QtCore.Qt.AlignCenter)
        self.attachcc_pumpinopen_button.setObjectName("SET_PUMP_IN_ON")

        self.attachcc_pumpinclose_button = QtWidgets.QPushButton('关闭吸水')
        self.attachcc_layout.addWidget(self.attachcc_pumpinclose_button, 5, 1, 1, 1, QtCore.Qt.AlignCenter)
        self.attachcc_pumpinclose_button.setObjectName("SET_PUMP_IN_OFF")

        self.attachcc_pumpoutopen_button = QtWidgets.QPushButton('开启排水')
        self.attachcc_layout.addWidget(self.attachcc_pumpoutopen_button, 4, 2, 1, 1, QtCore.Qt.AlignCenter)
        self.attachcc_pumpoutopen_button.setObjectName("SET_PUMP_OUT_ON")

        self.attachcc_pumpoutclose_button = QtWidgets.QPushButton('关闭排水')
        self.attachcc_layout.addWidget(self.attachcc_pumpoutclose_button, 5, 2, 1, 1, QtCore.Qt.AlignCenter)
        self.attachcc_pumpoutclose_button.setObjectName("SET_PUMP_OUT_OFF")

        # 云台控制
        self.gimbalcc_frame = QtWidgets.QFrame()
        self.gimbalcc_layout = QtWidgets.QGridLayout()
        self.gimbalcc_frame.setLayout(self.gimbalcc_layout)
        self.gimbalcc_frame.setFrameShape(QtWidgets.QFrame.Box)
        self.gimbalcc_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.gimbalcc_frame.setLineWidth(1)
        self.console_layout.addWidget(self.gimbalcc_frame, 1, 10, 10, 2)

        self.gimbalcc_fixed_label = QtWidgets.QLabel('云台控制')
        self.gimbalcc_fixed_label.setFont(QtGui.QFont('Microsoft YaHei', 15, QtGui.QFont.Bold))
        self.gimbalcc_layout.addWidget(self.gimbalcc_fixed_label, 1, 0, 1, 2, QtCore.Qt.AlignCenter)

        self.gimbalcc_start_button = QtWidgets.QPushButton('启动')
        self.gimbalcc_layout.addWidget(self.gimbalcc_start_button, 2, 0, 1, 2, QtCore.Qt.AlignCenter)
        self.gimbalcc_start_button.setObjectName("SET_GIMBAL_RUN")

        self.gimbalcc_stop_button = QtWidgets.QPushButton('停止')
        self.gimbalcc_layout.addWidget(self.gimbalcc_stop_button, 3, 0, 1, 2, QtCore.Qt.AlignCenter)
        self.gimbalcc_stop_button.setObjectName("SET_GIMBAL_STOP")

        self.gimbalcc_zero_button = QtWidgets.QPushButton('归中')
        self.gimbalcc_layout.addWidget(self.gimbalcc_zero_button, 4, 0, 1, 2, QtCore.Qt.AlignCenter)
        self.gimbalcc_zero_button.setObjectName("SET_GIMBAL_ZERO")


        # 飞轮控制
        self.flywheelcc_frame = QtWidgets.QFrame()
        self.flywheelcc_layout = QtWidgets.QGridLayout()
        self.flywheelcc_frame.setLayout(self.flywheelcc_layout)
        self.flywheelcc_frame.setFrameShape(QtWidgets.QFrame.Box)
        self.flywheelcc_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.flywheelcc_frame.setLineWidth(1)
        self.console_layout.addWidget(self.flywheelcc_frame, 1, 12, 10, 3)

        self.flywheelcc_fixed_label = QtWidgets.QLabel('飞轮控制')
        self.flywheelcc_fixed_label.setFont(QtGui.QFont('Microsoft YaHei', 15, QtGui.QFont.Bold))
        self.flywheelcc_layout.addWidget(self.flywheelcc_fixed_label, 1, 0, 1, 3, QtCore.Qt.AlignCenter)

        self.flywheelcc_start_button = QtWidgets.QPushButton('启动')
        self.flywheelcc_layout.addWidget(self.flywheelcc_start_button, 2, 0, 1, 3, QtCore.Qt.AlignCenter)
        self.flywheelcc_start_button.setObjectName("SET_FLYWHEEL_RUN")

        self.flywheelcc_stop_button = QtWidgets.QPushButton('停止')
        self.flywheelcc_layout.addWidget(self.flywheelcc_stop_button, 3, 0, 1, 3, QtCore.Qt.AlignCenter)
        self.flywheelcc_stop_button.setObjectName("SET_FLYWHEEL_STOP")

    # 初始化command shell面板
    def init_cmdshell_panel(self):
        """
        初始化command shell面板
        主要分为:输出窗口,输入命令和串口控制部分
        :return:
        """
        self.cmdshell_title_label = QtWidgets.QLabel('Command Shell')
        self.cmdshell_title_label.setFont(QtGui.QFont('Microsoft YaHei', 20, QtGui.QFont.Bold))
        self.cmdshell_layout.addWidget(self.cmdshell_title_label, 0, 0, 1, 10, QtCore.Qt.AlignCenter)

        # 输出窗口和输入命令
        self.cmdshell_text_frame = QtWidgets.QFrame()
        self.cmdshell_text_layout = QtWidgets.QGridLayout()
        self.cmdshell_text_frame.setLayout(self.cmdshell_text_layout)
        self.cmdshell_text_frame.setFrameShape(QtWidgets.QFrame.Box)
        self.cmdshell_text_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.cmdshell_text_frame.setLineWidth(1)
        self.cmdshell_layout.addWidget(self.cmdshell_text_frame, 1, 0, 10, 10)

        self.cmdshell_browser_label = QtWidgets.QLabel('输出窗口')
        self.cmdshell_browser_label.setFont(QtGui.QFont('Microsoft YaHei', 15, QtGui.QFont.Bold))
        self.cmdshell_text_layout.addWidget(self.cmdshell_browser_label, 0, 0, 1, 10, QtCore.Qt.AlignLeft)
        self.cmdshell_text_browser = QtWidgets.QTextBrowser()
        self.cmdshell_text_browser.setFixedSize(400, 500)
        self.cmdshell_text_browser.setStyleSheet('''background-color:rgb(47,79,79);border-radius: 5px; color: rgb(255, 215, 0);''')
        self.cmdshell_text_layout.addWidget(self.cmdshell_text_browser, 1, 0, 8, 10, QtCore.Qt.AlignCenter)
        self.cmdshell_text_browser.append("<font color='Cyan'>roboremora-host:~$&nbsp;</font> ")

        self.cmdshell_editor_label = QtWidgets.QLabel('输入命令')
        self.cmdshell_editor_label.setFont(QtGui.QFont('Microsoft YaHei', 15, QtGui.QFont.Bold))
        self.cmdshell_text_layout.addWidget(self.cmdshell_editor_label, 9, 0, 1, 2, QtCore.Qt.AlignLeft)
        self.cmdshell_text_editor = QtWidgets.QLineEdit()
        self.cmdshell_text_editor.setFixedSize(310, 25)
        self.cmdshell_text_editor.setStyleSheet('''background-color:rgb(47,79,79);border-radius: 5px; color: rgb(255, 255, 255);''')
        self.cmdshell_text_layout.addWidget(self.cmdshell_text_editor, 9, 2, 1, 8, QtCore.Qt.AlignCenter)

        # 串口控制
        self.serial_frame = QtWidgets.QFrame()
        self.serial_layout = QtWidgets.QGridLayout()
        self.serial_frame.setLayout(self.serial_layout)
        self.serial_frame.setFrameShape(QtWidgets.QFrame.Box)
        self.serial_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.serial_frame.setLineWidth(1)
        self.cmdshell_layout.addWidget(self.serial_frame, 11, 0, 4, 10)

        self.serial_fixed_label = QtWidgets.QLabel('串口控制')
        self.serial_fixed_label.setFont(QtGui.QFont('Microsoft YaHei', 15, QtGui.QFont.Bold))
        self.serial_layout.addWidget(self.serial_fixed_label, 0, 0, 1, 6, QtCore.Qt.AlignCenter)

        # 串口1--发送串口
        self.serial1_com_label = QtWidgets.QLabel('发送COM')
        self.serial1_com_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.serial_layout.addWidget(self.serial1_com_label, 1, 0, 1, 1, QtCore.Qt.AlignCenter)

        self.serial1_com_combo = QtWidgets.QComboBox()
        self.serial1_com_combo.addItem('ttyUSB0')
        self.serial1_com_combo.addItem('ttyUSB1')
        self.serial1_com_combo.addItem('ttyUSB2')
        self.serial1_com_combo.addItem('ttyUSB3')
        self.serial1_com_combo.addItem('COM3')
        self.serial1_com_combo.addItem('COM5')
        self.serial1_com_combo.addItem('COM6')
        self.serial1_com_combo.addItem('COM7')
        self.serial1_com_combo.addItem('COM9')
        self.serial1_com_combo.addItem('COM11')
        self.serial1_com_combo.addItem('COM12')
        self.serial1_com_combo.setFixedSize(120, 30)
        self.serial_layout.addWidget(self.serial1_com_combo, 2, 0, 1, 2, QtCore.Qt.AlignLeft)

        self.serial1_bps_label = QtWidgets.QLabel('BPS')
        self.serial1_bps_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.serial_layout.addWidget(self.serial1_bps_label, 1, 2, 1, 1, QtCore.Qt.AlignLeft)

        self.serial1_bps_combo = QtWidgets.QComboBox()
        self.serial1_bps_combo.addItem('9600')
        self.serial1_bps_combo.addItem('14400')
        self.serial1_bps_combo.addItem('19200')
        self.serial1_bps_combo.addItem('38400')
        self.serial1_bps_combo.addItem('56000')
        self.serial1_bps_combo.addItem('57600')
        self.serial1_bps_combo.addItem('115200')
        self.serial1_bps_combo.setFixedSize(120, 30)
        self.serial_layout.addWidget(self.serial1_bps_combo, 2, 2, 1, 2, QtCore.Qt.AlignLeft)

        self.serial1_hex_checkbox = QtWidgets.QCheckBox("HEX")
        self.serial_layout.addWidget(self.serial1_hex_checkbox, 1, 5, 1, 1, QtCore.Qt.AlignLeft)

        self.serial1_open_button = QtWidgets.QPushButton('打开')
        self.serial1_open_button.setFixedSize(60, 30)
        self.serial_layout.addWidget(self.serial1_open_button, 2, 4, 1, 1, QtCore.Qt.AlignCenter)

        self.serial1_close_button = QtWidgets.QPushButton('关闭')
        self.serial1_close_button.setFixedSize(60, 30)
        self.serial_layout.addWidget(self.serial1_close_button, 2, 5, 1, 1, QtCore.Qt.AlignCenter)

        # 串口2--接收串口
        self.serial2_com_label = QtWidgets.QLabel('接收COM')
        self.serial2_com_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.serial_layout.addWidget(self.serial2_com_label, 3, 0, 1, 1, QtCore.Qt.AlignCenter)

        self.serial2_com_combo = QtWidgets.QComboBox()
        self.serial2_com_combo.addItem('ttyUSB1')
        self.serial2_com_combo.addItem('ttyUSB0')
        self.serial2_com_combo.addItem('ttyUSB2')
        self.serial2_com_combo.addItem('ttyUSB3')
        self.serial2_com_combo.addItem('COM3')
        self.serial2_com_combo.addItem('COM5')
        self.serial2_com_combo.addItem('COM6')
        self.serial2_com_combo.addItem('COM7')
        self.serial2_com_combo.addItem('COM9')
        self.serial2_com_combo.addItem('COM11')
        self.serial2_com_combo.addItem('COM12')
        self.serial2_com_combo.setFixedSize(120, 30)
        self.serial_layout.addWidget(self.serial2_com_combo, 4, 0, 1, 2, QtCore.Qt.AlignLeft)

        self.serial2_bps_label = QtWidgets.QLabel('BPS')
        self.serial2_bps_label.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.serial_layout.addWidget(self.serial2_bps_label, 3, 2, 1, 1, QtCore.Qt.AlignLeft)

        self.serial2_bps_combo = QtWidgets.QComboBox()
        self.serial2_bps_combo.addItem('19200')
        self.serial2_bps_combo.addItem('9600')
        self.serial2_bps_combo.addItem('14400')
        self.serial2_bps_combo.addItem('38400')
        self.serial2_bps_combo.addItem('56000')
        self.serial2_bps_combo.addItem('57600')
        self.serial2_bps_combo.addItem('115200')
        self.serial2_bps_combo.setFixedSize(120, 30)
        self.serial_layout.addWidget(self.serial2_bps_combo, 4, 2, 1, 2, QtCore.Qt.AlignLeft)

        self.serial2_hex_checkbox = QtWidgets.QCheckBox("HEX")
        self.serial_layout.addWidget(self.serial2_hex_checkbox, 3, 5, 1, 1, QtCore.Qt.AlignLeft)

        self.serial2_open_button = QtWidgets.QPushButton('打开')
        self.serial2_open_button.setFixedSize(60, 30)
        self.serial_layout.addWidget(self.serial2_open_button, 4, 4, 1, 1, QtCore.Qt.AlignCenter)

        self.serial2_close_button = QtWidgets.QPushButton('关闭')
        self.serial2_close_button.setFixedSize(60, 30)
        self.serial_layout.addWidget(self.serial2_close_button, 4, 5, 1, 1, QtCore.Qt.AlignCenter)

        self.serial_shakehand_button = QtWidgets.QPushButton('握手')
        self.serial_shakehand_button.setFixedSize(160, 30)
        self.serial_shakehand_button.setObjectName("SHAKING_HANDS")
        self.serial_layout.addWidget(self.serial_shakehand_button, 5, 0, 1, 6, QtCore.Qt.AlignCenter)

    # 初始化传感器数据显示区面板
    def init_datashow_panel(self):
        """
        初始化传感器数据显示区面板
        :return:...........................
        """
        self.datashow_title_label = QtWidgets.QLabel('传感器数据显示区')
        self.datashow_title_label.setFont(QtGui.QFont('Microsoft YaHei', 20, QtGui.QFont.Bold))
        self.datashow_layout.addWidget(self.datashow_title_label, 0, 0, 1, 13, QtCore.Qt.AlignCenter)

        # 图像显示部分
        self.canvas_frame = QtWidgets.QFrame()
        self.canvas_layout = QtWidgets.QVBoxLayout()
        self.canvas_frame.setLayout(self.canvas_layout)
        self.canvas_frame.setFrameShape(QtWidgets.QFrame.Box)
        self.canvas_frame.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.canvas_frame.setLineWidth(2)
        self.datashow_layout.addWidget(self.canvas_frame, 1, 0, 10, 10)

        self.sensor_data_canvas = sensor_data_canvas.SensorDataCanvas()
        self.navigationbar = NavigationToolbar(self.sensor_data_canvas,self.canvas_frame)
        self.canvas_layout.addWidget(self.navigationbar, QtCore.Qt.AlignCenter)
        self.canvas_layout.addWidget(self.sensor_data_canvas)

        self.datasc_frame = QtWidgets.QFrame()
        self.datasc_layout = QtWidgets.QGridLayout()
        self.datasc_frame.setLayout(self.datasc_layout)
        self.datasc_frame.setFrameShape(QtWidgets.QFrame.Box)
        self.datasc_frame.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.datasc_frame.setLineWidth(2)
        self.datashow_layout.addWidget(self.datasc_frame, 1, 10, 10, 3)

        # 数据显示控制台
        self.datasc_label = QtWidgets.QLabel("数据显示控制台")
        self.datasc_label.setFont(QtGui.QFont('Microsoft YaHei', 15, QtGui.QFont.Bold))
        self.datasc_layout.addWidget(self.datasc_label, 1, 0, 1, 3, QtCore.Qt.AlignCenter)

        self.imu_checkbox = QtWidgets.QCheckBox("IMU")
        self.imu_checkbox.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.imu_checkbox.setChecked(True)
        self.datasc_layout.addWidget(self.imu_checkbox, 2, 0, 1, 3, QtCore.Qt.AlignCenter)

        self.imu1_checkbox = QtWidgets.QCheckBox("IMU1")
        self.imu1_checkbox.setChecked(True)
        self.datasc_layout.addWidget(self.imu1_checkbox, 3, 0, 1, 1, QtCore.Qt.AlignLeft)

        self.imu2_checkbox = QtWidgets.QCheckBox("IMU2")
        self.datasc_layout.addWidget(self.imu2_checkbox, 3, 1, 1, 1, QtCore.Qt.AlignLeft)

        self.accel_checkbox = QtWidgets.QCheckBox("加速度")
        self.datasc_layout.addWidget(self.accel_checkbox, 4, 1, 1, 1, QtCore.Qt.AlignLeft)

        self.gyro_checkbox = QtWidgets.QCheckBox("角速度")
        self.datasc_layout.addWidget(self.gyro_checkbox, 4, 2, 1, 1, QtCore.Qt.AlignLeft)

        self.angle_checkbox = QtWidgets.QCheckBox("角度")
        self.angle_checkbox.setChecked(True)
        self.datasc_layout.addWidget(self.angle_checkbox, 4, 0, 1, 1, QtCore.Qt.AlignLeft)

        self.x_checkbox = QtWidgets.QCheckBox("X轴")
        self.x_checkbox.setChecked(True)
        self.datasc_layout.addWidget(self.x_checkbox, 5, 0, 1, 1, QtCore.Qt.AlignLeft)

        self.y_checkbox = QtWidgets.QCheckBox("Y轴")
        self.datasc_layout.addWidget(self.y_checkbox, 5, 1, 1, 1, QtCore.Qt.AlignLeft)

        self.z_checkbox = QtWidgets.QCheckBox("Z轴")
        self.datasc_layout.addWidget(self.z_checkbox, 5, 2, 1, 1, QtCore.Qt.AlignLeft)

        self.varistor_checkbox = QtWidgets.QCheckBox("压敏电阻")
        self.varistor_checkbox.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.datasc_layout.addWidget(self.varistor_checkbox, 6, 0, 1, 3, QtCore.Qt.AlignCenter)

        self.var1_checkbox = QtWidgets.QCheckBox("电阻1")
        self.datasc_layout.addWidget(self.var1_checkbox, 7, 0, 1, 1, QtCore.Qt.AlignLeft)

        self.var2_checkbox = QtWidgets.QCheckBox("电阻2")
        self.datasc_layout.addWidget(self.var2_checkbox, 7, 1, 1, 1, QtCore.Qt.AlignLeft)

        self.varistor_checkbox.setChecked(False)
        self.var1_checkbox.setEnabled(False)
        self.var2_checkbox.setEnabled(False)

        self.anglesensor_checkbox = QtWidgets.QCheckBox("云台角度传感器")
        self.anglesensor_checkbox.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.datasc_layout.addWidget(self.anglesensor_checkbox, 8, 0, 1, 3, QtCore.Qt.AlignCenter)

        self.ang1_checkbox = QtWidgets.QCheckBox("传感器1")
        self.datasc_layout.addWidget(self.ang1_checkbox, 9, 0, 1, 1, QtCore.Qt.AlignLeft)

        self.ang2_checkbox = QtWidgets.QCheckBox("传感器2")
        self.datasc_layout.addWidget(self.ang2_checkbox, 9, 1, 1, 1, QtCore.Qt.AlignLeft)

        self.anglesensor_checkbox.setChecked(False)
        self.ang1_checkbox.setEnabled(False)
        self.ang2_checkbox.setEnabled(False)

        self.encoder_checkbox = QtWidgets.QCheckBox("飞轮编码器")
        self.encoder_checkbox.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.datasc_layout.addWidget(self.encoder_checkbox, 10, 0, 1, 3, QtCore.Qt.AlignCenter)

        self.encang_checkbox = QtWidgets.QCheckBox("角度")
        self.datasc_layout.addWidget(self.encang_checkbox, 11, 0, 1, 1, QtCore.Qt.AlignLeft)

        self.encvel_checkbox = QtWidgets.QCheckBox("速度")
        self.datasc_layout.addWidget(self.encvel_checkbox, 11, 1, 1, 1, QtCore.Qt.AlignLeft)

        self.encoder_checkbox.setChecked(False)
        self.encang_checkbox.setEnabled(False)
        self.encvel_checkbox.setEnabled(False)

        self.depthsensor_checkbox = QtWidgets.QCheckBox("深度传感器")
        self.depthsensor_checkbox.setFont(QtGui.QFont('SimSun', 12, QtGui.QFont.Bold))
        self.datasc_layout.addWidget(self.depthsensor_checkbox, 12, 0, 1, 3, QtCore.Qt.AlignCenter)

        self.depth_checkbox = QtWidgets.QCheckBox("深度")
        self.datasc_layout.addWidget(self.depth_checkbox, 13, 0, 1, 1, QtCore.Qt.AlignLeft)

        self.depth_checkbox.setChecked(False)
        self.depth_checkbox.setEnabled(False)

        self.datashow_start_button = QtWidgets.QPushButton('开始显示')
        #self.datashow_start_button.setFixedSize(60, 30)
        self.datasc_layout.addWidget(self.datashow_start_button, 14, 0, 1, 1, QtCore.Qt.AlignCenter)

        self.datashow_stop_button = QtWidgets.QPushButton('停止显示')
        #self.datashow_stop_button.setFixedSize(60, 30)
        self.datasc_layout.addWidget(self.datashow_stop_button, 14, 1, 1, 1, QtCore.Qt.AlignCenter)
        self.datashow_stop_button.setObjectName("SET_DATASHOW_OVER")

        self.datashow_clear_button = QtWidgets.QPushButton('清空界面')
        #self.datashow_clear_button.setFixedSize(60, 30)
        self.datasc_layout.addWidget(self.datashow_clear_button, 14, 2, 1, 1, QtCore.Qt.AlignCenter)

        self.datashow_storage_button = QtWidgets.QPushButton('记录数据')
        # self.datashow_clear_button.setFixedSize(60, 30)
        self.datasc_layout.addWidget(self.datashow_storage_button, 15, 0, 1, 1, QtCore.Qt.AlignCenter)
        self.datashow_storage_button.setObjectName("GOTO_STORAGE_DATA")

        self.datashow_stopstorage_button = QtWidgets.QPushButton('停止记录')
        # self.datashow_clear_button.setFixedSize(60, 30)
        self.datasc_layout.addWidget(self.datashow_stopstorage_button, 15, 1, 1, 1, QtCore.Qt.AlignCenter)
        self.datashow_stopstorage_button.setObjectName("GOTO_STOP_STORAGE")

        self.datashow_save_button = QtWidgets.QPushButton('回传数据')
        # self.datashow_clear_button.setFixedSize(60, 30)
        self.datasc_layout.addWidget(self.datashow_save_button, 15, 2, 1, 1, QtCore.Qt.AlignCenter)
        self.datashow_save_button.setObjectName("GOTO_SEND_DATA")


    def closeEvent(self, event):
        self.close_signal.emit()
        self.close()

    #####################################################################################################
    #####################################################################################################
    ## 第二部分:关于Slot和Signal的
    #####################################################################################################
    #####################################################################################################
    # 信号连接
    def widgets_connect(self):
        """
        本函数将按钮发送信号与对应槽函数构建连接
        :return:
        """
        # 按钮
        self.swimcc_start_button.clicked.connect(self.console_button_clicked)
        self.swimcc_stop_button.clicked.connect(self.console_button_clicked)
        self.swimcc_forcestop_button.clicked.connect(self.console_button_clicked)
        self.swimcc_speedup_button.clicked.connect(self.console_button_clicked)
        self.swimcc_speeddown_button.clicked.connect(self.console_button_clicked)
        self.swimcc_turnleft_button.clicked.connect(self.console_button_clicked)
        self.swimcc_straight_button.clicked.connect(self.console_button_clicked)
        self.swimcc_turnright_button.clicked.connect(self.console_button_clicked)
        self.swimcc_dive_button.clicked.connect(self.console_button_clicked)
        self.swimcc_raise_button.clicked.connect(self.console_button_clicked)
        self.swimcc_leftfinzero_button.clicked.connect(self.console_button_clicked)
        self.swimcc_leftfinup_button.clicked.connect(self.console_button_clicked)
        self.swimcc_leftfindown_button.clicked.connect(self.console_button_clicked)
        self.swimcc_rightfinzero_button.clicked.connect(self.console_button_clicked)
        self.swimcc_rightfinup_button.clicked.connect(self.console_button_clicked)
        self.swimcc_rightfindown_button.clicked.connect(self.console_button_clicked)
        self.cpgcc_amp_button.clicked.connect(self.console_button_clicked)
        self.cpgcc_freq_button.clicked.connect(self.console_button_clicked)
        self.cpgcc_offset_button.clicked.connect(self.console_button_clicked)
        self.cpgcc_readparam_button.clicked.connect(self.console_button_clicked)
        self.attachcc_attach_button.clicked.connect(self.console_button_clicked)
        self.attachcc_detach_button.clicked.connect(self.console_button_clicked)
        self.attachcc_pumpinopen_button.clicked.connect(self.console_button_clicked)
        self.attachcc_pumpinclose_button.clicked.connect(self.console_button_clicked)
        self.attachcc_pumpoutopen_button.clicked.connect(self.console_button_clicked)
        self.attachcc_pumpoutclose_button.clicked.connect(self.console_button_clicked)
        self.attachcc_v1open_button.clicked.connect(self.console_button_clicked)
        self.attachcc_v1close_button.clicked.connect(self.console_button_clicked)
        self.attachcc_v2open_button.clicked.connect(self.console_button_clicked)
        self.attachcc_v2close_button.clicked.connect(self.console_button_clicked)
        self.gimbalcc_start_button.clicked.connect(self.console_button_clicked)
        self.gimbalcc_stop_button.clicked.connect(self.console_button_clicked)
        self.gimbalcc_zero_button.clicked.connect(self.console_button_clicked)
        self.flywheelcc_start_button.clicked.connect(self.console_button_clicked)
        self.flywheelcc_stop_button.clicked.connect(self.console_button_clicked)
        self.serial_shakehand_button.clicked.connect(self.console_button_clicked)
        

        # 数据显示
        self.datashow_start_button.clicked.connect(self.datashow_start_button_clicked)
        self.datashow_stop_button.clicked.connect(self.datashow_stop_button_clicked)
        self.datashow_clear_button.clicked.connect(self.datashow_clear_button_clicked)
        self.datashow_stopstorage_button.clicked.connect(self.console_button_clicked)

        # 串口
        self.serial1_open_button.clicked.connect(self.serial1_open_button_clicked)
        self.serial1_close_button.clicked.connect(self.serial1_close_button_clicked)
        self.serial2_open_button.clicked.connect(self.serial2_open_button_clicked)
        self.serial2_close_button.clicked.connect(self.serial2_close_button_clicked)

        # Command Shell
        self.cmdshell_text_editor.returnPressed.connect(self.command_shell_backstage)

        # Checkbox
        ## IMU
        self.imu_checkbox.stateChanged.connect(self.imu_checkbox_ctl)
        self.imu1_checkbox.stateChanged.connect(self.imu1_checkbox_ctl)
        self.imu2_checkbox.stateChanged.connect(self.imu2_checkbox_ctl)
        self.accel_checkbox.stateChanged.connect(self.accel_checkbox_ctl)
        self.gyro_checkbox.stateChanged.connect(self.gyro_checkbox_ctl)
        self.angle_checkbox.stateChanged.connect(self.angle_checkbox_ctl)
        self.x_checkbox.stateChanged.connect(self.x_checkbox_ctl)
        self.y_checkbox.stateChanged.connect(self.y_checkbox_ctl)
        self.z_checkbox.stateChanged.connect(self.z_checkbox_ctl)
        ## 压敏电阻
        self.varistor_checkbox.stateChanged.connect(self.varistor_checkbox_ctl)
        self.var1_checkbox.stateChanged.connect(self.var1_checkbox_ctl)
        self.var2_checkbox.stateChanged.connect(self.var2_checkbox_ctl)
        ## 角度传感器
        self.anglesensor_checkbox.stateChanged.connect(self.anglesensor_checkbox_ctl)
        self.ang1_checkbox.stateChanged.connect(self.ang1_checkbox_ctl)
        self.ang2_checkbox.stateChanged.connect(self.ang2_checkbox_ctl)
        ## 飞轮编码器
        self.encoder_checkbox.stateChanged.connect(self.encoder_checkbox_ctl)
        self.encang_checkbox.stateChanged.connect(self.encang_checkbox_ctl)
        self.encvel_checkbox.stateChanged.connect(self.encvel_checkbox_ctl)
        ## 深度传感器
        self.depthsensor_checkbox.stateChanged.connect(self.depthsensor_checkbox_ctl)
        self.depth_checkbox.stateChanged.connect(self.depth_checkbox_ctl)

    # 控制台按钮回调函数
    def console_button_clicked(self):
        """
        本函数为控制台按钮按下时,关联的槽函数
        每个控制台的按钮都对应了RFLink通讯协议中的一条Command,所以可以统一用一个函数来处理
        每当按钮按下时,串口将Command发送出去,发给机器人
        :return:
        """
        sender_button = self.sender()
        if rflink.Command[sender_button.objectName()] is rflink.Command.SET_SINE_MOTION_AMP:
            data = (self.cpgcc_amp_edit.text()).encode('ascii')
        elif rflink.Command[sender_button.objectName()] is rflink.Command.SET_SINE_MOTION_FREQ:
            data = (self.cpgcc_freq_edit.text()).encode('ascii')
        elif rflink.Command[sender_button.objectName()] is rflink.Command.SET_SINE_MOTION_OFFSET:
            data = (self.cpgcc_offset_edit.text()).encode('ascii')
        else:
            data = 0

        # 数据打包
        datapack = rftool.RFLink_packdata(rflink.Command[sender_button.objectName()].value, data)

        # 数据发送
        with QtCore.QMutexLocker(ser_mutex):
            try:
                send_sertool.write_cmd(datapack)
            except serial.serialutil.SerialException:
                self.statusBar().showMessage('串口未打开,无法发送')

    # Command Shell后端函数
    def command_shell_backstage(self):
        """
        本函数为Command Shell的后端函数
        每当输入命令栏,敲击回车键以后,会调用此函数
        :return:
        """
        # 获取用户输入的指令
        prefix = "<font color='Cyan'>roboremora-host:~$&nbsp;</font> "
        instr = self.cmdshell_text_editor.text()
        # self.cmdshell_text_editor.clear() # 清除编辑区的文字
        self.cmdshell_text_browser.append(prefix + instr)
        instrlist = instr.split()
        try:
            cmd = instrlist[0]
        except IndexError:
            return

        # 判断指令所属类型
        if cmd == "clear": # 清除Shell显示区
            self.cmdshell_text_browser.clear()
            self.cmdshell_text_browser.append(prefix)

        elif cmd == "help": # 打开帮助
            self.cmdshell_text_browser.append("<font color='DarkOrange'>Help&nbsp;Doc</font>")
            self.cmdshell_text_browser.append("<font color='DeepPink'>Basic&nbsp;operate&nbsp;commands&nbsp;including:</font>")
            self.cmdshell_text_browser.append("<font color='GreenYellow'>(1)&nbsp;ls</font>")
            self.cmdshell_text_browser.append("<font color='GreenYellow'>(1)&nbsp;clear</font>")
            self.cmdshell_text_browser.append("<font color='GreenYellow'>(2)&nbsp;help</font>")
            self.cmdshell_text_browser.append("<font color='GreenYellow'>(2)&nbsp;SET</font>")
            self.cmdshell_text_browser.append("<font color='GreenYellow'>(2)&nbsp;READ</font>")
            self.cmdshell_text_browser.append("<font color='GreenYellow'>(2)&nbsp;GOTO</font>")
            self.cmdshell_text_browser.append("<font color='DeepPink'>Commands&nbsp;consist&nbsp;of&nbsp;four&nbsp;categories,&nbsp;including:</font>")
            self.cmdshell_text_browser.append("<font color='GreenYellow'>(1)&nbsp;SHAKING_HANDS&nbsp;:&nbsp;build&nbsp;communication&nbsp;with&nbsp;slave</font>")
            self.cmdshell_text_browser.append("<font color='GreenYellow'>(2)&nbsp;SET&nbsp;cmd:&nbsp;set&nbsp;parameters&nbsp;of&nbsp;slave</font>")
            self.cmdshell_text_browser.append("<font color='GreenYellow'>(3)&nbsp;READ&nbsp;cmd:&nbsp;read&nbsp;parameters&nbsp;from&nbsp;slave</font>")
            self.cmdshell_text_browser.append("<font color='GreenYellow'>(4)&nbsp;GOTO&nbsp;cmd:&nbsp;goto&nbsp;execute&nbsp;behaviors&nbsp;of&nbsp;slave</font>")
            self.cmdshell_text_browser.append("<font color='DarkOrange'>Further&nbsp;explanation,&nbsp;please&nbsp;type&nbsp;'SET*'&nbsp;or&nbsp;'READ*'&nbsp;or&nbsp;'GOTO*'</font>")

        elif cmd == "SET": # 查询SET相关命令
            self.cmdshell_text_browser.append("<font color='DarkOrange'>" + "Usage&nbsp;:&nbsp;SET*&nbsp;[param1]&nbsp;[param2]&nbsp;..." + "</font>")
            self.cmdshell_text_browser.append("<font color='DeepPink'>" + "Example&nbsp;:&nbsp;SET_SINE_MOTION_AMP&nbsp;0.1" + "</font>")
            for i in range(33):
                self.cmdshell_text_browser.append("<font color='GreenYellow'>"+rflink.Command(i+2).name+"</font>")

        elif cmd == "READ": # 查询READ相关命令
            self.cmdshell_text_browser.append("<font color='DarkOrange'>" + "Usage&nbsp;:&nbsp;READ*" + "</font>")
            self.cmdshell_text_browser.append("<font color='DeepPink'>" + "Example&nbsp;:&nbsp;READ_ROBOT_STATUS" + "</font>")
            for i in range(15):
                self.cmdshell_text_browser.append("<font color='GreenYellow'>" + rflink.Command(i + 35).name + "</font>")

        elif cmd == "GOTO": # 查询GOTO相关命令
            self.cmdshell_text_browser.append("<font color='DarkOrange'>" + "Usage&nbsp;:&nbsp;GOTO*" + "</font>")
            self.cmdshell_text_browser.append("<font color='DeepPink'>" + "Example&nbsp;:&nbsp;GOTO_ATTACH" + "</font>")
            for i in range(4):
                self.cmdshell_text_browser.append("<font color='GreenYellow'>" + rflink.Command(i + 50).name + "</font>")

        elif cmd == "ls": # 显示下位机SD卡中的文件名
            # 发送一条读取文件列表的命令,等待下位机响应,并返回文件列表
            datapack = rftool.RFLink_packdata(rflink.Command.READ_FILE_LIST.value, None)
            with QtCore.QMutexLocker(ser_mutex):
                try:
                    send_sertool.write_cmd(datapack)
                except serial.serialutil.SerialException:
                    self.cmdshell_text_browser.append(
                        "<font color='red'>Warning&nbsp;:&nbsp;Serial&nbsp;port&nbsp;not&nbsp;open,&nbsp;false&nbsp;!</font>")
            # self.polling_state_thread.pause()
            # time.sleep(1.0)
            # self.polling_state_thread.resume()

        elif cmd == "save":
            self.cmdshell_text_browser.append("<font color='orange'>(1)GOTO_STORAGE_DATA</font>")
            self.cmdshell_text_browser.append("<font color='orange'>(2)GOTO_SEND_DATA</font>")

        else: # 其他指令,也就是rflink中定义的指令
            if cmd in rflink.Command.__members__:
                self.cmdshell_text_browser.append("<font color='DodgerBlue'>Execute&nbsp;"+ instr + "</font>")
                # 如果是设置运动参数相关的命令
                if rflink.Command[cmd] is rflink.Command.SET_SINE_MOTION_AMP \
                    or rflink.Command[cmd] is rflink.Command.SET_SINE_MOTION_FREQ \
                    or rflink.Command[cmd] is rflink.Command.SET_SINE_MOTION_OFFSET:
                    try:
                        data = (instrlist[1]).encode('ascii')
                    except IndexError:
                        self.cmdshell_text_browser.append("<font color='red'>Error&nbsp;:&nbsp;Command&nbsp;parameters&nbsp;too&nbsp;be&nbsp;less!</font>")
                        self.cmdshell_text_browser.append(
                            "<font color='DarkOrange'>Usage&nbsp;:&nbsp;SET_SINE_MOTION_AMP&nbsp;[float]</font>")
                        return
                # 如果是设置是否读取数据文件相关的命令
                elif rflink.Command[cmd] is rflink.Command.GOTO_STORAGE_DATA \
                  or rflink.Command[cmd] is rflink.Command.GOTO_SEND_DATA:
                    try:
                        filenamelist = instrlist[2].split('.')
                        # 判断是不是bin文件
                        if filenamelist[1] != 'bin':
                            self.cmdshell_text_browser.append(
                                "<font color='DarkOrange'>Usage&nbsp;:&nbsp;GOTO_STORAGE_DATA&nbsp;[int]&nbsp;[(string).bin]</font>")
                            return

                        data = int(instrlist[1]).to_bytes(1,'big') + (instrlist[2]).encode('ascii')
                    except IndexError or ValueError:
                        self.cmdshell_text_browser.append("<font color='red'>Error&nbsp;:&nbsp;Command&nbsp;parameters&nbsp;error!</font>")
                        self.cmdshell_text_browser.append(
                            "<font color='DarkOrange'>Usage&nbsp;:&nbsp;GOTO_STORAGE_DATA&nbsp;[int]&nbsp;[(string).bin]</font>")
                        return
                # 如果是设置飞轮操作的相关命令
                elif rflink.Command[cmd] is rflink.Command.SET_FLYWHEEL_CMD:
                    try:
                        data = (instrlist[1]).encode('ascii')
                    except IndexError:
                        self.cmdshell_text_browser.append("<font color='red'>Error&nbsp;:&nbsp;Command&nbsp;parameters&nbsp;too&nbsp;be&nbsp;less!</font>")
                        self.cmdshell_text_browser.append(
                            "<font color='DarkOrange'>Usage&nbsp;:&nbsp;SET_FLYWHEEL_CMD&nbsp;[char]</font>")
                        return

                # 打包成数据包,发送给下位机
                datapack = rftool.RFLink_packdata(rflink.Command[cmd].value, data)

                # self.cmdshell_text_browser.append(str(datapack))
                with QtCore.QMutexLocker(ser_mutex):
                    try:
                        send_sertool.write_cmd(datapack)
                    except serial.serialutil.SerialException:
                        self.cmdshell_text_browser.append(
                            "<font color='red'>Warning&nbsp;:&nbsp;Serial&nbsp;port&nbsp;not&nbsp;open,&nbsp;false&nbsp;!</font>")
            else:
                self.cmdshell_text_browser.append(
                    "<font color='red'>Warning&nbsp;:&nbsp;Command&nbsp;not&nbsp;found&nbsp;!&nbsp;Type&nbsp;'help'&nbsp;for&nbsp;detailed&nbsp;usages.</font>")

    # 有关数据显示的一系列按钮
    def datashow_start_button_clicked(self):
        """
        开始显示数据
        每当输入命令栏,敲击回车键以后,会调用此函数
        :return:
        """
        cmdvalue = None
        data = None
        # 判断传感器类型
        ### IMU
        if self.datashow_sensor_type == 1:
            # 判断传感器ID和数据类型
            if self.datashow_sensor_id == 1: # IMU1
                if self.datashow_sensor_datatype == 1:
                    cmdvalue = rflink.Command["READ_IMU1_ATTITUDE"].value
                elif self.datashow_sensor_datatype == 2:
                    cmdvalue = rflink.Command["READ_IMU1_ACCEL"].value
                elif self.datashow_sensor_datatype == 3:
                    cmdvalue = rflink.Command["READ_IMU1_GYRO"].value
                else:
                    self.statusBar().showMessage('未选定需要显示的数据')
                    return
            elif self.datashow_sensor_id == 2: # IMU2
                if self.datashow_sensor_datatype == 1:
                    cmdvalue = rflink.Command["READ_IMU2_ATTITUDE"].value
                elif self.datashow_sensor_datatype == 2:
                    cmdvalue = rflink.Command["READ_IMU2_ACCEL"].value
                elif self.datashow_sensor_datatype == 3:
                    cmdvalue = rflink.Command["READ_IMU2_GYRO"].value
                else:
                    self.statusBar().showMessage('未选定需要显示的数据')
                    return
            else:
                self.statusBar().showMessage('未选定需要显示的数据')
                return

            # 判断数据的轴向
            if self.datashow_sensor_dataaxis == 1:
                data = 1
            elif self.datashow_sensor_dataaxis == 2:
                data = 2
            elif self.datashow_sensor_dataaxis == 3:
                data = 3
            else:
                self.statusBar().showMessage('未选定需要显示的数据')
                return

        ### 压敏电阻
        elif self.datashow_sensor_type == 2:
            if self.datashow_sensor_id == 1:
                cmdvalue = rflink.Command["READ_VARISTOR1_VAL"].value
            elif self.datashow_sensor_id == 2:
                cmdvalue = rflink.Command["READ_VARISTOR2_VAL"].value
            else:
                self.statusBar().showMessage('未选定需要显示的数据')
                return

        ### 云台角度传感器
        elif self.datashow_sensor_type == 3:
            if self.datashow_sensor_id == 1:
                cmdvalue = rflink.Command["READ_GIMBAL1_ANGLE"].value
            elif self.datashow_sensor_id == 2:
                cmdvalue = rflink.Command["READ_GIMBAL2_ANGLE"].value
            else:
                self.statusBar().showMessage('未选定需要显示的数据')
                return

        ### 飞轮编码器
        elif self.datashow_sensor_type == 4:
            if self.datashow_sensor_id == 1:
                cmdvalue = rflink.Command["READ_FLYWHEEL_ANGLE"].value
            elif self.datashow_sensor_id == 2:
                cmdvalue = rflink.Command["READ_FLYWHEEL_VEL"].value
            else:
                self.statusBar().showMessage('未选定需要显示的数据')
                return
        
        ### 深度传感器
        elif self.datashow_sensor_type == 5:
            if self.datashow_sensor_id == 1:
                cmdvalue = rflink.Command["READ_DEPTH"].value
            else:
                self.statusBar().showMessage('未选定需要显示的数据')
                return
        else:
            self.statusBar().showMessage('未选定需要显示的数据')
            return

        # 发送信号
        datapack = rftool.RFLink_packdata(cmdvalue, str(data).encode('ascii'))
        with QtCore.QMutexLocker(ser_mutex):
            try:
                send_sertool.write_cmd(datapack)
            except serial.serialutil.SerialException:
                self.statusBar().showMessage('串口未打开,无法发送')
                return
        self.datashow_running_flag = True
        ## 一旦开始显示数据,全部checkbox都会停止
        # IMU
        self.imu_checkbox.setEnabled(False)
        self.imu1_checkbox.setEnabled(False)
        self.imu2_checkbox.setEnabled(False)
        self.accel_checkbox.setEnabled(False)
        self.gyro_checkbox.setEnabled(False)
        self.angle_checkbox.setEnabled(False)
        self.x_checkbox.setEnabled(False)
        self.y_checkbox.setEnabled(False)
        self.z_checkbox.setEnabled(False)
        # 压敏电阻
        self.varistor_checkbox.setEnabled(False)
        self.var1_checkbox.setEnabled(False)
        self.var2_checkbox.setEnabled(False)
        # 云台角度
        self.anglesensor_checkbox.setEnabled(False)
        self.ang1_checkbox.setEnabled(False)
        self.ang2_checkbox.setEnabled(False)
        # 飞轮编码器
        self.encoder_checkbox.setEnabled(False)
        self.encang_checkbox.setEnabled(False)
        self.encvel_checkbox.setEnabled(False)
         # 深度传感器
        self.depthsensor_checkbox.setChecked(False)
        self.depth_checkbox.setEnabled(False)


    def datashow_stop_button_clicked(self):
        datapack = rftool.RFLink_packdata(rflink.Command["SET_DATASHOW_OVER"].value, None)
        with QtCore.QMutexLocker(ser_mutex):
            try:
                send_sertool.write_cmd(datapack)
            except serial.serialutil.SerialException:
                self.statusBar().showMessage('串口未打开,无法发送')
                return
        self.datashow_running_flag = False

        ### 停止显示后使能Checkbox
        self.imu_checkbox.setEnabled(True)
        self.varistor_checkbox.setEnabled(True)
        self.anglesensor_checkbox.setEnabled(True)
        self.encoder_checkbox.setEnabled(True)
        if self.datashow_sensor_type == 1:
            self.imu1_checkbox.setEnabled(True)
            self.imu2_checkbox.setEnabled(True)
            self.accel_checkbox.setEnabled(True)
            self.gyro_checkbox.setEnabled(True)
            self.angle_checkbox.setEnabled(True)
            self.x_checkbox.setEnabled(True)
            self.y_checkbox.setEnabled(True)
            self.z_checkbox.setEnabled(True)
        elif self.datashow_sensor_type == 2:
            self.var1_checkbox.setEnabled(True)
            self.var2_checkbox.setEnabled(True)
        elif self.datashow_sensor_type == 3:
            self.ang1_checkbox.setEnabled(True)
            self.ang2_checkbox.setEnabled(True)
        elif self.datashow_sensor_type == 4:
            self.encang_checkbox.setEnabled(True)
            self.encvel_checkbox.setEnabled(True)
        elif self.datashow_sensor_type == 5:        # 深度传感器
            self.depthsensor_checkbox.setChecked(True)
            self.depth_checkbox.setEnabled(True)
        else:
            return

    def datashow_clear_button_clicked(self):
        if self.datashow_running_flag == False:
            # 停止绘制后的操作
            plt_mutex.lock()
            self.datalist = []
            self.timelist = []
            self.showtime = 0
            self.sensor_data_canvas.clear()
            plt_mutex.unlock()

    def datashow_save_button_clicked(self, filename):
        if self.datashow_running_flag == True:
            self.statusBar().showMessage('停止显示后,方可回传数据')
            self.SBBW.set_lineeditor_text('停止显示后,方可回传数据')
            return
        self.savefile_name = filename
        datapack = rftool.RFLink_packdata(rflink.Command["GOTO_SEND_DATA"].value, b'\x01'+filename.encode('ascii'))
        with QtCore.QMutexLocker(ser_mutex):
            try:
                send_sertool.write_cmd(datapack)
            except serial.serialutil.SerialException:
                self.statusBar().showMessage('串口未打开,无法发送')
                self.SBBW.set_lineeditor_text('串口未打开,无法发送')
            

    def datashow_storage_button_clicked(self, filename):
        datapack = rftool.RFLink_packdata(rflink.Command["GOTO_STORAGE_DATA"].value, b'\x01'+filename.encode('ascii'))
        with QtCore.QMutexLocker(ser_mutex):
            try:
                send_sertool.write_cmd(datapack)
                self.statusBar().showMessage('数据已开始储存')
            except serial.serialutil.SerialException:
                self.statusBar().showMessage('串口未打开,无法发送')

    # 有关串口开关的一系列按钮
    def serial1_open_button_clicked(self):
        """
        串口打开按钮对应的槽函数
        :return:
        """
        global send_sertool

        if(platform.system()=='Windows'):
            port = self.serial1_com_combo.currentText()
        elif(platform.system()=='Linux'):
            port = '/dev/'+self.serial1_com_combo.currentText()

        baud = int(self.serial1_bps_combo.currentText())
        try:
            send_sertool.init_serial(port,baud)
            self.statusBar().showMessage('发送串口已开启')
        except serial.serialutil.SerialException:
            self.statusBar().showMessage('该串口不存在')

    def serial1_close_button_clicked(self):
        """
        串口关闭对应的槽函数
        :return:
        """
        self.polling_state_thread.pause()
        send_sertool.close_serial()
        self.statusBar().showMessage('发送串口已关闭')

    def serial2_open_button_clicked(self):
        """
        接收串口打开按钮对应的槽函数
        :return:
        """
        global recv_sertool

        if(platform.system()=='Windows'):
            port = self.serial2_com_combo.currentText()
        elif(platform.system()=='Linux'):
            port = '/dev/'+self.serial2_com_combo.currentText()

        baud = int(self.serial2_bps_combo.currentText())
        try:
            recv_sertool.init_serial(port,baud)

            if self.receive_data_thread.is_running is False:
                self.receive_data_thread.start()
            else:
                self.receive_data_thread.resume()

            if self.analysis_data_thread.is_running is False:
                self.analysis_data_thread.start()
            else:
                self.analysis_data_thread.resume()

            self.statusBar().showMessage('接收串口已开启')
        except serial.serialutil.SerialException:
            self.statusBar().showMessage('该串口不存在')

    def serial2_close_button_clicked(self):
        """
        接收串口关闭对应的槽函数
        :return:
        """
        self.receive_data_thread.pause()
        self.analysis_data_thread.pause()
        recv_sertool.close_serial()
        self.statusBar().showMessage('接收串口已关闭')

    # 有关Check box 配置的一系列槽函数
    ## IMU部分
    def imu_checkbox_ctl(self):

        if self.imu_checkbox.isChecked():
            # IMU
            self.imu_checkbox.setChecked(True)
            self.imu1_checkbox.setEnabled(True)
            self.imu2_checkbox.setEnabled(True)
            self.accel_checkbox.setEnabled(True)
            self.gyro_checkbox.setEnabled(True)
            self.angle_checkbox.setEnabled(True)
            self.x_checkbox.setEnabled(True)
            self.y_checkbox.setEnabled(True)
            self.z_checkbox.setEnabled(True)

            # 压敏电阻
            self.varistor_checkbox.setChecked(False)
            self.var1_checkbox.setEnabled(False)
            self.var2_checkbox.setEnabled(False)
            # 云台角度
            self.anglesensor_checkbox.setChecked(False)
            self.ang1_checkbox.setEnabled(False)
            self.ang2_checkbox.setEnabled(False)
            # 飞轮编码器
            self.encoder_checkbox.setChecked(False)
            self.encang_checkbox.setEnabled(False)
            self.encvel_checkbox.setEnabled(False)
            # 深度传感器
            self.depthsensor_checkbox.setChecked(False)
            self.depth_checkbox.setEnabled(False)

            ## 刷新datashow状态变量
            ### datashow_sensor_type
            self.datashow_sensor_type = 1
            self.datashow_sensor_id = 0
            self.datashow_sensor_datatype = 0
            self.datashow_sensor_dataaxis = 0
            ### datashow_sensor_id
            if self.imu1_checkbox.isChecked():
                self.datashow_sensor_id = 1
            elif self.imu2_checkbox.isChecked():
                self.datashow_sensor_id = 2
            else:
                self.datashow_sensor_id = 0
            ### datashow_sensor_datatype
            if self.angle_checkbox.isChecked():
                self.datashow_sensor_datatype = 1
            elif self.accel_checkbox.isChecked():
                self.datashow_sensor_datatype = 2
            elif self.gyro_checkbox.isChecked():
                self.datashow_sensor_datatype = 3
            else:
                self.datashow_sensor_datatype = 0
            ### datashow_sensor_dataaxis
            if self.x_checkbox.isChecked():
                self.datashow_sensor_dataaxis = 1
            elif self.y_checkbox.isChecked():
                self.datashow_sensor_dataaxis = 2
            elif self.z_checkbox.isChecked():
                self.datashow_sensor_dataaxis = 3
            else:
                self.datashow_sensor_dataaxis = 0

    def imu1_checkbox_ctl(self):

        if self.imu1_checkbox.isChecked():
            self.imu2_checkbox.setChecked(False)
            self.datashow_sensor_type = 1
            self.datashow_sensor_id = 1

    def imu2_checkbox_ctl(self):

        if self.imu2_checkbox.isChecked():
            self.imu1_checkbox.setChecked(False)
            self.datashow_sensor_type = 1
            self.datashow_sensor_id = 2

    def accel_checkbox_ctl(self):

        if self.accel_checkbox.isChecked():
            self.gyro_checkbox.setChecked(False)
            self.angle_checkbox.setChecked(False)
            self.datashow_sensor_type = 1
            self.datashow_sensor_datatype = 2

    def gyro_checkbox_ctl(self):

        if self.gyro_checkbox.isChecked():
            self.accel_checkbox.setChecked(False)
            self.angle_checkbox.setChecked(False)
            self.datashow_sensor_type = 1
            self.datashow_sensor_datatype = 3

    def angle_checkbox_ctl(self):

        if self.angle_checkbox.isChecked():
            self.gyro_checkbox.setChecked(False)
            self.accel_checkbox.setChecked(False)
            self.datashow_sensor_type = 1
            self.datashow_sensor_datatype = 1

    def x_checkbox_ctl(self):

        if self.x_checkbox.isChecked():
            self.y_checkbox.setChecked(False)
            self.z_checkbox.setChecked(False)
            self.datashow_sensor_type = 1
            self.datashow_sensor_dataaxis = 1

    def y_checkbox_ctl(self):

        if self.y_checkbox.isChecked():
            self.x_checkbox.setChecked(False)
            self.z_checkbox.setChecked(False)
            self.datashow_sensor_type = 1
            self.datashow_sensor_dataaxis = 2

    def z_checkbox_ctl(self):

        if self.z_checkbox.isChecked():
            self.x_checkbox.setChecked(False)
            self.y_checkbox.setChecked(False)
            self.datashow_sensor_type = 1
            self.datashow_sensor_dataaxis = 3

    ## 压敏电阻部分
    def varistor_checkbox_ctl(self):

        if self.varistor_checkbox.isChecked():
            # IMU
            self.imu_checkbox.setChecked(False)
            self.imu1_checkbox.setEnabled(False)
            self.imu2_checkbox.setEnabled(False)
            self.accel_checkbox.setEnabled(False)
            self.gyro_checkbox.setEnabled(False)
            self.angle_checkbox.setEnabled(False)
            self.x_checkbox.setEnabled(False)
            self.y_checkbox.setEnabled(False)
            self.z_checkbox.setEnabled(False)
            # 压敏电阻
            self.varistor_checkbox.setChecked(True)
            self.var1_checkbox.setEnabled(True)
            self.var2_checkbox.setEnabled(True)
            # 云台角度
            self.anglesensor_checkbox.setChecked(False)
            self.ang1_checkbox.setEnabled(False)
            self.ang2_checkbox.setEnabled(False)
            # 飞轮编码器
            self.encoder_checkbox.setChecked(False)
            self.encang_checkbox.setEnabled(False)
            self.encvel_checkbox.setEnabled(False)
            # 深度传感器
            self.depthsensor_checkbox.setChecked(False)
            self.depth_checkbox.setEnabled(False)

            ## 刷新datashow状态变量
            ### datashow_sensor_type
            self.datashow_sensor_type = 2
            self.datashow_sensor_id = 0
            self.datashow_sensor_datatype = 0
            self.datashow_sensor_dataaxis = 0
            ### datashow_sensor_id
            if self.var1_checkbox.isChecked():
                self.datashow_sensor_id = 1
            elif self.var2_checkbox.isChecked():
                self.datashow_sensor_id = 2
            else:
                self.datashow_sensor_id = 0

    def var1_checkbox_ctl(self):

        if self.var1_checkbox.isChecked():
            self.var2_checkbox.setChecked(False)
            self.datashow_sensor_type = 2
            self.datashow_sensor_id = 1

    def var2_checkbox_ctl(self):

        if self.var2_checkbox.isChecked():
            self.var1_checkbox.setChecked(False)
            self.datashow_sensor_type = 2
            self.datashow_sensor_id = 2

    # 角度传感器部分
    def anglesensor_checkbox_ctl(self):

        if self.anglesensor_checkbox.isChecked():
            # IMU
            self.imu_checkbox.setChecked(False)
            self.imu1_checkbox.setEnabled(False)
            self.imu2_checkbox.setEnabled(False)
            self.accel_checkbox.setEnabled(False)
            self.gyro_checkbox.setEnabled(False)
            self.angle_checkbox.setEnabled(False)
            self.x_checkbox.setEnabled(False)
            self.y_checkbox.setEnabled(False)
            self.z_checkbox.setEnabled(False)
            # 压敏电阻
            self.varistor_checkbox.setChecked(False)
            self.var1_checkbox.setEnabled(False)
            self.var2_checkbox.setEnabled(False)
            # 云台角度
            self.anglesensor_checkbox.setChecked(True)
            self.ang1_checkbox.setEnabled(True)
            self.ang2_checkbox.setEnabled(True)
            # 飞轮编码器
            self.encoder_checkbox.setChecked(False)
            self.encang_checkbox.setEnabled(False)
            self.encvel_checkbox.setEnabled(False)
            # 深度传感器
            self.depthsensor_checkbox.setChecked(False)
            self.depth_checkbox.setEnabled(False)

            ## 刷新datashow状态变量
            ### datashow_sensor_type
            self.datashow_sensor_type = 3
            self.datashow_sensor_id = 0
            self.datashow_sensor_datatype = 0
            self.datashow_sensor_dataaxis = 0
            ### datashow_sensor_id
            if self.ang1_checkbox.isChecked():
                self.datashow_sensor_id = 1
            elif self.ang2_checkbox.isChecked():
                self.datashow_sensor_id = 2
            else:
                self.datashow_sensor_id = 0

    def ang1_checkbox_ctl(self):

        if self.ang1_checkbox.isChecked():
            self.ang2_checkbox.setChecked(False)
            self.datashow_sensor_type = 3
            self.datashow_sensor_id = 1

    def ang2_checkbox_ctl(self):

        if self.ang2_checkbox.isChecked():
            self.ang1_checkbox.setChecked(False)
            self.datashow_sensor_type = 3
            self.datashow_sensor_id = 2

    ## 飞轮编码器部分
    def encoder_checkbox_ctl(self):

        if self.encoder_checkbox.isChecked():
            # IMU
            self.imu_checkbox.setChecked(False)
            self.imu1_checkbox.setEnabled(False)
            self.imu2_checkbox.setEnabled(False)
            self.accel_checkbox.setEnabled(False)
            self.gyro_checkbox.setEnabled(False)
            self.angle_checkbox.setEnabled(False)
            self.x_checkbox.setEnabled(False)
            self.y_checkbox.setEnabled(False)
            self.z_checkbox.setEnabled(False)
            # 压敏电阻
            self.varistor_checkbox.setChecked(False)
            self.var1_checkbox.setEnabled(False)
            self.var2_checkbox.setEnabled(False)
            # 云台角度
            self.anglesensor_checkbox.setChecked(False)
            self.ang1_checkbox.setEnabled(False)
            self.ang2_checkbox.setEnabled(False)
            # 飞轮编码器
            self.encoder_checkbox.setChecked(True)
            self.encang_checkbox.setEnabled(True)
            self.encvel_checkbox.setEnabled(True)
            # 深度传感器
            self.depthsensor_checkbox.setChecked(False)
            self.depth_checkbox.setEnabled(False)

            ## 刷新datashow状态变量
            ### datashow_sensor_type
            self.datashow_sensor_type = 4
            self.datashow_sensor_id = 0
            self.datashow_sensor_datatype = 0
            self.datashow_sensor_dataaxis = 0
            ### datashow_sensor_datatype
            if self.encang_checkbox.isChecked():
                self.datashow_sensor_id = 1
            elif self.encvel_checkbox.isChecked():
                self.datashow_sensor_id = 2
            else:
                self.datashow_sensor_id = 0

    def encang_checkbox_ctl(self):

        if self.encang_checkbox.isChecked():
            self.encvel_checkbox.setChecked(False)
            self.datashow_sensor_type = 4
            self.datashow_sensor_id = 1

    def encvel_checkbox_ctl(self):

        if self.encvel_checkbox.isChecked():
            self.encang_checkbox.setChecked(False)
            self.datashow_sensor_type = 4
            self.datashow_sensor_id = 2

    def depthsensor_checkbox_ctl(self):
        if self.depthsensor_checkbox.isChecked():
            # IMU
            self.imu_checkbox.setChecked(False)
            self.imu1_checkbox.setEnabled(False)
            self.imu2_checkbox.setEnabled(False)
            self.accel_checkbox.setEnabled(False)
            self.gyro_checkbox.setEnabled(False)
            self.angle_checkbox.setEnabled(False)
            self.x_checkbox.setEnabled(False)
            self.y_checkbox.setEnabled(False)
            self.z_checkbox.setEnabled(False)
            # 压敏电阻
            self.varistor_checkbox.setChecked(False)
            self.var1_checkbox.setEnabled(False)
            self.var2_checkbox.setEnabled(False)
            # 云台角度
            self.anglesensor_checkbox.setChecked(False)
            self.ang1_checkbox.setEnabled(False)
            self.ang2_checkbox.setEnabled(False)
            # 飞轮编码器
            self.encoder_checkbox.setChecked(False)
            self.encang_checkbox.setEnabled(False)
            self.encvel_checkbox.setEnabled(False)
            # 深度传感器
            self.depthsensor_checkbox.setChecked(True)
            self.depth_checkbox.setEnabled(True)

            ## 刷新datashow状态变量
            ### datashow_sensor_type
            self.datashow_sensor_type = 5
            self.datashow_sensor_id = 0
            self.datashow_sensor_datatype = 0
            self.datashow_sensor_dataaxis = 0
            ### datashow_sensor_datatype
            if self.depth_checkbox.isChecked():
                self.datashow_sensor_id = 1
            else:
                self.datashow_sensor_id = 0

    def depth_checkbox_ctl(self):
        if self.depth_checkbox.isChecked():
            self.datashow_sensor_type = 5
            self.datashow_sensor_id = 1

    #####################################################################################################
    #####################################################################################################
    ## 第三部分:下位机数据处理,就一个函数
    #####################################################################################################
    #####################################################################################################
    def newdata_comming_slot(self,command_id):
        """
        窗口更新槽函数
        每当接收到来自AnalysisDataThread的Command的ID,开始刷新窗口界面
        :param command_id:接收的Command的ID
        :return:
        """
        global roboremora
        global rftool

        if rflink.Command(command_id) is rflink.Command.SHAKING_HANDS:
            # 握手成功,打开轮询线程
            if self.polling_state_thread.is_running is False:
                self.polling_state_thread.start()
            else:
                self.polling_state_thread.resume()
            # 刷新cmdshell
            prefix = "<font color='red'>slave:~$&nbsp;</font> "
            self.cmdshell_text_browser.append(prefix + "Shaking&nbsp;hands&nbsp;succeed&nbsp;!")

        elif rflink.Command(command_id) is rflink.Command.READ_ROBOT_STATUS:
            # 更新状态栏
            rm_mutex.lock()
            pal = QtGui.QPalette()
            self.swimstate_label.setAutoFillBackground(True)
            if roboremora.swim_state is remorastate.SwimState.SWIM_FORCESTOP:
                self.swimstate_label.setText('停止')
                pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.red)
                self.swimstate_label.setPalette(pal)
            elif roboremora.swim_state is remorastate.SwimState.SWIM_STOP:
                self.swimstate_label.setText('暂停')
                pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.blue)
                self.swimstate_label.setPalette(pal)
            elif roboremora.swim_state is remorastate.SwimState.SWIM_RUN:
                self.swimstate_label.setText('运行')
                pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.green)
                self.swimstate_label.setPalette(pal)
            elif roboremora.swim_state is remorastate.SwimState.SWIM_INIT:
                self.swimstate_label.setText('初始化')
                pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.gray)
                self.swimstate_label.setPalette(pal)

            self.valve1state_label.setAutoFillBackground(True)
            if roboremora.valve1_state is remorastate.ValveState.VALVE_OFF:
                self.valve1state_label.setText('关闭')
                pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.red)
                self.valve1state_label.setPalette(pal)
            elif roboremora.valve1_state is remorastate.ValveState.VALVE_ON:
                self.valve1state_label.setText('打开')
                pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.green)
                self.valve1state_label.setPalette(pal)

            if roboremora.valve2_state is remorastate.ValveState.VALVE_OFF:
                self.valve2state_label.setText('关闭')
                pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.red)
                self.valve2state_label.setPalette(pal)
            elif roboremora.valve2_state is remorastate.ValveState.VALVE_ON:
                self.valve2state_label.setText('打开')
                pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.green)
                self.valve2state_label.setPalette(pal)

            if roboremora.pumpin_state is remorastate.PumpState.PUMP_OFF:
                self.pumpinstate_label.setText('停止')
                pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.red)
                self.pumpinstate_label.setPalette(pal)
            elif roboremora.pumpin_state is remorastate.PumpState.PUMP_ON:
                self.pumpinstate_label.setText('运行')
                pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.green)
                self.pumpinstate_label.setPalette(pal)

            if roboremora.pumpout_state is remorastate.PumpState.PUMP_OFF:
                self.pumpoutstate_label.setText('停止')
                pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.red)
                self.pumpoutstate_label.setPalette(pal)
            elif roboremora.pumpout_state is remorastate.PumpState.PUMP_ON:
                self.pumpoutstate_label.setText('运行')
                pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.green)
                self.pumpoutstate_label.setPalette(pal)

            if roboremora.gimbal_state is remorastate.GimbalState.GIMBAL_STOP:
                self.gimbalstate_label.setText('停止')
                pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.red)
                self.gimbalstate_label.setPalette(pal)
            elif roboremora.gimbal_state is remorastate.GimbalState.GIMBAL_RUN:
                self.gimbalstate_label.setText('运行')
                pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.green)
                self.gimbalstate_label.setPalette(pal)
            elif roboremora.gimbal_state is remorastate.GimbalState.GIMBAL_ZERO:
                self.gimbalstate_label.setText('归中')
                pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.yellow)
                self.gimbalstate_label.setPalette(pal)

            if roboremora.flywheel_state is remorastate.FlywheelState.FLYWHEEL_STOP:
                self.flywheelstate_label.setText('停止')
                pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.red)
                self.flywheelstate_label.setPalette(pal)
            elif roboremora.flywheel_state is remorastate.FlywheelState.FLYWHEEL_RUN:
                self.flywheelstate_label.setText('运行')
                pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.green)
                self.flywheelstate_label.setPalette(pal)
            rm_mutex.unlock()

        elif rflink.Command(command_id) is rflink.Command.READ_SINE_MOTION_PARAM:
            rm_mutex.lock()
            self.cpgamp_label.setText(str(round(roboremora.motion_amp,2)))
            self.cpgfreq_label.setText(str(round(roboremora.motion_freq,2)))
            self.cpgoffset_label.setText(str(round(roboremora.motion_offset,2)))
            rm_mutex.unlock()
            pal = QtGui.QPalette()
            pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.blue)
            self.cpgamp_label.setPalette(pal)
            self.cpgfreq_label.setPalette(pal)
            self.cpgoffset_label.setPalette(pal)

        elif command_id >= rflink.Command.READ_IMU1_ATTITUDE.value and \
            command_id <= rflink.Command.READ_DEPTH.value:

            rf_mutex.lock() 
            try:
                if rftool.length == 4:
                    showdata = struct.unpack('f', rftool.message[1:])[0]
                elif rftool.length == 2:
                    showdata = struct.unpack('H', rftool.message[1:])[0]
                else:
                    showdata = 0
            except:
                 showdata = 0
            rf_mutex.unlock()

            plt_mutex.lock()
            self.datalist.append(showdata)
            self.timelist.append(self.showtime)
            self.showtime = self.showtime + 0.2
            self.sensor_data_canvas.plot(self.timelist, self.datalist)

            if len(self.datalist) > 100:
                self.timelist.pop(0)
                self.datalist.pop(0)
            plt_mutex.unlock()

        elif rflink.Command(command_id) is rflink.Command.PRINT_SYS_MSG:
            rf_mutex.lock()
            # 读取当前消息
            mes = rftool.message
            rf_mutex.unlock()
            # 刷新cmdshell
            self.cmdshell_text_browser.append("<font color='orange'>"+str(mes[1:],'ascii')+"</font>")

        # 记录数据到文件中
        elif rflink.Command(command_id) is rflink.Command.GOTO_SEND_DATA:
            # 读取当前消息
            rf_mutex.lock()
            mes = rftool.message
            meslen = rftool.length
            rf_mutex.unlock()
            
            if meslen == 1:
                if mes[1] == 1:
                    self.SBBW.set_lineeditor_text('回传中，请耐心等待~~~')
                    filename = 'data/' + self.savefile_name
                    # filename = 'data/'+time.strftime('%Y-%m-%d-%H-%M-%S',time.localtime(time.time()))+'.bin'
                    self.datafile = open(filename,'ab+')
                    prefix = "<font color='red'>slave:~$&nbsp;</font> "
                    self.cmdshell_text_browser.append(prefix + "Transfer Beginning!")
                elif mes[1] == 2:
                    filename = 'data/' + self.savefile_name
                    # filename = 'data/' + time.strftime('traindata-%Y-%m-%d-%H-%M-%S', time.localtime(time.time())) + '.bin'
                    self.datafile = open(filename, 'ab+')
                    prefix = "<font color='red'>slave:~$&nbsp;</font> "
                    self.cmdshell_text_browser.append(prefix + "Transfer Beginning!")
                elif mes[1] == 239:# mes[1]=b'\xef'
                    self.SBBW.set_lineeditor_text('回传成功！')
                    self.datafile.close()
                    prefix = "<font color='red'>slave:~$&nbsp;</font> "
                    self.cmdshell_text_browser.append(prefix + "Transfer Succeed!")
            else:
                self.datafile.write(mes[2:])

        elif rflink.Command(command_id) is not rflink.Command.LAST_COMMAND_FLAG:

            # 读取当前消息
            rf_mutex.lock()
            mes = rftool.message
            meslen = rftool.length
            rf_mutex.unlock()

            # 刷新cmdshell
            prefix = "<font color='red'>slave:~$&nbsp;</font> "
            self.cmdshell_text_browser.append(prefix + rflink.Command(command_id).name)
            # self.cmdshell_text_browser.append(str(mes))


        QtWidgets.QApplication.processEvents()



if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)  # 创建QApplication对象是必须，管理整个程序，参数可有可无，有的话可接收命令行参数

    RRW = RobotRemoraWindow()  # 创建窗体对象
    
    sys.exit(app.exec_())
