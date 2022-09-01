# SPDX-License-Identifier: Apache-2.0
# (C) The Linux Foundation
# Author: Jan-Simon Moeller (jsmoeller@linuxfoundation.org)

from machine import Pin
from machine import ADC
from time import sleep
import gc
from rp2 import *

# Enable debug messages over serial (a bit slower)
DEBUG = 1
DEBUG2 = 0
# Enable canbus output
CANBUS = 1
# enable only messages on changes
ONLYNEW = 1

# invert the button pins
INVERTPINS = 1

if CANBUS:
    c = CAN()
    led = Pin(25, Pin.OUT)
    led.value(0)

oldcandata = bytearray(8)

# Hardware connection
HORN       = Pin(18, Pin.IN, Pin.PULL_UP)
LANEASSIST = Pin(17, Pin.IN, Pin.PULL_UP)
INFOBUTTON = Pin(16, Pin.IN, Pin.PULL_UP)
AUDIOADC   = ADC(26)
PHONEADC   = ADC(27)
CRUISEADC  = ADC(28)

# ADC voltage/resolution conversion
conversion = 3.3/65535

def strhex(c):
    return str("0x%02X" % int(c))
def int2hex(c):
    return str("%02X" % int(c))

myAUDIObutton = "NONE"
myPHONEbutton = "NONE"
myCRUISEbutton = "NONE"
myAUDIOcan = 0
myPHONEcan = 0
myCRUISEcan = 0
myBUTTONcan = 0

while True:
    # reset before read
    myAUDIObutton = "NONE"
    myPHONEbutton = "NONE"
    myCRUISEbutton = "NONE"
    myAUDIOcan = 0
    myPHONEcan = 0
    myCRUISEcan = 0
    myBUTTONcan = 0

    # read values:
    myLANE = (INVERTPINS - LANEASSIST.value())**2
    myINFO = (INVERTPINS - INFOBUTTON.value())**2
    myHORN = (INVERTPINS - HORN.value())**2
    myAUDIO = float("{:.2f}".format(float(AUDIOADC.read_u16())*conversion))
    myPHONE = float("{:.2f}".format(float(PHONEADC.read_u16())*conversion))
    myCRUISE = float("{:.2f}".format(float(CRUISEADC.read_u16())*conversion))
    
    # Q'n'd spaghetticode for adc
    # AUDIO
    #   Vin = 3.3V                        ADCx
    #   R1  = 680 Ohm                      | 
    #                   3.3V o----[=R1=]---x---[=Steering Wheel=]---o GND
    #
    # Tipping point = ((V2a-V2b)/2)+V2b
    #            e.g. ((2.959-2.305)/2)+2.305 ~= 2.6
    #
    #             Button      Resistance       Voltage V2    tipping point
    #   No button pressed:    5.900  Ohm        2.959        -> 2.6
    #   < :                   1.577  Ohm        2.305        -> 2.0
    #   > :                     752  Ohm        1.733        -> 1.5
    #   MODE:                   421  Ohm        1.26         -> 1.0
    #   - :                     242  Ohm        0.866        -> 0.7
    #   + :                     132  Ohm        0.536        -> 0.4
    #   mute:                    57  Ohm        0.255        -> 0
    #
    if float(myAUDIO) < 2.60:
        myAUDIObutton = "<"
        myAUDIOcan = 128
        # 0x80
    if float(myAUDIO) < 2.00:
        myAUDIObutton = ">"
        myAUDIOcan = 8
        #0x08
    if float(myAUDIO) < 1.50:
        myAUDIObutton = "MODE"
        myAUDIOcan = 32
    if float(myAUDIO) < 1.00:
        myAUDIObutton = "-"
        myAUDIOcan = 16
    if float(myAUDIO) < 0.70:
        myAUDIObutton = "+"
        myAUDIOcan = 64
    if float(myAUDIO) < 0.4:
        myAUDIObutton = "MUTE"
        myAUDIOcan = 1
    if not myINFO:
        myAUDIOcan = 2
        
    # Phone
    #   Vin = 3.3V                        ADCx
    #   R1  = 680 Ohm                      | 
    #                   3.3V o----[=R1=]---x---[=Steering Wheel=]---o GND
    #
    # Tipping point = ((V2a-V2b)/2)+V2b
    #            e.g. ((2.91-1.7)/2)+1.7 ~= 2.3
    #
    #             Button      Resistance       Voltage V2    tipping point
    #   No button pressed:    5.180  Ohm        2.91         -> 2.3
    #   Hang-up :               753  Ohm        1.7          -> 1.3
    #   Take call :             242  Ohm        0.866        -> 0.56
    #   Hands free/voice:        57  Ohm        0.255
    #
    if float(myPHONE) < 2.30:
        myPHONEbutton = "HANGUP"
        myPHONEcan = 1
    if float(myPHONE) < 1.30:
        myPHONEbutton = "TAKECALL"
        myPHONEcan = 2
    if float(myPHONE) < 0.56:
        myPHONEbutton = "HANDSFREE"
        myPHONEcan = 4
    
    # Cruise
    #   Vin = 3.3V                        ADCx
    #   R1  = 1000 Ohm                     | 
    #                   3.3V o----[=R1=]---x---[=Steering Wheel=]---o GND
    #
    # Tipping point = ((V2a-V2b)/2)+V2b
    #            e.g. ((2.58-1.96)/2)+1.96 ~= 2.27
    #
    #             Button      Resistance       Voltage V2    tipping point
    #   No button pressed:    5.180  Ohm        2.58           -> 2.27
    #   Distance :            1.463  Ohm        1.96           -> 1.70
    #   Res/+ :                 782  Ohm        1.45           -> 1.19
    #   Set/-:                  390  Ohm        0.93           -> 0.75
    #   Limit :                 211  Ohm        0.57           -> 0.44
    #   Cancel :                101  Ohm        0.30           -> 0.15
    #   Cruise Enable:            0  Ohm        0 !!
    #
    if float(myCRUISE) < 2.27:
        myCRUISEbutton = "Distance"
        myCRUISEcan = 1
    if float(myCRUISE) < 1.70:
        myCRUISEbutton = "Res/+"
        myCRUISEcan = 64
    if float(myCRUISE) < 1.19:
        myCRUISEbutton = "Set/-"
        myCRUISEcan = 16
    if float(myCRUISE) < 0.75:
        myCRUISEbutton = "Limit"    
        myCRUISEcan = 2
    if float(myCRUISE) < 0.44:
        myCRUISEbutton = "Cancel"
        myCRUISEcan = 8
    if float(myCRUISE) < 0.15:
        myCRUISEbutton = "CruiseEnable"
        myCRUISEcan = 128


    if not myLANE:
        myBUTTONcan = 1
    if not myINFO:
        myBUTTONcan = 2
    if not myHORN:
        myBUTTONcan = 128

    if DEBUG:
        print("LANE       - %s" % ( 1 - myLANE ) )
        print("INFO       - %s" % ( 1 - myINFO ) )
        print("HORN       - %s" % ( 1 - myHORN ) )
        print("AUDIOADC   - %s" % myAUDIO)
        print("AUDIObutton  %s" % myAUDIObutton)
        print("PHONEADC   - %s" % myPHONE)
        print("PHONEbutton  %s" % myPHONEbutton)
        print("CRUISEADC  - %s" % myCRUISE)
        print("CRUISEbutton %s" % myCRUISEbutton)
        print("")
        print("ALLOC - %s" % gc.mem_alloc())
        print("FREE  - %s" % gc.mem_free())
        print("")

    #CanMessage:
    #Button ADC0  ADC1  ADC2 AUDIO PHONE CRUISE BUTTONS
    # 0x00  0x00  0x00  0x00  0x00  0x00  0x00  0x00
    if DEBUG2:
        print(  "CanMessage: %s,%s,%s,%s,%s,%s,%s,%s" % 
               ( strhex(myBUTTONcan), strhex(myAUDIO*10), strhex(myPHONE*10), strhex(myCRUISE*10),
                 strhex(myAUDIOcan), strhex(myPHONEcan), strhex(myCRUISEcan), strhex(myBUTTONcan) )
             )

    if CANBUS:
        # send out can message
        canid = 0x21
#        candata = bytearray([myBUTTONcan, int(myAUDIO*10),
#                              int(myPHONE*10), int(myCRUISE*10),
#                              myAUDIOcan, myPHONEcan,
#                              myCRUISEcan, myBUTTONcan])
        candata = bytearray([myBUTTONcan, 0,
                              0, 0,
                              myAUDIOcan, myPHONEcan,
                              myCRUISEcan, myBUTTONcan])
        if DEBUG2:
            print(candata)
        
        if ONLYNEW:
            # only send on differences
            if not candata == oldcandata:
                oldcandata = candata
                f = CANFrame(CANID(canid), data=bytes(candata))
                led.toggle()
                c.send_frame(f)
                sleep(0.01)
                while f.get_timestamp() is None:
                    print("*****************waiting for can frame to be sent")
                    sleep(0.1)
                led.toggle()
            else:
                continue
        else:
            # always send
            f = CANFrame(CANID(canid), data=bytes(candata))
            led.toggle()
            c.send_frame(f)
            sleep(0.01)
            while f.get_timestamp() is None:
                print("*****************waiting for can frame to be sent")
                sleep(0.1)
            led.toggle()
        
    else:
        # do nothing
        sleep(0.01)
    sleep(0.04)
    if DEBUG:
        # debug output on serial is slower
        sleep(0.05)