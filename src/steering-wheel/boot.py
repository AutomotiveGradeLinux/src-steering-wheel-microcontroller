# SPDX-License-Identifier: Apache-2.0
# (C) The Linux Foundation
# Author: Jan-Simon Moeller (jsmoeller@linuxfoundation.org)

from machine import Pin
import time

led = Pin(25, Pin.OUT)
i = 8


led.value(0)

while i > 0:
    led.toggle()
    time.sleep(0.1)
    i = i-1





