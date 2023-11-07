# Copyright (c) 2022 Nutanix Inc. All rights reserved.
#
# Author: errol@nutanix.com
""" Utility functions used by wreport checks """


def get_vmvg_info(node_obj, nfs_name):
  """ Returns vm(s) and volume group names
  based on a given vdisk NFS name

  Requires the following node datasets:
    arithmos_vdisks
    vdisk_to_vg
    vm_to_vg
    vm_ls

  Args:
    node_obj: The individual node to be inspected
    nfs_name: vdisk NFS name, i.e. NFS:2:0:120

  Returns a dict (example):
    foo = {'vms':['vm01', 'vm02'], 'vg': 'data_vg01'}

  When foo['vms'] is None, VG is accessed via external iSCSI client
  When foo['vg'] is None, the vdisk is not part of a VG
  """

  vm_info = {'vms':None, 'vg':None}

  # check pre-reqs
  _has_vmls = node_obj.vm_ls is not None
  _has_vgs = all((item in list(node_obj.datasets.keys())
                  for item in ["vdisk_to_vg", "vm_to_vg"]))

  # Check if NFS name is a standard direct-attached vdisk
  if _has_vmls:
    vmname = get_vmname(nfs_name, node_obj.vm_ls)
    if vmname is not None:
      vm_info['vms'] = list()
      vm_info['vms'].append(vmname)
      # if the NFS name is found in the vm_ls dataset, we're done
      return vm_info
  # if we are continuing, we must be dealing with a VG
  vdisk_uuid = get_vdisk_uuid(node_obj, nfs_name)
  if _has_vgs:
    if vdisk_uuid is not None:
      df = node_obj.datasets.vdisk_to_vg.df
      vg_name = df.loc[df['vmdisk_uuid'] == vdisk_uuid, 'vg_name'].values[0]
      vm_info['vg'] = vg_name
      vg_uuid = df.loc[df['vmdisk_uuid'] == vdisk_uuid, 'vg_uuid'].values[0]
      vg_attachment_type = df.loc[df['vmdisk_uuid'] == vdisk_uuid, \
                                     'vg_attachment_type'].values[0]
      del df
    # If this is 'kDirectAttach' we can obtain vm name(s)
    if vg_attachment_type == 'kDirectAttach':
      df = node_obj.datasets.vm_to_vg.df
      vm_uuids = df.loc[df['vg_uuid'] == vg_uuid, 'uuid'].values
      vm_names = get_vmnames(node_obj, vm_uuids)
      vm_info['vms'] = vm_names
      # vm_info['vms'] = [vm for vm in vms]
      del df
  return vm_info

def get_vmnames(node_obj, vmuuid_list):
  """ Returns a list of vm names from vm UUIDs """
  vmnames = []
  if node_obj.vm_ls is not None:
    for vmname in node_obj.vm_ls:
      for uuid in vmuuid_list:
        if node_obj.vm_ls[vmname].uuid == uuid:
          vmnames.append(vmname)
  return vmnames


def get_vdisk_uuid(node_obj, nfs_name):
  """ Returns the vdisk UUID from nfs_name

  Args:
    nfs_name: vdisk NFS name, i.e. NFS:2:0:120
    arithmos_vdisks: the nodes arithmos_vdisks dataset
  """
  vdisk_uuid = None
  if "arithmos_vdisks" in list(node_obj.datasets.keys()):
    df = node_obj.datasets.arithmos_vdisks.df
    if df is not None:
      vdisk_uuid = df.loc[df.nfs_name == nfs_name, \
                          'virtual_disk_uuid'].values[0]
    del df
  return vdisk_uuid


def get_vmname(nfs_name, vmls):
  """ Returns the UVM name that's mapped
  to a specific vdisk NFS name.

  Returns None if the vdisk isn't seen in
  the vmls dataset.

  Args:
    nfs_name: vdisk NFS name, i.e. NFS:2:0:120
    vmls: the nodes vmls dataset data
  """
  vmname = None
  for vm in list(vmls.items()):
    if vm[1].vdisks is not None:
      if nfs_name in vm[1].vdisks:
        vmname = vm[0]
  return vmname
