import math
import salabim as sim
import enum
import collections
from typing import *

ROAD_NUM = 4
ROAD_COLOR = "30%gray"
ROAD_Y_OFFSET = 10
ROAD_LENGTH = 100
ROAD_WIDTH = 4
ROAD_INTERVAL = 10
GATE_MOVE_TIME = 2
# road y pos = road y offset + id of road * road interval


# 在这里面直接设置的值不能重复且需要使用value域调用
class LightColor(enum.Enum):  # the color of indicator light
    RED = enum.auto()  # car stops
    YELLOW = enum.auto()  # car stops and gate moves
    GREEN = enum.auto()
    YELLOW1 = enum.auto()


LIGHT_COLOR_2_STRING = {
    LightColor.RED: "red",
    LightColor.YELLOW: "yellow",
    LightColor.GREEN: "green",
    LightColor.YELLOW1: "yellow",
}


PositionInfo = collections.namedtuple("position_info", "x y angle")


# 坐标轴逆时针旋转角度
class Direction(enum.Enum):
    SOUTH = enum.auto()


DIRECTION_2_ANGLE = {
    Direction.SOUTH: math.radians(270),
}

VEHICLE_COLOR = "blue"


# 坐标轴逆时针旋转
# 原来y轴在上，x轴在右
def rotate(x, y, angle):
    return x * math.cos(angle) - y * math.sin(angle), +x * math.sin(
        angle
    ) + y * math.cos(angle)


# 位置声明，用于碰撞检测和碰撞面动画渲染
class Claim:
    claims = set()

    def __init__(self, xll, yll, xur, yur, vehicle):
        """
        ll lower left
        ur upper right
        :type vehicle: Vehicle
        """
        self.xll = xll
        self.yll = yll
        self.xur = xur
        self.yur = yur
        self.vehicle = vehicle
        self.color = (vehicle.cstr, 50)
        self.an = None

    def set(self):
        self.vehicle.claims.append(self)
        Claim.claims.add(self)
        if show_claims:
            self.an = sim.AnimateRectangle(
                spec=(self.xll, self.yll, self.xur, self.yur),
                fillcolor=self.color,
            )

    def reset(self):
        self.vehicle.claims.remove(self)
        Claim.claims.remove(self)
        if show_claims:
            self.an.remove()

    def overlaps(self, claims):
        return any(
            claim.xll < self.xur
            and claim.xur > self.xll
            and claim.yll < self.yur
            and claim.yur > self.yll
            for claim in claims
        )

    def __repr__(self):
        return (
            f"Claim({self.xll:5.1f}, {self.yll:5.1f}, {self.xur:5.1f}, {self.yur:5.1f})"
        )


class Vehicle(sim.Component):
    __BORDER_COLOR = "white"
    __BORDER_WIDTH = 0.1
    __LENGTH = 5
    __WIDTH = 2
    __BOUNDARY_LENGTH = __LENGTH + 1
    __BOUNDARY_WIDTH = __WIDTH + 0.5

    def setup(self, from_direction, cstr, v, xfrom, yfrom, gate):
        """
        :type from_direction: Direction
        :param cstr: color name string
        :type cstr: str
        :param v: velocity
        :type v: int
        """
        self.from_direction = from_direction
        self.xfrom = xfrom
        self.yfrom = yfrom
        self.cstr = cstr
        self.v = v
        self.l = 0
        self.l_end = ROAD_LENGTH
        self.claims = []  # can't be a set as the order is important
        self.t0 = env.now()
        self.t1 = env.now()
        self.passed_gate = False
        self.gate = gate

    # t时刻汽车行驶距离
    def __time_2_length(self, t):
        return sim.interpolate(t, self.t0, self.t1, self.l - resolution, self.l)

    def __length_2_x(self, l):
        x, y = rotate(
            self.xfrom - l, self.yfrom, DIRECTION_2_ANGLE[self.from_direction]
        )
        return x

    def __length_2_y(self, l):
        x, y = rotate(
            self.xfrom - l, self.yfrom, DIRECTION_2_ANGLE[self.from_direction]
        )
        return y

    def __length_2_angle(self, l):
        return DIRECTION_2_ANGLE[self.from_direction]

    # t时刻汽车中点位置
    def __time_2_x(self, t):
        return self.__length_2_x(self.__time_2_length(t))

    def __time_2_y(self, t):
        return self.__length_2_y(self.__time_2_length(t))

    def __time_2_angle(self, t):
        return math.degrees(self.__length_2_angle(self.__time_2_length(t)))

    # 声明当前位置
    def __claim(self, l):
        """
        :param l: length have passed
        :type l: int
        """
        angle = self.__length_2_angle(l)
        x = self.__length_2_x(l)
        y = self.__length_2_y(l)
        len = self.__BOUNDARY_LENGTH / 2
        wid = self.__BOUNDARY_WIDTH / 2
        xa, ya = rotate(-len, -wid, angle=angle)
        xb, yb = rotate(len, wid, angle=angle)
        xc, yc = rotate(-len, wid, angle=angle)
        xd, yd = rotate(len, -wid, angle=angle)
        xa, xb = min(xa, xb, xc, xd), max(xa, xb, xc, xd)
        ya, yb = min(ya, yb, yc, yd), max(ya, yb, yc, yd)
        return Claim(
            xll=x + xa,
            yll=y + ya,
            xur=x + xb,
            yur=y + yb,
            vehicle=self,
        )

    def __has_to_stop(
        self,
    ):  # this should (and will) be only called when none of the tryclaims overlaps with claims
        if self.l > self.xfrom - Gate.X_POS - self.__LENGTH / 2:
            if not self.passed_gate:
                if self.gate.light[self.from_direction] not in (LightColor.GREEN,):
                    return True
                self.passed_gate = True
        return False

    def process(self):
        # self.indicator_frequency = sim.Uniform(1, 2)()
        self.passed_gate = False
        while self.__claim(self.l).overlaps(Claim.claims):
            self.standby()
        self.__claim(self.l).set()
        an_vehicle = sim.AnimateRectangle(
            x=self.__time_2_x,
            y=self.__time_2_y,
            angle=self.__time_2_angle,
            spec=(
                -self.__LENGTH / 2,
                -self.__WIDTH / 2,
                self.__LENGTH / 2,
                self.__WIDTH / 2,
            ),
            linecolor=self.__BORDER_COLOR,
            linewidth=self.__BORDER_WIDTH,
            fillcolor=self.cstr,
        )
        an3d_vehicle0 = sim.Animate3dBox(
            x=self.__time_2_x,
            y=self.__time_2_y,
            z=0.5,
            z_angle=self.__time_2_angle,
            x_len=self.__LENGTH,
            y_len=self.__WIDTH,
            z_len=1,
            z_ref=1,
            color=self.cstr,
            shaded=True,
        )
        an3d_vehicle1 = sim.Animate3dBox(
            x=self.__time_2_x,
            y=self.__time_2_y,
            z=1.5,
            z_angle=self.__time_2_angle,
            x_len=self.__LENGTH * 0.6,
            y_len=self.__WIDTH,
            z_len=1,
            z_ref=1,
            color=self.cstr,
            shaded=True,
        )

        while self.l <= self.l_end:
            if len(self.claims) == 1:
                self.tryclaims = [self.__claim(self.l + resolution)]
                while (
                    any(
                        claim.overlaps(Claim.claims - set(self.claims))
                        for claim in self.tryclaims
                    )
                    or self.__has_to_stop()
                ):
                    self.standby()

                for claim in self.tryclaims:
                    claim.set()

            duration = resolution / self.v
            self.t0, self.t1 = self.env.now(), self.env.now() + duration
            self.l += resolution

            self.hold(duration)

            self.claims[0].reset()
        for claim in self.claims:
            claim.reset()
        an_vehicle.remove()
        an3d_vehicle0.remove()
        an3d_vehicle1.remove()


class Gate(sim.Component):
    X_POS = ROAD_LENGTH / 2
    __Y_OFFSET = 2

    def setup(self, y_offset):
        y_offset += self.__Y_OFFSET
        self.light = {}  # Direction 2 LightColor
        self.gates = []
        self.gate3ds = []
        for direction in Direction:
            self.light[direction] = LightColor.RED
            for distance, this_color in enumerate(LightColor):
                x, y = rotate(
                    self.X_POS + distance,
                    y_offset,
                    angle=DIRECTION_2_ANGLE[direction],
                )
                an = sim.AnimateCircle(
                    radius=0.4,
                    x=x,
                    y=y,
                    fillcolor=lambda arg, t: (
                        LIGHT_COLOR_2_STRING[arg.this_color]
                        if self.light[arg.direction] == arg.this_color
                        else "50%gray"
                    ),
                )
                an.direction = direction
                an.this_color = this_color
                x, y = rotate(
                    self.X_POS,
                    y_offset,
                    angle=DIRECTION_2_ANGLE[direction],
                )
                an = sim.Animate3dSphere(
                    radius=0.4,
                    x=x,
                    y=y,
                    z=3 - distance,
                    color=lambda arg, t: (
                        LIGHT_COLOR_2_STRING[arg.this_color]
                        if self.light[arg.direction] == arg.this_color
                        else "50%gray"
                    ),
                )
                an.direction = direction
                an.this_color = this_color
            x, y = rotate(
                self.X_POS,
                y_offset,
                angle=DIRECTION_2_ANGLE[direction],
            )
            gate = sim.AnimateRectangle(
                x=(
                    lambda arg, t: (
                        x
                        if LightColor.RED == arg.light
                        else (
                            x + ROAD_WIDTH
                            if LightColor.GREEN == arg.light
                            else (
                                x + gate_move_speed * (t - arg.start_move)
                                if LightColor.YELLOW == arg.light
                                else (
                                    x
                                    + ROAD_WIDTH
                                    - gate_move_speed * (t - arg.start_move)
                                )
                            )
                        )
                    )
                ),
                y=y,
                spec=(
                    0,
                    1,
                    -ROAD_WIDTH,
                    2,
                ),
                fillcolor="white",
            )
            gate3d = sim.Animate3dBox(
                x=(
                    lambda arg, t: (
                        x - 2.5
                        if LightColor.RED == arg.light
                        else (
                            x + ROAD_WIDTH - 2.5
                            if LightColor.GREEN == arg.light
                            else (
                                x + gate_move_speed * (t - arg.start_move) - 2.5
                                if LightColor.YELLOW == arg.light
                                else (
                                    x
                                    + ROAD_WIDTH
                                    - gate_move_speed * (t - arg.start_move)
                                    - 2.5
                                )
                            )
                        )
                    )
                ),
                y=y + 1,
                z=0.5,
                x_len=ROAD_WIDTH,
                y_len=1,
                z_len=1,
                z_ref=1,
                color="white",
                shaded=True,
            )
            gate.light = LightColor.RED
            gate.start_move = env.now()
            gate3d.light = LightColor.RED
            gate3d.start_move = env.now()
            self.gates.append(gate)
            self.gate3ds.append(gate3d)

    def process(self):
        while True:
            for light, duration in (
                (LightColor.RED, red_duration),
                (LightColor.YELLOW, amber_duration),
                (LightColor.GREEN, green_duration),
                (LightColor.YELLOW1, amber_duration),
            ):
                self.light[Direction.SOUTH] = light
                for gate in self.gates:
                    gate.light = light
                    gate.start_move = env.now()
                for gate3d in self.gate3ds:
                    gate3d.light = light
                    gate3d.start_move = env.now()
                self.hold(duration)


class VehicleGenerator(sim.Component):
    def setup(self, from_direction, cstr, xfrom, yfrom, gate):
        """
        :type gate: Gate
        :type from_direction: Direction
        :param cstr: color name string
        :type cstr: str
        """
        self.cstr = cstr
        self.from_direction = from_direction
        self.xfrom = xfrom
        self.yfrom = yfrom

    def process(self):
        while True:
            v = sim.Uniform(0.5, 1.5)()
            Vehicle(
                from_direction=self.from_direction,
                cstr=self.cstr,
                v=v,
                xfrom=self.xfrom,
                yfrom=self.yfrom,
                gate=gate,
            )
            self.hold(sim.Exponential(50))


# define set_env():
env = sim.Environment()
# 确定画面窗口大小
WINDOW_SIZE = 768
env.speed(8)
env.background_color("black")
env.width3d(WINDOW_SIZE)
env.height3d(WINDOW_SIZE)
env.position3d((0, 0))
env.width(WINDOW_SIZE)
env.height(WINDOW_SIZE)
env.position((WINDOW_SIZE + 10, 0))
env.view(
    x_eye=50,
    y_eye=50,
    z_eye=50,
    x_center=0,
    y_center=-ROAD_LENGTH,
    z_center=0,
    field_of_view_y=30,
)

red_duration = 20
amber_duration = 5
green_duration = 20

gate_move_speed = float(ROAD_WIDTH) / amber_duration

resolution = 1
show_claims = True
do_animation = True

# 确定分辨率，坐标原点
# 坐标原点在左上角
env.x0(0)
env.y0(-ROAD_LENGTH)
env.x1(ROAD_LENGTH)

for i in range(ROAD_NUM):
    offset = ROAD_Y_OFFSET + i * ROAD_INTERVAL
    x0, y0 = rotate(
        ROAD_LENGTH, offset - ROAD_WIDTH / 2, angle=DIRECTION_2_ANGLE[Direction.SOUTH]
    )
    x1, y1 = rotate(
        0, offset + ROAD_WIDTH / 2, angle=DIRECTION_2_ANGLE[Direction.SOUTH]
    )
    sim.AnimateRectangle(spec=(x0, y0, x1, y1), linewidth=0, fillcolor=ROAD_COLOR)
    sim.Animate3dRectangle(x0=x0, y0=y0, x1=x1, y1=y1, color=ROAD_COLOR)
    gate = Gate(y_offset=offset)
    VehicleGenerator(
        from_direction=Direction.SOUTH,
        cstr=VEHICLE_COLOR,
        xfrom=ROAD_LENGTH,
        yfrom=offset,
        gate=gate,
    )

make_video = True
if make_video:
    type_of_video = "2d"
    env.run(100)
    env.camera_auto_print(True)
    env.show_fps(True)
    env.animate("?")
    env.animate3d("?")
    env.video_mode(type_of_video)
    env.video_repeat(0)
    env.video_pingpong(False)
    env.video(f"lights {type_of_video}.gif")
    env.run(till=3000)
    env.video_close()
else:
    env.animate(True)
    env.animate3d(True)
    env.run()
