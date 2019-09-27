#/usr/bin/env python3

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
        self.prev_target_ = thermostat.temperature
        self.target_ = self.prev_target_
        self.current_ = thermostat.temperature
        self.prev_mode_ = thermostat.mode
        self.mode_ = self.prev_mode_
        self.name_ = thermostat.name
        if thermostat.temperature_scale is 'F':
            self.offset_ = 3
            self.range_ = (50, 90)
            self.unit_ = 'F'
        else:
            self.offset_ = 2
            self.range_ = (9, 32)
            self.unit_ = '°C'

    @property
    def target(self):
        return self.target_
    @target.setter
    def target(self, temp):
        if self.mode_ == 'heat-cool':
            temp = (temp - self.offset_, temp + self.offset_)
        print(self.name_, temp)
        self.target_ = temp
    def target_label(self):
        if self.mode_ is 'heat-cool':
            return 'Target: %0.1f–%0.1f%s' % (self.target_[0], self.target_[1], self.unit_)
        elif self.mode_ in ('eco', 'off'):
            return 'Target: —'
        else:
            return 'Target: %0.1f%s' % (self.target_, self.unit_)
    @property
    def current(self):
        return self.current_
    def current_label(self):
        return 'Current: %0.1f%s' % (self.current_, self.unit_)
    @property
    def mode(self):
        return self.mode_
    @mode.setter
    def mode(self, m):
        self.mode_ = m
    def mode_label(self):
        return 'Mode: %s' % self.mode_
    @property
    def name(self):
        return self.name_
    @property
    def target_range(self):
        return self.range_

    def update(self):
        if self.prev_mode_ != self.mode_:
            self.prev_mode_ = self.mode_
            self.thermostat_.mode = self.mode_
        else:
            self.mode_ = self.thermostat_.mode
        if self.prev_target_ != self.target_:
            self.prev_target_ = self.target_
            self.thermostat_.target = self.target_
        else:
            self.target_ = self.thermostat_.target
        self.current_ = self.thermostat_.temperature

class NestBarApp(rumps.App):
    def __init__(self):
        super().__init__('Nest', icon='nest_menubar.icns', template=True)
        token_cache = os.path.expanduser(os.path.sep.join(('~', '.config', 'nest', 'token_cache')))

        settings = nest.helpers.get_config()
        self.nest_api = nest.Nest(
            client_id=settings['client_id'],
            client_secret=settings['client_secret'],
            access_token_cache_file=token_cache)
        if self.nest_api.authorization_required:
            window = rumps.Window(
                f'Control-click on {self.nest_api.authorize_url} to authorize, then enter PIN below',
                title='Nest PIN required to get access token.',
                default_text='1234',
                cancel=True,
                dimensions=(100, 40))
            response = window.run()
            if response.clicked:
                self.nest_api.request_token(response.text)
            else:
                rumps.quit_application()

        self.thermostats = [ThermostatWrapper(t) for t in self.nest_api.thermostats]
        for i, thermostat in enumerate(self.thermostats):
            self.menu.add(rumps.MenuItem(
                title=thermostat.name,
                icon='nest_menubar.icns',
                template=True))
            self.menu.add(rumps.MenuItem(
                title=f'{i}_mode',
                callback=partial(self.setMode, i)))
            self.menu.add(rumps.MenuItem(title=f'{i}_current'))
            self.menu.add(rumps.MenuItem(title=f'{i}_target'))
            min_temp, max_temp = thermostat.target_range
            self.menu.add(rumps.SliderMenuItem(
                thermostat.current, min_temp, max_temp,
                partial(self.setTemp, i)))
            self.menu.add(rumps.separator)
        self.update(None)

    @rumps.timer(10)
    def update(self, _):
        for i, thermostat in enumerate(self.thermostats):
            thermostat.update()
            self.menu[f'{i}_mode'].title = thermostat.mode_label()
            self.menu[f'{i}_current'].title = thermostat.current_label()
            self.menu[f'{i}_target'].title = thermostat.target_label()

    def setTemp(self, i, sender):
        temp = round(sender.value)
        self.thermostats[i].target = temp
        self.menu[f'{i}_target'].title = self.thermostats[i].target_label()

    def setMode(self, i, _):
        window = rumps.Window(
            f'Select mode for {self.thermostats[i].name}', ok="Cancel", dimensions=(0, 0))
        modes = ['off', 'eco', 'heat-cool', 'heat', 'cool']
        window.add_buttons(modes)
        response = window.run()
        if response.clicked > 1:
            self.thermostats[i].mode = modes[response.clicked - 2]
            self.menu[f'{i}_mode'].title = self.thermostats[i].mode_label()

if __name__ == "__main__":
    NestBarApp().run()
