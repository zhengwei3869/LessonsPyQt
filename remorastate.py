from enum import Enum

class SwimState(Enum):
    """
    游动状态枚举类型
    """
    SWIM_FORCESTOP = 0
    SWIM_STOP = 1
    SWIM_RUN = 2
    SWIM_INIT = 3


class ValveState(Enum):
    """
    电磁阀状态枚举类型
    """
    VALVE_OFF = 0
    VALVE_ON = 1

class PumpState(Enum):
    """
    水泵状态枚举类型
    """
    PUMP_OFF = 0
    PUMP_ON = 1

class GimbalState(Enum):
    """
    云台状态枚举类型
    """
    GIMBAL_STOP = 0
    GIMBAL_ZERO = 1
    GIMBAL_RUN = 2

class FlywheelState(Enum):
    """
    飞轮状态枚举类型
    """
    FLYWHEEL_STOP = 0
    FLYWHEEL_RUN = 1


class RoboRemoraState:
    """
    RoboRemora状态类
    """
    def __init__(self):
        self.swim_state = SwimState.SWIM_FORCESTOP.value
        self.valve1_state = ValveState.VALVE_OFF.value
        self.valve2_state = ValveState.VALVE_OFF.value
        self.pumpin_state = PumpState.PUMP_OFF.value
        self.pumpout_state = PumpState.PUMP_OFF.value
        self.gimbal_state = GimbalState.GIMBAL_STOP.value
        self.flywheel_state = FlywheelState.FLYWHEEL_STOP.value
        self.motion_amp = 0.0
        self.motion_freq = 0.0
        self.motion_offset = 0.0
        self.pecfin_angle = 0.0
        self.onboard_imu_roll = 0.0
        self.onboard_imu_pitch = 0.0
        self.onboard_imu_yaw = 0.0
        self.onboard_imu_accelx = 0.0
        self.onboard_imu_accely = 0.0
        self.onboard_imu_accelz = 0.0
        self.onboard_imu_gyrox = 0.0
        self.onboard_imu_gyroy = 0.0
        self.onboard_imu_gyroz = 0.0
        self.gimbal_imu_roll = 0.0
        self.gimbal_imu_pitch = 0.0
        self.gimbal_imu_yaw = 0.0
        self.gimbal_imu_accelx = 0.0
        self.gimbal_imu_accely = 0.0
        self.gimbal_imu_accelz = 0.0
        self.gimbal_imu_gyrox = 0.0
        self.gimbal_imu_gyroy = 0.0
        self.gimbal_imu_gyroz = 0.0
        self.varistor1_data = 0
        self.varistor2_data = 0

