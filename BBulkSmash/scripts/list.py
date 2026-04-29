import os

def list_xml_files(directory):
    try:
        uac_files = []
        uas_files = []
        
        files = [file for file in os.listdir(directory)]
        
        for file in files:
            if file.startswith('uac'):
                uac_files.append(file)
            elif file.startswith('uas'):
                uas_files.append(file)
        
        # Sort the lists of files
        uac_files.sort()
        uas_files.sort()
        
        return uac_files, uas_files
    except FileNotFoundError:
        return "Directory not found.", "Directory not found."


def list_pcap_files(directory):
    try:
        pcap_files = []
        files = [file for file in os.listdir(directory)]  
        for file in files:
            if file.endswith('.pcap'):
                pcap_files.append(file)     
        # Sort the list of pcap files
        pcap_files.sort()
        
        return pcap_files
    except FileNotFoundError:
        return "Directory not found."
    
def list_csv_files(directory):
    try:
        csv_files = []      
        files = [file for file in os.listdir(directory)]
        for file in files:
            if file.endswith('.csv'):
                csv_files.append(file)
        # Sort the list of csv files
        csv_files.sort()
        
        return csv_files
    except FileNotFoundError:
        return "Directory not found."
    
def list_wav_files(directory):
    try:
        wav_files = []      
        files = [file for file in os.listdir(directory)]
        for file in files:
            if file.endswith('.wav'):
                wav_files.append(file)
        # Sort the list of wav files
        wav_files.sort()
        
        return wav_files
    except FileNotFoundError:
        return "Directory not found."

def list_log_files(directory):
    try:
        log_files = []
        for file in os.listdir(directory):
            if file.endswith('.log'):
                log_files.append(file)
        log_files.sort(reverse=True)  # newest first (alphabetically by timestamp prefix)
        return log_files
    except FileNotFoundError:
        return []
