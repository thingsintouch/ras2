import time
#import zmq
import os
from os.path import join, isfile

from common.constants import LAST_REGISTERED, PARAMS, CLOCKINGS, IN_OR_OUT, DEFAULT_MINIMUM_TIME_BETWEEN_CLOCKINGS
from common.logger import loggerINFO, loggerCRITICAL, loggerDEBUG, loggerERROR

from messaging.messaging import SubscriberMultipart as Subscriber
from messaging.messaging import PublisherMultipart as Publisher


from common.params import Params, mkdirs_exists_ok, read_db
from common.common import write_to_file, insert_line_at_top

from datetime import datetime
import pytz

params = Params(db=PARAMS)

if not os.path.exists(CLOCKINGS):
    mkdirs_exists_ok(CLOCKINGS)
    
if not os.path.exists(IN_OR_OUT):
    mkdirs_exists_ok(IN_OR_OUT)

def get_two_lines_name(card):
    if card in os.listdir(PARAMS+'/d'):
        full_name = read_db(PARAMS, card).decode('utf-8')
        if full_name != "":
            if " " in full_name:
                two_lines_name = full_name.replace(" ", "\n", 1)
            else:
                two_lines_name = "\n" + full_name
            return two_lines_name
    two_lines_name = "card\n"+str(card)
    return two_lines_name

def write_clocking(card, now_in_seconds):
    file_name_of_the_clocking = CLOCKINGS + "/" + str(card) + "-" + str(now_in_seconds)
    write_to_file(file_name_of_the_clocking, "Odoo server has not been contacted for this clocking. Refer to previous clockings of this card.\n")
    tz = params.get("tz") or "Europe/Berlin"
    tzinfo = pytz.timezone(tz)
    line_to_insert = datetime.fromtimestamp(int(now_in_seconds), tz=tzinfo).strftime('%H:%M:%S %A %d-%b-%y') + " - " +  str(card) + "\n" 
    insert_line_at_top(LAST_REGISTERED, line_to_insert)

def get_minimum_time():
    n = params.get("minimumTimeBetweenClockings")
    if n is None or not n: 
        min_time_between_clockings = DEFAULT_MINIMUM_TIME_BETWEEN_CLOCKINGS
    elif n:
        min_time_between_clockings = int(n)
    else:
        min_time_between_clockings = DEFAULT_MINIMUM_TIME_BETWEEN_CLOCKINGS
    return min_time_between_clockings

def get_clocking_handling(last_clockings, card, now_in_seconds):
    if enough_time_between_clockings(last_clockings, str(card), now_in_seconds):
        how_to_handle_the_clocking = "card_registered"
        write_clocking(card, now_in_seconds)
    else:
        how_to_handle_the_clocking = "too_little_time_between_clockings"
    loggerDEBUG(f"how the card swipe will be processed: {how_to_handle_the_clocking}")
    return how_to_handle_the_clocking

def enough_time_between_clockings(last_clockings, card_id_as_string, now_in_seconds):
    min_time_between_clockings = get_minimum_time()
    if not last_clockings.d.get(card_id_as_string, False):
        last_clockings.d[card_id_as_string]= now_in_seconds
        enough_time = True
    elif (now_in_seconds - last_clockings.d[card_id_as_string]) > min_time_between_clockings:
        last_clockings.d[card_id_as_string]= now_in_seconds
        enough_time = True
    else:
        enough_time = False     
    return enough_time

def get_last_clocking(card):
    file = join(IN_OR_OUT,card)
    if isfile(file):
        with open(file, 'r') as f:
            last_clocking = f.readline().rstrip('\n') 
    else:
        last_clocking = False
    return last_clocking  

def display_check_in_or_out(card):
    message_for_check_in = params.get("check_in_message_display") or "CHECK IN"
    message_for_check_out = params.get("check_out_message_display") or "CHECK OUT"
    last_clocking = get_last_clocking(card)
    if last_clocking:
        if last_clocking =="check_in":
            message_display_in_or_out = message_for_check_out
        else:
            message_display_in_or_out = message_for_check_in
        return message_display_in_or_out
    else:
        return False

def change_check_in_or_check_out_in_the_file(card):
    last_clocking = get_last_clocking(card)
    if last_clocking:
        if last_clocking =="check_in":
            message_to_store = "check_out"
        else:
            message_to_store = "check_in"
        write_to_file(join(IN_OR_OUT,card), message_to_store + "\n")
        return message_to_store
    else:
        write_to_file(join(IN_OR_OUT,card), "")
        return False

class LastClockings():
    def __init__(self):
        self.d = {}
    
def main():
    display_publisher   = Publisher("5559")
    buzzer_publisher    = Publisher("5558")
    odoo_subscriber     = Subscriber("5557")
    odoo_subscriber.subscribe("new_card")
    last_clockings = LastClockings()

    while 1:
        #loggerDEBUG("POINT 1 ############  before the BLOCKING receive on process odoo -- waiting for a card ")
        topic, card = odoo_subscriber.receive() # BLOCKING
        #loggerDEBUG("POINT 99 ############  after the BLOCKING receive on process odoo -- waiting for a card ")
        if topic == "new_card":
            now_in_seconds = int(time.time())
            two_lines_name = get_two_lines_name(card)
            how_to_handle_the_clocking = get_clocking_handling(last_clockings, card, now_in_seconds)
            text = display_check_in_or_out_message = False

            if how_to_handle_the_clocking != "too_little_time_between_clockings" and params.get("show_checkin_or_out_display") == "1":
                text = display_check_in_or_out_message = display_check_in_or_out(card)
            
            if display_check_in_or_out_message:
                sound_to_play = change_check_in_or_check_out_in_the_file(card) # this is made because there is no guarantee that the message will be updated from odoo
                # After changing the clocking, the check_in or check_out is then up to date
                if sound_to_play:
                    buzzer_publisher.publish("buzz", sound_to_play)
                else:
                    buzzer_publisher.publish("buzz", how_to_handle_the_clocking)
            else:
                buzzer_publisher.publish("buzz", how_to_handle_the_clocking)
                text = params.get_filtered(how_to_handle_the_clocking)

            text = text + "\n" + two_lines_name
            display_publisher.publish("display_card_related_message", text) 

        time.sleep(0.2)


if __name__ == "__main__":
    main()
