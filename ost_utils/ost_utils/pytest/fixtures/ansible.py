# -*- coding: utf-8 -*-
#
# Copyright 2020 Red Hat, Inc.
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

import pytest

from ost_utils import ansible


@pytest.fixture(scope="session")
def ansible_engine():
    return ansible.module_mapper_for('~lago-.*-engine')


@pytest.fixture(scope="session")
def ansible_hosts():
    return ansible.module_mapper_for('~lago-.*-host-[0-9]')


@pytest.fixture(scope="session")
def ansible_host0():
    return ansible.module_mapper_for('~lago-.*-host-0')


@pytest.fixture(scope="session")
def ansible_host1():
    return ansible.module_mapper_for('~lago-.*-host-1')
