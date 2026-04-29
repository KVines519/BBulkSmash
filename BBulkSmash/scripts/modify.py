import os
import re
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def tmp_xml_behind_nat(xml, externalIp, externalPort):
    xmlPath = str(settings.BASE_DIR / 'BBulkSmash' / 'xml' / xml)
    with open(xmlPath, 'r') as file:
        xml_content = file.read()
    
    replaceExtIp = xml_content.replace('[local_ip]', externalIp)

    if xml.startswith("uac"):
        modifiedXML = replaceExtIp.replace('[local_port]',str(externalPort))
        # newXml = 'uac.xml'
    else: 
        modifiedXML = replaceExtIp #Not changing the NAT port for UAS 
        # newXml = 'uas.xml'
    tmpXmlPath = str(settings.BASE_DIR / 'BBulkSmash' / 'xml' / 'tmp' / xml)

    with open(tmpXmlPath, 'w') as file:
        file.write(modifiedXML)
        
    return tmpXmlPath


# code for modifying Calling or Called Party

def modify_number_xml_path(xmlPath, calling_party, called_party):

    with open(xmlPath, 'r') as file:
        xml_content = file.read()
    
    logger.info("Modifying numbers in: %s", xmlPath)
    logger.info(f'CallingParty = {calling_party} and CalledParty = {called_party}')

    if calling_party:
        calling_display=f'"{calling_party}" '

        from_pattern = r'(?i)\bFrom\b\:\s*"?(\w*)"?\s*(<?sip:)([^@\:\;\n]+)@'
        xml_content = re.sub(from_pattern, lambda m: f'From: {calling_display if m.group(1) else ""}{m.group(2)}{calling_party}@', xml_content)

        contact_pattern = r'(?i)\bContact\b\:\s*"?(\w*)"?\s*(<?sip:)([^@\:\;\n]+)@'
        xml_content = re.sub(contact_pattern, lambda m: f'Contact: {calling_display if m.group(1) else ""}{m.group(2)}{calling_party}@', xml_content)

    if called_party:
        called_display=f'"{called_party}" '

        ruri_pattern = r'(INVITE|ACK|BYE|CANCEL|OPTIONS|REGISTER)\s*sip:([^@\:\;\n]+)@'
        xml_content = re.sub(ruri_pattern, r'\1 sip:'+ called_party +'@', xml_content)

        to_pattern = r'(?i)\bTo\b\:\s*(\[|"?)(\w*)(\]|"?)\s*(<?sip:)([^@\:\;\n]+)@'
        xml_content = re.sub(to_pattern, lambda m: f'To: {called_display if m.group(2) else ""}{m.group(4)}{called_party}@', xml_content)
    
    xmlName = os.path.basename(xmlPath)
    tmpDir = str(settings.BASE_DIR / 'BBulkSmash' / 'xml' / 'tmp' )

    if not os.path.exists(tmpDir):
        os.makedirs(tmpDir, exist_ok=True)
        logger.warning(f"Temporary directory '{tmpDir}' did not exist. Created now.")

    tmpXmlPath = os.path.join (tmpDir, xmlName)
     
    with open(tmpXmlPath, 'w') as file:
        file.write(xml_content)

    logger.info("Updated XML Path %s", tmpXmlPath)    
    return tmpXmlPath
