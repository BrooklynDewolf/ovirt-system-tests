# -*- coding: utf-8 -*-
#
# Copyright 2014, 2017, 2019 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#

from os import environ, path

from ost_utils.pytest.fixtures.ansible import *
from ost_utils.pytest.fixtures.engine import *
from ost_utils.pytest.fixtures.env import suite_dir

def test_init_terraform(ansible_engine, suite_dir):
    working_dir = '/tmp'
    func = 'func.sh'
    script = 'test-init-terraform.sh'
    pr = os.environ.get('STD_CI_REFSPEC')
    if pr == None or not pr:
        pr = "master"

    src_script_file=os.path.join(
        suite_dir, func
    )
    dst_script_file=os.path.join(
        working_dir, func
    )
    ansible_engine.copy(
        src=src_script_file,
        dest=dst_script_file,
        mode='0755'
    )
    src_script_file=os.path.join(
        suite_dir, script
    )
    dst_script_file=os.path.join(
        working_dir, script
    )
    ansible_engine.copy(
        src=src_script_file,
        dest=dst_script_file,
        mode='0755'
    )
    ansible_engine.shell(
        f'{dst_script_file} '
        '-w /tmp '
        f'-t {pr}'
    )
