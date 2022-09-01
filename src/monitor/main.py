# SPDX-License-Identifier: Apache-2.0
# (C) The Linux Foundation
# Author: Jan-Simon Moeller (jsmoeller@linuxfoundation.org)

from rp2 import *
from time import sleep


led = Pin(25, Pin.OUT)
led.value(0)

c = CAN()

while True:
    frames = c.recv()
    for frame in frames:
        led.toggle()
        print(frame)
    sleep(0.2)
