#!/usr/bin/env python3
"""Motor driver node."""

import Jetson.GPIO as GPIO
from rclpy.node import Node
import rclpy
from geometry_msgs.msg import Twist
from rclpy.qos import qos_profile_sensor_data


GPIO.setmode(GPIO.BOARD)

class DCMotor:
    # the min_duty and max_duty are defined for 15000Hz frequency
    # you can pass as arguments
    def __init__(
        self,
        pin1: int,
        pin2: int,
        pwm_pin: int,
        min_duty: int = 0,
        max_duty: int = 100,
    ) -> None:
        GPIO.setup(pin1, GPIO.OUT, initial=GPIO.LOW)
        self.__pin1 = pin1

        GPIO.setup(pin2, GPIO.OUT, initial=GPIO.LOW)
        self.__pin2 = pin2

        GPIO.setup(pwm_pin, GPIO.OUT)
        self.__pwm = GPIO.PWM(pwm_pin, 100)
        self.pwm.start(0)

        self.__min_duty = min_duty
        self.__max_duty = max_duty
        # self.speed: int = 0

    @property
    def pwm(self) -> GPIO.PWM:
        return self.__pwm

    # speed value can be between 0 and 100
    def forward(self, speed: int = 50) -> None:
        if speed < self.__min_duty or speed > self.__max_duty:
            print(f"Invalid speed: {speed}. Setting to 0.")
            speed = 0
        GPIO.output(self.__pin1, GPIO.LOW)
        GPIO.output(self.__pin2, GPIO.HIGH)
        self.duty_cycle(speed)

    def backward(self, speed: int = 50) -> None:
        if speed < self.__min_duty or speed > self.__max_duty:
            print(f"Invalid speed: {speed}. Setting to 0.")
            speed = 0
        GPIO.output(self.__pin1, GPIO.HIGH)
        GPIO.output(self.__pin2, GPIO.LOW)
        self.duty_cycle(speed)

    def stop(self):
        GPIO.output(self.__pin1, GPIO.LOW)
        GPIO.output(self.__pin2, GPIO.LOW)
        self.duty_cycle(0)

    def duty_cycle(self, speed: int = 50) -> None:
        if speed < self.__min_duty or speed > self.__max_duty:
            print(f"Invalid speed: {speed}. Setting to 0.")
            speed = 0
        # self.speed = speed
        # self.pwm.start(0)
        self.pwm.ChangeDutyCycle(speed)
        # if self.speed <= 0 or self.speed > 100:
        #     duty_cycle = 0
        # else:
        #     duty_cycle = int(
        #         self.min_duty
        #         + (self.max_duty - self.min_duty) * ((self.speed - 1) / (100 - 1))
        #     )
        # return duty_cycle


class MotorsControllerNode(Node):
    def __init__(self):
        super().__init__("motors_controller")

        self.motor1 = DCMotor(
            11,
            13,
            32,
        )
        self.motor2 = DCMotor(
            16,
            18,
            33,
        )

        # Initialize serial communication with Arduino
        # try:
        #     self.ser = serial.Serial("/dev/ttyUSB0", 115200, timeout=1)
        #     self.get_logger().info("Serial connection established with Arduino.")
        # except serial.SerialException as e:
        #     self.get_logger().error(f"Failed to connect to Arduino: {e}")
        #     self.ser = None
        #     raise

        self.last_ctl_command: Twist | None = None
        self.timer = self.create_timer(0.05, self.motor_control)

        # Create a subscriber to the 'distance' topic
        self.subscription = self.create_subscription(
            Twist,
            "cmd_vel",
            self.listener_callback,
            qos_profile_sensor_data,
        )

    def motor_control(self) -> None:
        if self.last_ctl_command is None:
            return

        cmd = self.last_ctl_command
        self.last_ctl_command = None

        if cmd.linear is not None and cmd.linear.x != 0:
            if abs(cmd.linear.x) > 1:
                self.get_logger().info(
                    "Velocity can not greater than 100% (1 for FORWARD, -1 for BACKWARD), setting to maximum."
                )
                cmd.linear.x = 1.0 if cmd.linear.x > 0 else -1.0

            speed = round(abs(cmd.linear.x) * 100)

            if cmd.linear.x < 0:
                # command = "BACKWARD\n"
                self.motor1.backward(speed)
                self.motor2.backward(speed)
                self.get_logger().info(f"Obstacle detected, moving backward. SPEED: {speed}")
            # elif cmd.linear.x == 0:
            #     if cmd.angular.z == 0:
            #         command = 'STOP\n'
            #         self.get_logger().info("No signal from sensor, stopping.")
            else:
                # command = "FORWARD\n"

                self.motor1.forward(speed)
                self.motor2.forward(speed)
                self.get_logger().info(f"No obstacle detected, moving forward. SPEED: {speed}")
        elif cmd.angular is not None and cmd.angular.z != 0:
            if abs(cmd.angular.z) > 1:
                self.get_logger().info(
                    "Velocity can not greater than 100% (1 for RIGHT, -1 for LEFT), setting to maximum."
                )
                cmd.angular.z = 1.0 if cmd.angular.z > 0 else -1.0
            speed = round(abs(cmd.angular.z) * 100)
            if cmd.angular.z > 0:
                # command = "LEFT\n"
                self.motor1.backward(speed)
                self.motor2.forward(speed)
                self.get_logger().info("Turning left")
            # elif cmd.linear.x == 0:
            #     if cmd.angular.z == 0:
            #         command = 'STOP\n'
            #         self.get_logger().info("No signal from sensor, stopping.")
            else:
                # command = "RIGHT\n"
                self.motor1.forward(speed)
                self.motor2.backward(speed)
                self.get_logger().info("Turning right")
        else:
            # command = "STOP\n"
            self.motor1.stop()
            self.motor2.stop()
            self.get_logger().info("Stopping...")

        # if self.ser:
        #     self.ser.write(command.encode())
        #     self.get_logger().info(f"Sent command: {command.strip()}")

    def listener_callback(self, msg: Twist) -> None:
        self.last_ctl_command = msg


def main(args=None):
    rclpy.init(args=args)
    try:
        node = MotorsControllerNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # node.ser.close()
        node.motor1.stop()
        node.motor2.stop()
        GPIO.cleanup()
        node.destroy_node()
        rclpy.shutdown()
