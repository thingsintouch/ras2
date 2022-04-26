import os
import time

from common.logger import loggerDEBUG, loggerINFO, loggerWARNING, loggerERROR, loggerCRITICAL
import common.constants as co
import common.common as cc

from common.constants import PARAMS
from common.params import Params, Log
from common.keys import TxType, keys_by_Type

from display.helpers import sh1106
from common.connectivity import isPingable
from odoo.odooRequests import getAnswerFromOdooRoutineCheck

params = Params(db=PARAMS)
log_db =  Log()

keys_to_be_saved =  keys_by_Type[TxType.ON_ROUTINE_CALLS] + keys_by_Type[TxType.DISPLAY_MESSAGE]
# cc.pPrint(keys_to_be_saved)
productName = params.get('productName')


def display_off():
    try:
        display = sh1106()
        display.display_off()
    except Exception as e:
        loggerINFO(f"could not execute -display_off- before shutdown or reboot: {e}")   

def shutdownTerminal():
    display_off()
    loggerINFO("-----############### SHUTDOWN ###############------")
    os.system("sudo shutdown now")
    time.sleep(60)
    sys.exit(0)

def firmwareUpdateAndReboot():
    if isPingable("github.com"):
        loggerINFO("<<<<++++++++ Firmware Update and Reboot +++++++>>>>>>")
        os.chdir(co.WORKING_DIR)
        os.system("sudo git pull")
        # os.system("sudo git fetch ras released")
        # os.system("sudo git reset --hard ras/released")
        display_off()
        time.sleep(1)
        os.system("sudo reboot")
        time.sleep(60)
        sys,exit(0)     
    else:
        loggerINFO("Firmware Update not possible: GitHub is down")        

def saveChangesToParams(answer):
    for k in answer:
        ans = answer.get(k, None)
        if ans is not None:
            if ans is False: ans = "0"
            if ans is True : ans = "1"
            if k in keys_to_be_saved:
                ans = str(ans)
                if ans != params.get(k):
                    loggerDEBUG(f"from routine check - storing {k}: {ans}")
                    params.put(k,ans)
            elif k == "rfid_codes_to_names":
                for code in ans:
                    if code in params.keys:
                        if ans[code] != params.get(code):
                            loggerDEBUG(f"from routine check - storing {code}: {ans[code]}")
                            params.put(code,ans[code])
                    else:
                        params.add_rfid_card_code_to_keys(code)
                        loggerDEBUG(f"from routine check - CREATED and storing {code}: {ans[code]}")
                        loggerDEBUG(f"params.keys {params.keys}")
                        params.put(code,ans[code])                        
            else:
                loggerDEBUG(f"this key in answer from routine call is NOT STORED {k}: {ans}")

def synchronize_Terminal_timestamp_with_Odoo_UTC_timestamp(answer):
    if 'odoo_server_utc_timestamp' in answer:
        utc_now_on_odoo_server = (answer['odoo_server_utc_timestamp'])
        loggerDEBUG(f"utc now on odoo server: {utc_now_on_odoo_server}")
        cc.set_device_time(utc_now_on_odoo_server)

def routineCheck():
    incrementalLog = log_db.get_inc_log()
    answer = getAnswerFromOdooRoutineCheck(incrementalLog)

    if answer:
        error = answer.get("error", False)
        if error:
            loggerDEBUG(f"Routine Check not Available - error in answer from Odoo: {error}")
        else:
            loggerDEBUG(f"Routine Check done - no error - {answer}") # {answer}
            params.put("isRemoteOdooControlAvailable", True)
            saveChangesToParams(answer)
            synchronize_Terminal_timestamp_with_Odoo_UTC_timestamp(answer)
            if params.get("shouldGetFirmwareUpdate") == "1":
                params.put("shouldGetFirmwareUpdate",'0')
                firmwareUpdateAndReboot()
            if params.get('shutdownTerminal') == "1":
                params.put('shutdownTerminal','0')
                shutdownTerminal()
            return True
    else:
        loggerDEBUG(f"Routine Check not Available - No Answer from Odoo")        

    params.put("isRemoteOdooControlAvailable", False)
    return False
