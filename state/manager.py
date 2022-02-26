import time

from common.constants import PERIOD_STATE_MANAGER
from common.logger import loggerINFO, loggerCRITICAL, loggerDEBUG
from common.connectivity import internetReachable, isOdooPortOpen
from state.checks import Status_Flags_To_Check, Timezone_Checker


status_flags        = Status_Flags_To_Check()
timezone_checker    = Timezone_Checker()

def main():
    while True:
        status_flags.check_and_execute()
        timezone_checker.check_and_set()
        internet_reachable  = internetReachable()
        odoo_port_open      = isOdooPortOpen()
        loggerDEBUG(f"internet pingable {internet_reachable} - odoo port open {odoo_port_open}")
        time.sleep(PERIOD_STATE_MANAGER)

if __name__ == "__main__":
    main()
