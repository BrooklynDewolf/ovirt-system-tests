#
# Copyright 2008-2016 Red Hat, Inc.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#

from __future__ import absolute_import
from __future__ import division

try:
    from sos.plugins import Plugin, RedHatPlugin
except ImportError:
    import sos.plugintools
    Plugin = RedHatPlugin = sos.plugintools.PluginBase

import json
import os
import re
import stat
import subprocess

# Hardcode data comain storage class until this is properly exposed
# by the vdsm api.
DATA_DOMAIN = 1

# This configuration is based on vdsm.storage.lvm.LVM_CONF_TEMPLATE.
#
# locking_type is set to 0 (disable locks) avoids the possibility of
# hanging lvm commands when another process holds a conflicting lock, or
# there is a bug in lvm locking.
#
# metadata_read_only is set to 1 (disable metadata updates) to ensure
# that no operations that change on-disk metadata are permitted.
# Additionally, read-only commands that encounter metadata in need of
# repair will still be allowed to proceed exactly as if the repair had
# been performed (except for the unchanged vg_seqno).
#
# use_lvmetad is set to 0 to avoid using lvmetad, which is not
# compatible with vdsm shared storage.
#
# preferred_names and filter config values are set to capture Vdsm
# devices.
LVM_CONFIG = """
global {
    locking_type=0
    metadata_read_only=1
    use_lvmetad=0
}
devices {
    preferred_names=[ "^/dev/mapper/" ]
    ignore_suspended_devices=1
    write_cache_state=0
    disable_after_error_count=3
    filter=[ "a|^/dev/mapper/.*|", "r|.*|" ]
}
"""
LVM_CONFIG = re.sub(r"\s+", " ", LVM_CONFIG).strip()


# This is hack for import vdsm modules. because this plugin's name was
# same with vdsm module, so it can not import vdsm modules directly. File name
# should be named as the class and we keep the name for compatability.
def _importVdsmPylibModule(fullName):
    import imp
    from distutils.sysconfig import get_python_lib
    search = get_python_lib(False)
    parts = fullName.split(".")
    fullName = ""
    for name in parts:
        if fullName:
            fullName += "."
        fullName += name
        f, path, desc = imp.find_module(name, [search])
        try:
            module = imp.load_module(fullName, f, path, desc)
        finally:
            if f:
                f.close()
        search = os.path.join(search, name)
    return module

client = _importVdsmPylibModule("vdsm.client")
utils = _importVdsmPylibModule("vdsm.utils")


class vdsm(Plugin, RedHatPlugin):
    """VDSM server related information
    """

    option_list = [("logsize", 'max size (MiB) to collect per log file', '',
                    False),
                   ("dump-volume-chains", 'Collect volume chains info', '',
                    False)]

    # Make compatible com sos version >= 3
    if not hasattr(Plugin, 'addCopySpec'):
        addCopySpec = Plugin.add_copy_spec
        # REQUIRED_FOR sosreport 3.4 replaced add_copy_spec_limit with
        # add_copy_spec
        if hasattr(Plugin, 'add_copy_spec_limit'):
            addCopySpecLimit = Plugin.add_copy_spec_limit
        else:
            addCopySpecLimit = Plugin.add_copy_spec
        collectExtOutput = Plugin.add_cmd_output
        getOption = Plugin.get_option
        addForbiddenPath = Plugin.add_forbidden_path
        addStringAsFile = Plugin.add_string_as_file

    def collectVdsmCommand(self, name, call, **kwargs):
        try:
            result = call(**kwargs)
            self.addStringAsFile(json.dumps(result), name)
        except Exception as e:
            self.addStringAsFile(str(e), name)

    def setup(self):
        self.addForbiddenPath('/etc/pki/vdsm/keys/*')
        self.addForbiddenPath('/etc/pki/vdsm/libvirt-spice/*-key.*')
        self.addForbiddenPath('/etc/pki/libvirt/private/*')

        self.collectExtOutput("service vdsmd status")
        self.addCopySpec("/tmp/vds_installer*")
        self.addCopySpec("/tmp/vds_bootstrap*")
        self.addCopySpec("/etc/vdsm/*")
        logsize = self.getOption('logsize')
        if logsize is not None:
            self.addCopySpecLimit("/var/log/vdsm/*", logsize)
        else:
            self.addCopySpec("/var/log/vdsm/*")
        self._addVdsmRunDir()
        self.addCopySpec("/usr/libexec/vdsm/hooks")  # NOQA: E501 (potentially long line)
        self.addCopySpec("/var/lib/vdsm")  # NOQA: E501 (potentially long line)
        self.addCopySpec("/var/log/ovirt.log")
        self.addCopySpec("/var/log/sanlock.log")
        p = subprocess.Popen(['/usr/bin/pgrep', 'qemu-kvm'],
                             stdout=subprocess.PIPE)
        out, err = p.communicate()
        for line in out.splitlines():
            pid = line.strip()
            self.addCopySpec("/proc/%s/cmdline" % pid)
            self.addCopySpec("/proc/%s/status" % pid)
            self.addCopySpec("/proc/%s/mountstats" % pid)
        self.collectExtOutput("/bin/ls -ldZ /etc/vdsm")
        self.collectExtOutput(
            "/bin/su vdsm -s /bin/sh -c '/usr/bin/tree -l /rhev/data-center'")
        self.collectExtOutput(
            "/bin/su vdsm -s /bin/sh -c '/bin/ls -lR /rhev/data-center'")
        self.collectExtOutput(
            "/sbin/lvm vgs -v -o +tags --config \'%s\'" % LVM_CONFIG)
        self.collectExtOutput(
            "/sbin/lvm lvs -v -o +tags --config \'%s\'" % LVM_CONFIG)
        self.collectExtOutput(
            "/sbin/lvm pvs -v -o +all --config \'%s\'" % LVM_CONFIG)
        self.collectExtOutput("/sbin/fdisk -l")
        self.collectExtOutput("/usr/bin/iostat")
        self.collectExtOutput("/sbin/iscsiadm -m node")
        self.collectExtOutput("/sbin/iscsiadm -m session")
        self.collectExtOutput("/usr/sbin/nodectl info")
        self.collectExtOutput("/usr/bin/abrt-cli list")

        try:
            cli = client.connect('localhost')
        except Exception as e:
            self.addStringAsFile(
                "Cannot connect to vdsm: %s" % e, "client.connect")
            return

        with utils.closing(cli):
            self.collectVdsmCommand(
                "Host.getCapabilities", cli.Host.getCapabilities)
            self.collectVdsmCommand("Host.getStats", cli.Host.getStats)
            self.collectVdsmCommand(
                "Host.getAllVmStats", cli.Host.getAllVmStats)
            self.collectVdsmCommand(
                "Host.getVMFullList", cli.Host.getVMFullList)
            self.collectVdsmCommand(
                "Host.getDeviceList", cli.Host.getDeviceList,
                checkStatus=False)
            self.collectVdsmCommand(
                "Host.hostdevListByCaps", cli.Host.hostdevListByCaps)
            self.collectVdsmCommand(
                "Host.getAllTasksInfo", cli.Host.getAllTasksInfo)
            self.collectVdsmCommand(
                "Host.getAllTasksStatuses", cli.Host.getAllTasksStatuses)

            pools_list = cli.Host.getConnectedStoragePools()
            for pool in pools_list:
                self.collectVdsmCommand(
                    "StoragePool.getSpmStatus " + pool,
                    cli.StoragePool.getSpmStatus,
                    storagepoolID=pool)

            if self.getOption('dump-volume-chains'):
                sd_uuids = cli.Host.getStorageDomains(domainClass=DATA_DOMAIN)
                for sd_uuid in sd_uuids:
                    self.collectExtOutput("vdsm-tool dump-volume-chains %s" %
                                          sd_uuid)

    def _addVdsmRunDir(self):
        """Add everything under /var/run/vdsm except possibly confidential
        sysprep vfds and sockets"""

        import glob

        for f in glob.glob("/var/run/vdsm/*"):  # NOQA: E501 (potentially long line)
            if not f.endswith('.vfd') and not f.endswith('/isoUploader') \
                    and not f.endswith('/storage') \
                    and not stat.S_ISSOCK(os.stat(f).st_mode):
                self.addCopySpec(f)
