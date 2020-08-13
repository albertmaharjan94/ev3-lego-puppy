#!/usr/bin/env python3
# Copyright 2019 Amazon.com, Inc. or its affiliates.  All Rights Reserved.
# 
# You may not use this file except in compliance with the terms and conditions 
# set forth in the accompanying LICENSE.TXT file.
#
# THESE MATERIALS ARE PROVIDED ON AN "AS IS" BASIS. AMAZON SPECIFICALLY DISCLAIMS, WITH 
# RESPECT TO THESE MATERIALS, ALL WARRANTIES, EXPRESS, IMPLIED, OR STATUTORY, INCLUDING 
# THE IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.

import os
import sys
import time
import logging
import json
import random
import threading

from enum import Enum
from agt import AlexaGadget


from ev3dev2.led import Leds
from ev3dev2.sound import Sound
from ev3dev2.motor import OUTPUT_A, SpeedPercent, MediumMotor, OUTPUT_B, OUTPUT_C, MoveTank, LargeMotor
from ev3dev2.sensor.lego import InfraredSensor
from ev3dev2.sensor.lego import TouchSensor
from ev3dev2.display import Display

# Set the logging level to INFO to see messages from AlexaGadget
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(message)s')
logging.getLogger().addHandler(logging.StreamHandler(sys.stderr))
logger = logging.getLogger(__name__)


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
    ANGRY = ['angry bark','angry' ,'bark','chey chey','chase','cheey' ,'cheey cheey']
    CUTE = ['cute','cute bark','cutie cutie','cutie pie','hello cutie','beepash my cutie','good boy beepash']
    COFFIN = ['coughing','coffee','coffin','coffin bark','die','beepash die','die beepash']
    DANCE=['sing','dance','dance for me']

class EventName(Enum):
    """
    The list of custom events sent from this gadget to Alexa
    """
    BARK = "bark"


class MindstormsGadget(AlexaGadget):
    """
    A Mindstorms gadget that performs movement based on voice commands.
    Two types of commands are supported, directional movement and preset.
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
        self.dance=False
        self.sound = Sound()
        self.drive = MoveTank(OUTPUT_B, OUTPUT_C)
        self.sound.speak('Hello, my name is Beipas!')



        # Connect medium motor on output port A:
        self.medium_motor = MediumMotor(OUTPUT_A)
        # Connect two large motors on output ports B and C:
        self.left_motor = LargeMotor(OUTPUT_B)
        self.right_motor = LargeMotor(OUTPUT_C)


        # Gadget states
        self.bpm = 0
        self.trigger_bpm = "off"
        self.eyes=True

        # Start threads
        threading.Thread(target=self._dance_thread, daemon=True).start()
        threading.Thread(target=self._patrol_thread, daemon=True).start()
        threading.Thread(target=self._heel_thread, daemon=True).start()
        threading.Thread(target=self._touchsensor_thread, daemon=True).start()
        threading.Thread(target=self._eyes_thread, daemon=True).start()

    def on_connected(self, device_addr):
        """
        Gadget connected to the paired Echo device.
        :param device_addr: the address of the device we connected to
        """
        self.leds.set_color("LEFT", "GREEN")
        self.leds.set_color("RIGHT", "GREEN")
        logger.info("{} connected to Echo device".format(self.friendly_name))

    def on_disconnected(self, device_addr):
        """
        Gadget disconnected from the paired Echo device.
        :param device_addr: the address of the device we disconnected from
        """
        self.leds.set_color("LEFT", "BLACK")
        self.leds.set_color("RIGHT", "BLACK")
        logger.info("{} disconnected from Echo device".format(self.friendly_name))

    def on_custom_mindstorms_gadget_control(self, directive):
        """
        Handles the Custom.Mindstorms.Gadget control directive.
        :param directive: the custom directive with the matching namespace and name
        """
        try:
            payload = json.loads(directive.payload.decode("utf-8"))
            print("Control payload: {}".format(payload), file=sys.stderr)
            control_type = payload["type"]
            if control_type == "move":
                
                speed = random.randint(3, 4) * 25
                # Expected params: [direction, duration, speed]
                self._move(payload["direction"], int(payload["duration"]), speed)

            if control_type == "command":
                # Expected params: [command]
                self._activate(payload["command"])

        except KeyError:
            print("Missing expected parameters: {}".format(directive), file=sys.stderr)

    def _dance_thread(self):
        """
        Perform motor movement in sync with the beat per minute value from tempo data.
        :param bpm: beat per minute from AGT
        """
        bpm = 100
        color_list = ["GREEN", "RED", "AMBER", "YELLOW"]
        led_color = random.choice(color_list)
        motor_speed = 400
        milli_per_beat = min(1000, (round(60000 / bpm)) * 0.65)
        print("Adjusted milli_per_beat: {}".format(milli_per_beat))
        while True:
            while self.dance == True:
                print("Dancing")
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


    def _move(self, direction, duration: int, speed=70, is_blocking=False):
        """
        Handles move commands from the directive.
        Right and left movement can under or over turn depending on the surface type.
        :param direction: the move direction
        :param duration: the duration in seconds
        :param speed: the speed percentage as an integer
        :param is_blocking: if set, motor run until duration expired before accepting another command
        """
        print("Move command: ({}, {}, {}, {})".format(direction, speed, duration, is_blocking), file=sys.stderr)
        if direction in Direction.FORWARD.value:
            self.drive.on_for_seconds(SpeedPercent(speed), SpeedPercent(speed), duration, block=is_blocking)

        if direction in Direction.BACKWARD.value:
            self.drive.on_for_seconds(SpeedPercent(-speed), SpeedPercent(-speed), duration, block=is_blocking)

        if direction in (Direction.RIGHT.value):
            
            self.drive.on_for_seconds(SpeedPercent(-speed), SpeedPercent(speed), duration, block=is_blocking)

        if direction in (Direction.LEFT.value):
            
            self.drive.on_for_seconds(SpeedPercent(speed), SpeedPercent(-speed), duration, block=is_blocking)

        if direction in Direction.STOP.value:
            self.drive.off()
            self.patrol_mode = False
            self.dance=False

    def _activate(self, command):
        """
        Handles preset commands.
        :param command: the preset command
        """
        print("Activate command: ({}".format(command))
        if command in Command.COME.value:
            #call _come method
            self.right_motor.run_timed(speed_sp=750, time_sp=2500)
            self.left_motor.run_timed(speed_sp=750, time_sp=2500)

        if command in Command.HEEL.value:
            #call _hell method
            self.heel_mode = True

        if command in Command.SIT.value:
            # call _sit method
            self.heel_mode = False
            
            self.trigger_bpm == "on"
            self._sitdown()

        if command in Command.SENTRY.value:
            # call _stay method
            
            self.trigger_bpm == "on"
            self.heel_mode = False
            self._standup()

        if command in Command.STAY.value:
            # call _stay method
            self.heel_mode = False
            self._standup()
        
        
        if command in Command.ANGRY.value:
            # call _stay method
            self._angrybark()
            
        if command in Command.CUTE.value:
            # call _stay method
            self._cutebark()
            
        if command in Command.COFFIN.value:
            # call _stay method
            self.dance = True
            self.trigger_bpm = "on"
            self._coffinbark()
            self.dance= False

        if command in Command.DANCE.value:
            # call _stay method
            self.trigger_bpm = "on"
            self.dance = True
            print(self.dance)

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
                if distance < 35:  
                    threading.Thread(target=self.__movebackwards).start()
                    # self._send_event(EventName.BARK, {'distance': distance})
                    # follow the object
                if distance > 50:
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
    
    def _eyes_thread(self):
        print("Drawing Eyes")
        while True:
            while self.eyes:
                self._draweyes()

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
        self.right_motor.run_timed(speed_sp=-750, time_sp=2500)
        self.left_motor.run_timed(speed_sp=-750, time_sp=2500)

    def __moveforwards(self):
        self.right_motor.run_timed(speed_sp=750, time_sp=2500)
        self.left_motor.run_timed(speed_sp=750, time_sp=2500)

    def __stay(self):
        self.right_motor.run_timed(speed_sp=0, time_sp=1000)
        self.left_motor.run_timed(speed_sp=0, time_sp=1000)


    
    def _angrybark(self):
        self.sound.play_file('angry_bark.wav')

    def _cutebark(self):
        self.sound.play_file('cute_bark.wav')

    def _coffinbark(self):
        self.sound.play_file('coffin_dance.wav')


    def _draweyes(self):
        close = True

        while True:
            self.screen.clear()
            # if close:
            #     self.screen.draw.line(50,65,90, 100, width=5)
            #     self.screen.draw.line(50,105,90, 105, width=5)

            #     self.screen.draw.line(120,100,160,65, width=5)
            #     self.screen.draw.line(120,105,160,105, width=5)

            #     time.sleep(10)
            # else:
            #     self.screen.draw.rectangle(50,45,90, 125, radius=10, fill_color='white')
            #     self.screen.draw.rectangle(120,45,160,125, radius=10, fill_color='white')

            #     self.screen.draw.rectangle(65,65,80, 105, radius=7, fill_color='black')
            #     self.screen.draw.rectangle(130,65,145,105, radius=7, fill_color='black')
                

            ## alt
                # self.screen.draw.line(50,105,90, 105, width=5).rotate(135)
                # self.screen.draw.line(50,105,90, 105, width=5)

                # self.screen.draw.line(50,105,90, 105, width=5).rotate(45)
                # self.screen.draw.line(50,105,90, 105, width=5)
            if close:
                # self.screen.draw.ellipse(( 5, 30,  75, 50),fill='white')
                # self.screen.draw.ellipse((103, 30, 173, 50), fill='white')
                self.screen.draw.rectangle(( 5, 60,  75, 50), fill='black')
                self.screen.draw.rectangle((103, 60, 173, 50), fill='black')
                
                # self.screen.draw.rectangle(( 5, 30,  75, 50), fill='black')
                # self.screen.draw.rectangle((103, 30, 173, 50), fill='black')
                time.sleep(10)
            else:
                # self.screen.draw.ellipse(( 5, 30,  75, 100))
                # self.screen.draw.ellipse((103, 30, 173, 100))
                # self.screen.draw.ellipse(( 35, 30,  105, 30),fill='black')
                # self.screen.draw.ellipse((133, 30, 203, 30), fill='black')
                self.screen.draw.rectangle(( 5, 10,  75, 100), fill='black')
                self.screen.draw.rectangle((103, 10, 173, 100), fill='black')

            close = not close  # toggle between True and False

            # Update screen display
            # Applies pending changes to the screen.
            # Nothing will be drawn on the screen screen
            # until this function is called.
            self.screen.update() 
            time.sleep(1)



if __name__ == '__main__':

    gadget = MindstormsGadget()

    # Set LCD font and turn off blinking LEDs
    os.system('setfont Lat7-Terminus12x6')
    gadget.leds.set_color("LEFT", "BLACK")
    gadget.leds.set_color("RIGHT", "BLACK")

    # expermental

    # Input an existing wav filename
    # wavFile = input("Enter a wav filename: ")
    # # Play the wav file
    # playsound(wavFile)

    # Startup sequence
    # gadget.sound.play_song((('C4', 'e'), ('C4', 'e')))
    gadget.leds.set_color("LEFT", "GREEN")
    gadget.leds.set_color("RIGHT", "GREEN")

    # Gadget main entry point
    gadget.main()

    # Shutdown sequence
    gadget.sound.play_song((('E5', 'e'), ('C4', 'e')))
    gadget.leds.set_color("LEFT", "BLACK")
    gadget.leds.set_color("RIGHT", "BLACK")
