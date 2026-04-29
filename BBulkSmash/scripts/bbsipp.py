from django.conf import settings
import os, shlex, socket, time, datetime
from pathlib import Path
import subprocess
from .bbstun import get_ip_info
from .modify import tmp_xml_behind_nat, modify_number_xml_path
import psutil, re
import logging

logger = logging.getLogger(__name__)

sipp = str(settings.BASE_DIR / 'BBulkSmash' / 'sipp')

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
    with open(output_file, 'w') as f:
        cport = get_free_control_port()
        args = shlex.split(command)
        args.extend(["-cp", str(cport)])
        process = subprocess.Popen(args, stdout=f, stderr=subprocess.STDOUT)
    return process


def build_uac_command(uac_config):
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

    if csvFile:
        return f"./sipp -sf {uacXml} {uacRemote} {uacLocal} -m {noOfCalls} -r {cps} -l {maxCcl} -t {uacProtocol} -min_rtp_port {minRtpPort} -max_rtp_port {maxRtpPort} -inf {csvFile}"
    else:
        return f"./sipp -sf {uacXml} {uacRemote} {uacLocal} -m {noOfCalls} -r {cps} -l {maxCcl} -t {uacProtocol} -min_rtp_port {minRtpPort} -max_rtp_port {maxRtpPort}"


def build_uas_command(uas_config):
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

    if csvFile:
        return f"./sipp -sf {uasXml} {uasRemote} {uasLocal} -r {cps} -l {maxCcl} -t {uasProtocol} -min_rtp_port {minRtpPort} -max_rtp_port {maxRtpPort} -rxinf {csvFile}"
    else:
        return f"./sipp -sf {uasXml} {uasRemote} {uasLocal} -r {cps} -l {maxCcl} -t {uasProtocol} -min_rtp_port {minRtpPort} -max_rtp_port {maxRtpPort}"


def run_uac(uac_config):
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

    try:
        if any(stunServer):
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
            uacCommand = f"{sipp} -sf {uacXmlPath} {uacRemote} {uacLocal} -m {noOfCalls} -r {cps} -l {maxCcl} -t {uacProtocol} -min_rtp_port {minRtpPort} -max_rtp_port {maxRtpPort} -inf {csv_path}"
        else:
            uacCommand = f"{sipp} -sf {uacXmlPath} {uacRemote} {uacLocal} -m {noOfCalls} -r {cps} -l {maxCcl} -t {uacProtocol} -min_rtp_port {minRtpPort} -max_rtp_port {maxRtpPort}"

        outputFile = str(settings.BASE_DIR / 'logs' / f'{uacXml}.log')
        uacProc = run_sipp_in_background(uacCommand, outputFile)
        time.sleep(0.4)
        # Check if Process has immediately exited
        return_code = uacProc.poll()

        if return_code != 0 and return_code != None:
            with open(outputFile, 'r') as file:
                lines = file.readlines()
                # last_lines = lines[-18:]
                sipp_error = ''.join(lines)
                logger.error(sipp_error)
                return sipp_error

    except Exception as e:
        sipp_error = f"Error: {e}"
        logger.exception('Exception occurred while trying to run sipp')
        return sipp_error


def run_uas(uas_config):
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

    try:
        if csvFile:
            csv_path = Path(settings.BASE_DIR) / 'BBulkSmash' / 'xml' / 'csv' / csvFile
            uasCommand = f"{sipp} -sf {uasXmlPath} {uasRemote} {uasLocal} -r {cps} -l {maxCcl} -t {uasProtocol} -min_rtp_port {minRtpPort} -max_rtp_port {maxRtpPort} -rxinf {csv_path}"
        else:
            uasCommand = f"{sipp} -sf {uasXmlPath} {uasRemote} {uasLocal} -r {cps} -l {maxCcl} -t {uasProtocol} -min_rtp_port {minRtpPort} -max_rtp_port {maxRtpPort}"


        outputFile = str(settings.BASE_DIR / 'logs' / f'{uasXml}.log')
        uasProc=run_sipp_in_background(uasCommand, outputFile)
        time.sleep(0.4)
        # Check if Process has immediately exited
        return_code = uasProc.poll()
        if return_code != 0 and return_code != None:
            with open(outputFile, 'r') as file:
                lines = file.readlines()
                # Extract the last 'num_lines' lines from the list
                # last_lines = lines[-14:]
                sipp_error = ''.join(lines)
                return sipp_error
            
    except Exception as e:
        sipp_error = f"Error: {e}"
        logger.exception('Exception occurred while trying to run sipp')
        return sipp_error


############ function to get running Sipp Process ######################################
def get_sipp_processes():
    sipp_processes = []
    sipp_pattern = r"sipp"  # Regular expression to match "sipp" in the command-line
    shell_name = r"(bash|sh)"  # Regular expression to match shell names

    script_name = None
    control_port = None
    mcalls = False

    for process in psutil.process_iter(['pid', 'cmdline']):
        if process.info['cmdline']:
            cmdline = ' '.join(process.info['cmdline'])
            cmdraw = process.info['cmdline']
            if re.search(sipp_pattern, cmdline) and not re.search(shell_name, cmdline):
                arguments = ' '.join(os.path.basename(arg) if os.path.isabs(arg) else arg for arg in process.info['cmdline'][1:])
                # Reset per-process values
                script_name = None
                control_port = None
                mcalls = False
                # Look for -sf and -cp arguments
                for i, arg in enumerate(cmdraw):
                    if arg == "-sf" and i + 1 < len(cmdraw):
                        script_name = os.path.basename(cmdraw[i + 1])
                    if arg == "-cp" and i + 1 < len(cmdraw):
                        control_port = cmdraw[i + 1]
                    if arg == "-m" and i + 1 < len(cmdraw):
                        mcalls = int(cmdraw[i + 1])

                sipp_processes.append({
                    'pid': process.info['pid'],
                    'command_line': f"./sipp {arguments}",
                    'script_name' : script_name,
                    'cport' : control_port,
                    'mcalls' : mcalls,
                })

    sorted_sipp_processes = sorted(sipp_processes, key=lambda x: x['pid'], reverse=True)
    return sorted_sipp_processes

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

        # Check if it's a file and ends with the specified suffix
        if os.path.isfile(filepath) and (filename.endswith("screen.log") or filename.endswith("xml.log")):
            try:
                modification_time = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))

                if modification_time < threshold:
                    os.remove(filepath)
                    logger.info(f"Deleted: {filepath}")
                else:
                    logger.debug(f"Not Deleted: {filepath}")

            except OSError as e:
                logger.exception(f"Error Deleting {filepath}: {e}")

