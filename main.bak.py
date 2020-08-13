#!/usr/bin/env python3

# -----------------------------------------------------------------------------
# Copyright (c) 2019 Timur Tentimishov <family.tentimishov@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# -----------------------------------------------------------------------------#
# This software demonstrates usage of motors, sensors, buttons, and leds and
# uses source code provided in https://www.hackster.io/alexagadgets/ 

import logging
import json
import threading
import time
import random

from random import choice, randint
from enum import Enum
from agt import AlexaGadget

from ev3dev2.led import Leds
from ev3dev2.sound import Sound
from ev3dev2.motor import OUTPUT_A, SpeedPercent, MediumMotor, OUTPUT_B, OUTPUT_C, MoveTank, LargeMotor
from ev3dev2.sensor.lego import InfraredSensor
from ev3dev2.sensor.lego import TouchSensor
from ev3dev2.display import Display

# Set the logging level to INFO to see messages from AlexaGadget
logging.basicConfig(level=logging.INFO)


class Command(Enum):
    """
    The list of preset commands and their invocation variation.
    These variations correspond to the skill slot values.
    """
    SENTRY = ['guard', 'protect', 'sentry', 'sentry mode','watch', 'watch mode']
    SIT = ['sitz', 'sit']
    STAY = ['bleib', 'stay', 'steh auf', 'stehen bleiben']
    HEEL = ['fuss', 'heel']
    COME = ['come to me', 'Komm', 'come']
    SPEAK = ['speak', 'laut']

class Direction(Enum):
    """
    The list of directional commands and their variations.
    These variations correspond to the skill slot values.
    """
    FORWARD = ['forward', 'forwards', 'go forward']
    BACKWARD = ['back', 'backward', 'backwards', 'go backward']
    LEFT = ['left', 'go left']
    RIGHT = ['right', 'go right']
    STOP = ['stop', 'brake']

class EventName(Enum):
    """
    The list of custom events sent from this gadget to Alexa
    """
    BARK = "bark"

class MindstormsGadget(AlexaGadget):
    """
    A Mindstorms gadget that performs movement based on voice commands.
    Four types of commands are supported: sit, stay, come, speak, heel.
    """

    def __init__(self):
        """
        Performs Alexa Gadget initialization routines and ev3dev resource allocation.
        """

        super().__init__()

        # Gadget state
        self.heel_mode = False
        self.patrol_mode = False
        self.sitting = False

        # Ev3dev initialization
        self.leds = Leds()
        self.sound = Sound()

        # Connect infrared and touch sensors.
        self.ir = InfraredSensor()
        self.ts = TouchSensor()
        # Init display
        self.screen = Display()

        # Connect medium motor on output port A:
        self.medium_motor = MediumMotor(OUTPUT_A)
        # Connect two large motors on output ports B and C:
        self.left_motor = LargeMotor(OUTPUT_B)
        self.right_motor = LargeMotor(OUTPUT_C)


        # Gadget states
        self.bpm = 0
        self.trigger_bpm = "off"

        # Start threads
        threading.Thread(target=self._patrol_thread, daemon=True).start()
        threading.Thread(target=self._heel_thread, daemon=True).start()
        threading.Thread(target=self._touchsensor_thread, daemon=True).start()

    # ------------------------------------------------
    # Callbacks
    # ------------------------------------------------
    def on_connected(self, device_addr):
        """
        Gadget connected to the paired Echo device.
        :param device_addr: the address of the device we connected to
        """
        print("{} Connected to Echo device".format(self.friendly_name))

        # Draw blinking eyes of the puppy
        threading.Thread(target=self._draweyes, daemon=True).start()

        # Turn lights on:
        for light in ('LEFT', 'RIGHT'):
            self.leds.set_color(light, 'GREEN')


    def on_disconnected(self, device_addr):
        """
        Gadget disconnected from the paired Echo device.
        :param device_addr: the address of the device we disconnected from
        """
        # Turn lights off:
        for light in ('LEFT', 'RIGHT'):
            self.leds.set_color(light, 'BLACK')

    def on_custom_mindstorms_gadget_control(self, directive):
        """
        Handles the Custom.Mindstorms.Gadget control directive.
        :param directive: the custom directive with the matching namespace and name
        """
        try:
            payload = json.loads(directive.payload.decode("utf-8"))
            print("Control payload: {}".format(payload))
            control_type = payload["type"]

            if control_type == "command":
                # Expected params: [command]
                self._activate(payload["command"])
            
        except KeyError:
            print("Missing expected parameters: {}".format(directive))


    # On Amazon music play
    def on_alexa_gadget_musicdata_tempo(self, directive):
        """
        Provides the music tempo of the song currently playing on the Echo device.
        :param directive: the music data directive containing the beat per minute value
        """
        tempo_data = directive.payload.tempoData
        for tempo in tempo_data:

            print("tempo value: {}".format(tempo.value))
            if tempo.value > 0:
                # dance pose
                #self.drive.on_for_seconds(SpeedPercent(5), SpeedPercent(25), 1)
                self.right_motor.run_timed(speed_sp=750, time_sp=2500)
                self.left_motor.run_timed(speed_sp=-750, time_sp=2500)
                # shake ev3 head
                threading.Thread(target=self._sitdown).start()
                
                self.leds.set_color("LEFT", "GREEN")
                self.leds.set_color("RIGHT", "GREEN")
                time.sleep(3)
                # starts the dance loop
                self.trigger_bpm = "on"
                threading.Thread(target=self._dance_loop, args=(tempo.value,)).start()

            elif tempo.value == 0:
                # stops the dance loop
                self.trigger_bpm = "off"
                self.leds.set_color("LEFT", "BLACK")
                self.leds.set_color("RIGHT", "BLACK")

    def _dance_loop(self, bpm):
        """
        Perform motor movement in sync with the beat per minute value from tempo data.
        :param bpm: beat per minute from AGT
        """
        color_list = ["GREEN", "RED", "AMBER", "YELLOW"]
        led_color = random.choice(color_list)
        motor_speed = 400
        milli_per_beat = min(1000, (round(60000 / bpm)) * 0.65)
        print("Adjusted milli_per_beat: {}".format(milli_per_beat))
        while self.trigger_bpm == "on":

            # Alternate led color and motor direction
            led_color = "BLACK" if led_color != "BLACK" else random.choice(color_list)
            motor_speed = -motor_speed

            self.leds.set_color("LEFT", led_color)
            self.leds.set_color("RIGHT", led_color)

            self.right_motor.run_timed(speed_sp=motor_speed, time_sp=150)
            self.left_motor.run_timed(speed_sp=-motor_speed, time_sp=150)
            time.sleep(milli_per_beat / 1000)

            self.left_motor.run_timed(speed_sp=-motor_speed, time_sp=150)
            self.right_motor.run_timed(speed_sp=motor_speed, time_sp=150)
            time.sleep(milli_per_beat / 1000)

            self.right_motor.run_timed(speed_sp=350, time_sp=300)
            self.left_motor.run_timed(speed_sp=-350, time_sp=300)
            time.sleep(milli_per_beat / 1000)

            self.right_motor.run_timed(speed_sp=motor_speed, time_sp=150)
            self.left_motor.run_timed(speed_sp=-motor_speed, time_sp=150)
            time.sleep(milli_per_beat / 1000)

    def _move(self, direction, duration: int, speed: int, is_blocking=False):
        """
        Handles move commands from the directive.
        Right and left movement can under or over turn depending on the surface type.
        :param direction: the move direction
        :param duration: the duration in seconds
        :param speed: the speed percentage as an integer
        :param is_blocking: if set, motor run until duration expired before accepting another command
        """
        print("Move command: ({}, {}, {}, {})".format(direction, speed, duration, is_blocking))
        if direction in Direction.FORWARD.value:
            #self.drive.on_for_seconds(SpeedPercent(speed), SpeedPercent(speed), duration, block=is_blocking)
                self.right_motor.run_timed(speed_sp=-750, time_sp=2500)
                self.left_motor.run_timed(speed_sp=-750, time_sp=2500)

        if direction in Direction.BACKWARD.value:
            #self.drive.on_for_seconds(SpeedPercent(-speed), SpeedPercent(-speed), duration, block=is_blocking)
            self.right_motor.run_timed(speed_sp=750, time_sp=2500)
            self.left_motor.run_timed(speed_sp=750, time_sp=2500)

        if direction in (Direction.RIGHT.value + Direction.LEFT.value):
            self._turn(direction, speed)
            #self.drive.on_for_seconds(SpeedPercent(speed), SpeedPercent(speed), duration, block=is_blocking)
            self.right_motor.run_timed(speed_sp=750, time_sp=2500)
            self.left_motor.run_timed(speed_sp=-750, time_sp=2500)

        if direction in Direction.STOP.value:
            #self.drive.off()
            self.right_motor.stop
            self.left_motor.stop
            self.heel_mode = False
            self.patrol_mode = False

    def _activate(self, command):
        """
        Handles preset commands.
        :param command: the preset command
        """
        print("Activate command: ({}".format(command))
        if command in Command.COME.value:
            #call _come method
            self.right_motor.run_timed(speed_sp=750, time_sp=2500)
            self.left_motor.run_timed(speed_sp=50, time_sp=100)

        if command in Command.HEEL.value:
            #call _hell method
            self.heel_mode = True

        if command in Command.SIT.value:
            # call _sit method
            self.heel_mode = False
            self._sitdown()

        if command in Command.STAY.value:
            # call _stay method
            self.heel_mode = False
            self._standup()


    def _turn(self, direction, speed):
        """
        Turns based on the specified direction and speed.
        Calibrated for hard smooth surface.
        :param direction: the turn direction
        :param speed: the turn speed
        """
        if direction in Direction.LEFT.value:
            #self.drive.on_for_seconds(SpeedPercent(0), SpeedPercent(speed), 2)
            self.right_motor.run_timed(speed_sp=0, time_sp=100)
            self.left_motor.run_timed(speed_sp=750, time_sp=100)

        if direction in Direction.RIGHT.value:
            #self.drive.on_for_seconds(SpeedPercent(speed), SpeedPercent(0), 2)
            self.right_motor.run_timed(speed_sp=750, time_sp=100)
            self.left_motor.run_timed(speed_sp=0, time_sp=100)

    def _send_event(self, name: EventName, payload):
        """
        Sends a custom event to trigger a sentry action.
        :param name: the name of the custom event
        :param payload: the sentry JSON payload
        """
        self.send_custom_event('Custom.Mindstorms.Gadget', name.value, payload)

    def _heel_thread(self):
        """
        Monitors the distance between the puppy and an obstacle when heel command called.
        If the maximum distance is breached, decrease the distance by following an obstancle
        """
        while True:
            while self.heel_mode:
                distance = self.ir.proximity
                print("Proximity distance: {}".format(distance))
                # keep distance and make step back from the object
                if distance < 45:  
                    threading.Thread(target=self.__movebackwards).start()
                    self._send_event(EventName.BARK, {'distance': distance})
                    # follow the object
                if distance > 60:
                    threading.Thread(target=self.__moveforwards).start()
                    # otherwise stay still
                else: 
                    threading.Thread(target=self.__stay).start()
                time.sleep(0.2)
            time.sleep(1)

    def _touchsensor_thread(self):
        print("Touch sensor activated")
        while True:
            if self.ts.is_pressed:
                self.leds.set_color("LEFT", "RED")
                self.leds.set_color("RIGHT", "RED")
                if (self.sitting):
                    threading.Thread(target=self._standup).start()
                    self.sitting = False
                else:
                    threading.Thread(target=self._sitdown).start()
                    self.sitting = True
            else:
                self.leds.set_color("LEFT", "GREEN")
                self.leds.set_color("RIGHT", "GREEN")

    def _sitdown(self):
        self.medium_motor.on_for_rotations(SpeedPercent(20), 0.5)

    def _standup(self):
        # run the wheels backwards to help the puppy to stand up.
        threading.Thread(target=self.__back).start()
        self.medium_motor.on_for_rotations(SpeedPercent(50), -0.5)

    def __back(self):
        self.right_motor.run_timed(speed_sp=-350, time_sp=1000)
        self.left_motor.run_timed(speed_sp=-350, time_sp=1000)

    def __movebackwards(self):
        self.right_motor.run_timed(speed_sp=-650, time_sp=1000)
        self.left_motor.run_timed(speed_sp=-650, time_sp=1000)

    def __moveforwards(self):
        self.right_motor.run_timed(speed_sp=650, time_sp=1000)
        self.left_motor.run_timed(speed_sp=650, time_sp=1000)

    def __stay(self):
        self.right_motor.run_timed(speed_sp=0, time_sp=1000)
        self.left_motor.run_timed(speed_sp=0, time_sp=1000)

    def _draweyes(self):
        close = True

        while True:
            self.screen.clear()

            if close:
                #self.screen.draw.ellipse(( 5, 30,  75, 50),fill='white')
                #self.screen.draw.ellipse((103, 30, 173, 50), fill='white')
                self.screen.draw.rectangle(( 5, 60,  75, 50), fill='black')
                self.screen.draw.rectangle((103, 60, 173, 50), fill='black')
                
                #self.screen.draw.rectangle(( 5, 30,  75, 50), fill='black')
                #self.screen.draw.rectangle((103, 30, 173, 50), fill='black')
                time.sleep(10)
            else:
                #self.screen.draw.ellipse(( 5, 30,  75, 100))
                #self.screen.draw.ellipse((103, 30, 173, 100))
                #self.screen.draw.ellipse(( 35, 30,  105, 30),fill='black')
                #self.screen.draw.ellipse((133, 30, 203, 30), fill='black')
                self.screen.draw.rectangle(( 5, 10,  75, 100), fill='black')
                self.screen.draw.rectangle((103, 10, 173, 100), fill='black')

            close = not close  # toggle between True and False

            # Update screen display
            # Applies pending changes to the screen.
            # Nothing will be drawn on the screen screen
            # until this function is called.
            self.screen.update() 
            time.sleep(1)


    def _patrol_thread(self):
        """
        Performs random movement when patrol mode is activated.
        """
        while True:
            while self.patrol_mode:
                print("Patrol mode activated randomly picks a path")
                direction = random.choice(list(Direction))
                duration = random.randint(1, 5)
                speed = random.randint(1, 4) * 25

                while direction == Direction.STOP:
                    direction = random.choice(list(Direction))

                # direction: all except stop, duration: 1-5s, speed: 25, 50, 75, 100
                self._move(direction.value[0], duration, speed)
                time.sleep(duration)
            time.sleep(1)



if __name__ == '__main__':

    # Startup sequence
    gadget = MindstormsGadget()
    # Gadget main entry point
    gadget.main()
