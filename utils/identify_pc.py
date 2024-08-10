import socket
import uuid
import platform
import subprocess


def get_mac_address():
    # Get the MAC address of the first network interface
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0, 2 * 6, 8)][::-1])
    return mac


def get_system_uuid():
    # Get the system UUID
    if platform.system() == "Windows":
        command = "wmic csproduct get uuid"
        uuid = str(subprocess.check_output(command, shell=True).decode()).split("\n")[1].strip()
    elif platform.system() == "Linux":
        command = "cat /sys/class/dmi/id/product_uuid"
        uuid = str(subprocess.check_output(command, shell=True).decode()).strip()
    else:
        uuid = "UNKNOWN"
    return uuid


def get_hostname():
    # Get the hostname
    return socket.gethostname()
