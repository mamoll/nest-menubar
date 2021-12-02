#!/usr/bin/env python3

######################################################################
# Software License Agreement (BSD License)
#
#  Copyright (c) 2019, Mark Moll
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above
#     copyright notice, this list of conditions and the following
#     disclaimer in the documentation and/or other materials provided
#     with the distribution.
#   * Neither the name of Mark Moll nor the names of its
#     contributors may be used to endorse or promote products derived
#     from this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
#  FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
#  COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
#  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
#  BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#  LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
#  CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
#  LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
#  ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
#  POSSIBILITY OF SUCH DAMAGE.
######################################################################

# Author: Mark Moll

import os
from functools import partial
import nest
import nest.helpers
import rumps


class ThermostatWrapper(object):
    def __init__(self, thermostat):
        self.thermostat_ = thermostat
        self.prev_target_ = self.set_point
        self.target_ = self.prev_target_
        self.current_ = thermostat.traits["Temperature"]["ambientTemperatureCelsius"]
        self.prev_mode_ = thermostat.traits["ThermostatMode"]["mode"]
        self.mode_ = self.prev_mode_
        self.name_ = thermostat.where
        self.offset_ = 2
        self.range_ = (9, 32)

    @property
    def target(self):
        return self.target_

    @target.setter
    def target(self, temp):
        if self.mode_ == "HEATCOOL":
            temp = (temp - self.offset_, temp + self.offset_)
        self.target_ = temp

    def _label(self, temp):
        if self.thermostat_.traits["Settings"]["temperatureScale"] == "FAHRENHEIT":
            temp = temp * 9.0 / 5.0 + 32.0
            return f"{temp:.1f}F"
        return f"{temp:.1f}˚C"

    def target_label(self):
        if self.mode_ == "HEATCOOL":
            return (
                f"Target: {self._label(self.target_[0])}–{self._label(self.target_[1])}"
            )
        elif self.mode_ in ("ECO", "OFF"):
            return "Target: —"
        else:
            return f"Target: {self._label(self.target_)}"

    @property
    def current(self):
        return self.current_

    def current_label(self):
        return f"Current: {self._label(self.current_)}"

    @property
    def set_point(self):
        sp = self.thermostat_.traits["ThermostatTemperatureSetpoint"]
        if "heatCelsius" in sp:
            return sp["heatCelsius"]
        else:
            return sp["coolCelsius"]

    @set_point.setter
    def set_point(self, target):
        if self.mode_ == "HEAT":
            self.thermostat_.send_cmd(
                "ThermostatTemperatureSetpoint.SetHeat",
                {"heatCelsius": target},
            )
        elif self.mode_ == "COOL":
            self.thermostat_.send_cmd(
                "ThermostatTemperatureSetpoint.SetCool",
                {"coolCelsius": self.target_},
            )
        elif self.mode_ == "HEATCOOL":
            self.thermostat_.send_cmd(
                "ThermostatTemperatureSetpoint.SetRange",
                {"heatCelsius": target[0], "coolCelsius": target[1]},
            )

    @property
    def mode(self):
        return self.mode_

    @mode.setter
    def mode(self, m):
        self.mode_ = m

    def mode_label(self):
        return f"Mode: {self.mode_}"

    @property
    def name(self):
        return self.name_

    @property
    def target_range(self):
        return self.range_

    def update(self):
        if self.prev_mode_ != self.mode_:
            self.prev_mode_ = self.mode_
            self.thermostat_.send_cmd("ThermostatMode.SetMode", {"mode": self.mode_})
        else:
            self.mode_ = self.thermostat_.traits["ThermostatMode"]["mode"]
        if self.prev_target_ != self.target_:
            self.prev_target_ = self.target_
            self.set_point = self.target_
        else:
            self.target_ = self.set_point
        self.current_ = self.thermostat_.traits["Temperature"][
            "ambientTemperatureCelsius"
        ]


def reauthorize_callback(url):
    from AppKit import NSPasteboard

    window = rumps.Window(
        f"Control-click on {url} to authorize, then copy full callback URL to clipboard and click OK",
        title="Google authentication to get access token.",
        default_text="",
        cancel=True,
        dimensions=(500, 9),
    )
    response = window.run()
    if response.clicked:
        return (
            NSPasteboard.generalPasteboard()
            .pasteboardItems()[0]
            .stringForType_("public.utf8-plain-text")
        )
    else:
        rumps.quit_application()


class NestBarApp(rumps.App):
    def __init__(self):
        super().__init__("Nest", icon="nest_menubar.icns", template=True)

        settings = nest.helpers.get_config()
        self.nest_api = nest.Nest(
            client_id=settings["client_id"],
            client_secret=settings["client_secret"],
            project_id=settings["project_id"],
            reautherize_callback=reauthorize_callback,
            access_token_cache_file=os.path.expanduser(settings["token_cache"]),
        )

        self.thermostats = [
            ThermostatWrapper(t)
            for t in self.nest_api.get_devices(types=["THERMOSTAT"])
        ]
        self.temp_sliders = []
        for i, thermostat in enumerate(self.thermostats):
            self.menu.add(
                rumps.MenuItem(
                    title=thermostat.name, icon="nest_menubar.icns", template=True
                )
            )
            self.menu.add(
                rumps.MenuItem(title=f"{i}_mode", callback=partial(self.setMode, i))
            )
            self.menu.add(rumps.MenuItem(title=f"{i}_current"))
            self.menu.add(rumps.MenuItem(title=f"{i}_target"))
            min_temp, max_temp = thermostat.target_range
            self.temp_sliders.append(
                rumps.SliderMenuItem(
                    thermostat.current, min_temp, max_temp, partial(self.setTemp, i)
                )
            )
            self.menu.add(self.temp_sliders[-1])
            self.menu.add(rumps.separator)
        self.update(None)

    @rumps.timer(10)
    def update(self, _):
        for i, thermostat in enumerate(self.thermostats):
            thermostat.update()
            self.menu[f"{i}_mode"].title = thermostat.mode_label()
            self.menu[f"{i}_current"].title = thermostat.current_label()
            self.menu[f"{i}_target"].title = thermostat.target_label()
            target = thermostat.target
            if isinstance(target, list):
                target = 0.5 * (target[0] + target[1])
            self.temp_sliders[i].value = target

    def setTemp(self, i, sender):
        self.thermostats[i].target = sender.value
        self.menu[f"{i}_target"].title = self.thermostats[i].target_label()

    def setMode(self, i, _):
        window = rumps.Window(
            f"Select mode for {self.thermostats[i].name}",
            ok="Cancel",
            dimensions=(0, 0),
        )
        modes = ["OFF", "ECO", "HEATCOOL", "HEAT", "COOL"]
        window.add_buttons(modes)
        response = window.run()
        if response.clicked > 1:
            self.thermostats[i].mode = modes[response.clicked - 2]
            self.menu[f"{i}_mode"].title = self.thermostats[i].mode_label()


if __name__ == "__main__":
    NestBarApp().run()
