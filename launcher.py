#! /usr/bin/python3.7

import os, sys, time 
import importlib
from multiprocessing import Process, Manager

from typing import Dict, List
import flask
import zmq
from colorama import Fore as cf
# Fore: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
# Back: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
# Style: DIM, NORMAL, BRIGHT, RESET_ALL

from common import constants as co
from common.params import Params
from common.launcher import launcher
from common.logger import loggerDEBUG, loggerINFO, loggerWARNING, loggerERROR, loggerCRITICAL
from messaging.messaging import SubscriberMultipart as Subscriber
from common.common import setTimeZone, store_hashed_machine_id, store_factory_settings_in_database
from common.common import set_bluetooth_device_name, ensure_git_does_not_change_env_file
from common.common import runShellCommand_and_returnOutput as rs

import lib.Utils as ut

params = Params(db=co.PARAMS)

params.put("acknowledged", "0") # terminal is NOT acknowledged at the beginning
store_factory_settings_in_database()
setTimeZone()

loggerINFO("###################### RAS launched ###################")
# loggerINFO(f'running on python version: {sys.version}')

store_hashed_machine_id()
set_bluetooth_device_name()
params.put("firmwareVersion",co.RAS_VERSION)
ensure_git_does_not_change_env_file()

configured_odoo_local = False
try:
    if params.get("configuredOdooLocal") == "1":
        configured_odoo_local = True
except Exception as e:
    print(f"parameter configuredOdooLocal not defined: {e}")

if co.ODOO_SERVER_LOCAL == 'True':
    odoo_url_local_template = co.ODOO_SCHEME_LOCAL+"://"+ co.ODOO_HOST_LOCAL + ":" + co.ODOO_PORT_LOCAL
    params.put("odooUrlTemplate",odoo_url_local_template)
    params.put("odoo_host",co.ODOO_HOST_LOCAL)
    params.put("odoo_port",co.ODOO_PORT_LOCAL)
    if not configured_odoo_local:
        ssidName = co.SSID_NAME
        ssidPassword = co.SSID_PASSWORD
        if " " in ssidName:
            ssidName = "'" + ssidName + "'"
        try:
            answer = (rs('sudo nmcli dev wifi con '+ssidName+' password '+ssidPassword))
        except Exception as e:
            print(f"could not setup ssid : {ssidName}, error: {e}")    
        try:
            answer = (rs('sudo nmcli connection modify "Wired connection 1" ipv4.method "manual" ipv4.addresses "192.168.10.167/24"'))
        except Exception as e:
            print(f"could not change (Wired) Ethernet IP Address to 167: {e}")    
        try:
            answer = (rs('sudo nmcli connection modify '+ssidName+ ' ipv4.method "manual" ipv4.addresses "192.168.10.168/24"'))
        except Exception as e:
            print(f"could not change wiFi IP Address to 168: {e}")
        try:
            params.put("configuredOdooLocal", "1")
        except Exception as e:
            print(f"could not change parameter configuredOdooLocal: {e}")       
        answer = (rs('sudo systemctl restart NetworkManager')
        print("-----############### SHUTDOWN ###############------")
        os.system("sudo shutdown now")
        time.sleep(60)
        sys.exit(0)


managed_essential_processes = { # key(=process name) : (pythonmodule where the process is defined (= process name))
    "thermal_d": "thermal.manager",
    "display_d": "display.manager",
    "clock_d": "clock.manager",
    "reader_d": "reader.manager",
    "odoo_routine_check_d": "odooRoutineCheck.manager",
    "bluetooth_d": "bluetooth.server",
    "odoo_d": "odoo.manager",
    "state_d": "state.manager",
    "buzzer_d": "buzzer.manager",
    "odoo_register_clockings_d": "odooRegisterClockings.manager"
    #"RAS_d": "oldLauncher"
}

managed_NON_essential_processes = {}
daemon_processes = {}
running: Dict[str, Process] = {}

managed_processes = {
    **managed_essential_processes,
    **managed_NON_essential_processes
    }

def start_managed_process(name):
    if name not in running and name in managed_processes:
        preimport_managed_process(name)
        process = managed_processes[name]
        loggerINFO(f"starting python process {process}")
        running[name] = Process(name=name, target=launcher, args=(process,))
        running[name].start()

def start_daemon_process(name):
    pass

def start_all_daemon_processes():
    pass

def terminate_managed_process(name):
    loggerINFO(f"terminating python process {process}")
    pass

def preimport_managed_process(name):
    module = managed_processes[name]
    loggerDEBUG(f"preimporting {module}")
    importlib.import_module(module)

def start_all_managed_processes():
    for name in managed_processes:
        start_managed_process(name)

def start_all_daemon_processes():
    for name in daemon_processes:
        start_daemon_process(name)

def terminate_non_essential_managed_processes():
    for p in managed_NON_essential_processes:
        terminate_managed_process(p)

def log_begin_manager_thread():
    loggerINFO(f"starting manager thread") 
    #loggerDEBUG({"environ": os.environ})

def log_running_processes_list():
    running_alive = [p for p in running if running[p].is_alive()]
    running_dead = [p for p in running if p not in running_alive]
    if running_dead:
        loggerINFO("alive processes: " + cf.GREEN + ' ; '.join(running_alive) + cf.RESET)    
        loggerINFO("dead processes: " + cf.RED + ' ; '.join(running_dead) + cf.RESET) 

def manager_thread():
    def get_thermal_status(counter):
        def log_info_when_needed(counter):
            try:
                period_between_logs = int(params.get("periodCPUtemperatureLOGS")) * 60
            except:
                period_between_logs = 360

            if counter*co.PERIOD_MAIN_THREAD > period_between_logs:
                loggerINFO(f"thermal update - T {temperature}°C," + \
                    f" CPU load (5 minutes avg) {load_5min}%, mem used {memUsed}%")
                counter = 0
            return counter

        topic, message = ras_subscriber.receive() # BLOCKING
        #loggerDEBUG(f"received {topic} {message}")
        #loggerDEBUG(f"thermal status counter {counter}")
        if topic == "thermal":
            temperature, load_5min, memUsed = \
                message.split()
            counter = log_info_when_needed(counter)
        return counter 


    ras_subscriber = Subscriber("5556")
    ras_subscriber.subscribe("thermal")
    log_begin_manager_thread()
    start_all_daemon_processes()
    start_all_managed_processes()
    #thermal = ThermalStatus() # instance of class ThermalStatus
    counter = 0
    while 1:
        counter = get_thermal_status(counter) # BLOCKING

        if False: #thermal.isCritical()
            terminate_non_essential_managed_processes()
        else:
            start_all_managed_processes()
        log_running_processes_list()
        time.sleep(co.PERIOD_MAIN_THREAD)
        counter += 1


def main():

  try:
    manager_thread()
  except Exception as e:
    loggerCRITICAL(f'managerThread() failed to start with exception {e}')
  finally:
    # TODO cleanupAllProcesses()
    pass


if __name__ == "__main__":

  try:
    main()
  except Exception as e:
    loggerCRITICAL(f'main() failed to start with exception {e}')