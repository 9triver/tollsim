import math
import salabim as sim
import enum
import collections
from typing import *

ROAD_NUM = 8
ROAD_COLOR = "30%gray"
ROAD_Y_OFFSET = 10
ETC_DISTANCE =15 #etc感应天线距离闸门的距离
ROAD_LENGTH = 100
ROAD_WIDTH = 4
ROAD_INTERVAL = 10
VEHICLE_STARTING_INTERVAL = 3
# road y pos = road y offset + id of road * road interval

#道路类型，包括ETC和人工
class RoadType(enum.Enum):
    ARTIFICIAL  = enum.auto()
    ETC = enum.auto()
ROAD_TYPE={
    RoadType.ARTIFICIAL:1,
    RoadType.ETC:2,
}
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
        :param self.an: animate
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
        # if show_claims:
        #     self.an = sim.AnimateRectangle(
        #         spec=(self.xll, self.yll, self.xur, self.yur),
        #         fillcolor=self.color,
        #     )

    def reset(self):
        self.vehicle.claims.remove(self)
        Claim.claims.remove(self)
        # if show_claims:
        #     self.an.remove()

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
    LENGTH = 5
    __WIDTH = 2
    __BOUNDARY_LENGTH = LENGTH + 1
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
        self.gate.set_velocity(self.v)

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
        length = self.__BOUNDARY_LENGTH / 2
        width = self.__BOUNDARY_WIDTH / 2
        xa, ya = rotate(-length, -width, angle=angle)
        xb, yb = rotate(length, width, angle=angle)
        xc, yc = rotate(-length, width, angle=angle)
        xd, yd = rotate(length, -width, angle=angle)
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
        if self.l > self.xfrom - Gate.X_POS - self.LENGTH / 2:
            if not self.passed_gate:
                # wait the gate resets
                if LightColor.RED != self.gate.light:
                    return True
                    # self.passed_gate = True
                    # if self.gate.light[self.from_direction] not in (LightColor.GREEN,):
                    #     return True
                self.passed_gate = True
                self.gate.activate()
                # self.gate.set_light(LightColor.YELLOW, vehicle_velocity=self.v)
                self.hold(Gate.MOVE_TIME)
                # self.gate.set_light(LightColor.GREEN, vehicle_velocity=self.v)
                
                return True
        return False
    def __trigger_ETC(
        self,
    ):
        if self.gate.roadtype==RoadType.ETC:
            if self.l > self.xfrom - Gate.X_POS - ETC_DISTANCE - self.LENGTH / 2:
                if not self.passed_gate:
                    # wait the gate resets
                    if LightColor.RED != self.gate.light:
                        return True
                    # self.passed_gate = True
                    # if self.gate.light[self.from_direction] not in (LightColor.GREEN,):
                    #     return True
                    self.passed_gate = True
                    self.gate.activate()
                    return True
        return False

    def process(self):
        # self.indicator_frequency = sim.Uniform(1, 2)()
        self.passed_gate = False
        while self.__claim(self.l).overlaps(Claim.claims):
            self.hold(VEHICLE_STARTING_INTERVAL)
            self.standby()
        self.__claim(self.l).set()
        an_vehicle = sim.AnimateRectangle(
            x=self.__time_2_x,
            y=self.__time_2_y,
            angle=self.__time_2_angle,
            spec=(
                -self.LENGTH / 2,
                -self.__WIDTH / 2,
                self.LENGTH / 2,
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
            x_len=self.LENGTH,
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
            x_len=self.LENGTH * 0.6,
            y_len=self.__WIDTH,
            z_len=1,
            z_ref=1,
            color=self.cstr,
            shaded=True,
        )

        while self.l <= self.l_end:
            if len(self.claims) == 1:
                self.__trigger_ETC()
                self.tryclaims = [self.__claim(self.l + resolution)]
                while (
                    any(
                        claim.overlaps(Claim.claims - set(self.claims))
                        for claim in self.tryclaims
                    )
                    or self.__has_to_stop()
                ):  
                    #self.hold(VEHICLE_STARTING_INTERVAL)#起步时间间隔
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
    MOVE_TIME = 20
    MOVE_SPEED = float(ROAD_WIDTH) / MOVE_TIME
    X_POS = ROAD_LENGTH / 2
    __Y_OFFSET = 2

    def setup(self, y_offset,road_type):
        y_offset += self.__Y_OFFSET
        # self.light = None
        self.vehicle_velocity=1
        self.gates = []
        self.gate3ds = []
        self.light = LightColor.RED
        self.roadtype = road_type
        for distance, this_color in enumerate(LightColor):
            x, y = rotate(
                self.X_POS + distance,
                y_offset,
                angle=DIRECTION_2_ANGLE[Direction.SOUTH],
            )
            an = sim.AnimateCircle(
                radius=0.4,
                x=x,
                y=y,
                fillcolor=lambda arg, t: (
                    LIGHT_COLOR_2_STRING[arg.this_color]
                    if self.light == arg.this_color
                    else "50%gray"
                ),
            )
            an.this_color = this_color
            x, y = rotate(
                self.X_POS, y_offset, angle=DIRECTION_2_ANGLE[Direction.SOUTH]
            )
            an = sim.Animate3dSphere(
                radius=0.4,
                x=x,
                y=y,
                z=3 - distance,
                color=lambda arg, t: (
                    LIGHT_COLOR_2_STRING[arg.this_color]
                    if self.light == arg.this_color
                    else "50%gray"
                ),
            )
            an.this_color = this_color
        x, y = rotate(
            self.X_POS,
            y_offset,
            angle=DIRECTION_2_ANGLE[Direction.SOUTH],
        )
        gate_an = sim.AnimateRectangle(
            x=(
                lambda arg, t: (
                    x
                    if LightColor.RED == arg.light
                    else (
                        x + ROAD_WIDTH
                        if LightColor.GREEN == arg.light
                        else (
                            x + self.MOVE_SPEED * (t - arg.start_move)
                            if LightColor.YELLOW == arg.light
                            else (
                                x + ROAD_WIDTH - self.MOVE_SPEED * (t - arg.start_move)
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
        gate_an_3d = sim.Animate3dBox(
            x=(
                lambda arg, t: (
                    x - 2.5
                    if LightColor.RED == arg.light
                    else (
                        x + ROAD_WIDTH - 2.5
                        if LightColor.GREEN == arg.light
                        else (
                            x + self.MOVE_SPEED * (t - arg.start_move) - 2.5
                            if LightColor.YELLOW == arg.light
                            else (
                                x
                                + ROAD_WIDTH
                                - self.MOVE_SPEED * (t - arg.start_move)
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
        gate_an.light = LightColor.RED
        gate_an.start_move = env.now()
        gate_an.roadtype = road_type
        gate_an_3d.light = LightColor.RED
        gate_an_3d.start_move = env.now()
        gate_an_3d.roadtype=road_type
        self.gates.append(gate_an)
        self.gate3ds.append(gate_an_3d)
        self.inductionPiles= []
        self.inductionPiles3d=[]
        if(road_type==RoadType.ETC):
            x, y = rotate(
                self.X_POS + distance,
                y_offset,
                angle=DIRECTION_2_ANGLE[Direction.SOUTH],
            )
            ip =sim.AnimateRectangle(
            x=x - ROAD_WIDTH,
            y=y - ETC_DISTANCE,
            spec=(
                0,
                1,
                -ROAD_WIDTH/4,
                2,
            ),
            fillcolor="gray",
        )
            ip_3d =sim.Animate3dBox(
            x=x - ROAD_WIDTH-0.5,
            y=y - ETC_DISTANCE,
            z=0.5,
            x_len=ROAD_WIDTH/4,
            y_len=1,
            z_len=5,
            z_ref=1,
            color="gray",
            shaded=True,
        )
            self.inductionPiles.append(ip)
            self.inductionPiles3d.append(ip_3d)
        elif(road_type==RoadType.ARTIFICIAL):
            x, y = rotate(
                self.X_POS + distance,
                y_offset,
                angle=DIRECTION_2_ANGLE[Direction.SOUTH],
            )
            ip =sim.AnimateRectangle(
            x=x - ROAD_WIDTH,
            y=y,
            spec=(
                0,
                1,
                -ROAD_WIDTH/4,
                2,
            ),
            fillcolor="green",
        )
            ip_3d =sim.Animate3dBox(
            x=x - ROAD_WIDTH-0.5,
            y=y,
            z=0,
            x_len=ROAD_WIDTH/4,
            y_len=1,
            z_len=3,
            z_ref=1,
            color="green",
            shaded=True,
        )
            self.inductionPiles.append(ip)
            self.inductionPiles3d.append(ip_3d)
    def set_velocity(self,vehicle_velocity=1):
        self.vehicle_velocity = vehicle_velocity
    def set_light(self, light):
        self.light = light
        for g in self.gates:
            g.light = light
            g.start_move = env.now()
        for g in self.gate3ds:
            g.light = light
            g.start_move = env.now()

    def process(self):
        # while True:
        #     for light, duration in (
        #         (LightColor.RED, red_duration),
        #         (LightColor.YELLOW, amber_duration),
        #         (LightColor.GREEN, green_duration),
        #         (LightColor.YELLOW1, amber_duration),
        #     ):
        #         self.light = light
        #         for g in self.gates:
        #             g.light = light
        #             g.start_move = env.now()
        #         for g in self.gate3ds:
        #             g.light = light
        #             g.start_move = env.now()
        #         self.hold(duration)
        while True:
            if self.roadtype == RoadType.ARTIFICIAL:
                if self.light == LightColor.GREEN:
                    self.hold(Vehicle.LENGTH / self.vehicle_velocity)
                    self.set_light(LightColor.YELLOW1)
                    self.hold(self.MOVE_TIME)
                    self.set_light(LightColor.RED)
                    self.passivate()
                elif self.light == LightColor.RED:
                    # self.hold(Vehicle.LENGTH / self.vehicle_velocity)
                    self.set_light(LightColor.YELLOW)
                    self.hold(self.MOVE_TIME)
                    self.set_light(LightColor.GREEN)
                    # self.standby()
            else:
                if self.light == LightColor.GREEN:
                    self.hold((Vehicle.LENGTH + ETC_DISTANCE)/ self.vehicle_velocity)
                    self.set_light(LightColor.YELLOW1)
                    self.hold(self.MOVE_TIME)
                    self.set_light(LightColor.RED)
                    self.passivate()
                # elif self.light ==LightColor.YELLOW:
                #     self.hold(self.MOVE_TIME)
                #     self.set_light(LightColor.GREEN)
                elif self.light == LightColor.RED:
                    # self.hold((Vehicle.LENGTH + ETC_DISTANCE)/ self.vehicle_velocity)
                    self.set_light(LightColor.YELLOW)
                    self.hold(self.MOVE_TIME)
                    self.set_light(LightColor.GREEN)
                else:
                    self.standby()
            pass


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
        self.gate = gate

    def process(self):
        while True:
            v = sim.Uniform(0.5, 1.5)()
            Vehicle(
                from_direction=self.from_direction,
                cstr=self.cstr,
                v=v,
                xfrom=self.xfrom,
                yfrom=self.yfrom,
                gate=self.gate,
            )
            self.hold(sim.Exponential(100))


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


resolution = 1
show_claims = True
do_animation = True

# 确定分辨率，坐标原点
# 坐标原点在左上角
env.x0(0)
env.y0(-ROAD_LENGTH)
env.x1(ROAD_LENGTH)

for i in range(ROAD_NUM):
    r_type=RoadType.ARTIFICIAL
    if(RoadType.ETC.value==i%2+1):
            r_type=RoadType.ETC
    offset = ROAD_Y_OFFSET + i * ROAD_INTERVAL
    x0, y0 = rotate(
        ROAD_LENGTH, offset - ROAD_WIDTH / 2, angle=DIRECTION_2_ANGLE[Direction.SOUTH]
    )
    x1, y1 = rotate(
        0, offset + ROAD_WIDTH / 2, angle=DIRECTION_2_ANGLE[Direction.SOUTH]
    )
    sim.AnimateRectangle(spec=(x0, y0, x1, y1), linewidth=0, fillcolor=ROAD_COLOR)
    sim.Animate3dRectangle(x0=x0, y0=y0, x1=x1, y1=y1, color=ROAD_COLOR)
    gate = Gate(y_offset=offset,road_type=r_type)
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
