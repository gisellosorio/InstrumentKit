#!/usr/bin/python
# -*- coding: utf-8 -*-
##
# cc1.py: Class for the Qubitekk Coincidence Counter instrument
##
# © 2014 Steven Casagrande (scasagrande@galvant.ca).
#
# This file is a part of the InstrumentKit project.
# Licensed under the AGPL version 3.
##
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
##
# CC1 Class contributed by Catherine Holloway.
##

# IMPORTS #####################################################################

import quantities as pq
from flufl.enum import IntEnum

from instruments.generic_scpi.scpi_instrument import SCPIInstrument
from instruments.util_fns import ProxyList, assume_units, split_unit_str

# CLASSES #####################################################################


class CC1(SCPIInstrument):
    """
    The CC1 is a hand-held coincidence counter.
    
    It has two setting values, the dwell time and the coincidence window. The 
    coincidence window determines the amount of time (in ns) that the two 
    detections may be from each other and still be considered a coincidence. 
    The dwell time is the amount of time that passes before the counter will 
    send the clear signal.
    
    More information can be found at :
    http://www.qubitekk.com
    """
    def __init__(self, filelike):
        super(CC1, self).__init__(filelike)
        self.terminator = "\n"
        self.end_terminator = "\n"
        self.channel_count = 3
        self.channel1 = self.Channel(self, 1)
        self.channel2 = self.Channel(self, 2)
        self.channelc = self.Channel(self, 3)

    # INNER CLASSES ##

    class Channel(object):
        """
        Class representing a channel on the Qubitekk CC1.
        """

        __CHANNEL_NAMES = {
            1: 'C1',
            2: 'C2',
            3: 'C0'
        }

        def __init__(self, cc1, idx):
            self._cc1 = cc1
            # Use zero-based indexing for the external API, but one-based
            # for talking to the instrument.
            self._idx = idx + 1
            self._chan = self.__CHANNEL_NAMES[self._idx]
            self._count = 0
            
        # PROPERTIES ##
        
        @property
        def count(self):
            """
            Gets the counts of this channel.
            
            :rtype: `int`
            """
            count = self._cc1.query("COUN:{0}?".format(self._chan))
            # FIXME: Does this property actually work? The try block seems wrong.
            try:
                count = int(count)
                self._count = count
                return self.count
            except ValueError:
                self._count = self.count

    class TriggerMode(IntEnum):
        continuous = 0
        start_stop = 0

    # METHOD OVERRIDES #
    def sendcmd(self, cmd):
        # We override sendcmd here to check for the response
        # "Unknown command", so that property factories not aware
        # of this response can blindly call sendcmd() and rely on
        # exception handling to get us the rest of the way there.
        #
        # Note that we call the superclass *query* and not *sendcmd*;
        # this is so we can get the error message out!
        resp = super(CC1, self).query(cmd)

        if "Unknown command" == resp.strip():
            raise IOError("CC1 reported that command {0} is unknown: {1}".format(
                cmd, resp
            ))

    def query(self, cmd):
        # We override query for the same reason as
        # above.
        resp = super(CC1, self).query(cmd)

        if "Unknown command" == resp.strip():
            raise IOError("CC1 reported that command {0} is unknown: {1}".format(
                cmd, resp
            ))

        # If we survived, then the command was not marked as unknown.
        # Something else may have gone wrong, but since we don't know that,
        # we should return what we believe to be a successful response.
        return resp
            
    # PROPERTIES #
    @property
    def window(self):
        """
        Gets/sets the length of the coincidence window between the two signals.
        
        :units: As specified (if a `~quantities.Quantity`) or assumed to be
            of units nanoseconds.
        :type: `~quantities.Quantity`
        """
        return pq.Quantity(*split_unit_str(self.query("DWEL?"), "s"))

    @window.setter
    def window(self, new_val):
        new_val_mag = assume_units(new_val, pq.ns).rescale(pq.ns).magnitude
        if new_val_mag < 0:
            raise ValueError("Window is too small.")
        if new_val_mag > 7:
            raise ValueError("Window is too big")
        self.sendcmd(":WIND {}".format(new_val_mag))

    @property
    def delay(self):
        """
        Get the delay value (in nanoseconds) on Channel 1. N may be 0, 2, 4, 6, 8, 10, 12, or 14ns.
        :rtype: quantities.ns
        :return: the delay value
        """
        response = self.query("DELA?")
        return int(response)*pq.ns

    @delay.setter
    def delay(self, new_val):
        """
        Set the delay value (in nanoseconds) on Channel 1. N may be 0, 2, 4, 6, 8, 10, 12, or 14ns.
        """
        new_val = assume_units(new_val, pq.ns).rescale(pq.ns)
        if new_val < 0*pq.ns or new_val > 14*pq.ns:
            raise ValueError("New delay value is out of bounds.")
        if new_val.magnitude % 2 != 0:
            raise ValueError("New magnitude must be an even number")
        self.sendcmd(":DELA "+str(int(new_val.magnitude)))

    
    @property
    def dwell_time(self):
        """
        Gets/sets the length of time before a clear signal is sent to the 
        counters.
        
        :units: As specified (if a `~quantities.Quantity`) or assumed to be
            of units seconds.
        :type: `~quantities.Quantity`
        """
        return pq.Quantity(*split_unit_str(self.query("DWEL?"), "s"))

    @dwell_time.setter
    def dwell_time(self, new_val):
        new_val_mag = assume_units(new_val, pq.s).rescale(pq.s).magnitude
        if new_val_mag < 0:
            raise ValueError("Dwell time cannot be negative.")
        self.sendcmd(":DWEL {}".format(new_val_mag))
            
    @property
    def gate_enable(self):
        """
        Gets/sets the Gate mode of the CC1.
        
        A setting of `True` means the input signals are anded with the gate 
        signal and `False` means the input signals are not anded with the gate 
        signal.
        
        :type: `bool`
        """
        response = self.query("GATE?")
        response = int(response)
        return True if response is 1 else False

    @gate_enable.setter
    def gate_enable(self, new_val):
        if isinstance(new_val, int):
            if new_val != 0 and new_val != 1:
                raise ValueError("Not a valid gate_enable mode.")
            new_val = bool(new_val)
        elif not isinstance(new_val, bool):
            raise TypeError("CC1 gate_enable must be specified as a boolean.")
        
        if new_val is False:
            self.sendcmd(":GATE:OFF")
        else:
            self.sendcmd(":GATE:ON")

    @property
    def count_enable(self):
        """
        The count mode of the CC1.
        
        A setting of `True` means the dwell time passes before the counters are 
        cleared and `False` means the counters are cleared every 0.1 seconds.
        
        :type: `bool`
        """
        response = self.query("COUN?")
        response = int(response)
        return True if response is 1 else False

    @count_enable.setter
    def count_enable(self, new_val):
        if isinstance(new_val, int):
            if new_val != 0 and new_val != 1:
                raise ValueError("Not a valid count_enable mode.")
            new_val = bool(new_val)
        elif not isinstance(new_val, bool):
            raise TypeError("CC1 count_enable must be specified as a boolean.")
        
        if new_val is False:
            self.sendcmd(":COUN:OFF")
        else:
            self.sendcmd(":COUN:ON")
    
    @property
    def channel(self):
        """
        Gets a specific channel object. The desired channel is specified like 
        one would access a list.
        
        For instance, this would print the counts of the first channel::
        
        >>> cc = ik.qubitekk.CC1.open_serial('COM8', 19200, timeout=1)
        >>> print cc.channel[0].count
        
        :rtype: `CC1.Channel`
        
        """
        return ProxyList(self, CC1.Channel, xrange(self.channel_count))

    @property
    def trigger(self):
        """
        Gets the current trigger mode, meaning, whether the coincidence counter is tallying counts every dwell
        time over and over - continuous, or start/stop, meaning the coincidence counter is tallying counts between
        start and stop triggers.
        :rtype: ik.qubitekk.CC1.TriggerMode
        :return: the current trigger mode
        """
        response = self.query("TRIG?")
        return self.TriggerMode[int(response)]

    @trigger.setter
    def trigger(self, new_setting):
        if new_setting is not self.TriggerMode:
            raise TypeError("The new trigger setting must be a Trigger Mode.")
        self.sendcmd(":TRIG "+str(int(new_setting)))
    
    # METHODS #
    
    def clear_counts(self):
        """
        Clears the current total counts on the counters.
        """
        self.sendcmd("CLEA")
