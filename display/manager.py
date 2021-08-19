import time
import zmq

from common import constants as co
from common.logger import loggerINFO, loggerCRITICAL, loggerDEBUG, loggerERROR
#from messaging.messaging import PublisherMultipart as Publisher
from messaging.messaging import SubscriberMultipart as Subscriber

from display.helpers import Oled

from common.params import Params

params = Params(db=co.PARAMS)


def main():

    display_subscriber = Subscriber("5559")
    display_subscriber.subscribe("display_card_related_message")

    oled = Oled()
    
    while 1:
        # get 
        topic, message = display_subscriber.receive() # BLOCKING
        #loggerDEBUG(f"received {topic} {message}")
        if topic == "display_card_related_message":
            params.put("displayClock", "no")
            # counter, load = \
            #     message.split()
            text = f"new message \n {message}"
            loggerDEBUG(text)           
            oled.three_lines_text(text)

        time.sleep(co.PERIOD_DISPLAY_MANAGER)
        params.put("displayClock", "yes")

if __name__ == "__main__":
    main()
