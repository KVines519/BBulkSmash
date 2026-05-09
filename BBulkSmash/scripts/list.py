import os
import time as _time

def _file_entry(path, name):
    """Return (name, mtime_iso) for a file."""
    try:
        mtime = os.path.getmtime(os.path.join(path, name))
        mtime_str = _time.strftime('%Y-%m-%d %H:%M:%S', _time.localtime(mtime))
    except OSError:
        mtime_str = ''
    return {'name': name, 'mtime': mtime_str}

def list_xml_files(directory):
    try:
        uac_files = []
        uas_files = []
        files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
        for f in files:
            if f.startswith('uac'):
                uac_files.append(_file_entry(directory, f))
            elif f.startswith('uas'):
                uas_files.append(_file_entry(directory, f))
        uac_files.sort(key=lambda x: x['name'])
        uas_files.sort(key=lambda x: x['name'])
        return uac_files, uas_files
    except FileNotFoundError:
        return [], []


def list_pcap_files(directory):
    try:
        files = [_file_entry(directory, f) for f in os.listdir(directory)
                 if f.endswith('.pcap') and os.path.isfile(os.path.join(directory, f))]
        files.sort(key=lambda x: x['name'])
        return files
    except FileNotFoundError:
        return []

def list_csv_files(directory):
    try:
        files = [_file_entry(directory, f) for f in os.listdir(directory)
                 if f.endswith('.csv') and os.path.isfile(os.path.join(directory, f))]
        files.sort(key=lambda x: x['name'])
        return files
    except FileNotFoundError:
        return []

def list_wav_files(directory):
    try:
        files = [_file_entry(directory, f) for f in os.listdir(directory)
                 if f.endswith('.wav') and os.path.isfile(os.path.join(directory, f))]
        files.sort(key=lambda x: x['name'])
        return files
    except FileNotFoundError:
        return []

def list_log_files(directory):
    try:
        files = [_file_entry(directory, f) for f in os.listdir(directory)
                 if (f.endswith('.log') or f.endswith('.csv') or f.endswith('.pcap'))
                 and os.path.isfile(os.path.join(directory, f))]
        files.sort(key=lambda x: x['mtime'], reverse=True)
        return files
    except FileNotFoundError:
        return []
