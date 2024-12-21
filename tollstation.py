from __future__ import annotations

import enum
from typing import Optional

# import mySalabim_2dEnhanced as sim
import mySalabim_3dEnhanced as sim

# sim.Animate spec = (xll, yll, xur, yur) and Coordinate origin is x, y

ROAD_NUM = 10
ROAD_COLOR = "30%gray"
ROAD_X_OFFSET = 10
VIEWPORT_LENGTH = 100
ROAD_LENGTH = 1000
ROAD_WIDTH = 4
ROAD_INTERVAL = 10

ENABLE_3D = True
ENABLE_2D = False

# simulator setting
SIMULATE_SPEED = 1000
WINDOW_SIZE = 768
SHOW_CLAIMS = True

VEHICLE_COLOR = "blue"

STEP_LENGTH = 1


class ClaimSet:
    def __init__(self, x_pos: float, show_animate: bool = False):
        self.claims = set()
        self.x = x_pos
        self.show_animate = show_animate


class Claim:
    class Type(enum.Enum):
        ETC = enum.auto()
        GATE = enum.auto()
        ETC_GATE = enum.auto()
        VEHICLE = enum.auto()
        GENERATOR = enum.auto()

    def __init__(
        self,
        y_lower: float,
        y_upper: float,
        claim_set: ClaimSet,
        component: sim.Component,
        claim_type: Claim.Type,
    ):
        self.yl = y_lower
        self.yu = y_upper
        self.claim_set = claim_set
        self.an = None
        self.component = component
        self.type = claim_type

    def set(self) -> None:
        self.claim_set.claims.add(self)
        if ENABLE_2D and self.claim_set.show_animate:
            self.an = sim.AnimateRectangle(
                spec=(
                    self.claim_set.x - ROAD_WIDTH / 2,
                    self.yl,
                    self.claim_set.x + ROAD_WIDTH / 2,
                    self.yu,
                ),
                fillcolor=("red", 50),
            )

    def reset(self) -> None:
        self.claim_set.claims.remove(self)
        if ENABLE_2D and self.claim_set.show_animate:
            self.an.remove()

    # todo 改进算法减少计算量
    # 比如可以采用多个set,或者更高效的算法
    def get_gate_next_to(self) -> Optional[Claim]:
        for c in self.claim_set.claims:
            if c.type == Claim.Type.GATE and c.yl < self.yu and c.yu > self.yl:
                return c
        return None

    # def get_vehicle_next_to_behind(self) -> Optional[Claim]:
    #     for c in self.claim_set.claims:
    #         if c.type == Claim.Type.VEHICLE and abs(self.yl - c.yu) <= STEP_LENGTH:
    #             return c
    #     assert False

    def overlaps(self, claims: set = None) -> bool:
        if claims is None:
            claims = self.claim_set.claims
        return any(claim.yl < self.yu and claim.yu > self.yl for claim in claims)


class Road:
    def __init__(
        self,
        x_pos: float,
        vehicle_color: str,
        road_color: str,
        toll_type: Gate.Type,
        show_claims: bool = False,
    ):
        """
        :param x_pos: mid x-coordinate of Road
        """
        claim_set = ClaimSet(x_pos, show_claims)
        half_width = ROAD_WIDTH / 2
        sim.AnimateRectangle(
            spec=(x_pos - half_width, 0, x_pos + half_width, ROAD_LENGTH),
            fillcolor=ROAD_COLOR,
        )
        gate = GATE_TYPE_2_SUBCLASS[toll_type](
            toll_type=toll_type, x_pos=x_pos, claim_set=claim_set
        )
        vehicle_generator = VehicleGenerator(
            x_pos=x_pos,
            vehicle_color=vehicle_color,
            claim_set=claim_set,
        )


class Gate(sim.Component):
    __GATE_WIDTH = ROAD_WIDTH
    __GATE_LENGTH = 1
    _MOVE_TIME = 1
    _MOVE_SPEED = float(ROAD_WIDTH) / _MOVE_TIME
    __ETC_DISTANCE = 15
    __ETC_SENSOR_WIDTH = 1

    class Status(enum.Enum):
        CLOSED = enum.auto()
        OPENING = enum.auto()
        OPEN = enum.auto()
        CLOSING = enum.auto()

    STATUS_2_STRING = {
        Status.CLOSED: "red",
        Status.OPENING: "yellow",
        Status.OPEN: "green",
        Status.CLOSING: "yellow",
    }

    class Type(enum.Enum):
        ETC = enum.auto()
        MANUAL = enum.auto()

    def setup(
        self,
        toll_type: Gate.Type,
        x_pos: float,
        claim_set: ClaimSet,
        dis_from_starter_of_road: float = ROAD_LENGTH / 2,
    ):
        # 注意,不能用status,status salabim.Component 是保留字
        self.gate_status = Gate.Status.CLOSED
        self.toll_type = toll_type
        self.dis = dis_from_starter_of_road
        # 如何解决共享?可以定义一个新的类,传入这个类的同一个实例
        self.x = x_pos
        self.claim_set = claim_set
        self.vehicle_waiting = None

        half_width = self.__GATE_WIDTH / 2
        half_length = self.__GATE_LENGTH / 2
        x = self.x
        v = self._MOVE_SPEED
        w = self.__GATE_WIDTH
        y = self.dis
        self.gate_an = sim.AnimateRectangle(
            x=(
                lambda arg, t: (
                    x
                    if arg.gate_status == Gate.Status.CLOSED
                    else (
                        x + w
                        if arg.gate_status == Gate.Status.OPEN
                        else (
                            x + v * (t - arg.start_move)
                            if arg.gate_status == Gate.Status.OPENING
                            else (x + w - v * (t - arg.start_move))
                        )
                    )
                )
            ),
            y=y,
            spec=(
                -half_width,
                -half_length,
                half_width,
                half_length,
            ),
            fillcolor="white",
        )
        self.gate_an.start_move = self.env.now()
        self.gate_an.gate_status = Gate.Status.CLOSED
        etc_w = self.__ETC_SENSOR_WIDTH
        if self.toll_type == Gate.Type.ETC:
            self.etc_sensor_an = sim.AnimateRectangle(
                x=x + half_width,
                y=y - self.__ETC_DISTANCE,
                spec=(0, -etc_w / 2, etc_w, etc_w / 2),
                fillcolor="green",
            )
            self.etc_detect_area_claim = Claim(
                y_lower=(y - half_length - self.__ETC_DISTANCE),
                y_upper=y + half_length,
                claim_set=self.claim_set,
                component=self,
                claim_type=Claim.Type.ETC,
            )
        self.gate_claim = Claim(
            y_lower=y - half_length,
            y_upper=y + half_length,
            claim_set=self.claim_set,
            component=self,
            claim_type=(
                Claim.Type.ETC_GATE
                if self.toll_type == Gate.Type.ETC
                else Claim.Type.GATE
            ),
        )
        self.gate_claim.set()

    def _set_moving_status(self, status: Gate.Status):
        self.gate_status = status
        self.gate_an.gate_status = status
        self.gate_an.start_move = self.env.now()
        self.hold(self._MOVE_TIME)

    def _set_motionless_status(self, status: Gate.Status):
        self.gate_status = status
        self.gate_an.gate_status = status


class EtcGate(Gate):

    def process(self):
        while True:
            while not self.etc_detect_area_claim.overlaps(
                self.claim_set.claims - {self.gate_claim}
            ):
                self.standby()
            self._set_moving_status(Gate.Status.OPENING)
            self._set_motionless_status(Gate.Status.OPEN)
            self.gate_claim.reset()
            # 实现一杆抬起多车通行
            while self.etc_detect_area_claim.overlaps(
                self.claim_set.claims - {self.gate_claim}
            ):
                self.standby()
            self.gate_claim.set()
            self._set_moving_status(Gate.Status.CLOSING)
            self._set_motionless_status(Gate.Status.CLOSED)


class ManualGate(Gate):
    def process(self):
        if self.toll_type == Gate.Type.MANUAL:
            self.passivate()
        while True:
            self._set_moving_status(Gate.Status.OPENING)
            self._set_motionless_status(Gate.Status.OPEN)
            self.gate_claim.reset()
            # vehicle = self.gate_claim.get_vehicle_next_to_behind()
            # 注意,activate别人不会让自己退出执行,需要standby或passivate
            self.vehicle_waiting.activate()
            self.standby()
            # todo 需要解决多个车紧挨着过去,人工窗口应该是一车一杆
            while self.gate_claim.overlaps():
                self.standby()
            self.gate_claim.set()
            self._set_moving_status(Gate.Status.CLOSING)
            self._set_motionless_status(Gate.Status.CLOSED)
            self.passivate()


GATE_TYPE_2_SUBCLASS = {Gate.Type.ETC: EtcGate, Gate.Type.MANUAL: ManualGate}


class VehicleGenerator(sim.Component):
    __SLOWEST_V = 5
    __FASTEST_V = 5

    def setup(self, x_pos: float, vehicle_color: str, claim_set: ClaimSet):
        self.cstr = vehicle_color
        self.x = x_pos
        self.claim_set = claim_set
        self.claim = Claim(
            y_lower=0,
            y_upper=Vehicle.LENGTH,
            claim_set=self.claim_set,
            component=self,
            claim_type=Claim.Type.GENERATOR,
        )

    def process(self):
        while True:
            while self.claim.overlaps():
                self.hold(sim.Exponential(100))
            v = sim.Uniform(self.__SLOWEST_V, self.__FASTEST_V)()
            Vehicle(
                velocity=v,
                x_pos=self.x,
                claim_set=self.claim_set,
                vehicle_color=self.cstr,
            )
            # self.hold(sim.Exponential(10))
            self.hold(10)


class Vehicle(sim.Component):
    __BORDER_COLOR = "white"
    __BORDER_WIDTH = 0.1
    LENGTH = 5
    __WIDTH = 2
    __BOUNDARY_LENGTH = LENGTH + 1
    __BOUNDARY_WIDTH = __WIDTH + 0.5

    def setup(
        self, velocity: float, x_pos: float, claim_set: ClaimSet, vehicle_color: str
    ):
        self.length_passed = 0
        self.length_to_end = ROAD_LENGTH
        self.v = velocity
        self.x = x_pos
        self.claim_set = claim_set
        self.cstr = vehicle_color
        now = self.env.now()
        self.last_sampled_time = now
        self.next_sampled_time = now
        self.claim = None

    def process(self):
        self.claim = self.__claim(self.length_passed)
        self.claim.set()
        if ENABLE_2D:
            an_vehicle = sim.AnimateRectangle(
                x=self.__time_2_x,
                y=self.__time_2_y,
                spec=(
                    -self.__WIDTH / 2,
                    -self.LENGTH / 2,
                    self.__WIDTH / 2,
                    self.LENGTH / 2,
                ),
                linecolor=self.__BORDER_COLOR,
                linewidth=self.__BORDER_WIDTH,
                fillcolor=self.cstr,
            )
        if ENABLE_3D:
            an_3d = sim.Animate3dBox(
                x=self.__time_2_x,
                y=self.__time_2_y,
                z=0.5,
                x_len=self.LENGTH,
                y_len=self.__WIDTH,
                z_len=1,
                color=self.cstr,
                shaded=True,
            )
        while self.length_passed < self.length_to_end:
            self.next_claim = self.__claim(self.length_passed + STEP_LENGTH)

            while self.next_claim.overlaps(self.claim.claim_set.claims - {self.claim}):
                overlapped_gate = self.next_claim.get_gate_next_to()
                if (
                    overlapped_gate is not None
                    and overlapped_gate.component.gate_status == Gate.Status.CLOSED
                ):
                    overlapped_gate.component.vehicle_waiting = self
                    overlapped_gate.component.activate()
                    # todo 记得文档中提到过一种不可打断的队列
                    self.passivate()
                    break
                self.standby()
            self.claim.reset()
            self.next_claim.set()
            self.claim = self.next_claim
            self.next_claim = None
            t = STEP_LENGTH / self.v
            now = self.env.now()
            self.last_sampled_time = now
            self.next_sampled_time = now + t
            self.length_passed += STEP_LENGTH
            self.hold(t)
        self.claim.reset()
        if ENABLE_2D:
            an_vehicle.remove()
        if ENABLE_3D:
            an_3d.remove()

    def __claim(self, length_passed) -> Claim:
        return Claim(
            y_lower=length_passed - self.LENGTH / 2,
            y_upper=length_passed + self.LENGTH / 2,
            claim_set=self.claim_set,
            component=self,
            claim_type=Claim.Type.VEHICLE,
        )

    def __time_2_x(self, t: float) -> float:
        return self.x

    def __time_2_y(self, t: float) -> float:
        return self.__time_2_length(t)

    def __time_2_length(self, t: float) -> float:
        return sim.interpolate(
            t,
            self.last_sampled_time,
            self.next_sampled_time,
            self.length_passed - STEP_LENGTH,
            self.length_passed,
        )


if __name__ == "__main__":
    env = sim.Environment()

    # 界面左上角在显示器中的位置, 原点为屏幕左上角, x朝右y朝下
    if ENABLE_3D:
        env.position3d((0, 0))
    env.position((WINDOW_SIZE + 10, 0))

    # 设置界面大小
    if ENABLE_3D:
        env.width3d(WINDOW_SIZE)
        env.height3d(WINDOW_SIZE)
    env.width(WINDOW_SIZE)
    env.height(WINDOW_SIZE)
    # 设置界面中坐标轴原点,x0y0为lower left坐标,x朝右y朝上
    env.x0(0)
    env.y0(0)
    env.x1(VIEWPORT_LENGTH)

    for i in range(ROAD_NUM):
        x_pos = ROAD_X_OFFSET + i * ROAD_INTERVAL
        toll_type = Gate.Type.MANUAL if i % 2 == 0 else Gate.Type.ETC
        vehicle_color = VEHICLE_COLOR
        road_color = ROAD_COLOR
        show_claims = SHOW_CLAIMS
        claim_set = ClaimSet(x_pos, show_claims)
        half_width = ROAD_WIDTH / 2
        x0 = x_pos - half_width
        y0 = 0
        x1 = x_pos + half_width
        y1 = ROAD_LENGTH
        if ENABLE_2D:
            sim.AnimateRectangle(
                spec=(x0, y0, x1, y1),
                fillcolor=ROAD_COLOR,
            )
        if ENABLE_3D:
            sim.Animate3dRectangle(x0=x0, y0=y0, x1=x1, y1=y1, color=ROAD_COLOR)
        GATE_TYPE_2_SUBCLASS[toll_type](
            toll_type=toll_type, x_pos=x_pos, claim_set=claim_set
        )
        VehicleGenerator(
            x_pos=x_pos,
            vehicle_color=vehicle_color,
            claim_set=claim_set,
        )

    env.speed(SIMULATE_SPEED)
    env.background_color("black")
    env.view(
        # x_eye=-6.9024,
        # y_eye=-95.8334,
        # z_eye=30.0000,
        # x_center=93.4761,
        # y_center=623.7552,
        # z_center=0.0000,
        # field_of_view_y=55.5556,
        x_eye=176.9024,
        y_eye=295.8334,
        z_eye=30.0000,
        x_center=993.4761,
        y_center=123.7552,
        z_center=0.0000,
        field_of_view_y=55.5556,
    )

    make_video = False
    if make_video:
        type_of_video = "2d"
        # env.run(100)
        env.camera_auto_print(True)
        env.show_fps(True)
        env.animate("?")
        if ENABLE_3D:
            env.animate3d("?")
        env.video_mode(type_of_video)
        env.video_repeat(0)
        env.video_pingpong(False)
        env.video(f"lights {type_of_video}.gif")
        env.run(till=300)
        env.video_close()
    else:
        env.show_fps(True)
        env.animate(True)
        if ENABLE_3D:
            env.animate3d(True)
        env.camera_auto_print(True)
        env.run(till=1000)
