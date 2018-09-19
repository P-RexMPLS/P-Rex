_scale = {'kB': 1024.0, 'mB': 1024.0*1024.0,
          'KB': 1024.0, 'MB': 1024.0*1024.0}

def _VmB(VmKey, pid):
    '''Private.
    '''
     # get pseudo file  /proc/<pid>/status
    proc_status = f"'/proc/{pid}/status'"
    try:
        with open(proc_status) as f:
            status = f.read()
    except:
        return 0.0  # non-Linux?
     # get VmKey line e.g. 'VmRSS:  9999  kB\n ...'
    i = status.index(VmKey)
    row = status[i:].split(None, 3)  # whitespace
    if len(row) < 3:
        return 0.0  # invalid format?
     # convert Vm value to bytes
    return float(row[1]) * _scale[row[2]]


def memory(pid):
    '''Return memory usage in bytes.
    '''
    return _VmB('VmSize:', pid)


def resident(pid):
    '''Return resident memory usage in bytes.
    '''
    return _VmB('VmRSS:', pid)


def resident_peak(pid):
    return _VmB('VmHWM', pid)


def stacksize(pid):
    '''Return stack size in bytes.
    '''
    return _VmB('VmStk:', pid)