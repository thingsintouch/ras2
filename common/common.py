from pprint import PrettyPrinter
pPrint = PrettyPrinter(indent=1).pprint

#import time
import subprocess
import os
import time
import socket
import secrets

from hashlib import blake2b

from common.logger import loggerDEBUG, loggerINFO, loggerWARNING, loggerERROR, loggerCRITICAL
# from . import constants as co
#import lib.Utils as ut
from dicts import tz_dic
from common.params import Params
import common.constants as co
from common.keys import keys_by_Type, TxType
from factory_settings.custom_params import factory_settings


params = Params(db=co.PARAMS)

def prettyPrint(message):
    pPrint(message)

def runShellCommand(command):
    try:
        completed = subprocess.run(command.split(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT)
        loggerDEBUG(f'shell command {command} - returncode: {completed.returncode}')
        return completed.returncode
    except:
        loggerERROR(f"error on shell command: {command}")
        return False

def runShellCommand_and_returnOutput(command):
    try:
        completed = subprocess.check_output(command, shell=True)
        #loggerDEBUG(f'shell command {command} - returncode: {completed}')
        return str(completed, 'utf-8', 'ignore')
    except:
        #loggerERROR(f"error on shell command: {command}")
        return False

def setTimeZone(tz = False):
    try:
        if tz:
            timezone = tz
        else:
            timezone = params.get("tz")
        #print(timezone)
        os.environ["TZ"] = timezone
        time.tzset()
        loggerINFO(f"Timezone: {timezone} - was set using tz database")
        return True
    except Exception as e:
        loggerERROR(f"exception in method setTimeZone (using tz database): {e}")
        return False

def getMachineID():
    # Extract serial from cpuinfo file
    try:
        with open('/proc/cpuinfo','r') as f:
            for line in f:
                if 'Serial' in line:
                    machine_id = line[10:26]
    except Exception as e:
        loggerERROR(f"Exception while getting serial number from cpuinfo file : {e}, machine_id gets random id")
        machine_id = secrets.token_hex(16)
    loggerDEBUG(f"machine id (= cpuinfo serial number (or random when there was an Exception)) is {machine_id}")
    return machine_id 

def computeHashedMachineId():
    machine_id = bytes(getMachineID(), encoding='utf8')

    hashed_machine_id = blake2b( \
        machine_id,
        digest_size=co.HASH_DIGEST_SIZE,
        key=co.HASH_KEY,
        salt=co.HASH_SALT,
        person=co.HASH_PERSON_REGISTER_TERMINAL, 
        ).hexdigest()

    return hashed_machine_id

def get_hashed_machine_id():
    hashed_machine_id = params.get('hashed_machine_id')
    if hashed_machine_id is None:
        hashed_machine_id = computeHashedMachineId()
        params.put('hashed_machine_id', hashed_machine_id)
    return hashed_machine_id

def store_factory_settings_in_database():    
    if params.get("odooConnectedAtLeastOnce") != "1":
        keys_to_store = keys_by_Type[TxType.FACTORY_SETTINGS] + \
                        keys_by_Type[TxType.FACTORY_DEFAULT_VALUES]
        # loggerDEBUG(f"keys to store {keys_to_store}")
        # prettyPrint(keys_to_store)
        for k in keys_to_store:
            try:
                loggerDEBUG("-"*80)
                loggerDEBUG(f"key: {k} - stored value in params db: {params.get(k)}")
                loggerDEBUG(f"key: {k} - storing value of factory_settings: {factory_settings[k]}")
                params.put(k, factory_settings[k])
            except Exception as e:
                loggerDEBUG(f"exception while storing factory setting {k}: {e}")

def set_bluetooth_device_name():
    # RASxxx = params.get('RASxxx')
    # if RASxxx is None or RASxxx == "not defined":
    #     bluetooth_device_name = "RAS - thingsintouch.com"
    # else:
    #     bluetooth_device_name = RASxxx
    bluetooth_device_name = "RAS - thingsintouch.com" # have to change ionic app
    params.put("bluetooth_device_name", bluetooth_device_name)

def get_own_IP_address():
    st = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:       
        st.connect(('10.255.255.255', 1))
        IP = st.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        st.close()
    params.put("ip", IP)
    return IP

def isIpPortOpen(ipPort): # you can not ping ports, you have to use connect_ex for ports
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(2)
        canConnectResult = s.connect_ex(ipPort)
        if canConnectResult == 0:
            #print("Utils - IP Port OPEN ", ipPort)
            isOpen = True
        else:
            #print("Utils - IP Port CLOSED ", ipPort)
            isOpen = False
    except Exception as e:
        loggerERROR(f"Utils - exception in method isIpPortOpen: {e}")
        isOpen = False
    finally:
        s.close()
    return isOpen

def ensure_git_does_not_change_env_file():
    try:
        #runShellCommand("cd /home/pi/ras")
        runShellCommand("sudo git update-index --skip-worktree .env")
    except Exception as e:
        loggerDEBUG(f"ensure_git_does_not_change_env_file -- Exception: {e}")

def get_period(period_name):
    try:
        n = params.get(period_name)
        default = co.DEFAULT_MINIMUM_PERIOD
        if n is None:
            period = default
        elif n:
            period = int(n)
            if period < default:
                period = default
        else:
            period = default
    except Exception as e:
        loggerDEBUG(f"exception in  get_period for {period_name}: {e} - period set to 14s")
        period = 14     
    return period

def BLOCKING_waiting_until_RAS_acknowledged_from_Odoo():
    while params.get("acknowledged") != "1":
        time.sleep(16) # waiting_to_be_acknowledged
