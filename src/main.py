import logging
import sys
from mailgun.component import MailgunApp

# Environment setup
sys.tracebacklimit = 0

if __name__ == '__main__':

    mg = MailgunApp()
    mg.run()

    logging.info("Sending finished.")
