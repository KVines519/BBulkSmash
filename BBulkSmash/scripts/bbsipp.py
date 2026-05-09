from django.conf import settings
import os, shlex, socket, time, datetime
from pathlib import Path
import subprocess, threading
from .bbstun import get_ip_info
from .modify import tmp_xml_behind_nat, modify_number_xml_path
import psutil, re
import logging

logger = logging.getLogger(__name__)

sipp = str(settings.BASE_DIR / 'BBulkSmash' / 'sipp')

# Track tcpdump processes keyed by SIPp PID (thread-safe)
_tcpdump_procs = {}
_tcpdump_lock = threading.Lock()

# Regex patterns as constants to avoid tool corruption of $ anchors
_SAFE_HOSTNAME_RE = re.compile(r'^[a-zA-Z0-9.\-]+' + r'$')
_PID_LOG_RE = re.compile(r'\.xml_\d+\.log' + r'$')

######## Trace flag helpers

def _build_trace_flags(trace_flags):
    """Return a string of SIPp trace flags from a dict or AppSettings instance.
    Note: pre_run_delay is handled as a Python sleep before Popen, not a SIPp flag.
    """
    if trace_flags is None:
        return ''
    parts = []
    if getattr(trace_flags, 'trace_stat',   False) or (isinstance(trace_flags, dict) and trace_flags.get('trace_stat')):
        parts.append('-trace_stat')
    if getattr(trace_flags, 'trace_msg',    False) or (isinstance(trace_flags, dict) and trace_flags.get('trace_msg')):
        parts.append('-trace_msg')
    if getattr(trace_flags, 'trace_counts', False) or (isinstance(trace_flags, dict) and trace_flags.get('trace_counts')):
        parts.append('-trace_counts')
    if getattr(trace_flags, 'trace_err', False) or (isinstance(trace_flags, dict) and trace_flags.get('trace_err')):
        parts.append('-trace_err')
    return (' ' + ' '.join(parts)) if parts else ''


######## tcpdump capture helpers

def start_tcpdump(sipp_pid, xml_name, local_ip, local_port, remote_port,
                  min_rtp_port=None, max_rtp_port=None, stun_server=None):
    """Start a tcpdump capture alongside a SIPp process.

    Args:
        sipp_pid: PID of the SIPp process (used in pcap filename and tracking)
        xml_name: XML scenario filename (used in pcap filename)
        local_ip: SIPp local IP address for BPF host filter
        local_port: SIPp local SIP port
        remote_port: SIPp remote SIP port
        min_rtp_port: If set (with max_rtp_port), include RTP portrange in BPF
        max_rtp_port: Upper bound of RTP port range
        stun_server: If set, include STUN traffic (host <stun_server>) in capture
    """
    logs_dir = str(settings.BASE_DIR / 'logs')
    pcap_file = os.path.join(logs_dir, f"{xml_name}_{sipp_pid}.pcap")

    # Build BPF filter: host <local_ip> and (port X or port Y [or portrange M-N])
    ports = sorted(set([int(local_port), int(remote_port)]))
    port_terms = " or ".join(f"port {p}" for p in ports)
    if min_rtp_port and max_rtp_port:
        sip_rtp_filter = f"host {local_ip} and ({port_terms} or portrange {int(min_rtp_port)}-{int(max_rtp_port)})"
    else:
        sip_rtp_filter = f"host {local_ip} and ({port_terms})"

    # Include STUN traffic if a STUN server is configured
    if stun_server:
        # Validate stun_server is a safe hostname/IP (defense-in-depth)
        if not _SAFE_HOSTNAME_RE.match(stun_server):
            logger.warning(f"Invalid stun_server value rejected: {stun_server!r}")
            stun_server = None
    if stun_server:
        bpf = f"({sip_rtp_filter}) or host {stun_server}"
    else:
        bpf = sip_rtp_filter

    cmd = ["tcpdump", "-i", "any", "-s", "0", "-w", pcap_file, bpf]
    logger.info(f"Starting tcpdump for SIPp PID {sipp_pid}: {' '.join(cmd)}")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        with _tcpdump_lock:
            _tcpdump_procs[sipp_pid] = proc
        logger.info(f"tcpdump started: pid={proc.pid}, pcap={pcap_file}")
    except Exception as e:
        logger.error(f"Failed to start tcpdump for SIPp PID {sipp_pid}: {e}")


def stop_tcpdump(sipp_pid):
    """Stop the tcpdump process associated with a SIPp PID."""
    with _tcpdump_lock:
        proc = _tcpdump_procs.pop(sipp_pid, None)
    if proc is None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=5)
        logger.info(f"tcpdump (pid={proc.pid}) stopped for SIPp PID {sipp_pid}")
    except subprocess.TimeoutExpired:
        proc.kill()
        logger.warning(f"tcpdump (pid={proc.pid}) killed after timeout for SIPp PID {sipp_pid}")
    except Exception as e:
        logger.error(f"Error stopping tcpdump for SIPp PID {sipp_pid}: {e}")


######## For behind NAT sipp
def stun4nat(xmlName, srcPort, stunServer):
    stun_host_str = ''.join(stunServer)
    nat_type, external_ip, external_port = get_ip_info(stun_host=stun_host_str, source_port=int(srcPort))
    if external_ip is not None and external_port is not None:
        newXmlPath = tmp_xml_behind_nat(xmlName, external_ip, external_port)
    else:
        return None
    return newXmlPath


# get free udp port for controlling sipp through -cp
def get_free_control_port(start=8888, end=8948):
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free UDP port available")


def run_sipp_in_background(command, output_file):
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        cport = get_free_control_port()
        args = shlex.split(command)
        args.extend(["-cp", str(cport)])
        # Run from logs dir so SIGUSR2 screen logs and trace files land there
        process = subprocess.Popen(args, stdout=f, stderr=subprocess.STDOUT,
                                   cwd=str(settings.BASE_DIR / 'logs'))
    # Rename the stdout log to include the PID now that we have it
    pid_output_file = output_file.replace('.log', f'_{process.pid}.log')
    try:
        os.rename(output_file, pid_output_file)
        process._bbulksmash_log = pid_output_file
    except OSError:
        process._bbulksmash_log = output_file
    return process


def build_uac_command(uac_config, trace_flags=None):
    """Build and return the SIPp command string for a UAC config without running it."""
    uacXml = uac_config.select_uac
    uacLocalPort = int(uac_config.uac_local_port)
    uacRemotePort = int(uac_config.uac_remote_port)
    uacProtocol = uac_config.uac_protocol
    noOfCalls = int(uac_config.total_no_of_calls)
    cps = int(uac_config.cps)
    maxCcl = int(uac_config.max_ccl)
    minRtpPort = int(uac_config.min_rtp_port)
    maxRtpPort = int(uac_config.max_rtp_port)
    csvFile = uac_config.csv_inf
    uacRemote = f"{uac_config.uac_remote}:{uacRemotePort}"
    uacLocal = f"-i {uac_config.uac_local} -p {uacLocalPort}"
    trace_str = _build_trace_flags(trace_flags)
    delay = getattr(trace_flags, 'pre_run_delay', 0) if trace_flags else 0
    delay_note = f"  [+{delay}s pre-run delay]" if delay else ""
    aa_str = " -aa" if uac_config.auto_accept_options else ""

    if csvFile:
        return f"./sipp -sf {uacXml} {uacRemote} {uacLocal} -m {noOfCalls} -r {cps} -l {maxCcl} -t {uacProtocol} -min_rtp_port {minRtpPort} -max_rtp_port {maxRtpPort} -inf {csvFile}{aa_str}{trace_str}{delay_note}"
    else:
        return f"./sipp -sf {uacXml} {uacRemote} {uacLocal} -m {noOfCalls} -r {cps} -l {maxCcl} -t {uacProtocol} -min_rtp_port {minRtpPort} -max_rtp_port {maxRtpPort}{aa_str}{trace_str}{delay_note}"


def build_uas_command(uas_config, trace_flags=None):
    """Build and return the SIPp command string for a UAS config without running it."""
    uasXml = uas_config.select_uas
    uasLocalPort = int(uas_config.uas_local_port)
    uasRemotePort = int(uas_config.uas_remote_port)
    uasProtocol = uas_config.uas_protocol
    cps = int(uas_config.cps)
    maxCcl = int(uas_config.max_ccl)
    minRtpPort = int(uas_config.min_rtp_port)
    maxRtpPort = int(uas_config.max_rtp_port)
    csvFile = uas_config.csv_inf
    uasRemote = f"{uas_config.uas_remote}:{uasRemotePort}"
    uasLocal = f"-i {uas_config.uas_local} -p {uasLocalPort}"
    trace_str = _build_trace_flags(trace_flags)
    delay = getattr(trace_flags, 'pre_run_delay', 0) if trace_flags else 0
    delay_note = f"  [+{delay}s pre-run delay]" if delay else ""
    aa_str = " -aa" if uas_config.auto_accept_options else ""

    if csvFile:
        return f"./sipp -sf {uasXml} {uasRemote} {uasLocal} -r {cps} -l {maxCcl} -t {uasProtocol} -min_rtp_port {minRtpPort} -max_rtp_port {maxRtpPort} -rxinf {csvFile}{aa_str}{trace_str}{delay_note}"
    else:
        return f"./sipp -sf {uasXml} {uasRemote} {uasLocal} -r {cps} -l {maxCcl} -t {uasProtocol} -min_rtp_port {minRtpPort} -max_rtp_port {maxRtpPort}{aa_str}{trace_str}{delay_note}"


def run_uac(uac_config):
    from BBulkSmash.models import AppSettings
    trace = AppSettings.get()
    uacXml = uac_config.select_uac
    uacLocalPort = int(uac_config.uac_local_port)
    uacRemotePort = int(uac_config.uac_remote_port)
    uacProtocol = uac_config.uac_protocol
    noOfCalls = int(uac_config.total_no_of_calls)
    cps = int(uac_config.cps)
    maxCcl = int(uac_config.max_ccl)
    calledParty = uac_config.called_party
    callingParty = uac_config.calling_party
    minRtpPort = int(uac_config.min_rtp_port)
    maxRtpPort = int(uac_config.max_rtp_port)
    stunServer = uac_config.stun_server
    uacXmlPath = str(settings.BASE_DIR / 'BBulkSmash' / 'xml' / uacXml)
    uacRemote = f"{uac_config.uac_remote}:{uacRemotePort}"
    uacLocal = f"-i {uac_config.uac_local} -p {uacLocalPort}"
    csvFile = uac_config.csv_inf
    trace_str = _build_trace_flags(trace)
    aa_str = " -aa" if uac_config.auto_accept_options else ""

    try:
        if stunServer and any(stunServer):
            stunnedPath = stun4nat(uacXml, uacLocalPort, stunServer)
            if stunnedPath is not None:
                uacXmlPath = stunnedPath
            else:
                sipp_error = f'Stun server at {stunServer} is not responding! Remove in "More Options" if not needed.'
                logger.error(sipp_error)
                return sipp_error

        if calledParty or callingParty:
            uacXmlPath = modify_number_xml_path(uacXmlPath, callingParty, calledParty)

        if csvFile:
            csv_path = Path(settings.BASE_DIR) / 'BBulkSmash' / 'xml' / 'csv' / csvFile
            uacCommand = f"{sipp} -sf {uacXmlPath} {uacRemote} {uacLocal} -m {noOfCalls} -r {cps} -l {maxCcl} -t {uacProtocol} -min_rtp_port {minRtpPort} -max_rtp_port {maxRtpPort} -inf {csv_path}{aa_str}{trace_str}"
        else:
            uacCommand = f"{sipp} -sf {uacXmlPath} {uacRemote} {uacLocal} -m {noOfCalls} -r {cps} -l {maxCcl} -t {uacProtocol} -min_rtp_port {minRtpPort} -max_rtp_port {maxRtpPort}{aa_str}{trace_str}"

        outputFile = str(settings.BASE_DIR / 'logs' / f'{uacXml}.log')
        pre_delay = int(trace.pre_run_delay) if trace.pre_run_delay else 0
        if pre_delay:
            logger.info(f"Pre-run delay: sleeping {pre_delay}s before launching UAC")
            time.sleep(pre_delay)
        uacProc = run_sipp_in_background(uacCommand, outputFile)
        time.sleep(0.4)
        # Check if Process has immediately exited
        return_code = uacProc.poll()
        logger.info(f"SIPp UAC launched: pid={uacProc.pid}, return_code={return_code}, cmd={uacCommand}")

        if return_code != 0 and return_code is not None:
            actual_log = getattr(uacProc, '_bbulksmash_log', outputFile)
            with open(actual_log, 'r') as file:
                sipp_error = ''.join(file.readlines())
                logger.error(sipp_error)
                return sipp_error

        # Start tcpdump capture if enabled
        if return_code is None:  # SIPp is still running
            stun = stunServer if stunServer and any(stunServer) else None
            if trace.capture_sip_rtp:
                start_tcpdump(uacProc.pid, uacXml, uac_config.uac_local,
                              uacLocalPort, uacRemotePort, minRtpPort, maxRtpPort,
                              stun_server=stun)
            elif trace.capture_sip:
                start_tcpdump(uacProc.pid, uacXml, uac_config.uac_local,
                              uacLocalPort, uacRemotePort, stun_server=stun)

    except Exception as e:
        sipp_error = f"Error: {e}"
        logger.exception('Exception occurred while trying to run sipp')
        return sipp_error


def run_uas(uas_config):
    from BBulkSmash.models import AppSettings
    trace = AppSettings.get()
    uasXml = uas_config.select_uas
    uasLocalPort = int(uas_config.uas_local_port)
    uasRemotePort = int(uas_config.uas_remote_port)
    uasProtocol = uas_config.uas_protocol
    cps = int(uas_config.cps)
    maxCcl = int(uas_config.max_ccl)
    uasXmlPath = str(settings.BASE_DIR / 'BBulkSmash' / 'xml' / uasXml)
    uasRemote = f"{uas_config.uas_remote}:{uasRemotePort}"
    uasLocal = f"-i {uas_config.uas_local} -p {uasLocalPort}"
    minRtpPort = int(uas_config.min_rtp_port)
    maxRtpPort = int(uas_config.max_rtp_port)
    csvFile = uas_config.csv_inf
    trace_str = _build_trace_flags(trace)
    aa_str = " -aa" if uas_config.auto_accept_options else ""

    try:
        if csvFile:
            csv_path = Path(settings.BASE_DIR) / 'BBulkSmash' / 'xml' / 'csv' / csvFile
            uasCommand = f"{sipp} -sf {uasXmlPath} {uasRemote} {uasLocal} -r {cps} -l {maxCcl} -t {uasProtocol} -min_rtp_port {minRtpPort} -max_rtp_port {maxRtpPort} -rxinf {csv_path}{aa_str}{trace_str}"
        else:
            uasCommand = f"{sipp} -sf {uasXmlPath} {uasRemote} {uasLocal} -r {cps} -l {maxCcl} -t {uasProtocol} -min_rtp_port {minRtpPort} -max_rtp_port {maxRtpPort}{aa_str}{trace_str}"

        outputFile = str(settings.BASE_DIR / 'logs' / f'{uasXml}.log')
        pre_delay = int(trace.pre_run_delay) if trace.pre_run_delay else 0
        if pre_delay:
            logger.info(f"Pre-run delay: sleeping {pre_delay}s before launching UAS")
            time.sleep(pre_delay)
        uasProc = run_sipp_in_background(uasCommand, outputFile)
        time.sleep(0.4)
        # Check if Process has immediately exited
        return_code = uasProc.poll()
        if return_code != 0 and return_code is not None:
            actual_log = getattr(uasProc, '_bbulksmash_log', outputFile)
            with open(actual_log, 'r') as file:
                sipp_error = ''.join(file.readlines())
                return sipp_error

        # Start tcpdump capture if enabled
        if return_code is None:  # SIPp is still running
            if trace.capture_sip_rtp:
                start_tcpdump(uasProc.pid, uasXml, uas_config.uas_local,
                              uasLocalPort, uasRemotePort, minRtpPort, maxRtpPort)
            elif trace.capture_sip:
                start_tcpdump(uasProc.pid, uasXml, uas_config.uas_local,
                              uasLocalPort, uasRemotePort)

    except Exception as e:
        sipp_error = f"Error: {e}"
        logger.exception('Exception occurred while trying to run sipp')
        return sipp_error


def is_sipp_pid(pid: int) -> bool:
    """Return True if `pid` belongs to a known SIPp process managed by BBulkSmash."""
    known = get_sipp_processes()
    return any(p['pid'] == pid for p in known)


def get_sipp_processes():
    sipp_processes = []
    sipp_pattern = r"sipp"
    shell_name = r"\b(bash|sh)\b"

    for process in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline_list = process.info['cmdline']
            if not cmdline_list:
                continue
            cmdline = ' '.join(cmdline_list)
            if not re.search(sipp_pattern, cmdline):
                continue
            if re.search(shell_name, cmdline):
                continue

            logger.info(f"Found SIPp process PID {process.info['pid']}: {cmdline[:200]}")
            cmdraw = cmdline_list
            arguments = ' '.join(
                os.path.basename(arg) if os.path.isabs(arg) else arg
                for arg in cmdraw[1:]
            )

            script_name = None
            control_port = None
            mcalls = False

            for i, arg in enumerate(cmdraw):
                if arg == "-sf" and i + 1 < len(cmdraw):
                    script_name = os.path.basename(cmdraw[i + 1])
                if arg == "-cp" and i + 1 < len(cmdraw):
                    control_port = cmdraw[i + 1]
                if arg == "-m" and i + 1 < len(cmdraw):
                    try:
                        mcalls = int(cmdraw[i + 1])
                    except (ValueError, IndexError):
                        mcalls = False

            sipp_processes.append({
                'pid': process.info['pid'],
                'command_line': f"./sipp {arguments}",
                'script_name': script_name,
                'cport': control_port,
                'mcalls': mcalls,
            })

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    logger.info(f"get_sipp_processes found {len(sipp_processes)} process(es)")
    return sorted(sipp_processes, key=lambda x: x['pid'], reverse=True)


def clean_filename(filename):
    # Replace spaces with underscores
    cleaned_filename = filename.replace(' ', '_')
    # Remove any characters that are not alphanumeric, underscores, hyphens, or periods
    cleaned_filename = re.sub(r'[^\w\-\.]', '', cleaned_filename)
    return cleaned_filename


def delete_old_screen_logs(directory):
    # Calculate the threshold for 1 hour ago
    hours_old = 1
    threshold = datetime.datetime.now() - datetime.timedelta(hours=hours_old)

    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)

        # Check if it's a file matching screen logs or PID-suffixed stdout logs
        if os.path.isfile(filepath) and (
            filename.endswith("screen.log")
            or filename.endswith("xml.log")
            or _PID_LOG_RE.search(filename)
        ):
            try:
                modification_time = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
                if modification_time < threshold:
                    os.remove(filepath)
                    logger.info(f"Deleted: {filepath}")
                else:
                    logger.debug(f"Not Deleted: {filepath}")
            except OSError as e:
                logger.exception(f"Error Deleting {filepath}: {e}")
