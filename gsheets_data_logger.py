import appdaemon.plugins.hass.hassapi as hass
from pprint import pprint
from googleapiclient import discovery
from apiclient import discovery
import time
import sys
import httplib2
import os
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from datetime import datetime
from datetime import timedelta
from pytz import timezone
import signal
import re
import smtplib
import pyowm
import requests 
import signal
import traceback
import photosynq_py as ps
import environment_variables
import subprocess
import socket


try:
    import argparse
    flags = tools.argparser.parse_args(args=[])

except ImportError:
    flags = None


carriers = {
    'att':    '@mms.att.net ',
    'tmobile':' @tmomail.net',
    'verizon':  '@vzwpix.com',
    'sprint':   '@messaging.sprintpcs.com'
}
#
# GSheets Data Logger
# This class opens the connection to google sheets and appends data to a file.
#
# Args:
#appdaemon

class GSheetsDataLogger(hass.Hass):
    def initialize(self):
        self.log("******* Hello from GSheetsDataLogger ********")
#        self.log("temp =%s" % self.entities.sensor.greenhouse_temp.state)

        self.SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
        self.CLIENT_SECRET_FILE = 'client_secret.json'
        self.CLIENT_TOKEN_FILE_NAME = 'gsheets_write_token.json' #Copied from token.json
        self.APPLICATION_NAME = 'GsheetsDataLogger' 
        self.spreadsheet_id = os.getenv('SPREADSHEET_ID') # FARM
        # Storage Queues
        self.pool_1_queue = []
        self.pool_2_queue = []
        self.pool_3_queue = []
        self.pool_4_queue = []
        self.outside_queue = []
        self.greenhouse_queue = []
        self.light_queue = []

        # Determines if pools are active currently
        self.pool_1_active = True
        self.pool_2_active = True
        self.pool_3_active = True
        self.pool_4_active = True
        self.pool_2_point_five_active = True

        self.pool1_sensor_off_count = 0
        self.pool2_sensor_off_count = 0
        self.pool2_5_sensor_off_count = 0
        self.pool3_sensor_off_count = 0
        self.pool4_sensor_off_count = 0

        self.pool1_sensor_off_text = False
        self.pool2_sensor_off_text = False
        self.pool2_5_sensor_off_text = False
        self.pool3_sensor_off_text = False
        self.pool4_sensor_off_text = False

        
        # These flags determine if temperature went over expected levels and to watch for when it returns
        self.pool1_flag = False
        self.pool2_flag = False
        self.pool2_5_flag = False
        self.pool3_flag = False
        self.pool4_flag = False
        self.greenhouse_flag = False
        self.farm_flag = False
        self.light_flag = False
        self.pool1_heater_on = False
        self.pool1_cooler_on = False
        self.pool2_heater_on = False
        self.pool2_cooler_on = False
        self.pool2_5_heater_on = False
        self.pool2_5_cooler_on = False
        self.pool3_heater_on = False
        self.pool3_cooler_on = False
        self.pool4_heater_on = False
        self.pool4_cooler_on = False

        self.pool1_cooler_needs_on = False
        self.pool2_cooler_needs_on = False

        self.notification_text_sent_out = False

        self.start_data_buffer = False
        self.end_data_buffer = False
        self.data_loss_count = 0
        # MQTT heating and cooling commands
        # Needs To Be Updated
        self.pool1_heater_turn_on = "http://192.168.1.11/cm?cmnd=Power%20On"
        self.pool1_heater_turn_off = "http://192.168.1.11/cm?cmnd=Power%20off"
        self.pool1_cooler_turn_on = "http://192.168.1.22/cm?cmnd=Power%20On"
        self.pool1_cooler_turn_off = "http://192.168.1.22/cm?cmnd=Power%20off"

        self.pool2_heater_turn_on = "http://192.168.1.8/cm?cmnd=Power%20On"
        self.pool2_heater_turn_off = "http://192.168.1.8/cm?cmnd=Power%20off"
        # self.pool2_cooler_turn_on = "http://192.168.1.22/cm?cmnd=Power%20On"
        # self.pool2_cooler_turn_off = "http://192.168.1.22/cm?cmnd=Power%20off"

        # pool 2.5
        self.pool2_5_heater_turn_on = "http://192.168.1.4/cm?cmnd=Power%20On"
        self.pool2_5_heater_turn_off = "http://192.168.1.4/cm?cmnd=Power%20off"
        self.pool2_5_cooler_turn_on = "http://192.168.1.17/cm?cmnd=Power%20On"
        self.pool2_5_cooler_turn_off = "http://192.168.1.17/cm?cmnd=Power%20off"
        # Pool 3.
        self.pool3_heater1_turn_on = "http://192.168.1.27/cm?cmnd=Power%20On"
        self.pool3_heater1_turn_off = "http://192.168.1.27/cm?cmnd=Power%20off"
        self.pool3_heater2_turn_on = "http://192.168.1.100/cm?cmnd=Power%20On"
        self.pool3_heater2_turn_off = "http://192.168.1.100/cm?cmnd=Power%20off"
        self.pool3_cooler_turn_on = "http://192.168.1.7/cm?cmnd=Power%20On"
        self.pool3_cooler_turn_off = "http://192.168.1.7/cm?cmnd=Power%20off"
        self.pool4_heater_turn_on = "http://192.168.1.47/cm?cmnd=Power%20On"
        self.pool4_heater_turn_off = "http://192.168.1.47/cm?cmnd=Power%20off"
        self.pool4_cooler_turn_on = "http://192.168.1.18/cm?cmnd=Power%20On"
        self.pool4_cooler_turn_off = "http://192.168.1.18/cm?cmnd=Power%20off"
        # Not Implemented
        self.pool3_lights_turn_on = "http://192.168.1.115/cm?cmnd=Power%20On"
        self.pool3_lights_turn_off = "http://192.168.1.115/cm?cmnd=Power%20off"
        self.pool4_lights_turn_on = "http://192.168.1.115/cm?cmnd=Power%20On"
        self.pool4_lights_turn_off = "http://192.168.1.115/cm?cmnd=Power%20off"
        # MQTT Check Relay Status
        self.pool1_cooler = "http://192.168.1.22/cm?cmnd=Power"
        self.pool1_heater = "http://192.168.1.11/cm?cmnd=Power"
        self.pool2_heater = "http://192.168.1.8/cm?cmnd=Power"

        self.pool2_5_cooler = "http://192.168.1.17/cm?cmnd=Power"
        self.pool2_5_heater = "http://192.168.1.4/cm?cmnd=Power"

        self.pool3_heater1 = "http://192.168.1.27/cm?cmnd=Power"
        self.pool3_heater2 = "http://192.168.1.100/cm?cmnd=Power"
        self.pool3_cooler = "http://192.168.1.7/cm?cmnd=Power"
        self.pool4_heater = "http://192.168.1.47/cm?cmnd=Power" # Changed this line
        self.pool4_cooler = "http://192.168.1.18/cm?cmnd=Power"
        # Not Implemented
        self.pool3_lights = "http://192.168.1.115/cm?cmnd=Power"
        self.pool4_lights = "http://192.168.1.115/cm?cmnd=Power"
        # Status
        self.pool2_cooler_status = "http://192.168.1.22/cm?cmnd=Status%209"
        self.pool1_heater_status = "http://192.168.1.11/cm?cmnd=Status%209"
        self.pool2_heater_status = "http://192.168.1.8/cm?cmnd=Status%209"
        self.pool2_5_cooler_status = "http://192.168.1.17/cm?cmnd=Status%209"
        self.pool2_5_heater_status = "http://192.168.1.4/cm?cmnd=Status%209"

        self.greenhouse_status = "http://192.168.1.6/cm?cmnd=Status%208"
        self.outside_status = "http://192.168.1.53/cm?cmnd=Status%208"
        self.illumination_status = "http://192.168.1.44/cm?cmnd=Status%208"

        self.pool3_cooler_status = "http://192.168.1.7/cm?cmnd=Status%209"
        self.pool3_heater1_status = "http://192.168.1.27/cm?cmnd=Status%209"
        self.pool3_heater2_status = "http://192.168.1.100/cm?cmnd=Status%209"
        self.pool4_cooler_status = "http://192.168.1.18/cm?cmnd=Status%209"
        self.pool4_heater_status = "http://192.168.1.47/cm?cmnd=Status%209"
        # Broken Relays Boolean
        self.p1_cooler_broken = False
        self.p1_heater_broken = False
        self.p2_heater_broken = False

        self.p2_5_heater_broken = False
        self.p2_5_cooler_broken = False

        self.p3_heater1_broken=False
        self.p3_heater2_broken=False
        self.p4_heater_broken=False
        self.p3_cooler_broken=False
        self.p4_heater_broken=False
        self.p4_cooler_broken=False
        # Broken Relay Text Boolean
        self.p1_cooler_broken_on_text=False
        self.p1_cooler_broken_off_text=False
        self.p1_heater_broken_on_text=False
        self.p1_heater_broken_off_text=False

        self.p2_cooler_broken_on_text=False

        self.p2_5_cooler_broken_on_text=False
        self.p2_5_heater_broken_on_text=False

        self.p3_heater1_broken_on_text=False
        self.p3_heater2_broken_on_text=False
        self.p4_heater_broken_on_text=False
        self.p3_cooler_broken_on_text=False
        self.p4_cooler_broken_on_text=False

        self.p1_cooler_broken_count = 0
        self.p2_cooler_broken_count = 0
        self.p2_5_cooler_broken_count = 0
        self.p3_cooler_broken_count = 0
        self.p4_cooler_broken_count = 0

        self.p1_heater_broken_on_checked = False
        self.p1_heater_broken_off_checked = False
        self.p1_cooler_broken_on_checked = False
        self.p1_cooler_broken_off_checked = False

        self.p2_5_heater_broken_on_checked = False
        self.p2_5_cooler_broken_on_checked = False
        self.p2_5_heater_broken_off_checked = False
        self.p2_5_cooler_broken_off_checked = False

        self.p3_heater1_broken_on_checked=False
        self.p3_heater2_broken_on_checked=False
        self.p4_heater_broken_on_checked=False
        self.p3_cooler_broken_on_checked=False
        self.p4_cooler_broken_on_checked=False

        self.p3_heater1_broken_off_text=False
        self.p3_heater2_broken_off_text=False
        self.p4_heater_broken_off_text=False
        self.p3_cooler_broken_off_text=False
        self.p4_heater_broken_off_text=False
        self.p4_cooler_broken_off_text=False

        self.p3_heater1_broken_off_checked=False
        self.p3_heater2_broken_off_checked=False
        self.p4_heater_broken_off_checked=False
        self.p3_cooler_broken_off_checked=False
        self.p4_heater_broken_off_checked=False
        self.p4_cooler_broken_off_checked=False
        # Command Flag Boolean
        self.look_for_command=False

        self.pool3_heater_count = 0
        self.pool3_cooler_count = 0

        self.forecast_trigger = False
        self.average_trigger = False
        self.photosynq_trigger = True
        # Google Sheet Spreadsheet id's
        self.photosynq_p1_spreadsheet_id = 1822891006
        self.photosynq_p2_spreadsheet_id = 1965910243
        self.photosynq_p3_spreadsheet_id = 1809622314
        self.photosynq_p4_spreadsheet_id = 633728140
        self.outside_spreadsheet_id =1139064985
        self.data_summary_spreadsheet_id =1
        self.pool_1_spreadsheet_id = 958614011
        self.pool_2_spreadsheet_id = 1261839026
        self.pool_4_spreadsheet_id =114357400
        self.pool_4_airpump_sheet = 1945572860
        self.pool_3_spreadsheet_id =1889372714
        self.pool_2_5_spreadsheet_id = 676971998
        self.greenhouse_spreadsheet_id =894214581
        self.sunlight_spreadsheet_id =202215001
        self.weather_forecast_sheet = 1366405747
        # self.weather_forecast_sheet = 1545130565
        self.average_sheet = 206396653

        self.poll_p1_failed = False
        self.poll_p2_failed = False
        self.poll_p2_5_failed = False
        self.poll_p3_failed = False
        self.poll_p4_failed = False
        self.poll_greenhouse_failed = False
        self.poll_outside_failed = False
        self.poll_illumination_failed = False



        self.row_1 = 1
        self.row_2 = 2
        self.row_42 = 42
        self.row_43 = 43
        
        self.brentwood_id = 5330642

        self.wind_speed_limit = 12
        self.wind_gust_limit = 16
        # Counters
        self.poll_restart_counter = 0

        self.restart_counter = 0
        self.three_hours = 3
        self.six_ten_minutes = 6
        self.four_failure_cycles = 4
        self.three_failure_cycles = 3
        self.six_failure_cycles = 6

        # Global Sensor Values
        self.pool1_temp_global = 0
        self.pool2_temp_global = 0
        self.pool2_5_temp_global = 0
        self.pool3_temp_global = 0
        self.pool4_temp_global = 0
        self.greenhouse_temp_global = 0
        self.greenhouse_humidity_global = 0
        self.outside_temp_global = 0
        self.outside_humidity_global = 0
        self.light_illuminance_global = 0
        self.light_infrared_global = 0
        self.light_uvindex_global = 0
        
        #---------------TEST AREA---------------
        # print("Start")
        # URL = self.pool3_heater1_status
        # r1 = requests.get(url = URL, timeout=7)
        # data1 = r1.json()
        # # print(data1)
        # print(data1['Status']['FriendlyName'][0])
        # if(data1['Status']['FriendlyName'][0] != u'Pool_3 Heater 1'):
        #     print("Pool 3 Heater 1 Being Reassigned")
        #     reassign_sonoffs_check = True 

        #---------------TEST AREA---------------

        self.discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
        numberTest = 100
        
        try:
            self.send_text("Raspberry pi Restarted", "Conrad")

        except Exception as e:
            print(e)
            self.log("Restart Text Failed")
        
        # testtext = 'Testing From Function How much can I send' + str(self.entities.sensor.greenhouse_temp.state)
        # self.send_text(testtext + str(numberTest), "Conrad")
        # 
        # self.log_sensor_data()
        
        #----------------TEST AREA-----------------
        # self.credentials = self.get_credentials()
        # self.http = self.credentials.authorize(httplib2.Http())
        # self.service = discovery.build('sheets', 'v4', http=self.http, discoveryServiceUrl=self.discoveryUrl)
        # self.get_photosynq()
        # while True:
        # #     # self.send_text(testtext, "Conrad")
        # #     control_values = self.gsheets_retrieve_data('Control!B2:B7', self.spreadsheet_id)
        # #     self.check_sensors_text(control_values[0], control_values[1], control_values[2], control_values[3], control_values[4], control_values[5])
        #     time_store_test = self.log_sensor_data()
        # #     self.log("*****! Made it past Check sensors !*****")

        # #     self.log("Before Weather Call")
        #     weather = self.weather_call(time_store_test, self.spreadsheet_id)
        #     sunrise = weather[9]
        #     sunset = weather[10]
        # #     self.log("After Weather Call")

        #     control_values2 = self.gsheets_retrieve_data('Control!B9:B21', self.spreadsheet_id)
        # #     # self.control_lights(control_values2[0])
        # #     self.log("*****! Made it Past Control Lights !*****")
        # #     # self.control_lights(control_values2[0])
        # #     # self.log("*****! Made it Past Control Lights !*****")
        #     self.control_pool_temp(control_values2[1], control_values2[2], control_values2[3], control_values2[4], control_values2[5], control_values2[6], control_values2[7], control_values2[8], control_values2[9], control_values2[10], control_values2[11], control_values2[12], sunrise, sunset)
        # #     self.log("*****! Made it Past Control Pool Temp !*****")



        #     # self.control_pool_temp(35, 33.3, 22.2, 35, 33.3, 22.2, 35, 33.3, 22.2, 35, 25, 10, 0, 0)
            
        #     time.sleep(60)
        # self.send_http(self.pool1_heater_turn_on)
        self.log("Pool 3temp =%s" % self.entities.sensor.pool3_temp.state)
        self.start_logging()
    #---------------------Start Logging---------------------
        # @desc:   Start the main program that creates the loop for the majority of the app
        # @param:  none
        # @return: none
    #-------------------------------------------------------
    def start_logging(self):
        # self.credentials = self.get_credentials()
        # self.http = self.credentials.authorize(httplib2.Http())
        # self.service = discovery.build('sheets', 'v4', http=self.http, discoveryServiceUrl=self.discoveryUrl)
        # self.get_averages()
        print("Tested it got in here.")
        # control_values = self.gsheets_retrieve_data('Control!B8:B10', self.spreadsheet_id)

        # self.control_pool_temp(35, 25, 26, 35, 25, 26, 35, 25, 22, 35, 25, 22, 0, 0)
        
        try:
            print("Checking Active Pools")
            # Credentials for Google sheets interface
            try:
                self.credentials = self.get_credentials()
                self.http = self.credentials.authorize(httplib2.Http())
                self.service = discovery.build('sheets', 'v4', http=self.http, discoveryServiceUrl=self.discoveryUrl)
                self.log("after services - discover.build")
                self.google_sheets_started = True
            except Exception as e:
                print("--------------------!!!!!!!FAILED CONNECTION TO GOOGLE SHEETS!!!!!!--------------------")
                print(e)
                self.google_sheets_started = False
            try:   

                active_pools = self.gsheets_retrieve_data('Control!D2:D6', self.spreadsheet_id)
                if(active_pools[0] == '0'):
                    self.pool_1_active = False
                    print("Pool 1 Inactive")
                else:
                    print("Pool 1 Active")
                if(active_pools[1] == '0'):
                    self.pool_2_active = False
                    print("Pool 2 Inactive")
                else:
                    print("Pool 2 Active")
                if(active_pools[2] == '0'):
                    self.pool_3_active = False
                    print("Pool 3 Inactive")
                else:
                    print("Pool 3 Active")
                if(active_pools[3] == '0'):
                    self.pool_4_active = False
                    print("Pool 4 Inactive")
                else:
                    print("Pool 4 Active")
                if(active_pools[4] == '0'):
                    self.pool_2_point_five_active = False
                    print("Pool 2.5 Inactive")
                else:
                    print("Pool 2.5 Active")

            except:
                self.pool_1_active = True
                self.pool_2_active = True
                self.pool_3_active = True
                self.pool_4_active = True
                self.pool_2_point_five_active = True

            # try:
            #     self.Look_For_Sonoffs()
            # except:
            #     print("Failed look for Sonoffs")
            # try:
            #     self.control_pi('ls -l')
            # except Exception as e:
            #     print(e)
            #     print('failed contorl pi')
            try:
                self.check_sonoff_status()
                print(self.pool4_heater)
            except Exception as e:

                print("check sonoff status failed")
                print(e)

            try:
                self.check_ip()

            except Exception as e:
                print("Failed the ip check")
            # TESTING NOTIFICATION
            # try:
            #     self.notification_start()
            # except Exception as e:
            #     print(e)
            #     print("Failed notification test")

            ten_minutes = 6
            forecast_counter = 0
            loop = 10
            error_count = 0
            
            
            
            self.log("***** Trying to run every 10 minute...")
            while True:
                if(self.google_sheets_started == False):
                    try:
                        self.credentials = self.get_credentials()
                        self.http = self.credentials.authorize(httplib2.Http())
                        self.service = discovery.build('sheets', 'v4', http=self.http, discoveryServiceUrl=self.discoveryUrl)
                        self.log("after services - discover.build")
                        self.google_sheets_started = True
                    except Exception as e:
                        print("--------------------!!!!!!!FAILED CONNECTION TO GOOGLE SHEETS!!!!!!--------------------")
                        print(e)
                        self.google_sheets_started = False

                self.log("***** inside timer *****")
                n = 0
                try:
                    # If All sensors are unknown then send text that there is a stop in logging and the sensors have disconnected
                    if(self.entities.sensor.greenhouse_temp.state =="unknown" and self.entities.sensor.pool3_temp.state == "unknown" and self.entities.sensor.outside_humidity.state =="unknown"
                        and self.entities.sensor.light_infrared.state == "unknown"):
                        error_count = error_count + 1
                        # Wait for 4 cycles before texting that all sensors are unkown
                        if(error_count == self.four_failure_cycles):
                            self.text_notification('Logging Has Stopped Due to Unknown Sensor Values.')
                    else:
                        error_count = 0
                    # signal.signal(signal.SIGALRM, alarm_handler)
                    # signal.alarm(8)

                    try:
                        print("Checking ping on problem retrieve!")
                        print(self.check_ping())
                        # make only one retreive for control values
                        control_values = self.gsheets_retrieve_data('Control!B2:B7', self.spreadsheet_id)
                        self.internet_works = True
                    except Exception as e:
                    # except TimeOutException as ex:
                        self.internet_works = False
                        self.log("!!!!!!!!!!!!!!!Failed Retrieve Data!!!!!!!!!!!!!!!!!!!")
                        traceback.print_exc()
                        print(ex)
                    # Check the sensors and compare them to the previously retrieved values.
                    try:
                        self.check_sensors_text(control_values[0], control_values[1], control_values[2], control_values[3], control_values[4], control_values[5])
                    except Exception as e:
                        self.log("!!!!!!!!!!!!!!!Failed Text Notification. (BIG Problem)!!!!!!!!!!!!!!!!!!!")
                        traceback.print_exc()
                        print(e)
                    # Check if there is need to empty the buffer
                    self.is_file_there()
                    # Call Log Sensor Data and if it fails
                    try:
                        if(self.check_ping()):
                            self.internet_works = True
                        else:
                            self.internet_works = False
                        if(self.file_exists == True and self.internet_works == True):
                            self.empty_data_buffer()
                        time_store = self.log_sensor_data()
                    except Exception as e:
                        self.log("!!!!!!!!!!Failed Log Sensor Data. (Internet Failed Likely)!!!!!!!!!!!!")
                        
                        traceback.print_exc()
                        print(e)
                        # Start Data Buffering
                        self.internet_works = False
                        time_store = self.data_buffer()
                        self.restart_counter = self.restart_counter+1
                        print("Got to final failure point")
                        if(self.restart_counter == self.six_failure_cycles):
                            print("Internet has not reconnected in an hour going to try to restart.")
                            self.restart_pi()
                            
                    # Pool and Light Temperature Control
                    

                    # if statement to run the weather code only once an hour to not send too many api calls
                    if(ten_minutes == self.six_ten_minutes):
                        self.log("Before Weather Call")
                        try:
                            # The weather call uses the Pyowm Api to collect data for brentwood california and stores it to a list
                            # that list is weather and the sunrise and sunset time are
                            weather = self.weather_call(time_store, self.spreadsheet_id)
                            sunrise = weather[9]
                            sunset = weather[10]
                            ten_minutes = 0
                            forecast_counter = forecast_counter + 1
                            print(forecast_counter)
                        except Exception as e:
                            self.log("!!!!!!!!!!!Failed Weather Call!!!!!!!!!!!!")
                            sunrise = 0
                            sunset = 0
                            traceback.print_exc()
                            print(e)
                            ten_minutes = ten_minutes - 1
                        self.log("After Weather Call")

                        
                    else:
                        # Make to minutes
                        ten_minutes = ten_minutes + 1
                        print("ten_minutes Increase : " + str(ten_minutes))

                    #---------------------Weather Forecast---------------------
                    # @desc Calls the weather forecast once a day between 5:30 and 6
                    # @param (none)
                    

                     #For use when only running at certain times
                    # if(current_time > photosynq_start_time and current_time < photosynq_end_time):
                    if(forecast_counter == self.three_hours):
                        try:
                            # self.get_forecast()
                            self.forecast_trigger = True
                            
                        except Exception as e:
                            print(e)


                    if(self.forecast_trigger == True):
                        try:
                            self.log("Its time for the Weather Forecast")
                            self.get_forecast()
                            self.forecast_trigger = False
                            forecast_counter = 0

                        except Exception as e:
                            print(e)
                            self.forecast_trigger = True
                            forecast_counter = forecast_counter - 1

                    #---------------------Gather Photosynq Information---------------------
                    # @desc Calls the get_photosynq function that gathers all the fluorometry data that was taken and 
                    #       inserts it into the google sheets for logging.  Runs this once a day between 12:00 PM and 12:10 PM
                    current_time = self.get_time()
                    photosynq_start_time = datetime.utcfromtimestamp(1547463600).strftime('%H:%M:%S')
                    photosynq_end_time = datetime.utcfromtimestamp(1547464800).strftime('%H:%M:%S')
                    self.log("Start Time =%s" % str(photosynq_start_time))
                    self.log("End Time =%s" % str(photosynq_end_time))
                    self.log("Current Time =%s" % str(current_time))

                    if(photosynq_start_time < current_time < photosynq_end_time):
                        self.photosynq_trigger = True
                        print("Its time for photosynq!")

                    if(self.photosynq_trigger == True):
                        try:
                            self.get_photosynq()
                            self.photosynq_trigger = False

                        except Exception as e:
                            print(e)
                            print("Photosynq Call Failed")
                            self.photosynq_trigger = True



                    #---------------------Gather Average Data and insert---------------------
                    # @desc 
                    #       
                    current_time = self.get_time()
                    average_start_time = datetime.utcfromtimestamp(1581636600).strftime('%H:%M:%S')
                    average_end_time = datetime.utcfromtimestamp(1581637500).strftime('%H:%M:%S')
                    self.log("Start Time =%s" % str(average_start_time))
                    self.log("End Time =%s" % str(average_end_time))
                    self.log("Current Time =%s" % str(current_time))

                    if(average_start_time < current_time < average_end_time):
                        self.average_trigger = True
                        print("Its time for collecting averages!")

                    if(self.average_trigger == True):
                        try:
                            self.get_averages()
                            self.average_trigger = False

                        except Exception as e:
                            print(e)
                            print("Average Call Failed")
                            self.average_trigger = True

                    #---------------------Pool Temperature Control Loop---------------------
                    # @desc Retrieve Control Values from the google sheets that will determine temperature for 
                    #       Controlling the Pools heating and cooling system.
                   #  
                    try:
                        control_values2 = self.gsheets_retrieve_data('Control!B9:B25', self.spreadsheet_id)
                        control_values3 = self.gsheets_retrieve_data('Control!B27:B29', self.spreadsheet_id)
                        # Check for restart
                        if(control_values2[13] =='1'):
                            self.restart_pi()

                        # Lock the Control Mode to input commands    
                        if(control_values2[15] == '1'):
                            text = 'Set to control Mode and now commands can be put in continuously from the Control Panel.'
                            self.send_text(text, 'Conrad')
                            while(1):
                                control_values_lock = self.gsheets_retrieve_data('Control!B23:B25', self.spreadsheet_id)

                                if(control_values_lock[1]=='0'):
                                    break

                        # Single Command
                        elif(control_values2[14] == '1'):
                            print("Control Command Initiated")
                            self.look_for_command=True
                            self.control_pi(control_values2[16])




                    except Exception as e:
                        self.log("Retrieve Data Failed.")
                        traceback.print_exc()
                        print(e)
                    # Pool Temperature control loop that will check every minute the status of the temperature and control heating and cooling based on the sensor data
                    while n < 10:
                        try:
                            try:
                                self.poll_sensors()
                            except Exception as e:
                                print(e)
                                print("Failed Poll Sensors")
                            try:
                                # Control Pool Temperature
                                self.control_pool_temp(control_values2[1], control_values2[2], control_values2[3], control_values2[4], control_values2[5], control_values2[6], control_values2[7], control_values2[8], control_values2[9], control_values2[10], control_values2[11], control_values2[12], sunrise, sunset, control_values3[0], control_values3[1], control_values3[2])
                                # Control Pi Section
                                if(self.look_for_command==True):
                                    control_pi = self.gsheets_retrieve_data('Control!B23:B25', self.spreadsheet_id)
                                    self.control_pi(control_pi[2])
                                    if(control_pi[0]=='0'):
                                        self.look_for_command=False
                            except Exception as e:
                                # Control values for temperature control in case of internet failure.  I chose to keep these readable so 
                                # It would be easier to alter them
                                self.control_pool_temp(35, 25, 25, 35, 25, 25, 35, 25, 22, 35, 25, 22, sunrise, sunset, 35, 25, 25)
                                traceback.print_exc()
                                print(e)
                            # notification text Timing
                            try:
                                self.notification_start()
                            except Exception as e:
                                print(e)
                                print("Failed Timed Notification Text")
                            # time = self.get_time()
                            # send_notifcation_text=self.check_notification_time(time)
                            # if(send_notification_text == True and self.notification_text_sent_out == False):
                            #     text = "Greenspring Farm Notification Update: Current Time: " str(time)
                            #     self.send_text('Conrad',text)
                            #     self.notification_text_sent_out = True

                                #sent Text self.notification_text_sent_out = True


                            if(self.poll_restart_counter > 8):
                                print("Need to Restart Pi Because of Broken Pipe.")
                                self.restart_pi()

                        except Exception as e:
                            self.log("!!!!!!!!!!!-----Cooling and Heating Control FAILED first one use standard values----!!!!!!!!!!!!!!")
                            traceback.print_exc()
                            print(e)
                        n = n + 1
                        # I chose 53 after testing the timing needed to have one cycle be completed and then reach another cycle for a ten minute iteration.
                        time.sleep(53)
                    n = 0
                except Exception as e:
                    self.log("***** System Failed Break and reinitialize *****")
                    traceback.print_exc()
                    print(e)
                    time.sleep(60)
                    break
        # This is for when the internet fails, allowing me to control heating and cooling
        except Exception as e:
            self.log("***** System Failed Internet Disconnected reinitialize *****")

            traceback.print_exc()
            n = 0
            try:
                self.credentials = self.get_credentials()
                self.http = self.credentials.authorize(httplib2.Http())
                self.service = discovery.build('sheets', 'v4', http=self.http, discoveryServiceUrl=self.discoveryUrl)
                control_values2 = self.gsheets_retrieve_data('Control!B9:B21', self.spreadsheet_id)
            except Exception as e:
                self.log("retrieved data failed in standardized")
                traceback.print_exc()
                print(e)
            while n < 10:
                        try:
                            # self.control_lights(control_values2[0])
                            # self.log("*****! Made it Past Control Lights !*****")
                            self.control_pool_temp(control_values2[1], control_values2[2], control_values2[3], control_values2[4], control_values2[5], control_values2[6], control_values2[7], control_values2[8], control_values2[9], control_values2[10], control_values2[11], control_values2[12], sunrise, sunset, control_values3[0], control_values3[1], control_values3[2])
                            # self.log("*****! Made it Past Control Pool Temp !*****")
                        except Exception as e:
                            try:
                                self.log("!!!!!!!!!!!-----Cooling and Heating Control use standard values----!!!!!!!!!!!!!!")
                                self.control_pool_temp(35, 25, 26, 35, 25, 26, 35, 30, 22, 35, 30, 22, 0,0, 35, 25, 25 )
                                traceback.print_exc()
                                print(e)
                            except:
                                # Final Failur point and if it reaches this point a second time it should restart the pi
                                self.restart_counter = self.restart_counter+1
                                print("Got to final failure point")
                                if(self.restart_counter == self.three_failure_cycles):
                                    self.restart_pi()
                        n = n + 1
                        time.sleep(50)
        # Restart On Break
        self.start_logging()

    #---------------------Log Sensor Data---------------------
        # @desc:   Collect the sensor data and then add them to their respective google sheets.
        #          
        # @param:  none
        # @return: none
    #---------------------------------------------------------
    def log_sensor_data(self):
        self.log("***** inside log_sensor_data *****")
        #self.log("***** last_updated:%s, last_changed:%s *****" % (self.entities.sensor.greenhouse_temp.last_updated,
        #                                                            self.entities.sensor.greenhouse_temp.last_changed))
        self.log("***** last_updated:%s, last_changed:%s *****" % (self.entities.sensor.outside_temp.last_updated,
                                                                    self.entities.sensor.outside_temp.last_changed))
        # Get Current Time for Log input
        fmt = '%Y-%m-%d %H:%M:%S'
        d = datetime.now()
        cur_time = d.strftime(fmt)
        # Check relays for their current status
        try:
            self.check_relays()
        except:
            print("Failed to check relays.")
        self.log("Greenhouse temp =%s" % self.entities.sensor.greenhouse_temp.state)
        # Insert Greenhouse data

        try:
            self.poll_sensors()
        except Exception as e:
            print(e)
            print('The Poll Sensor Failed!')

        if(self.entities.sensor.greenhouse_temp.state != "unknown"):
            self.gsheets_insert(cur_time,
                                self.spreadsheet_id,
                                # self.entities.sensor.greenhouse_temp.last_updated,
                                cur_time,
                                self.entities.sensor.greenhouse_temp.attributes.friendly_name,
                                #self.entities.sensor.greenhouse_temp.state,
                                str(self.greenhouse_temp_global), str(self.greenhouse_humidity_global),
                                #self.entities.sensor.greenhouse_humidity.state,
                                 "Null", "Null", "Null", "Null", "Null")

        # Check if heater or cooler is on and log 
        self.log("Pool 3 temp =%s" % self.entities.sensor.pool3_temp.state)
        if(self.pool_3_active):
            if(self.entities.sensor.pool3_temp.state != "unknown" and  self.poll_p3_failed == False):# and self.pool3_temp_global != "unknown"):
                self.pool3_sensor_off_text = False
                self.pool3_sensor_off_count = 0
                if(self.pool3_heater_on == True):
                    p3_heat = "5"
                else:
                    p3_heat = "0"
                if(self.pool3_cooler_on == True):
                    p3_cool = "5"
                else:
                    p3_cool = "0"
            # Insert Pool 3 Data
                self.gsheets_insert(cur_time,
                                    self.spreadsheet_id,
                                    # self.entities.sensor.pool3_temp.last_updated,
                                    cur_time,
                                    self.entities.sensor.pool3_temp.attributes.friendly_name,
                                    #self.entities.sensor.pool3_temp.state,
                                    str(self.pool3_temp_global),
                                     "Null", "Null",p3_heat, p3_cool, "Null", "Null")

            elif(self.entities.sensor.pool3_temp.state == "unknown" and self.pool3_sensor_off_count>1 and self.pool3_sensor_off_text != True):
                text = "Pool 3 Sensor is Not Recording Please Check"
                self.text_notification(text)
                self.pool3_sensor_off_text = True

            else:
                print("Pool 3 Sensor not logging")
                self.pool3_sensor_off_count = self.pool3_sensor_off_count + 1
                print(self.pool3_sensor_off_count)

        self.log("Pool 4 temp =%s" % self.entities.sensor.pool4_temp.state)
        # Check if heater or cooler is on and log
        if(self.pool_4_active):
            if(self.entities.sensor.pool4_temp.state != "unknown" and  self.poll_p4_failed == False): # and self.pool4_temp_global != "unknown"):
                self.pool4_sensor_off_text = False
                self.pool4_sensor_off_count = 0
                if(self.pool4_heater_on == True):
                    p4_heat = "10"
                else:
                    p4_heat = "0"
                if(self.pool4_cooler_on == True):
                    p4_cool = "10"
                else:
                    p4_cool = "0"
            # Insert Pool 4 Data
                self.gsheets_insert(cur_time,
                                    self.spreadsheet_id,
                                    # self.entities.sensor.pool4_temp.last_updated,
                                    cur_time,
                                    self.entities.sensor.pool4_temp.attributes.friendly_name,
                                    # self.entities.sensor.pool4_temp.state,
                                    str(self.pool4_temp_global),
                                     "Null", "Null", p4_heat, p4_cool, "Null", "Null")

            elif(self.entities.sensor.pool4_temp.state == "unknown" and self.pool4_sensor_off_count>1 and self.pool4_sensor_off_text != True):
                text = "Pool 4 Sensor is Not Recording Please Check"
                self.text_notification(text)
                self.pool4_sensor_off_text = True

            else:
                self.pool4_sensor_off_count = self.pool4_sensor_off_count + 1

        self.log("Outside temp =%s" % self.entities.sensor.outside_temp.state)
        # Insert Outside Data
        if(self.entities.sensor.outside_temp.state != "unknown" and  self.poll_outside_failed == False):
            self.gsheets_insert(cur_time,
                                self.spreadsheet_id,
                                # self.entities.sensor.outside_temp.last_updated,
                                cur_time,
                                self.entities.sensor.outside_temp.attributes.friendly_name,
                                # self.entities.sensor.outside_temp.state,
                                str(self.outside_temp_global),
                                # self.entities.sensor.outside_humidity.state,
                                str(self.outside_humidity_global),
                                 "Null", "Null", "Null", "Null", "Null")
        self.log("Light Lux =%s" % self.entities.sensor.light_illuminance.state)
        # Insert Light Data
        if(self.entities.sensor.light_illuminance.state != "unknown" and  self.poll_illumination_failed == False): # and self.light_illumance_global != "unknown"):
            self.gsheets_insert(cur_time,
                                self.spreadsheet_id,
                                # self.entities.sensor.light_illuminance.last_updated,
                                cur_time,
                                self.entities.sensor.light_illuminance.attributes.friendly_name,
                                # self.entities.sensor.light_illuminance.state,
                                # self.entities.sensor.light_infrared.state,
                                # self.entities.sensor.light_uv.state,
                                str(self.light_illuminance_global), str(self.light_infrared_global), str(self.light_uvindex_global),
                                "Null", "Null", "Null", "Null")
        # if(self.entities.sensor.pool_4_airpump_heat.state != "unknown"):

        # # Insert Pool 3 Data
        #     self.gsheets_insert(cur_time,
        #                         self.spreadsheet_id,
        #                         self.entities.sensor.pool_4_airpump_heat.last_updated,
        #                         "pool_4_airpump_temp",
        #                         self.entities.sensor.pool_4_airpump_heat.state, "Null", "Null", "Null", "Null", "Null", "Null")
        self.log("Pool 1 Temp =%s" % self.pool1_temp_global)
        if(self.pool_1_active):

            if(self.entities.sensor.pool_1_temp.state != "unknown" and  self.poll_p1_failed == False): # and self.pool1_temp_global != "unknown"):
                self.pool1_sensor_off_text = False
                self.pool1_sensor_off_count = 0
                if(self.pool1_heater_on == True):
                    p1_heat = "10"
                else:
                    p1_heat = "0"
                if(self.pool1_cooler_on == True):
                    p1_cool = "10"
                else:
                    p1_cool = "0"
            # Insert Pool 3 Data
                self.gsheets_insert(cur_time,
                                    self.spreadsheet_id,
                                    # self.entities.sensor.pool_1_temp.last_updated,
                                    cur_time,
                                    "pool_1_temp",
                                    # self.entities.sensor.pool_1_temp.state,
                                    str(self.pool1_temp_global),
                                    "Null", "Null", p1_heat, p1_cool, "Null", "Null")

            elif(self.entities.sensor.pool_1_temp.state == "unknown" and self.pool1_sensor_off_count>1 and self.pool1_sensor_off_text != True):
                text = "Pool 1 Sensor is Not Recording Please Check"

                self.text_notification(text)
                self.pool1_sensor_off_text = True


            else:
                self.pool1_sensor_off_count = self.pool1_sensor_off_count + 1

        self.log("Pool 2 Temp =%s" % self.pool2_temp_global)
        if(self.pool_2_active):
            if(self.entities.sensor.pool_2_temp.state != "unknown" and  self.poll_p2_failed == False):# and self.pool2_temp_global != "unknown"):
                self.pool2_sensor_off_count = 0
                self.pool2_sensor_off_text = False
                if(self.pool2_heater_on == True):
                    p2_heat = "5"
                else:
                    p2_heat = "0"
                # Only one cooling Implement so basing it all off pool 1
                if(self.pool1_cooler_on == True):
                    p2_cool = "5"
                else:
                    p2_cool = "0"
            # Insert Pool 3 Data
                self.gsheets_insert(cur_time,
                                    self.spreadsheet_id,
                                    # self.entities.sensor.pool_2_temp.last_updated,
                                    cur_time,
                                    "pool_2_temp",
                                    # self.entities.sensor.pool_2_temp.state,
                                    str(self.pool2_temp_global),
                                    "Null", "Null", p2_heat, p2_cool, "Null", "Null")

            elif(self.entities.sensor.pool_2_temp.state == "unknown" and self.pool2_sensor_off_count>1 and self.pool2_sensor_off_text != True):
                text = "Pool 2 Sensor is Not Recording Please Check"
                self.text_notification(text)
                self.pool2_sensor_off_text = True

            else:
                self.pool2_sensor_off_count = self.pool2_sensor_off_count + 1

        # Pool 2.5
        print(self.pool_2_point_five_active)
        if(self.pool_2_point_five_active):
            try:
                self.log("Pool 2.5 Temp =%s" % self.pool2_5_temp_global and  self.poll_p2_5_failed == False)
                if(self.entities.sensor.pool_2_5_temp.state != "unknown"):# and self.pool2_5_temp_global != "unknown"):
                    self.pool2_5_sensor_off_count = 0
                    self.pool2_5_sensor_off_text = False
                    if(self.pool2_5_heater_on == True):
                        p2_5_heat = "5"
                    else:
                        p2_5_heat = "0"
                    # Only one cooling Implement so basing it all off pool 1
                    if(self.pool2_5_cooler_on == True):
                        p2_5_cool = "5"
                    else:
                        p2_5_cool = "0"
                # Insert Pool 3 Data
                    self.gsheets_insert(cur_time,
                                        self.spreadsheet_id,
                                        # self.entities.sensor.pool_2_5_temp.last_updated,
                                        cur_time,
                                        "pool_2.5_temp",
                                        # self.entities.sensor.pool_2_5_temp.state,
                                        str(self.pool2_5_temp_global),
                                        "Null", "Null", p2_5_heat, p2_5_cool, "Null", "Null")

                elif(self.entities.sensor.pool_2_5_temp.state == "unknown" and self.pool2_5_sensor_off_count>1 and self.pool2_5_sensor_off_text != True):
                    text = "Pool 2.5 Sensor is Not Recording Please Check"
                    self.text_notification(text)
                    self.pool2_5_sensor_off_text = True

                else:
                    self.pool2_5_sensor_off_count = self.pool2_5_sensor_off_count + 1

            except Exception as e:
                print(e)
                print("no pool 2.5")
        return(cur_time)
     
    #---------------------Get Credentials for Google Sheets---------------------
        # @desc:   Obtain the credentials for the google sheets and use the client
        #          secret to complete the OAuth2 Verification Scheme.
        # @param:  none
        # @return: none
    #---------------------------------------------------------------------------
    def get_credentials(self):
        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        # credentials = store.get()
        try:
            credential_path = os.path.join(credential_dir, self.CLIENT_TOKEN_FILE_NAME)
            store = Storage(credential_path)
            credentials = store.get()
        except Exception as e:
            print('Working with flow-based credentials instantiation')
            credentials = None
            print(e)
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(self.CLIENT_SECRET_FILE, self.SCOPES)
            flow.user_agent = self.APPLICATION_NAME
            #credentials = tools.run_flow(flow, store)
            if flags:
                credentials = tools.run_flow(flow, store, flags)
            else: # Needed only for compatibility with Python 2.6
                credentials = tools.run(flow, store)
            self.log('Storing credentials to ' + credential_path)
        return credentials

    # Not Currently In Use
    # def gsheets_append(self, spreadsheet_id, last_updated, sheet_name, val1, val2):
    #     #time_str = time.strptime(last_updated, '%Y-%m-%dT%H:%M:%S')
    #     # last_updated looks something like:
    #     # 2018-12-04T22:34:30.389280+00:00
    #     # So replace the 'T' withs a space and trim the extra resolution
    #     self.log('***** gsheets_append last_updated:%s' % last_updated)
    #     time_str = str(last_updated)
    #     self.log('***** gsheets_append time_str:%s' % time_str)
    #     time_str = time_str.replace("T", " ", 1)
    #     time_str = time_str[:18]
    #     self.log('***** gsheets_append time_str:%s' % time_str)

    #     updated_dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
    #     self.log('***** gsheets_append updated_dt:%s' % updated_dt)

    #     #updated_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)
    #     my_timezone = timezone('US/Pacific')
    #     pacific_dt = updated_dt.replace(tzinfo=timezone('UTC')).astimezone(tz=my_timezone)
    #     self.log('***** gsheets_append pacfic_dt:%s' % pacific_dt)

    #     local_str = pacific_dt.strftime('%Y-%m-%d %H:%M:%S')
    #     self.log('***** gsheets_append local_str:%s' % local_str)

    #     fmt = '%Y-%m-%d %H:%M:%S'
    #     d = datetime.now()
    #     cur_time = d.strftime(fmt)

    #     if (val2 == "Null"):
    #         self.value_range_body = {"values": [[cur_time, local_str, val1]]}
    #     else:
    #         self.value_range_body = {"values": [[cur_time, local_str, val1, val2]]}

    #     # The A1 notation of a range to search for a logical table of data.
    #     # Values will be appended after the last row of the table.
    #     self.range_ = '%s!A2:E' % (sheet_name)  # sheet_name is the tab name to append to
    #     self.value_input_option = 'USER_ENTERED'
    #     self.insert_data_option = ''

    #     #request = self.service.spreadsheets().values().append(spreadsheetId=spreadsheet_id, range=self.range_, valueInputOption=self.value_input_option, body=self.value_range_body)
    #     #response = request.execute()
    #     ## TODO: Change code below to process the `response` dict:
    #     #self.log("google-api response: %s" % response)

    #     request = self.service.spreadsheets().values().append(spreadsheetId=spreadsheet_id, range=self.range_, valueInputOption=self.value_input_option, body=self.value_range_body)
    #     try :
    #         response = request.execute()
    #     except Exception as e:
    #         self.log("google-api ERROR: %s" % response)
    #         print(e)
    #     else :
    #         # TODO: Change code below to process the `response` dict:
    #         self.log("google-api response: %s" % response)

    # gsheets_add_sheet
    # Add a new tab to a google spreadsheet
    # This will throw an error if new_sheet_name already exists

    #---------------------Google Sheets Add New Sheet---------------------
        # @desc:    Add new sheet to the google sheet and create the sheet name
        # @param:   string(new_sheet_name)
        # @return:  (none)
    #---------------------------------------------------------------------
    def gsheets_add_sheet(self, new_sheet_name):
        req_body = {
            'requests': [{
                'addSheet':{
                    'properties':{
                    'title': new_sheet_name
                    }
                }
            }],
        }
        #sheet_props = SheetProperties(sheetId=self.spreadsheet_id, title=sheet_name)
        #request = self.service.spreadsheets().batchUpdate().AddSheetRequest(properties=sheet_props)
        #request = self.service.spreadsheets().batchUpdate().AddSheetRequest().SheetProperties(sheetId=self.spreadsheet_id, title=sheet_name, body={})
        request = self.service.spreadsheets().batchUpdate(spreadsheetId=self.spreadsheet_id, body=req_body)
        #response = request.execute()
        # TODO: Change code below to process the `response` dict:
        #self.log("google-api response: %s" % response)
        try :
            response = request.execute()
        except Exception as e:
            self.log("google-api ERROR: %s" % response)
            print(e)
        else :
            # TODO: Change code below to process the `response` dict:
            self.log("google-api response: %s" % response)

    #---------------------Google Sheets Insert---------------------
        # @desc:    Insert data into the Google Sheets page.  THis function uses a batch update
        #           These updates will move the entire google sheet down one and insert on top of the previous
        #           entry.
        # @param:   string(log_time), string(spreadsheet_id), string(last_updated), string(sheet_name), string(val1),
        #           string(val2), string(val3), string(val4), string(val5), string(val6), string(val7)
        # @return:  (None)
    #--------------------------------------------------------------
    def gsheets_insert(self, log_time, spreadsheet_id, last_updated, sheet_name, val1, val2, val3, val4, val5, val6, val7):
        # self.log('***** gsheets_insert last_updated:%s' % last_updated)
        self.log('***** gsheets_insert value:%s' % sheet_name)
        try:
            time_str = str(last_updated)
            # self.log('***** gsheets_insert time_str:%s' % time_str)
            time_str = time_str.replace("T", " ", 1)
            time_str = time_str[:18]
            # self.log('***** gsheets_insert time_str:%s' % time_str)

            updated_dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            # self.log('***** gsheets_insert updated_dt:%s' % updated_dt)

            #updated_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)
            my_timezone = timezone('US/Pacific')
            pacific_dt = updated_dt.replace(tzinfo=timezone('UTC')).astimezone(tz=my_timezone)
            # self.log('***** gsheets_insert pacfic_dt:%s' % pacific_dt)

            local_str = pacific_dt.strftime('%Y-%m-%d %H:%M:%S')
            local_str = last_updated
        except:
            print("Wrong conversion.")
        # self.log('***** gsheets_insert local_str:%s' % local_str)

        # fmt = '%Y-%m-%d %H:%M:%S'
        # d = datetime.now()
        # cur_time = d.strftime(fmt)

        spreadsheet_str = str(spreadsheet_id)
        # Temp
        if (val2 == "Null" and val3 == "Null" and val4 == "Null" and val5 == "Null" and val6 == "Null" and val7 == "Null"):
            data = log_time + "," + local_str + "," + val1
        # Pools 
        elif (val2 == "Null" and val3 == "Null"):
            data = log_time + "," + local_str + "," + val1 + "," + val4 + "," + val5
        # Temp & Humidity
        elif(val3 == "Null"):
            data = log_time + "," + local_str + "," + val1 + "," + val2
        # Light
        elif(val4 =="Null" and val5 == "Null"):
            data = log_time + "," + local_str + "," + val1 + "," + val2 + "," + val3
        # Averages
        elif(val7 =="Null"):
            data = log_time + "," + val1 + "," + val2 + "," + val3 + "," + val4 + "," + val5 + "," + val6
        else:
            data =  val1 + "," + val2 + "," + val3 + "," + val4 + "," + val5 + "," + val6 + "," + val7


        if(sheet_name ==  "outside_temp"):
            #sheet = o #TEST
            sheet = self.outside_spreadsheet_id
        elif(sheet_name ==  "pool4_temp"):
            #sheet = 1278687724 #TEST
            sheet = self.pool_4_spreadsheet_id
        elif(sheet_name ==  "pool3_temp"):
            #sheet = 1097097535 #TEST
            sheet = self.pool_3_spreadsheet_id
        elif(sheet_name == "greenhouse_temp"):
            #sheet = 1077133875 #TEST
            sheet = self.greenhouse_spreadsheet_id
        # elif(sheet_name == "Photosynq"):
        #     #sheet = 1077133875 #TEST
        #     sheet = 1809622314
        elif(sheet_name == "pool_4_airpump_temp"):
            #sheet = 1077133875 #TEST
            sheet = self.pool_4_airpump_sheet
        elif(sheet_name == "Averages"):
            sheet = self.average_sheet

        elif(sheet_name =="pool_1_temp"):
            sheet = self.pool_1_spreadsheet_id

        elif(sheet_name =="pool_2_temp"):
            sheet = self.pool_2_spreadsheet_id

        elif(sheet_name =="pool_2.5_temp"):
            sheet = self.pool_2_5_spreadsheet_id
        else:
            sheet = self.sunlight_spreadsheet_id

        batch_update_spreadsheet_request_body = {
                #Move all rows down to allow for new insert
                "requests": [{
                    "insertRange": {
                        "range": {
                            "sheetId": sheet,
                            "startRowIndex": self.row_1,
                            "endRowIndex": self.row_2
                        },
                        "shiftDimension": "ROWS"
                    }
                },
                {
                    "pasteData": {
                        "data":  data,
                        "type": "PASTE_NORMAL",
                        "delimiter": ",",
                        "coordinate": {
                            "sheetId": sheet,
                            "rowIndex": self.row_1
                        }
                    }
                }
                ],  # TODO: Update placeholder value.
                # TODO: Add desired entries to the request body.
            }

        request = self.service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=batch_update_spreadsheet_request_body)
        # response = request.execute()
        try :
            response = request.execute()
            # self.log("Made it to response: %s" % response)

        except Exception as e:
            self.log("google-api ERROR: %s" % response)
            print(e)
        else :
            # TODO: Change code below to process the `response` dict:
            self.log("google-api response: %s" % response)


    


    #---------------------Retrieve Data From Google Sheet---------------------
        # @desc:    Retrieve data from data sheet and use the sheet range and spreadsheet id
        #           to Grab the data and return it as a list.        

        # @param:  string(sheet_range), string(spreadsheet_id)
        # @return: none
    #-------------------------------------------------------------------------
    def gsheets_retrieve_data(self, sheet_range, spreadsheet_id):
        # timeout = Timeout(15, exception)
        # def handler(signum, frame):
        #     
        #     raise Exception('Action took too much time')

        # signal.signal(signal.SIGALRM, handler)
        # signal.alarm(10)

        # signal.signal(signal.SIGALRM, alarm_handler)
        # signal.alarm(8)
        if(self.check_ping() == True):
            try:

                self.log('***** Retrieving Control Values *****')
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id, range=sheet_range).execute()
                values = result.get('values', [])
                sensor_range = []
                count = 0
                if not values:
                    print('No data found.')
                else:
                    # print('Obtained values')
                    for row in values:
                        # Print columns A and E, which correspond to indices 0 and 4.
                        # print('%s' % (row[0]))
                        sensor_range.append(row[0]) 
                        count = count + 1
                # print(sensor_range[0])
                # print(sensor_range[1])
                return(sensor_range)
            # except TimeOutException as ex:
            except Exception as ex:
                # timeout.cancel()
                print(ex)
                print("-------------Failed Retrieve Data!!!!!!------------")
        else:
            print("Ping Check Failed, internet is not connecting.")



    #---------------------Send Text---------------------
        # @desc:    Send a text message to a specific person
        # @param:  string(message), string(person)
        # @return: none
    #---------------------------------------------------
    def send_text(self, message, person):
        # Replace the number with your own, or consider using an argument\dict for multiple people.
        message_subject = '--Greenspring Text Notification System--'
        text_user = os.getenv('TEXT_USER')
        text_pass = os.getenv('TEXT_PASSWORD')
        auth = (text_user, text_pass)

        aaron_phone= os.getenv('AARON_PHONE')
        sasha_phone= os.getenv('SASHA_PHONE')
        tarah_phone= os.getenv('TARAH_PHONE')
        conrad_phone= os.getenv('CONRAD_PHONE')
        elle_phone= os.getenv('ELLE_PHONE')
        current_time = self.get_time()
        current_time = str(current_time)

        if(person == "Aaron"):
            to_number = aaron_phone.format(carriers['verizon'])
            message = "From: %s\r\n" % auth[0] + "To: %s\r\n" % to_number + "Subject: %s\r\n" % message_subject + "\r\n" + str(current_time) + '  ' + message
        elif(person == "Sasha"):
            to_number = sasha_phone.format(carriers['tmobile'])
            message = "From: %s\r\n" % auth[0] + "To: %s\r\n" % to_number + "Subject: %s\r\n" % message_subject + "\r\n" + str(current_time) + '  ' + message
        elif(person == "Tarah"):
            to_number = tarah_phone.format(carriers['sprint'])
            message = "From: %s\r\n" % auth[0] + "To: %s\r\n" % to_number + "Subject: %s\r\n" % message_subject + "\r\n" + str(current_time) + '  ' + message
        elif(person == "Conrad"):
            to_number = conrad_phone.format(carriers['att'])
            message = "From: %s\r\n" % auth[0] + "To: %s\r\n" % to_number + "Subject: %s\r\n" % message_subject + "\r\n" + str(current_time) + '  ' + message
        elif(person == "Elle"):
            to_number = elle_phone.format(carriers['att'])
            message = "From: %s\r\n" % auth[0] + "To: %s\r\n" % to_number + "Subject: %s\r\n" % message_subject + "\r\n" + str(current_time) + '  ' + message
        # to_number = '2099147599{}'.format(carriers['att'])
        # auth = ('greenspringtext@yahoo.com', 'GSTextSMS')
        # auth = ('greenspringtext@outlook.com', 'GreenspringText')
        
        self.log('***** Gsheets Text to be sent: %s' % message)

        server = smtplib.SMTP( "smtp.gmail.com", 587)
        server.starttls()
        server.login(auth[0], auth[1])
        text = str(message)
        text = current_time + '  ' +  text
        # Send text message through SMS gateway of destination number
        server.sendmail( auth[0], to_number, text)

    #---------------------Check Sensors and report ---------------------
        # @desc:    Checks all the sensors and if they are outside the range of expected values send
        #           a text that will explain what is wrong, then send another once the temperature returns to normal

        # @param:  float(farm_high), float(farm_low), float(pool_high), float(pool_low), float(greenhouse_high), float(greenhouse_low)
        # @return: none
    #-------------------------------------------------------------------
    def check_sensors_text(self, farm_high, farm_low, pool_high, pool_low, greenhouse_high, greenhouse_low):
        #******************** Outside Check Sensors ************************* 
        try:
            if(self.entities.sensor.outside_temp.state != "unknown"):
                outside_conv = float(self.entities.sensor.outside_temp.state)
                if(outside_conv > float(farm_high) and self.farm_flag != True):
                    testtext = '__Outside Temperature Over Limit__ ' + farm_high + ' C __Value__ '+ str(self.entities.sensor.outside_temp.state)+ ' C'
                    self.text_notification(testtext)
                    self.farm_flag = True
                    self.log("Farm Temp over Limit: %s" % self.entities.sensor.outside_temp.state)
                elif(outside_conv < float(farm_low) and self.farm_flag != True):
                    testtext = '__Outside Temperature Under Limit__ ' +  farm_low + ' C __Value__ '+ str(self.entities.sensor.outside_temp.state)+ ' C'
                    self.text_notification(testtext)
                    self.farm_flag = True
                    self.log("Farm Temp under Limit: %s" % self.entities.sensor.outside_temp.state)
        except:
            print("outside check failed")

         #******************** Pool 3 Check Sensors ************************* 
        try:
            if(self.pool_3_active):
                if(self.entities.sensor.pool3_temp.state != "unknown"):
                    pool3_conv = float(self.entities.sensor.pool3_temp.state)
                    
                    if(pool3_conv > float(pool_high) and self.pool3_flag != True):
                        testtext = '___Pool 3 Temperature Over Limit___ ' + pool_high + ' C __Value__ ' + str(self.entities.sensor.pool3_temp.state)+ ' C'
                        self.text_notification(testtext)
                        self.log("Pool 3 Temp over Limit")
                        self.pool3_flag = True
                    elif(pool3_conv < float(pool_low) and self.pool3_flag != True):
                        testtext = '__Pool 3 Temperature Under Limit__ ' + pool_low + ' C __Value__ '+ str(self.entities.sensor.pool3_temp.state)+ ' C'
                        self.text_notification(testtext)
                        self.log("Pool 3 Temp under Limit")
                        self.pool3_flag = True
        except:
            print("Pool 3 check failed")

         #******************** Pool 4 Check Sensors ************************* 
        if(self.pool_4_active):
            if(self.entities.sensor.pool4_temp.state != "unknown"):
                pool4_conv = float(self.entities.sensor.pool4_temp.state)
                
                if(pool4_conv > float(pool_high) and self.pool4_flag != True):
                    testtext = '___Pool 4 Temperature Over Limit___ ' + pool_high + ' C __Value__ ' + str(self.entities.sensor.pool4_temp.state)+ ' C'
                    self.text_notification(testtext)
                    self.log("Pool 4 Temp over Limit")
                    self.pool4_flag = True
                elif(pool4_conv < float(pool_low) and self.pool4_flag != True):
                    testtext = '__Pool 4 Temperature Under Limit__ ' + pool_low + ' C __Value__ '+ str(self.entities.sensor.pool4_temp.state)+ ' C'
                    self.text_notification(testtext)
                    self.log("Pool 4 Temp under Limit")
                    self.pool4_flag = True

        #************************* Greenhouse Check ************************* 
        if(self.entities.sensor.greenhouse_temp.state != "unknown"):
            greenhouse_conv = float(self.entities.sensor.greenhouse_temp.state) 
            if(greenhouse_conv > float(greenhouse_high) and self.greenhouse_flag != True):
                testtext = '__Greenhouse Temperature Over Limit__ ' + greenhouse_high + ' C __Value__ '+ str(self.entities.sensor.greenhouse_temp.state)+ ' C'
             
                self.text_notification(testtext)
                self.greenhouse_flag = True
                self.log("greenhouse Temp over Limit")
            elif(greenhouse_conv < float(greenhouse_low) and self.greenhouse_flag != True):
                testtext = '__Greenhouse Temperature Under Limit__ ' + greenhouse_low + ' C __Value__ '+ str(self.entities.sensor.greenhouse_temp.state)+ ' C'
                self.text_notification(testtext)
                self.greenhouse_flag = True
                self.log("greenhouse Temp under Limit")

        #******************** Pool 1 Check Sensors ************************* 

        if(self.pool_1_active):
            if(self.entities.sensor.pool_1_temp.state != "unknown"):
                pool1_conv = float(self.entities.sensor.pool_1_temp.state)
                
                if(pool1_conv > float(pool_high) and self.pool1_flag != True):
                    testtext = '___Pool 1 Temperature Over Limit___ ' + pool_high + ' C __Value__ ' + str(self.entities.sensor.pool_1_temp.state)+ ' C'
                    self.text_notification(testtext)
                    self.log("Pool 4 Temp over Limit")
                    self.pool1_flag = True
                elif(pool1_conv < float(pool_low) and self.pool1_flag != True):
                    testtext = '__Pool 1 Temperature Under Limit__ ' + pool_low + ' C __Value__ '+ str(self.entities.sensor.pool_1_temp.state)+ ' C'
                    self.text_notification(testtext)
                    self.log("Pool 1 Temp under Limit")
                    self.pool4_flag = True

        #******************** Pool 2 Check Sensors ************************* 
        if(self.pool_2_active):

            if(self.entities.sensor.pool_2_temp.state != "unknown"):
                pool2_conv = float(self.entities.sensor.pool_2_temp.state)
                
                if(pool2_conv > float(pool_high) and self.pool2_flag != True):
                    testtext = '___Pool 2 Temperature Over Limit___ ' + pool_high + ' C __Value__ ' + str(self.entities.sensor.pool_2_temp.state)+ ' C'
                    self.text_notification(testtext)
                    self.log("Pool 2 Temp over Limit")
                    self.pool2_flag = True
                elif(pool2_conv < float(pool_low) and self.pool2_flag != True):
                    testtext = '__Pool 2 Temperature Under Limit__ ' + pool_low + ' C __Value__ '+ str(self.entities.sensor.pool_2_temp.state)+ ' C'
                    self.text_notification(testtext)
                    self.log("Pool 2 Temp under Limit")
                    self.pool2_flag = True


        #******************** Pool 2.5 Check Sensors ************************* 

        if(self.pool_2_point_five_active):
            if(self.entities.sensor.pool_2_5_temp.state != "unknown"):
                pool2_5_conv = float(self.entities.sensor.pool_2_5_temp.state)
                
                if(pool2_5_conv > float(pool_high) and self.pool2_5_flag != True):
                    testtext = '___Pool 2.5 Temperature Over Limit___ ' + pool_high + ' C __Value__ ' + str(self.entities.sensor.pool_2_5_temp.state)+ ' C'
                    self.text_notification(testtext)
                    self.log("Pool 2.5 Temp over Limit")
                    self.pool2_5_flag = True
                elif(pool2_5_conv < float(pool_low) and self.pool2_5_flag != True):
                    testtext = '__Pool 2.5 Temperature Under Limit__ ' + pool_low + ' C __Value__ '+ str(self.entities.sensor.pool_2_5_temp.state)+ ' C'
                    self.text_notification(testtext)
                    self.log("Pool 2.5 Temp under Limit")
                    self.pool2_5_flag = True

        #************************* Check if values returned to Normal ************************* 
        if(self.entities.sensor.outside_temp.state != "unknown"):
            if((float(farm_high) > float(self.entities.sensor.outside_temp.state) > float(farm_low)) and self.farm_flag == True):
                # outside_conv = float(self.entities.sensor.outside_temp.state)
                testtext = '__Outside Temperature Returned to Acceptable Level__ ' + str(self.entities.sensor.outside_temp.state)+ ' C'
                self.text_notification(testtext)
                self.farm_flag = False

        if(self.entities.sensor.pool3_temp.state != "unknown" and self.pool_3_active):
            if((float(pool_high) > float(self.entities.sensor.pool3_temp.state) > float(pool_low)) and self.pool3_flag == True):
                # pool3_conv = float(self.entities.sensor.pool3_temp.state)
                testtext = '__Pool3 Temperature Returned to Acceptable Level__ ' + str(self.entities.sensor.pool3_temp.state) + ' C' 
                self.text_notification(testtext)
                self.pool3_flag = False

        if(self.entities.sensor.pool4_temp.state != "unknown" and self.pool_4_active):
            if((float(pool_high) > float(self.entities.sensor.pool4_temp.state) > float(pool_low)) and self.pool4_flag == True):
                # pool3_conv = float(self.entities.sensor.pool3_temp.state)
                testtext = '__Pool4 Temperature Returned to Acceptable Level__ ' + str(self.entities.sensor.pool4_temp.state) + ' C' 
                self.text_notification(testtext)
                self.pool4_flag = False

        if(self.entities.sensor.greenhouse_temp.state != "unknown"):
            if((float(greenhouse_high) > float(self.entities.sensor.greenhouse_temp.state) > float(greenhouse_low)) and self.greenhouse_flag == True):
                # greenhouse_conv = float(self.entities.sensor.greenhouse_temp.state)
                testtext = '__Greenhouse Temperature Returned to Acceptable Level__ ' + str(self.entities.sensor.greenhouse_temp.state) + ' C'
                self.text_notification(testtext)
                self.greenhouse_flag = False

        if(self.entities.sensor.pool_1_temp.state != "unknown" and self.pool_1_active):
            if((float(pool_high) > float(self.entities.sensor.pool_1_temp.state) > float(pool_low)) and self.pool1_flag == True):
                # pool1_conv = float(self.entities.sensor.pool1_temp.state)
                testtext = '__Pool 1 Temperature Returned to Acceptable Level__ ' + str(self.entities.sensor.pool_1_temp.state) + ' C' 
                self.text_notification(testtext)
                self.pool1_flag = False

        if(self.entities.sensor.pool_2_temp.state != "unknown" and self.pool_2_active):
            if((float(pool_high) > float(self.entities.sensor.pool_2_temp.state) > float(pool_low)) and self.pool2_flag == True):
                # pool1_conv = float(self.entities.sensor.pool1_temp.state)
                testtext = '__Pool 2 Temperature Returned to Acceptable Level__ ' + str(self.entities.sensor.pool_2_temp.state) + ' C' 
                self.text_notification(testtext)
                self.pool2_flag = False

        if(self.entities.sensor.pool_2_5_temp.state != "unknown" and self.pool_2_point_five_active):
            if((float(pool_high) > float(self.entities.sensor.pool_2_5_temp.state) > float(pool_low)) and self.pool2_5_flag == True):
                # pool1_conv = float(self.entities.sensor.pool1_temp.state)
                testtext = '__Pool 2.5 Temperature Returned to Acceptable Level__ ' + str(self.entities.sensor.pool_2_5_temp.state) + ' C' 
                self.text_notification(testtext)
                self.pool2_5_flag = False


    def text_notification(self, textout):
        textout = textout + "                                                                                                                                                                                                                                                                                                          "
        self.send_text(textout, "Conrad")
        self.send_text(textout, "Tarah")
        self.send_text(textout, "Sasha")
        self.send_text(textout, "Aaron")
        self.send_text(textout, "Elle")
        
        
        
        
        
    #---------------------Get Weather---------------------
        # @desc:    Function for the obtaining weather information from the pywom 

        # @param: time, sheet_id, spreadsheet_id, wind_speed,wind_deg, wind_gust, humidity, temp, temp_max, temp_min, rain, clouds
        # @return: none
    #-----------------------------------------------------
    def get_weather(self):
        pyowm_api_key = os.environ.get('PYOWM_API_KEY')
        pyowm_api_key = str(pyowm_api_key)
        owm = pyowm.OWM(pyowm_api_key)  # You MUST provide a valid API key
        weather_list = []
        observation = owm.weather_at_id(self.brentwood_id)
        w = observation.get_weather()
        print(w)                      # <Weather - reference time=2013-12-18 09:20,
                                      # status=Clouds>
        # Weather details
        wind = w.get_wind()     # {'speed': 4.6, 'deg': 330}
        humidity = w.get_humidity()            
        temp = w.get_temperature('celsius') # {'temp_max': 10.5, 'temp': 9.7, 'temp_min': 9.0}
        rain = w.get_rain()
        clouds = w.get_clouds()

        weather_list.append(wind["speed"])
        try:
            if(wind["deg"] != ""):
                weather_list.append(wind["deg"])
        except:
            weather_list.append("0")
        try:
            if(wind["gust"] != ""):
                weather_list.append(wind["gust"])
                if(wind["gust"] >self.wind_gust_limit):
                    # self.text_notification("Wind gust is very High at the Farm, please take precautions.")
                    print("Very windy REplace")

        except:
            weather_list.append("0")
        weather_list.append(humidity)   
        weather_list.append(temp["temp"])
        weather_list.append(temp["temp_max"])
        weather_list.append(temp["temp_min"])
        try:
            if(rain != "{}" and rain > 0):
                weather_list.append(rain)
        except:
            weather_list.append("0")
        # weather_list.append(rain)
        weather_list.append(clouds)
        #2 hours is 7200 seconds
        sunrise = w.get_sunrise_time()
        sunset = w.get_sunset_time()
        
        sunrise = int(sunrise)-25200
        sunset = int(sunset)-25200
        
        weather_list.append(sunrise)
        weather_list.append(sunset)
        sunset_readable = datetime.utcfromtimestamp(sunset).strftime('%Y-%m-%d %H:%M:%S')
        sunrise_readable = datetime.utcfromtimestamp(sunrise).strftime('%Y-%m-%d %H:%M:%S')

        # {wind speed,wind deg, wind gust, humidity, temp, temp_max, temp_min, rain, clouds, sunrise, sunset} 11 units
        print(weather_list)        
        
        return weather_list


    #---------------------Weather Insert---------------------
        # @desc:    Insert Command for the Weather API.
        #           Works the same as the other insert command but it is specfically tailored to input the large amount of
        #           of Data that comes from the openweathermap api

        # @param: time, sheet_id, spreadsheet_id, wind_speed,wind_deg, wind_gust, humidity, temp, temp_max, temp_min, rain, clouds
        # @return: none
    #--------------------------------------------------------
    def weather_insert(self, time, sheet_id, spreadsheet_id, wind_speed,wind_deg, wind_gust, humidity, temp, temp_max, temp_min, rain, clouds):
        spreadsheet_str = str(spreadsheet_id)
        sheet = sheet_id
        if(sheet == self.weather_forecast_sheet):
            start_row_index = 1
            end_row_index = 2
        else:
            start_row_index = 41
            end_row_index = 42
        data = time + "," + str(temp) + "," + str(temp_min) + "," + str(temp_max) + "," + str(wind_speed) + "," + str(wind_deg) + "," + str(wind_gust) + "," + str(rain) + "," + str(clouds) + "," + str(humidity)
        # print(data)
        batch_update_spreadsheet_request_body = {
                #Move all rows down to allow for new insert
                "requests": [{
                    "insertRange": {
                        "range": {
                            "sheetId": sheet,
                            "startRowIndex": start_row_index,
                            "endRowIndex": end_row_index
                        },
                        "shiftDimension": "ROWS"
                    }
                },
                {
                    "pasteData": {
                        "data":  data,
                        "type": "PASTE_NORMAL",
                        "delimiter": ",",
                        "coordinate": {
                            "sheetId": sheet,
                            "rowIndex": start_row_index
                        }
                    }
                }
                ],  # TODO: Update placeholder value.
                # TODO: Add desired entries to the request body.
            }

        request = self.service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=batch_update_spreadsheet_request_body)
        # response = request.execute()
        try :
            # print("avoid try")
            response = request.execute()
            # self.log("Made it to response: %s" % response)

        except :
            response = request.execute()
            self.log("google-api ERROR: %s" % response)
        else :
            # TODO: Change code below to process the `response` dict:
            self.log("google-api response: %s" % response)


    #---------------------Weather Insert---------------------
        # @desc:    Insert Command for the Weather API.
        #           Works the same as the other insert command but it is specfically tailored to input the large amount of
        #           of Data that comes from the openweathermap api

        # @param: time, sheet_id, spreadsheet_id, wind_speed,wind_deg, wind_gust, humidity, temp, temp_max, temp_min, rain, clouds
        # @return: none
    #--------------------------------------------------------
    def bulk_weather_insert(self, time, sheet_id, spreadsheet_id, wind_speed,wind_deg, wind_gust, humidity, temp, temp_max, temp_min, rain, clouds):
        spreadsheet_str = str(spreadsheet_id)
        sheet = sheet_id
        if(sheet == self.weather_forecast_sheet):
            start_row_index = 1
            end_row_index = 40
        else:
            start_row_index = 41
            end_row_index = 42
        data = time + "," + str(temp) + "," + str(temp_min) + "," + str(temp_max) + "," + str(wind_speed) + "," + str(wind_deg) + "," + str(wind_gust) + "," + str(rain) + "," + str(clouds) + "," + str(humidity)
        # print(data)
        batch_update_spreadsheet_request_body = {
                #Move all rows down to allow for new insert
                "requests": [{
                    "insertRange": {
                        "range": {
                            "sheetId": sheet,
                            "startRowIndex": start_row_index,
                            "endRowIndex": end_row_index
                        },
                        "shiftDimension": "ROWS"
                    }
                },
                {
                    "pasteData": {
                        "data":  data,
                        "type": "PASTE_NORMAL",
                        "delimiter": ",",
                        "coordinate": {
                            "sheetId": sheet,
                            "rowIndex": start_row_index
                        }
                    }
                }
                ],  # TODO: Update placeholder value.
                # TODO: Add desired entries to the request body.

            }

        request = self.service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=batch_update_spreadsheet_request_body)
        # response = request.execute()
        try :
            # print("avoid try")
            response = request.execute()
            # self.log("Made it to response: %s" % response)

        except :
            self.log("google-api ERROR: %s" % response)
        else :
            # TODO: Change code below to process the `response` dict:
            self.log("google-api response: %s" % response)

    # The weather call function that calls get_weather function and saves the data to a list and then inserts
    # that list into the weather_insert function
    #---------------------Weather Call---------------------
        # @desc:    Simple function to call the get weather call and use it to return the list of weather values, then
        #           then pass the data to the weather insert function, and finally return the weather list.

        # @param: datetime(time), int(spreadsheet_id)
        # @return: none
    #------------------------------------------------------
    def weather_call(self, time, spreadsheet_id):
        weather = self.get_weather()    
        self.weather_insert(time, 1300964882, self.spreadsheet_id,  weather[0], weather[1], weather[2],
                            weather[3], weather[4],weather[5], weather[6], weather[7], weather[8])
        return(weather)

    #---------------------Control Lights---------------------
        # @desc:    This function is to control lights inside the pools,  This is done by checking the sensor
        #           values and then send a message to the sonoff switch dependent on what the sensor reading is.
        #           

        # @param: int(light_limit)
        # @return: none
    #---------------------------------------------------------
    def control_lights(self, light_limit):
        if(self.entities.sensor.light_illuminance.state != "unknown"):
            light_conv = float(self.entities.sensor.light_illuminance.state)
            if(light_conv < float(light_limit) and self.light_flag != True):
                self.send_http(self.pool3_lights_turn_on)
                self.light_flag = True
                self.log("Light Under Limit: %s" % self.entities.sensor.light_illuminance.state)
            elif(light_conv > float(light_limit) and self.light_flag == True):
                self.send_http(self.pool3_lights_turn_off)
                self.light_flag = False
                self.log("Farm Temp under Limit: %s" % self.entities.sensor.light_illuminance.state)
    #---------------------Send http message---------------------
        # @desc:    Send http message with MQTT command for a sonoff wifi switch.  This command
        #           is used to control the sonoff switches and turn on or off the relay to control 
        #           some electrical device.

        # @param: string(URL)
        # @return: none
    #--------------------------------------------------------
    def send_http(self, URL):
        try:
            r = requests.get(url = URL)
        except:
            self.log("Failed to http get request to %s", URL)

    #---------------------Control Pool Temperature---------------------
        # @desc:    Controls all the algae pools temperature by turning on and off the relays that control
        #           heating and cooling systems for each pool.  This is fascillitated with http requests and the mqtt commands
        #           which allow it to directly control the relays based on the current temperature.

        # @param: (float)pool1_high, (float)pool1_low_day, (float)pool1_low_night , (float)pool2_high, (float)pool2_low_day, (float)pool2_low_night, (float)pool3_high,
        #          (float)pool3_low_day, (float)pool3_low_night, (float)pool4_high, (float)pool4_low_day, (float)pool4_low_night, (datetime)sunrise, (datetime)sunset 
        # @return: None
    #------------------------------------------------------------------
    def control_pool_temp(self,pool1_high, pool1_low_day, pool1_low_night , pool2_high,pool2_low_day, pool2_low_night, pool3_high, pool3_low_day, pool3_low_night, pool4_high, pool4_low_day, pool4_low_night, sunrise, sunset, pool2_5_high, pool2_5_low_day, pool2_5_low_night):
        time = self.get_time()

        # self.log("Time: %s"%str(time))
        if(sunset == 0 and sunrise == 0):
            sunset_use = 1571164200 - 7200
            sunset_use = datetime.utcfromtimestamp(sunset_use).strftime('%H:%M:%S')
            sunrise_use = 1571122800 - 10800
            sunrise_use = datetime.utcfromtimestamp(sunrise_use).strftime('%H:%M:%S')
            self.log("Sunrise time: %s"%str(sunrise_use))
            self.log("Sunset time: %s"%str(sunset_use))
        else:
            sunset_use = sunset - 7200
            sunset_use = datetime.utcfromtimestamp(sunset_use).strftime('%H:%M:%S')
            sunrise_use = sunrise - 10800
            sunrise_use = datetime.utcfromtimestamp(sunrise_use).strftime('%H:%M:%S')
            # self.log("Sunrise time: %s"%str(sunrise_use))
            # self.log("Sunset time: %s"%str(sunset_use))

        peak_energy_start = datetime.utcfromtimestamp(1573029000).strftime('%H:%M:%S')
        peak_energy_end = datetime.utcfromtimestamp(1573075800).strftime('%H:%M:%S')
        # self.log("Peak Energy Start: %s"%str(peak_energy_start))
        # self.log("Peak Energy End: %s"%str(peak_energy_end))

        # if(time > peak_energy_start and time < peak_energy_end):
        #     self.log("Peak Energy Cost Time, Turn off Heaters unless dangerously low")
        #     pool3_low = pool3_low_night
        #     pool4_low = pool4_low_night

        # If time is between sunrise and sunset then use the day temperature values
        if(time > sunrise_use and time < sunset_use):
            self.log("Its Day: %s"%str(time))
            pool1_low = pool1_low_day
            pool2_low = pool2_low_day
            pool2_5_low = pool2_5_low_day
            pool3_low = pool3_low_day
            pool4_low = pool4_low_day
        # If time 
        elif(time < sunrise_use or time > sunset_use):
            self.log("Its Night: %s"%str(time))
            pool1_low = pool1_low_night
            pool2_low = pool2_low_night
            pool2_5_low = pool2_5_low_night
            pool3_low = pool3_low_night
            pool4_low =  pool4_low_night

        #---------------------------------- Need to update!!! ----------------------------------
        self.check_relays()
        self.check_sensor()

        #-----------------Pool 1-------------------------
        if(self.pool_1_active):
            try:
                if(self.entities.sensor.pool_1_temp.state != "unknown"):
                    pool1_conv = float(self.entities.sensor.pool_1_temp.state)
                    if(pool1_conv > float(pool1_high) and self.pool1_cooler_on != True and self.pool1_heater_on != True):
                        self.log("Pool 1 Cooler Turned On. Too Hot Temp: %s" % self.entities.sensor.pool_1_temp.state)
                        self.pool1_cooler_on = True 
                        self.pool1_cooler_needs_on = True
                        try:
                            self.send_http(self.pool1_cooler_turn_on)
                            # textout = 'Pool 1 Cooler Turned on at ' + str(self.entities.sensor.pool_1_temp.state)
                            # self.send_text(textout, "Conrad")
                        # Pool 4 Cooler is not responding
                        except:
                            self.log("Failed to http get request to the site.")
                            if(self.p1_cooler_broken_on_checked == False):
                                self.check_sonoff_status()
                                self.p1_cooler_broken_on_checked = True
                            elif(self.p1_cooler_broken_on_text == False):
                                testtext = 'Pool 1 Turn Cooler On Failed, Please Check'
                                self.text_notification(testtext)
                                self.p1_cooler_broken_on_text = True
                    if(pool1_conv < float(pool1_low) and self.pool1_heater_on != True and self.pool1_cooler_on != True):
                        self.log("Pool 1 Heater Turned On. Too Cool Temp: %s"% self.entities.sensor.pool_1_temp.state)
                        self.pool1_heater_on = True
                        try:

                            self.send_http(self.pool1_heater_turn_on)
                            print("Pool 1 heater successfully turned on")
                        # Pool 1 Heater is not responding
                        except Exception as e:
                            print(e)
                            if(self.p1_heater_broken_on_checked == False):
                                self.check_sonoff_status()
                                self.p1_heater_broken_on_checked = True
                            elif(self.p1_heater_broken_on_text == False):
                                self.log("Failed to http get request to the site.")
                                testtext = 'Pool 1 Turn Heater On Failed, Please Check'
                                self.text_notification(testtext)
                                self.p1_heater_broken_on_text==True
                    # Cooler Off Pool 1
                    if(self.pool_2_active):
                        if(pool1_conv < float(pool1_high) and self.pool1_cooler_on == True and self.pool2_cooler_on == False):
                            print(self.pool2_cooler_on)
                            
                            self.pool1_cooler_on = False
                            self.pool1_cooler_needs_on = False
                            if(self.pool2_cooler_needs_on == False):
                                try:
                                    self.log("Pool 1 Cooler Turned Off. Current Temp: %s"% self.entities.sensor.pool_1_temp.state)
                                    self.send_http(self.pool1_cooler_turn_off)
                                except:
                                    if(self.p1_cooler_broken_off_checked == False):
                                        self.check_sonoff_status()
                                        self.p1_cooler_broken_off_checked = True
                                    elif(self.p1_cooler_broken_off_text == False): 
                                        self.log("Failed to http get request to the site.")
                                        testtext = 'Pool 1 Turn Cooler Off Failed, Please Check'
                                        self.text_notification(testtext)
                    else:
                        if(pool1_conv < float(pool1_high) and self.pool1_cooler_on == True):
                            self.log("Pool 1 Cooler Turned Off. Current Temp: %s"% self.entities.sensor.pool_1_temp.state)
                            self.pool1_cooler_on = False
                            try:
                                self.send_http(self.pool1_cooler_turn_off)
                            except:
                                if(self.p1_cooler_broken_off_checked == False):
                                    self.check_sonoff_status()
                                    self.p1_cooler_broken_off_checked = True
                                elif(self.p1_cooler_broken_off_text == False): 
                                    self.log("Failed to http get request to the site.")
                                    testtext = 'Pool 1 Turn Cooler Off Failed, Please Check'
                                    self.text_notification(testtext)
                    if(pool1_conv > float(pool1_low) and self.pool1_heater_on == True):
                        self.log("Pool 1 Heater Turned Off. Current Temp: %s"% self.entities.sensor.pool_1_temp.state)
                        self.pool1_heater_on = False
                        try:
                            self.send_http(self.pool1_heater_turn_off)
                        except:
                            if(self.p1_heater_broken_off_checked == False):
                                self.check_sonoff_status()
                                self.p1_heater_broken_off_checked = True
                            elif(self.p1_heater_broken_off_text == False): 
                                self.log("Failed to http get request to the site.")
                                testtext = 'Pool 1 Turn Heater Off Failed, Please Check'
                                self.text_notification(testtext)
            except Exception as e:
                print(e)
                # testtext = 'Pool 1 Turn Cooler is off'
                # self.send_text(testtext, "Conrad")
        #-----------------Pool 2-------------------------
        if(self.pool_2_active):
            try:
                if(self.entities.sensor.pool_2_temp.state != "unknown"):
                    pool2_conv = float(self.entities.sensor.pool_2_temp.state)
                    if(pool2_conv > float(pool2_high) and self.pool1_cooler_on != True  and self.pool2_cooler_on != True and self.pool2_heater_on != True):
                        self.log("Pool 2 Cooler Turned On. Too Hot Temp: %s" % self.entities.sensor.pool_2_temp.state)
                        self.pool2_cooler_on = True 
                        self.pool2_cooler_needs_on = True
                        try:
                            self.send_http(self.pool1_cooler_turn_on)
                            # textout = 'Pool 1 & 2 Cooler Turned on at ' + str(self.entities.sensor.pool_2_temp.state)
                            # self.send_text(textout, "Conrad")
                        # Pool 4 Cooler is not responding
                        except:
                            self.log("Failed to http get request to the site.")
                            if(self.p1_cooler_broken_on_checked == False):
                                self.check_sonoff_status()
                                self.p1_cooler_broken_on_checked = True
                            elif(self.p1_cooler_broken_on_text == False):
                                testtext = 'Pool 2 Turn Cooler On Failed, Please Check'
                                self.text_notification(testtext)
                                self.p1_cooler_broken_on_text = True
                    if(pool2_conv < float(pool2_low) and self.pool2_heater_on != True and self.pool2_cooler_on != True):
                        self.log("Pool 2 Heater Turned On. Too Cool Temp: %s"% self.entities.sensor.pool_2_temp.state)
                        self.pool2_heater_on = True
                        try:
                            self.send_http(self.pool2_heater_turn_on)
                        # Pool 4 Heater is not responding
                        except:
                            if(self.p2_heater_broken_on_checked == False):
                                self.check_sonoff_status()
                                self.p2_heater_broken_on_checked = True
                            elif(self.p2_heater_broken_on_text == False):
                                self.log("Failed to http get request to the site.")
                                testtext = 'Pool 2 Turn Heater On Failed, Please Check'
                                self.text_notification(testtext)
                                self.p2_heater_broken_on_text==True
                    # Turn cooler off split when 
                    if(self.pool_1_active):
                        if(pool2_conv < float(pool2_high) and self.pool2_cooler_on == True and self.pool1_cooler_needs_on == False):
                            self.pool2_cooler_needs_on = False
                            
                            self.pool2_cooler_on = False
                            if(self.pool1_cooler_needs_on == False):
                                try:
                                    self.log("Pool 2 Cooler Turned Off. Current Temp: %s"% self.entities.sensor.pool_2_temp.state)
                                    self.send_http(self.pool1_cooler_turn_off)
                                except:
                                    if(self.p1_cooler_broken_off_checked == False):
                                        self.check_sonoff_status()
                                        self.p1_cooler_broken_off_checked = True
                                    elif(self.p1_cooler_broken_off_text == False): 
                                        self.log("Failed to http get request to the site.")
                                        testtext = 'Pool 2 Turn Cooler Off Failed, Please Check'
                                        self.text_notification(testtext)
                    else:
                        if(pool2_conv < float(pool2_high) and self.pool1_cooler_on == True):
                            self.log("Pool 2 Cooler Turned Off. Current Temp: %s"% self.entities.sensor.pool_2_temp.state)
                            self.pool2_cooler_on = False
                            try:
                                self.send_http(self.pool1_cooler_turn_off)
                            except:
                                if(self.p1_cooler_broken_off_checked == False):
                                    self.check_sonoff_status()
                                    self.p1_cooler_broken_off_checked = True
                                elif(self.p1_cooler_broken_off_text == False): 
                                    self.log("Failed to http get request to the site.")
                                    testtext = 'Pool 2 Turn Cooler Off Failed, Please Check'
                                    self.text_notification(testtext)
                    if(pool2_conv > float(pool2_low) and self.pool2_heater_on == True):
                        self.log("Pool 2 Heater Turned Off. Current Temp: %s"% self.entities.sensor.pool_2_temp.state)
                        self.pool2_heater_on = False
                        try:
                            self.send_http(self.pool2_heater_turn_off)
                        except:
                            if(self.p2_heater_broken_off_checked == False):
                                self.check_sonoff_status()
                                self.p2_heater_broken_off_checked = True
                            elif(self.p2_heater_broken_off_text == False): 
                                self.log("Failed to http get request to the site.")
                                testtext = 'Pool 2 Turn Heater Off Failed, Please Check'
                                self.text_notification(testtext)
            except Exception as e:
                print(e)
                # testtext = 'Pool 4 Turn Cooler is off'
                # self.send_text(testtext, "Conrad")


        # Pool 2.5 !
        if(self.pool_2_point_five_active):
            try:
                if(self.entities.sensor.pool_2_5_temp.state != "unknown"):
                    pool2_5_conv = float(self.entities.sensor.pool_2_5_temp.state)
                    if(pool2_5_conv > float(pool2_5_high) and self.pool2_5_cooler_on != True and self.pool2_5_heater_on != True):
                        self.log("Pool 2.5 Cooler Turned On. Too Hot Temp: %s" % self.entities.sensor.pool_2_5_temp.state)
                        self.pool2_5_cooler_on = True 
                        try:
                            self.send_http(self.pool2_5_cooler_turn_on)
                            textout = 'Pool 2.5 Cooler Turned on at ' + str(self.entities.sensor.pool_2_5_temp.state)
                            # self.send_text(textout, "Conrad")
                        # Pool 4 Cooler is not responding
                        except:
                            self.log("Failed to http get request to the site.")
                            if(self.p2_5_cooler_broken_on_checked == False):
                                self.check_sonoff_status()
                                self.p2_5_cooler_broken_on_checked = True
                            elif(self.p2_5_cooler_broken_on_text == False):
                                testtext = 'Pool 2.5 Turn Cooler On Failed, Please Check'
                                self.text_notification(testtext)
                                self.p2_5_cooler_broken_on_text = True
                    if(pool2_5_conv < float(pool2_5_low) and self.pool2_5_heater_on != True and self.pool2_5_cooler_on != True):
                        self.log("Pool 2.5 Heater Turned On. Too Cool Temp: %s"% self.entities.sensor.pool_2_5_temp.state)
                        self.pool2_5_heater_on = True
                        try:
                            self.send_http(self.pool2_5_heater_turn_on)
                        # Pool 4 Heater is not responding
                        except:
                            if(self.p2_5_heater_broken_on_checked == False):
                                self.check_sonoff_status()
                                self.p2_5_heater_broken_on_checked = True
                            elif(self.p2_5_heater_broken_on_text == False):
                                self.log("Failed to http get request to the site.")
                                testtext = 'Pool 4 Turn Heater On Failed, Please Check'
                                self.text_notification(testtext)
                                self.p2_5_heater_broken_on_text==True
                    if(pool2_5_conv < float(pool2_5_high) and self.pool2_5_cooler_on == True):
                        self.log("Pool 2.5 Cooler Turned Off. Current Temp: %s"% self.entities.sensor.pool_2_5_temp.state)
                        self.pool2_5_cooler_on = False
                        try:
                            self.send_http(self.pool2_5_cooler_turn_off)
                        except:
                            if(self.p2_5_cooler_broken_off_checked == False):
                                self.check_sonoff_status()
                                self.p2_5_cooler_broken_off_checked = True
                            elif(self.p2_5_cooler_broken_off_text == False): 
                                self.log("Failed to http get request to the site.")
                                testtext = 'Pool 2.5 Turn Cooler Off Failed, Please Check'
                                self.text_notification(testtext)
                    if(pool2_5_conv > float(pool2_5_low) and self.pool2_5_heater_on == True):
                        self.log("Pool 2.5 Heater Turned Off. Current Temp: %s"% self.entities.sensor.pool_2_5_temp.state)
                        self.pool2_5_heater_on = False
                        try:
                            self.send_http(self.pool2_5_heater_turn_off)
                        except:
                            if(self.p2_5_heater_broken_off_checked == False):
                                self.check_sonoff_status()
                                self.p2_5_heater_broken_off_checked = True
                            elif(self.p2_5_heater_broken_off_text == False): 
                                self.log("Failed to http get request to the site.")
                                testtext = 'Pool 2.5 Turn Heater Off Failed, Please Check'
                                self.text_notification(testtext)
            except Exception as e:
                print(e)
                testtext = 'Pool 2.5 Failed'
                # self.send_text(testtext, "Conrad")
        #-----------------Pool 3-------------------------
        if(self.pool_3_active):
            if(self.entities.sensor.pool3_temp.state != "unknown"):
                pool3_conv = float(self.entities.sensor.pool3_temp.state)
                if(pool3_conv > float(pool3_high) and self.pool3_cooler_on != True and self.pool3_heater_on != True):
                    self.log("Pool 3 Cooler Turned On. Too Hot Temp: %s" % self.entities.sensor.pool3_temp.state)
                    self.pool3_cooler_on = True 
                    try:
                        self.send_http(self.pool3_cooler_turn_on)
                        # textout = 'Pool 3 Cooler Turned on at ' + str(self.entities.sensor.pool3_temp.state)
                        # try:
                        #     self.send_text(textout, "Conrad")
                        # except:
                        #     self.log("text didnt work")
                    except:
                        time.sleep(20)
                        try:
                            self.send_http(self.pool3_cooler_turn_on)
                            textout = 'Pool 3 Cooler Turned on at ' + str(self.entities.sensor.pool3_temp.state)
                            self.send_text(textout, "Conrad")
                        except:
                            if(self.p3_cooler_broken_on_checked == False):
                                self.check_sonoff_status()
                                self.p3_cooler_broken_on_checked = True
                            self.log("Failed to http get request to the site.")
                            testtext = 'Pool 3 Turn Cooler On Failed, Please Check'
                            # self.text_notification(testtext)
                            # self.send_text(testtext, "Conrad")
                        
                if(pool3_conv < float(pool3_low) and self.pool3_heater_on != True and self.pool3_cooler_on != True):
                    self.log("Pool 3 Heater Turned On. Too Cool Temp: %s"% self.entities.sensor.pool3_temp.state)
                    self.pool3_heater_on = True
                    try:
                        self.send_http(self.pool3_heater1_turn_on)
                        self.send_http(self.pool3_heater2_turn_on)
                        
                        

                    except:
                        self.log("Failed to http get request to the site.")
                        if(self.p3_heater1_broken_on_checked == False or self.p3_heater2_broken_on_checked == False):
                            self.check_sonoff_status()
                            self.p3_heater1_broken_on_checked = True
                            self.p3_heater2_broken_on_checked = True
                        elif(self.p3_heater1_broken==True and self.p3_heater2_broken==True and self.p3_heater1_broken_on_text ==False):
                            testtext = 'Pool 3 Both Heaters failed to turn on, Please Check'  
                            self.text_notification(testtext)
                            # self.send_text( testtext,"Conrad")
                            self.p3_heater1_broken_on_text ==True
                        elif(self.p3_heater1_broken==True and self.p3_heater1_broken_on_text ==False):
                            testtext = 'Pool 3 Turn heater on failed , Please Check'  
                            # self.send_text(testtext,"Conrad")
                            self.text_notification(testtext)
                            self.p3_heater1_broken_on_text ==True
                        elif(self.p3_heater2_broken==True and self.p3_heater2_broken_on_text ==False):
                            testtext = 'Pool 3 Turn heater on failed , Please Check'  
                            self.text_notification(testtext)
                            # self.send_text(testtext,"Conrad")
                            self.p3_heater1_broken_on_text ==True
                        
                        
                if(pool3_conv < float(pool3_high) and self.pool3_cooler_on == True):
                    self.log("Pool 3 Cooler Turned Off. Current Temp: %s"% self.entities.sensor.pool3_temp.state)
                    self.pool3_cooler_on = False
                    try:
                        self.send_http(self.pool3_cooler_turn_off)
                    except:
                        self.log("Failed to http get request to the site.")
                        testtext = 'Pool 3 Turn Cooler Off Failed, Please Check'
                        self.text_notification(testtext)
                if(pool3_conv > float(pool3_low) and self.pool3_heater_on == True):
                    self.log("Pool 3 Heater Turned Off. Current Temp: %s"% self.entities.sensor.pool3_temp.state)
                    self.pool3_heater_on = False
                    try:
                        self.send_http(self.pool3_heater1_turn_off)
                        self.send_http(self.pool3_heater2_turn_off)
                    except:

                        self.log("Failed to http get request to the site.")
                        testtext = 'Pool 3 Turn heater Off Failed, Please Check'
                        self.text_notification(testtext)
        #-----------------Pool 4-------------------------
        if(self.pool_4_active):
            try:
                if(self.entities.sensor.pool4_temp.state != "unknown"):
                    pool4_conv = float(self.entities.sensor.pool4_temp.state)
                    if(pool4_conv > float(pool4_high) and self.pool4_cooler_on != True and self.pool4_heater_on != True):
                        self.log("Pool 4 Cooler Turned On. Too Hot Temp: %s" % self.entities.sensor.pool4_temp.state)
                        self.pool4_cooler_on = True 
                        try:
                            self.send_http(self.pool4_cooler_turn_on)
                            textout = 'Pool 4 Cooler Turned on at ' + str(self.entities.sensor.pool4_temp.state)
                            # self.send_text(textout, "Conrad")
                        # Pool 4 Cooler is not responding
                        except:
                            self.log("Failed to http get request to the site.")
                            if(self.p4_cooler_broken_on_checked == False):
                                self.check_sonoff_status()
                                self.p4_cooler_broken_on_checked = True
                            elif(self.p4_cooler_broken_on_text == False):
                                testtext = 'Pool 4 Turn Cooler On Failed, Please Check'
                                self.text_notification(testtext)
                                self.p4_cooler_broken_on_text = True
                    if(pool4_conv < float(pool4_low) and self.pool4_heater_on != True and self.pool4_cooler_on != True):
                        self.log("Pool 4 Heater Turned On. Too Cool Temp: %s"% self.entities.sensor.pool4_temp.state)
                        self.pool4_heater_on = True
                        try:
                            self.send_http(self.pool4_heater_turn_on)
                        # Pool 4 Heater is not responding
                        except:
                            if(self.p4_heater_broken_on_checked == False):
                                self.check_sonoff_status()
                                self.p4_heater_broken_on_checked = True
                            elif(self.p4_heater_broken_on_text == False):
                                self.log("Failed to http get request to the site.")
                                testtext = 'Pool 4 Turn Heater On Failed, Please Check'
                                self.text_notification(testtext)
                                self.p4_heater_broken_on_text==True
                    if(pool4_conv < float(pool4_high) and self.pool4_cooler_on == True):
                        self.log("Pool 4 Cooler Turned Off. Current Temp: %s"% self.entities.sensor.pool4_temp.state)
                        self.pool4_cooler_on = False
                        try:
                            self.send_http(self.pool4_cooler_turn_off)
                        except:
                            if(self.p4_cooler_broken_off_checked == False):
                                self.check_sonoff_status()
                                self.p4_cooler_broken_off_checked = True
                            elif(self.p4_cooler_broken_off_text == False): 
                                self.log("Failed to http get request to the site.")
                                testtext = 'Pool 4 Turn Cooler Off Failed, Please Check'
                                self.text_notification(testtext)
                    if(pool4_conv > float(pool4_low) and self.pool4_heater_on == True):
                        self.log("Pool 4 Heater Turned Off. Current Temp: %s"% self.entities.sensor.pool4_temp.state)
                        self.pool4_heater_on = False
                        try:
                            self.send_http(self.pool4_heater_turn_off)
                        except:
                            if(self.p4_heater_broken_off_checked == False):
                                self.check_sonoff_status()
                                self.p4_heater_broken_off_checked = True
                            elif(self.p4_heater_broken_off_text == False): 
                                self.log("Failed to http get request to the site.")
                                testtext = 'Pool 4 Turn Heater Off Failed, Please Check'
                                self.text_notification(testtext)
            except:
                testtext = 'Pool 4 Turn Cooler is off'
                self.send_text(testtext, "Conrad")
        
   #---------------------Check Relays---------------------
        # @desc:    Uses Http requests to check if the sonoffs relays are active and thus
        #           check if the heaters or coolers are currently running and update the booleans
        #           that indicate if any of these are on.

        # @param: (none)
        # @return: none
    #-----------------------------------------------------
    def check_relays(self):
         #------------------- Pool 3 -----------------------
        # Heaters
        #Need to add try excepts to get around these issues and make it known that there is a problem.
        if(self.pool_3_active):
            try:
                r = requests.get(url = self.pool3_heater1)
                data1 = r.json() 
            except:
                self.p3_heater1_broken = True
                self.log("Pool 3 Heater 1 is failing, probably off or not connected.")

            try:
                r = requests.get(url = self.pool3_heater2)
                data2 = r.json() 
            except:
                self.p3_heater2_broken = True
                self.log("Pool 3 Heater 2 is failing, probably off or not connected.")
            
            try:
                if(data1["POWER"] == "ON" and data2["POWER"] == "ON"):
                    self.pool3_heater_on = True
                else:
                    self.pool3_heater_on = False
            except:
                self.log("The check has Failed")
            # Cooler
            try:
                r = requests.get(url = self.pool3_cooler)
                data1 = r.json() 
                if(data1["POWER"] == "ON"):
                    self.pool3_cooler_on = True
                else:
                    self.pool3_cooler_on = False
                self.p3_cooler_broken = False
            except:
                self.p3_cooler_broken = True
                self.p3_cooler_broken_count = self.p3_cooler_broken_count + 1
                self.log("Pool 3 cooler failed to turn on.")

            if(self.p3_cooler_broken == True and self.p3_cooler_broken_count >3 and self.p3_cooler_broken_off_text ==False):
                testtext='Pool 3 Temp and Cooling is not on the network.'
                self.text_notification(testtext)
                self.p3_cooler_broken_off_text = True
            # Heaters Check

            if(self.p3_heater1_broken==True and self.p3_heater2_broken==True and self.p3_heater1_broken_on_text==False and self.p3_heater2_broken_on_text==False):
                testtext='Pool 3 both heaters are not responding please check.'
                self.p3_heater1_broken_on_text=True
                self.p3_heater1_broken_on_text=True
                self.send_text(testtext,"Conrad")
            elif(self.p3_heater1_broken==True and self.p3_heater1_broken_on_text==False):
                self.p3_heater1_broken_on_text=True
                testtext='Pool 3 heater 1 is not responding please check.'
                self.send_text(testtext,"Conrad")
            elif(self.p3_heater2_broken==True and self.p3_heater2_broken_on_text==False):
                self.p3_heater2_broken_on_text=True
                testtext='Pool 3 heater 2 is not responding please check.'
                self.send_text(testtext,"Conrad")
        
        # Plae holder if we get lights in the pools to connect to the sonoff.
        # Lights
        # r = requests.get(url = pool3_lights)
        # data1 = r.json() 
        # if(data1["POWER"] == "ON"):
        #     pool3_lights_on = True
        # else:
        #     pool3_lights_on = False
        #------------------- Pool 1 -----------------------
        if(self.pool_1_active):
            try:
                r = requests.get(url = self.pool1_heater)
                data1 = r.json() 
                self.p1_heater_broken_count = 0
                if(data1["POWER"] == "ON"):
                    self.pool1_heater_on = True
                else:
                    self.pool1_heater_on = False
                self.p1_heater_broken_count = 0
                self.p1_heater_broken == False
            except:
                self.p1_heater_broken = True
                self.log("Pool 1 Heater is failing, probably off or not connected.")
                self.pool1_heater_on = False
                self.p1_heater
                if(self.p1_heater_broken_count ==0):
                    self.reassign_sonoff_address()
                if(self.p1_heater_broken_count >2):
                    text = "Pool 1 Heater Sonoff is not connected to network please check"
                    self.text_notification(text)
            
            
            # Cooler
            try:
                r = requests.get(url = self.pool1_cooler)
                data1 = r.json() 
                if(data1["POWER"] == "ON"):
                    self.pool1_cooler_on = True
                else:
                    self.pool1_cooler_on = False
            except Exception as e:
                print(e)
                self.p1_cooler_broken = True
                self.log("Pool 1 cooler has failed and needs to be checked")
                self.pool1_cooler_on = False
                if(self.p1_cooler_broken_count==0):
                    self.reassign_sonoff_address()
                self.p1_cooler_broken_count = self.p1_cooler_broken_count + 1

            if(self.p1_cooler_broken == True and self.p1_cooler_broken_count >2 and self.p1_cooler_broken_off_text ==False):
                testtext='Pool 2 Temp and Cooling is not on the network.'

                self.text_notification(testtext)
                self.p1_cooler_broken_off_text = True


        #------------------- Pool 2 -----------------------

        if(self.pool_2_active):
            try:
                r = requests.get(url = self.pool2_heater)
                data1 = r.json() 
                self.p2_heater_broken_count = 0
                if(data1["POWER"] == "ON"):
                    self.pool2_heater_on = True
                else:
                    self.pool2_heater_on = False
                self.p2_heater_broken_count = 0
                self.p2_heater_broken == False
            except:
                self.p2_heater_broken = True
                self.log("Pool 2 Heater is failing, probably off or not connected.")
                self.pool2_heater_on = False

                if(self.p2_heater_broken_count ==0):
                    self.reassign_sonoff_address()
                if(self.p2_heater_broken_count >2):
                    text = "Pool 2 Heater Sonoff is not connected to network please check"
                    self.text_notification(text)

        #------------------- Pool 2.5 -----------------------

        #Pool 2.5 Relays
  

        if(self.pool_2_point_five_active):
            try:
                r = requests.get(url = self.pool2_5_heater)
                data1 = r.json() 
                if(data1["POWER"] == "ON"):
                    self.pool2_5_heater_on = True
                else:
                    self.pool2_5_heater_on = False
            except:
                self.p2_5_heater_broken = True
                self.log("Pool 2.5 Heater is failing, probably off or not connected.")
                self.pool2_5_heater_on = False
            
            
            # Cooler
            try:
                r = requests.get(url = self.pool2_5_cooler)
                data1 = r.json() 
                if(data1["POWER"] == "ON"):
                    self.pool2_5_cooler_on = True
                else:
                    self.pool2_5_cooler_on = False
                self.p2_5_cooler_broken_count = 0
            except:
                self.p2_5_cooler_broken = True
                self.log("Pool 2.5 cooler has failed and needs to be checked")
                self.pool2_5_cooler_on = False
                if(self.p2_5_cooler_broken_count==0):
                    self.reassign_sonoff_address()
                self.p2_5_cooler_broken_count = self.p2_5_cooler_broken_count + 1

            if(self.p2_5_cooler_broken == True and self.p2_5_cooler_broken_count >2 and self.p2_5_cooler_broken_off_text ==False):
                testtext='Pool 2.5 Temp and Cooling is not on the network.'

                self.text_notification(testtext)
                self.p4_cooler_broken_off_text = True
        # Lights

        #------------------- Pool 4 -----------------------

        if(self.pool_4_active):
            try:
                r = requests.get(url = self.pool4_heater)
                data1 = r.json() 
                if(data1["POWER"] == "ON"):
                    self.pool4_heater_on = True
                else:
                    self.pool4_heater_on = False
            except:
                self.p4_heater_broken = True
                self.log("Pool 4 Heater is failing, probably off or not connected.")
                self.pool4_heater_on = False
            
            
            # Cooler
            try:
                r = requests.get(url = self.pool4_cooler)
                data1 = r.json() 
                if(data1["POWER"] == "ON"):
                    self.pool4_cooler_on = True
                else:
                    self.pool4_cooler_on = False
                self.p4_cooler_broken_count = 0
            except:
                self.p4_cooler_broken = True
                self.log("Pool 4 cooler has failed and needs to be checked")
                self.pool4_cooler_on = False
                if(self.p4_cooler_broken_count==0):
                    self.reassign_sonoff_address()
                self.p4_cooler_broken_count = self.p4_cooler_broken_count + 1

            if(self.p4_cooler_broken == True and self.p4_cooler_broken_count >2 and self.p4_cooler_broken_off_text ==False):
                testtext='Pool 4 Temp and Cooling is not on the network.'

                self.text_notification(testtext)
                self.p4_cooler_broken_off_text = True
        # Lights
        # r = requests.get(url = pool4_lights)
        # data1 = r.json() 
        # if(data1["POWER"] == "ON"):
        #     pool4_lights_on = True
        # else:
        #     pool4_lights_on = False


    #---------------------Get Time---------------------
        # @desc:    Obtains the time using the datetime library and changes it
        #           Hour, Minute, Second

        # @param: (none)
        # @return: cur_time (string)
    #--------------------------------------------------
    def get_time(self):
        fmt = '%H:%M:%S'
        d = datetime.now()
        cur_time = d.strftime(fmt)
        return(cur_time)
    #---------------------Get Forecast---------------------
        # @desc:    Calls the pywom api that is the python extension for openweather api and retrieves the weather forecast for the next 5 days and inserts
        #           Them into the google sheets document.  it also checks the conditions for dangerous
        #           variables such as high winds and gusts.
        # @param:   (none)
        # @return:  (none)
        # @notes:   Pyowm has a peculiar response, and if there is none of a variable it will not return anything for that case.
        #           ex: If there is no rain for a day it will simply not return anything for that dict.
    #------------------------------------------------------
    def get_forecast(self):
        pyowm_api_key = os.environ.get('PYOWM_API_KEY')
        pyowm_api_key = str(pyowm_api_key)
        owm = pyowm.OWM(pyowm_api_key)
        fc = owm.three_hours_forecast_at_id(self.brentwood_id)
        f = fc.get_forecast()
        print(fc)
        time_list = []
        temp_list = []
        temp_min_list = []
        temp_max_list = []
        humidity_list = []
        wind_speed_list = []
        wind_deg_list = []
        wind_gust_list = []
        clouds_list = []
        rain_list = []
        final_data = []
        advisory_list = []
        advisory_flag = False

        
        rain_limit = 2
        text = ""


        # Iterate through every entry in the openweather api weather dict
        for weather in f:
            time_temp = weather.get_reference_time('iso')
            time_temp = time_temp[:-3]
            time_list.append(time_temp)
            temp2 = weather.get_temperature('celsius')
            temp_list.append(temp2["temp"])
            temp_min_list.append(temp2["temp_min"])
            temp_max_list.append(temp2["temp_max"])
            humidity2 =  weather.get_humidity()
            humidity_list.append(humidity2)
            wind2 = weather.get_wind()
            wind_speed_list.append(wind2["speed"])
            # If there is no wind deg then add 0, I do this because the api call does not include data if there is no wind degree
            try:
                if(wind2["deg"] != ""):
                    wind_deg_list.append(wind2["deg"])
            except:
                wind_deg_list.append("0")
            # If there is no wind gust then add 0.
            try:
                if(wind2["gust"] != ""):
                    wind_gust_list.append(wind2["gust"])
            except:
                wind_gust_list.append("0")
            clouds2 = weather.get_clouds()
            clouds_list.append(clouds2)

            rain = weather.get_rain()
            # If there is no rain then add 0.
            try:
                if(rain["3h"] != ""):
                    rain_inches = rain["3h"]
            except:
                rain_inches = 0

            rain_list.append(rain_inches)
        print("Got through the first for loop")

        for x in range(0, 40):
            collection = str(time_list[x]) + ',' +  str(temp_list[x]) + ',' + str(temp_min_list[x]) + ',' + str(temp_max_list[x]) + ',' + str(humidity_list[x]) + ',' + str(wind_speed_list[x]) + ',' +str(wind_deg_list[x]) + ',' + str(wind_gust_list[x]) + ',' + str(clouds_list[x])
            final_data.append(collection)
            print(collection)
            # Insert the data into the google sheet
            print("inserting data")
            self.weather_insert(time_list[x], self.weather_forecast_sheet, self.spreadsheet_id, wind_speed_list[x] ,wind_deg_list[x], wind_gust_list[x], humidity_list[x],temp_list[x], temp_max_list[x], temp_min_list[x], rain_list[x], clouds_list[x])

            if(float(wind_gust_list[x]) > self.wind_gust_limit): 
                str_conversion = str(time_list[x])
                str_conversion = str_conversion.replace(":", "-")
                str_conversion = str_conversion.replace("+", "")
                self.log(str_conversion)
                textout = 'Wind gust is at dangerous level of ' + str(wind_gust_list[x]) + ', on ' + str_conversion + ' \n\n'
                advisory_flag = True
                advisory_list.append(textout)
                self.log(textout)

        if(advisory_flag == True):
            for x in advisory_list:
                text += x
            # self.send_text(text, "Conrad")
            self.text_notification(text)

     #---------------------Get Photosynq information---------------------
        # @desc:   Uses the photosynq python library to query the photosynq database to gather the data that 
        # @param: int(spreadsheet_id), string(sheet_name_id), string(val1), string(row_location)
        # @return: (none)
    #--------------------------------------------------------------------
    def get_photosynq(self):
        email = os.getenv('PHOTOSYNQ_USER')
        password = os.environ.get('PHOTOSYNQ_PASSWORD')
        # p3_most_recent_time = self.gsheets_retrieve_data('!A2:A3', self.photosynq_spreadsheet_id)

        try:
            p1_most_recent_time = self.gsheets_retrieve_data('Photosynq P1!A2:A2', self.spreadsheet_id)
            p2_most_recent_time = self.gsheets_retrieve_data('Photosynq P2!A2:A2', self.spreadsheet_id)
            p3_most_recent_time = self.gsheets_retrieve_data('Photosynq P3!A2:A2', self.spreadsheet_id)
            p4_most_recent_time = self.gsheets_retrieve_data('Photosynq P4!A2:A2', self.spreadsheet_id)
        except Exception as e:
            self.log("Failed Retrieving most recent photosynq data.")
            print(e)
        # Convert Time of most recently input value to a datetime object to be compared against
        p1_recent_time = datetime.strptime(p1_most_recent_time[0], '%Y-%m-%d %H:%M:%S')
        p2_recent_time = datetime.strptime(p2_most_recent_time[0], '%Y-%m-%d %H:%M:%S')
        p3_recent_time = datetime.strptime(p3_most_recent_time[0], '%Y-%m-%d %H:%M:%S')
        p4_recent_time = datetime.strptime(p4_most_recent_time[0], '%Y-%m-%d %H:%M:%S')
        #login to PHotosynq
        ps.login(email,password)

        # retrieve a dataframe with data from the given project ID
        projectId = os.environ.get('PHOTOSYNQ_ID')
        # df = ps.get_project_dataframe(projectId)
        info = ps.get_project_info(projectId)
        data = ps.get_project_data(projectId, processed_data=True) # Use raw data
        df = ps.build_project_dataframe(info, data)


        fmt = '%m/%d/%y'

        d = datetime.now()
        cur_time = d.strftime(fmt)
        # p3_recent_time = p3_recent_time.strftime(fmt)
        # p4_recent_time = p4_recent_time.strftime(fmt)

        for key, value in df["Algae Photosynthesis MultispeQ V1.0"]["time"].items() :

            datetime_object = datetime.strptime(df["Algae Photosynthesis MultispeQ V1.0"]["time"][key], '%m/%d/%Y, %H:%M:%S %p')

            datetime_object = datetime_object - timedelta(hours=8)

            time = datetime_object.strftime(fmt)
            # print("Measurement Time:")
            # print(datetime_object)
            # ---------Pool 1----------
            if(p1_recent_time < datetime_object and df["Algae Photosynthesis MultispeQ V1.0"]["Which pool is being tested?"][key] == "Pool 1 Pre"):
            # if(df["Algae Photosynthesis MultispeQ V1.0"]["Which pool is being tested?"][key] == "Pool 3"):
                print("Pool 1 New Value Before the last Value!")
                # Stuff
                # p3_time = str(df["Algae Photosynthesis MultispeQ V1.0"]["time"][key])
                p1_time = str(datetime_object)
                p1_time = p1_time.replace(',', '')
                p1_phi2 = df["Algae Photosynthesis MultispeQ V1.0"]["Phi2"][key]
                p1_phinpq = df["Algae Photosynthesis MultispeQ V1.0"]["PhiNPQ"][key]
                p1_relative_chlorophyll = df["Algae Photosynthesis MultispeQ V1.0"]["Relative Chlorophyll"][key]
                print(p1_time)
                print("Pool 1 Phi2")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["Phi2"][key])
                print("Pool 1 PhiNPQ")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["PhiNPQ"][key])
                print("Pool 1 Relative Chlorophyl")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["Relative Chlorophyll"][key])
                self.gsheets_photosynq_insert(self.spreadsheet_id, self.photosynq_p1_spreadsheet_id, str(p1_time), str(p1_phi2), str(p1_phinpq), str(p1_relative_chlorophyll), "Pre Mix")

            if(p1_recent_time < datetime_object and df["Algae Photosynthesis MultispeQ V1.0"]["Which pool is being tested?"][key] == "Pool 1 Post"):
            # if(df["Algae Photosynthesis MultispeQ V1.0"]["Which pool is being tested?"][key] == "Pool 3"):
                print("Pool 1 New Value Before the last Value!")
                # Stuff
                # p3_time = str(df["Algae Photosynthesis MultispeQ V1.0"]["time"][key])
                p1_time = str(datetime_object)
                p1_time = p1_time.replace(',', '')
                p1_phi2 = df["Algae Photosynthesis MultispeQ V1.0"]["Phi2"][key]
                p1_phinpq = df["Algae Photosynthesis MultispeQ V1.0"]["PhiNPQ"][key]
                p1_relative_chlorophyll = df["Algae Photosynthesis MultispeQ V1.0"]["Relative Chlorophyll"][key]
                print(p1_time)
                print("Pool 1 Phi2")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["Phi2"][key])
                print("Pool 1 PhiNPQ")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["PhiNPQ"][key])
                print("Pool 1 Relative Chlorophyl")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["Relative Chlorophyll"][key])
                self.gsheets_photosynq_insert(self.spreadsheet_id, self.photosynq_p1_spreadsheet_id, str(p1_time), str(p1_phi2), str(p1_phinpq), str(p1_relative_chlorophyll),  "Post Mix")
            # ---------Pool 2----------
            if(p2_recent_time < datetime_object and df["Algae Photosynthesis MultispeQ V1.0"]["Which pool is being tested?"][key] == "Pool 2 Pre"):
            # if(df["Algae Photosynthesis MultispeQ V1.0"]["Which pool is being tested?"][key] == "Pool 4"):
                print("Pool 2 New Value Before the last Value!")
                # Stuff
                # p4_time = str(df["Algae Photosynthesis MultispeQ V1.0"]["time"][key])
                p2_time = str(datetime_object)
                p2_time = p2_time.replace(',', '')
                p2_phi2 = df["Algae Photosynthesis MultispeQ V1.0"]["Phi2"][key]
                p2_phinpq = df["Algae Photosynthesis MultispeQ V1.0"]["PhiNPQ"][key]
                p2_relative_chlorophyll = df["Algae Photosynthesis MultispeQ V1.0"]["Relative Chlorophyll"][key]
                print(p2_time)
                print("Pool 2 Phi2")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["Phi2"][key])
                print("Pool 2 PhiNPQ")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["PhiNPQ"][key])
                print("Pool 2 Relative Chlorophyl")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["Relative Chlorophyll"][key])
                self.gsheets_photosynq_insert(self.spreadsheet_id, self.photosynq_p2_spreadsheet_id, str(p2_time), str(p2_phi2), str(p2_phinpq), str(p2_relative_chlorophyll),  "Pre Mix")

            if(p2_recent_time < datetime_object and df["Algae Photosynthesis MultispeQ V1.0"]["Which pool is being tested?"][key] == "Pool 2 Post"):
            # if(df["Algae Photosynthesis MultispeQ V1.0"]["Which pool is being tested?"][key] == "Pool 4"):
                print("Pool 2 New Value Before the last Value!")
                # Stuff
                # p4_time = str(df["Algae Photosynthesis MultispeQ V1.0"]["time"][key])
                p2_time = str(datetime_object)
                p2_time = p2_time.replace(',', '')
                p2_phi2 = df["Algae Photosynthesis MultispeQ V1.0"]["Phi2"][key]
                p2_phinpq = df["Algae Photosynthesis MultispeQ V1.0"]["PhiNPQ"][key]
                p2_relative_chlorophyll = df["Algae Photosynthesis MultispeQ V1.0"]["Relative Chlorophyll"][key]
                print(p2_time)
                print("Pool 2 Phi2")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["Phi2"][key])
                print("Pool 2 PhiNPQ")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["PhiNPQ"][key])
                print("Pool 2 Relative Chlorophyl")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["Relative Chlorophyll"][key])
                self.gsheets_photosynq_insert(self.spreadsheet_id, self.photosynq_p2_spreadsheet_id, str(p2_time), str(p2_phi2), str(p2_phinpq), str(p2_relative_chlorophyll),  "Post Mix")
            # ---------Pool 3----------
            # if(cur_time == time): #doing it once a day and taking all the info from that day.
            if(p3_recent_time < datetime_object and df["Algae Photosynthesis MultispeQ V1.0"]["Which pool is being tested?"][key] == "Pool 3 Pre"):
            # if(df["Algae Photosynthesis MultispeQ V1.0"]["Which pool is being tested?"][key] == "Pool 3"):
                print("Pool 3 New Value Before the last Value!")
                # Stuff
                # p3_time = str(df["Algae Photosynthesis MultispeQ V1.0"]["time"][key])
                p3_time = str(datetime_object)
                p3_time = p3_time.replace(',', '')
                p3_phi2 = df["Algae Photosynthesis MultispeQ V1.0"]["Phi2"][key]
                p3_phinpq = df["Algae Photosynthesis MultispeQ V1.0"]["PhiNPQ"][key]
                p3_relative_chlorophyll = df["Algae Photosynthesis MultispeQ V1.0"]["Relative Chlorophyll"][key]
                print(p3_time)
                print("Pool 3 Phi2")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["Phi2"][key])
                print("Pool 3 PhiNPQ")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["PhiNPQ"][key])
                print("Pool 3 Relative Chlorophyl")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["Relative Chlorophyll"][key])
                self.gsheets_photosynq_insert(self.spreadsheet_id, self.photosynq_p3_spreadsheet_id, str(p3_time), str(p3_phi2), str(p3_phinpq), str(p3_relative_chlorophyll),  "Pre Mix")

            if(p3_recent_time < datetime_object and df["Algae Photosynthesis MultispeQ V1.0"]["Which pool is being tested?"][key] == "Pool 3 Post"):
            # if(df["Algae Photosynthesis MultispeQ V1.0"]["Which pool is being tested?"][key] == "Pool 3"):
                print("Pool 3 New Value Before the last Value!")
                # Stuff
                # p3_time = str(df["Algae Photosynthesis MultispeQ V1.0"]["time"][key])
                p3_time = str(datetime_object)
                p3_time = p3_time.replace(',', '')
                p3_phi2 = df["Algae Photosynthesis MultispeQ V1.0"]["Phi2"][key]
                p3_phinpq = df["Algae Photosynthesis MultispeQ V1.0"]["PhiNPQ"][key]
                p3_relative_chlorophyll = df["Algae Photosynthesis MultispeQ V1.0"]["Relative Chlorophyll"][key]
                print(p3_time)
                print("Pool 3 Phi2")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["Phi2"][key])
                print("Pool 3 PhiNPQ")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["PhiNPQ"][key])
                print("Pool 3 Relative Chlorophyl")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["Relative Chlorophyll"][key])
                self.gsheets_photosynq_insert(self.spreadsheet_id, self.photosynq_p3_spreadsheet_id, str(p3_time), str(p3_phi2), str(p3_phinpq), str(p3_relative_chlorophyll),  "Post Mix")
            # ---------Pool 4----------
            if(p4_recent_time < datetime_object and df["Algae Photosynthesis MultispeQ V1.0"]["Which pool is being tested?"][key] == "Pool 4 Pre"):
            # if(df["Algae Photosynthesis MultispeQ V1.0"]["Which pool is being tested?"][key] == "Pool 4"):
                print("Pool 4 New Value Before the last Value!")
                # Stuff
                # p4_time = str(df["Algae Photosynthesis MultispeQ V1.0"]["time"][key])
                p4_time = str(datetime_object)
                p4_time = p4_time.replace(',', '')
                p4_phi2 = df["Algae Photosynthesis MultispeQ V1.0"]["Phi2"][key]
                p4_phinpq = df["Algae Photosynthesis MultispeQ V1.0"]["PhiNPQ"][key]
                p4_relative_chlorophyll = df["Algae Photosynthesis MultispeQ V1.0"]["Relative Chlorophyll"][key]
                print(p4_time)
                print("Pool 4 Phi2")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["Phi2"][key])
                print("Pool 4 PhiNPQ")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["PhiNPQ"][key])
                print("Pool 4 Relative Chlorophyl")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["Relative Chlorophyll"][key])
                self.gsheets_photosynq_insert(self.spreadsheet_id, self.photosynq_p4_spreadsheet_id, str(p4_time), str(p4_phi2), str(p4_phinpq), str(p4_relative_chlorophyll), "Pre Mix")

            if(p4_recent_time < datetime_object and df["Algae Photosynthesis MultispeQ V1.0"]["Which pool is being tested?"][key] == "Pool 4 Post"):
            # if(df["Algae Photosynthesis MultispeQ V1.0"]["Which pool is being tested?"][key] == "Pool 4"):
                print("Pool 4 New Value Before the last Value!")
                # Stuff
                # p4_time = str(df["Algae Photosynthesis MultispeQ V1.0"]["time"][key])
                p4_time = str(datetime_object)
                p4_time = p4_time.replace(',', '')
                p4_phi2 = df["Algae Photosynthesis MultispeQ V1.0"]["Phi2"][key]
                p4_phinpq = df["Algae Photosynthesis MultispeQ V1.0"]["PhiNPQ"][key]
                p4_relative_chlorophyll = df["Algae Photosynthesis MultispeQ V1.0"]["Relative Chlorophyll"][key]
                print(p4_time)
                print("Pool 4 Phi2")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["Phi2"][key])
                print("Pool 4 PhiNPQ")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["PhiNPQ"][key])
                print("Pool 4 Relative Chlorophyl")
                print(df["Algae Photosynthesis MultispeQ V1.0"]["Relative Chlorophyll"][key])
                self.gsheets_photosynq_insert(self.spreadsheet_id, self.photosynq_p4_spreadsheet_id, str(p4_time), str(p4_phi2), str(p4_phinpq), str(p4_relative_chlorophyll), "Post Mix")
            

        # self.gsheets_insert(cur_time,
        #                         self.spreadsheet_id, cur_time, "Photosynq",test_time,
        #                         p3_phi2, p3_phinpq, p3_relative_chlorophyll, p4_phi2, p4_phinpq, p4_relative_chlorophyll)
        # logout
        ps.logout();

    #---------------------Gsheets Photosynq Insert---------------------
        # @desc Takes in the Different photosynq data and inserts it into the Google sheets document
        # @param (int(spreadsheet_id), int(sheet_name_id), str(val1), str(val2), str(val3), str(val4))
    #-------------------------------------------------------------------------
    def gsheets_photosynq_insert(self, spreadsheet_id, sheet_name_id, val1, val2, val3, val4, val5):

        spreadsheet_str = str(spreadsheet_id)
        
        data =  val1 + "," + val2 + "," + val3 + "," + val4 + "," + val5

        
        sheet = sheet_name_id
       

        batch_update_spreadsheet_request_body = {
                #Move all rows down to allow for new insert
                "requests": [{
                    "insertRange": {
                        "range": {
                            "sheetId": sheet,
                            "startRowIndex": self.row_1,
                            "endRowIndex": self.row_2
                        },
                        "shiftDimension": "ROWS"
                    }
                },
                {
                    "pasteData": {
                        "data":  data,
                        "type": "PASTE_NORMAL",
                        "delimiter": ",",
                        "coordinate": {
                            "sheetId": sheet,
                            "rowIndex": self.row_1
                        }
                    }
                }
                ],  # TODO: Update placeholder value.
                # TODO: Add desired entries to the request body.
            }

        request = self.service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=batch_update_spreadsheet_request_body)
        # response = request.execute()
        try :
            response = request.execute()
            # self.log("Made it to response: %s" % response)
        except Exception as e:
            self.log("google-api ERROR: %s" % response)
            print(e)
        else :
            self.log("google-api response: %s" % response)

    #---------------------Replace single cell---------------------
        # @desc:   Insert single value into the google sheets to replace a previous value in that spot
        # @param: int(spreadsheet_id), string(sheet_name_id), string(val1), string(row_location)
        # @return: (none)
    #-------------------------------------------------------------
    def gsheets_insert_single(self, spreadsheet_id, sheet_name_id, val1, row_location):

        spreadsheet_str = str(spreadsheet_id)
        data =  val1
        sheet = sheet_name_id
        row_location = str(row_location)
        
        range_location = sheet_name_id
        range_location = range_location + row_location

        
        values = [
            [
                val1# Cell values ...
            ],
            # Additional rows ...
        ]
        body = {
            'values': values
        }
        result = self.service.spreadsheets().values().update(
            spreadsheetId= self.spreadsheet_id, range=range_location,
            valueInputOption='USER_ENTERED', body=body).execute()
        print('{0} cells updated.'.format(result.get('updatedCells')))
    #---------------------Restart Pi---------------------
        # @desc:    Restarts the raspberry pi when called and uses the os.system to trigger a reboot
        # @param:  (none)
        # @return: (none)
    #----------------------------------------------------
    def restart_pi(self):
        try:
            self.gsheets_insert_single(self.spreadsheet_id, 'Control!','0', 'B22')
        except Exception as e:
            print("Replacing the item failed")
            print(e)
        # os.system('sudo shutdown -r now')
        os.system('sudo reboot')

    #---------------------Control Pi---------------------
        # @desc:   Functinon to remotely control the pi and run commands and output the response 
        # @param:  (command)
        # @return: (none)
    #----------------------------------------------------
    def control_pi(self, command):
        try:
            if(command != '0'):  
                # os.system(str(command))
                # subprocess.run(command, shell=True, check=True)
                args = command.split()
                result = subprocess.run(args, stdout=subprocess.PIPE)
                output = result.stdout.decode('utf-8')
                # Input command into the Google sheet
                self.gsheets_insert_single(self.spreadsheet_id, 'Control!', output, 'B26')
                # Clear last command
                self.gsheets_insert_single(self.spreadsheet_id, 'Control!', '0', 'B25')

        except Exception as e:
            print(e)

    def get_averages(self):
        try:
            # date = datetime.utcfromtimestamp(1581637500).strftime('%H:%M:%S')
            fmt = '%y-%m-%d'
            d = datetime.now()
            cur_time = d.strftime(fmt)

            print("-----getting averages-----")
            pool3_list = self.gsheets_retrieve_data('Pool_3!C2:C132', self.spreadsheet_id)
            pool3_average = self.Average(pool3_list) 

            pool4_list = self.gsheets_retrieve_data('Pool_4!C2:C132', self.spreadsheet_id)
            pool4_average = self.Average(pool4_list) 
            farm_list = self.gsheets_retrieve_data('Farm!C2:C132', self.spreadsheet_id)
            farm_average = self.Average(farm_list) 
            greenhouse_list = self.gsheets_retrieve_data('Greenhouse!C2:C132', self.spreadsheet_id)
            greenhouse_average = self.Average(greenhouse_list) 
            illuminance_list = self.gsheets_retrieve_data('Sunlight!C2:C132', self.spreadsheet_id)
            illuminance_average = self.Average(illuminance_list)
            clouds_list = self.gsheets_retrieve_data('Weather_Historical!I42:61', self.spreadsheet_id)
            clouds_average = self.Average(clouds_list)  
            print("Pool3, Pool4, Farm, Greenhouse, Illuminance, Clouds")
            print(pool3_average)
            print(pool4_average)
            print(farm_average)
            print(greenhouse_average)
            print(illuminance_average)
            print(clouds_average)
            # def gsheets_insert(self, log_time, spreadsheet_id, last_updated, sheet_name, val1, val2, val3, val4, val5, val6, val7):
            self.gsheets_insert(str(cur_time), self.spreadsheet_id, str(cur_time) , "Averages", str(pool3_average), str(pool4_average), str(farm_average), str(greenhouse_average), str(illuminance_average), str(clouds_average), "Null" )
            # print("Pool 3: %s  Pool 4: %s  Farm:  %s  Greenhouse: %s  Illuminance: %s Clouds: %s", pool3_average, pool4_average, farm_average, greenhouse_average, illuminance_average, clouds_average)
        except Exception as e:
            print(e)
    def Average(self, lst): 
        for i in range(0, len(lst)): 
            lst[i] = float(lst[i]) 
        return round(sum(lst) / len(lst), 2) 

    def iterate_averages(self):
        first_iterator=2
        second_iterator=131
        for i in range(0, 147):
            pool3_list = self.gsheets_retrieve_data('Pool_3!C2:C132', self.spreadsheet_id)
            pool3_average = self.Average(pool3_list) 
            pool4_list = self.gsheets_retrieve_data('Pool_4!C2:C132', self.spreadsheet_id)
            pool4_average = self.Average(pool4_list) 
            farm_list = self.gsheets_retrieve_data('Farm!C2:C132', self.spreadsheet_id)
            farm_average = self.Average(farm_list) 
            greenhouse_list = self.gsheets_retrieve_data('Greenhouse!C2:C131', self.spreadsheet_id)
            greenhouse_average = self.Average(greenhouse_list) 
            illuminance_list = self.gsheets_retrieve_data('Sunlight!C2:C131', self.spreadsheet_id)
            illuminance_average = self.Average(illuminance_list)
            clouds_list = self.gsheets_retrieve_data('Weather_Historical!I42:61', self.spreadsheet_id)
            clouds_average = self.Average(clouds_list) 

    def check_sonoff_status(self):
        reassign_sonoffs_check = False
        try:
            #------Pool 1------
            if(self.pool_1_active):
                try:   
                    URL = self.pool1_heater_status
                    r3 = requests.get(url = URL, timeout=10)
                    data3 = r3.json()
                    # print(data3)
                    print(data3['Status']['FriendlyName'][0])
                    if(data3['Status']['FriendlyName'][0] != u'Pool_1_temp'):
                        # print("Pool 1 Heater Being Reassigned")
                        reassign_sonoffs_check = True 
                except:
                    print("Pool 1 heater Failed to respond")
                    reassign_sonoffs_check = True
                    self.reassign_sonoff_address()
            #------Pool 2------
            if(self.pool_2_active):
                try:
                    URL = self.pool2_cooler_status
                    r4 = requests.get(url = URL, timeout=10)
                    data4 = r4.json() 
                    # print(data4)
                    print(data4['Status']['FriendlyName'][0])
                    if(data4['Status']['FriendlyName'][0] != u'Pool_2_Temp_and_Cooling'):
                        reassign_sonoffs_check = True
                except:
                    print("Pool 2 Failed Cooler check.")
                    reassign_sonoffs_check = True
                    self.reassign_sonoff_address()

                try:
                    URL = self.pool2_heater_status
                    r4 = requests.get(url = URL, timeout=10)
                    data4 = r4.json() 
                    # print(data4)
                    print(data4['Status']['FriendlyName'][0])
                    if(data4['Status']['FriendlyName'][0] != u'Pool_2_Heat'):
                        reassign_sonoffs_check = True
                except:
                    print("Pool 2 Failed Heater check.")
                    reassign_sonoffs_check = True
                    self.reassign_sonoff_address()

            #------Pool 2.5------
            if(self.pool_2_point_five_active):
                try:
                    URL = self.pool2_5_cooler_status
                    r4 = requests.get(url = URL, timeout=10)
                    data2_5 = r4.json() 
                    # print(data4)
                    print(data2_5['Status']['FriendlyName'][0])
                    if(data2_5['Status']['FriendlyName'][0] != u'Pool 2.5 Temp and Cooling'):
                        reassign_sonoffs_check = True
                except:
                    print("Pool 2.5 Failed Cooler check.")
                    reassign_sonoffs_check = True
                    self.reassign_sonoff_address()

                try:
                    URL = self.pool2_heater_status
                    r4 = requests.get(url = URL, timeout=10)
                    data2_5 = r4.json() 
                    # print(data4)
                    print(data2_5['Status']['FriendlyName'][0])
                    if(data2_5['Status']['FriendlyName'][0] != u'Pool 2.5 Heat'):
                        reassign_sonoffs_check = True
                except:
                    print("Pool 2.5 Failed Heater check.")
                    reassign_sonoffs_check = True
                    self.reassign_sonoff_address()
            #------Pool 3------
            if(self.pool_3_active):
                try:
                    URL = self.pool3_cooler_status
                    r = requests.get(url = URL, timeout=10)
                    data = r.json()
                    print(data['Status']['FriendlyName'][0])
                    if(data['Status']['FriendlyName'][0] != u'Pool_3 Temp and Cooler'):
                        reassign_sonoffs_check = True
                except:
                    print("Pool 3 Cooler Failed Check")
                    reassign_sonoffs_check = True
                    self.reassign_sonoff_address()

                    
                try:
                    URL = self.pool3_heater1_status
                    r1 = requests.get(url = URL, timeout=15)
                    data1 = r1.json()
                    # print(data1)
                    print(data1['Status']['FriendlyName'][0])
                    if(data1['Status']['FriendlyName'][0] != u'Pool_3 Heater 1'):
                        print("Pool 3 Heater 1 Being Reassigned")
                        reassign_sonoffs_check = True 
                except Exception as e:
                    print(e)
                    print("Pool 3 Failed Heater 1 check.")
                    reassign_sonoffs_check = True
                    self.reassign_sonoff_address()
                try:   
                    URL = self.pool3_heater2_status
                    r2 = requests.get(url = URL, timeout=10)
                    data2 = r2.json() 
                    # print(data2)
                    print(data2['Status']['FriendlyName'][0])
                    if(data2['Status']['FriendlyName'][0] != u'Pool3_Heater2'):
                        print("Pool 3 Heater 2 Being Reassigned")
                        reassign_sonoffs_check = True
                except:
                    print("Pool 3 Failed Heater 2 Check.")
                    reassign_sonoffs_check = True
                    self.reassign_sonoff_address()
            #------Pool 4------
            if(self.pool_4_active):
                try:   
                    URL = self.pool4_heater_status
                    r3 = requests.get(url = URL, timeout=10)
                    data3 = r3.json()
                    # print(data3)
                    print(data3['Status']['FriendlyName'][0])
                    if(data3['Status']['FriendlyName'][0] != u'Pool4_Heat'):
                        print("Pool 4 Heater Being Reassigned")
                        reassign_sonoffs_check = True 
                except:
                    print("Pool 4 heater Failed to respond")
                    reassign_sonoffs_check = True
                    self.reassign_sonoff_address()
                    
                try:
                    URL = self.pool4_cooler_status
                    r4 = requests.get(url = URL, timeout=10)
                    data4 = r4.json() 
                    # print(data4)
                    print(data4['Status']['FriendlyName'][0])
                    if(data4['Status']['FriendlyName'][0] != u'Pool_4_Cooling'):
                        reassign_sonoffs_check = True
                except:
                    print("Pool 4 Failed Cooler check.")
                    reassign_sonoffs_check = True
                    self.reassign_sonoff_address()
        except Exception as e:
            # if(reassign_sonoffs_check == True):
            print("This is final failure")
            print(e)
            self.reassign_sonoff_address()
            

        

        


        
    def poll_sensors(self):

        try:

            pool1_temp = self.pool1_heater_status.replace('Status%209', 'Status%208')
            r = requests.get(url = pool1_temp, timeout=10)
            p1_data = r.json() 
            # print(p1_data)
            # print(data4['Status']['FriendlyName'][0])
            # print(p1_data['StatusSNS']['DS18B20']['Temperature'])
            self.pool1_temp_global = p1_data['StatusSNS']['DS18B20']['Temperature']

        except Exception as e:
            print("Failed Pool 1 temp check")
            print(e)
            self.poll_restart_counter = self.poll_restart_counter + 1
            print(self.poll_restart_counter)



        try:

            pool2_temp = self.pool2_cooler_status.replace('Status%209', 'Status%208')
            r = requests.get(url = pool2_temp, timeout=10)
            p2_data = r.json() 
            # print(p2_data)
            # print(p2_data['StatusSNS']['DS18B20']['Temperature'])
            self.pool2_temp_global = p2_data['StatusSNS']['DS18B20']['Temperature']

        except Exception as e:
            print("Failed Pool 2 temp check")
            print(e)
            self.poll_restart_counter = self.poll_restart_counter + 1
            print(self.poll_restart_counter)
        if(self.pool_2_point_five_active):
            try:
                pool2_5_temp = self.pool2_5_cooler_status.replace('Status%209', 'Status%208')

                r = requests.get(url = pool2_5_temp, timeout=10)
                p2_5_data = r.json() 
                # print(p2_5_data['StatusSNS']['DS18B20']['Temperature'])
                self.pool2_5_temp_global = p2_5_data['StatusSNS']['DS18B20']['Temperature']

            except Exception as e:
                print("Failed pool 2.5 temp check")
                print(e)
                self.poll_restart_counter = self.poll_restart_counter + 1
                print(self.poll_restart_counter)


        try:
            pool3_temp = self.pool3_cooler_status.replace('Status%209', 'Status%208')
            r = requests.get(url = pool3_temp, timeout=10)
            p3_data = r.json() 
            # print(p3_data['StatusSNS']['DS18B20']['Temperature'])
            self.pool3_temp_global = p3_data['StatusSNS']['DS18B20']['Temperature']
        except Exception as e:
            print("Failed pool 3 temp check")
            print(e)
            self.poll_restart_counter = self.poll_restart_counter + 1
            print(self.poll_restart_counter)

        try:

            pool4_temp = self.pool4_cooler_status.replace('Status%209', 'Status%208')
            r = requests.get(url = pool4_temp, timeout=10)
            p4_data = r.json() 
            # print(p4_data['StatusSNS']['DS18B20']['Temperature'])
            self.pool4_temp_global = p4_data['StatusSNS']['DS18B20']['Temperature']
        except Exception as e:
            print("Failed pool 4 temp check")
            print(e)
            self.poll_restart_counter = self.poll_restart_counter + 1
            print(self.poll_restart_counter)

        try:

            r = requests.get(url = self.greenhouse_status, timeout=10)
            greenhouse_data = r.json() 
            # print(greenhouse_data['StatusSNS']['AM2301']['Humidity'])
            # print(greenhouse_data['StatusSNS']['AM2301']['Temperature'])
            self.greenhouse_temp_global = greenhouse_data['StatusSNS']['AM2301']['Temperature']
            self.greenhouse_humidity_global = greenhouse_data['StatusSNS']['AM2301']['Humidity']

        except Exception as e:
            print("Failed Greenhouse Check")
            print(e)
            self.poll_restart_counter = self.poll_restart_counter + 1
            print(self.poll_restart_counter)

        try:
            r = requests.get(url = self.outside_status, timeout=10)
            outside_data = r.json() 
            # print(outside_data['StatusSNS']['AM2301']['Humidity'])
            # print(outside_data['StatusSNS']['AM2301']['Temperature'])
            self.outside_temp_global = outside_data['StatusSNS']['AM2301']['Temperature']
            self.outside_humidity_global = outside_data['StatusSNS']['AM2301']['Humidity']
        except Exception as e:
            print("Failed outside data check")
            print(e)
            self.poll_restart_counter = self.poll_restart_counter + 1
            print(self.poll_restart_counter)

        try:
            r = requests.get(url = self.illumination_status, timeout=10)
            illumination_data = r.json() 
            # print(illumination_data)
            # print(illumination_data['StatusSNS']['SI1145']['Illuminance'])
            # print(illumination_data['StatusSNS']['SI1145']['Infrared'])
            # print(illumination_data['StatusSNS']['SI1145']['UvIndex'])
            self.light_illuminance_global = illumination_data['StatusSNS']['SI1145']['Illuminance']
            self.light_infrared_global = illumination_data['StatusSNS']['SI1145']['Infrared']
            self.light_uvindex_global = illumination_data['StatusSNS']['SI1145']['UvIndex']
        
        except Exception as e:
            print("Failed Light Sensor check")
            print(e)
            self.poll_restart_counter = self.poll_restart_counter + 1
            print(self.poll_restart_counter)


        




    def reassign_sonoff_address(self):
        for i in range (3,101):
            print(i)
            try:
                URL = "http://192.168.1." +str(i) +"/cm?cmnd=Status%209"
                r = requests.get(url = URL, timeout=1.5)
                data = r.json() 
                # print(data)
                print(data['Status']['FriendlyName'])
                if(data['Status']['FriendlyName'][0] ==u'Pool_3 Temp and Cooler'):
                    print("Found pool 3 temp and cooler at ")
                    self.pool3_cooler_turn_on = "http://192.168.1." + str(i) + "/cm?cmnd=Power%20On"
                    self.pool3_cooler_turn_off = "http://192.168.1." + str(i) + "/cm?cmnd=Power%20off"
                    self.pool3_cooler = "http://192.168.1." + str(i) + "/cm?cmnd=Power"
                    self.pool3_cooler_status = "http://192.168.1." + str(i) + "/cm?cmnd=Status%209"
                if(data['Status']['FriendlyName'][0] ==u'Pool_3 Heater 1'):
                    self.pool3_heater1_turn_on = "http://192.168.1." + str(i) + "/cm?cmnd=Power%20On"
                    self.pool3_heater1_turn_off = "http://192.168.1." + str(i) + "/cm?cmnd=Power%20off"
                    self.pool3_heater1 = "http://192.168.1." + str(i) + "/cm?cmnd=Power"
                    self.pool3_heater1_status = "http://192.168.1." + str(i) + "/cm?cmnd=Status%209"
                if(data['Status']['FriendlyName'][0] ==u'Pool3_Heater2'):
                    self.pool3_heater1_turn_on = "http://192.168.1." + str(i) + "/cm?cmnd=Power%20On"
                    self.pool3_heater1_turn_off = "http://192.168.1." + str(i) + "/cm?cmnd=Power%20off"
                    self.pool3_heater1 = "http://192.168.1." + str(i) + "/cm?cmnd=Power"
                    self.pool3_heater2_status = "http://192.168.1." + str(i) + "/cm?cmnd=Status%209"
                if(data['Status']['FriendlyName'][0] ==u'Pool4_Heat'):
                    self.pool4_heater_turn_on = "http://192.168.1." + str(i) + "/cm?cmnd=Power%20On"
                    self.pool4_heater_turn_off = "http://192.168.1." + str(i) + "/cm?cmnd=Power%20off"
                    self.pool4_heater = "http://192.168.1." + str(i) + "/cm?cmnd=Power"
                    self.pool4_heater_status = "http://192.168.1." + str(i) + "/cm?cmnd=Status%209"
                if(data['Status']['FriendlyName'][0] ==u'Pool4_Cooling'):
                    self.pool4_cooler_turn_on = "http://192.168.1." + str(i) + "/cm?cmnd=Power%20On"
                    self.pool4_cooler_turn_off = "http://192.168.1." + str(i) + "/cm?cmnd=Power%20off"
                    self.pool4_cooler = "http://192.168.1." + str(i) + "/cm?cmnd=Power"
                    self.pool4_cooler_status = "http://192.168.1." + str(i) + "/cm?cmnd=Status%209"
                if(data['Status']['FriendlyName'][0] ==u'Pool_2_Temp_and_Cooling'):
                    print("Found pool 2 temp and cooler at ")
                    self.pool2_cooler_turn_on = "http://192.168.1." + str(i) + "/cm?cmnd=Power%20On"
                    self.pool2_cooler_turn_off = "http://192.168.1." + str(i) + "/cm?cmnd=Power%20off"
                    self.pool2_cooler = "http://192.168.1." + str(i) + "/cm?cmnd=Power"
                    self.pool2_cooler_status = "http://192.168.1." + str(i) + "/cm?cmnd=Status%209"
                if(data['Status']['FriendlyName'][0] ==u'Pool_1_temp'):
                    print("Found pool 1 temp and cooler at ")
                    self.pool1_heater_turn_on = "http://192.168.1." + str(i) + "/cm?cmnd=Power%20On"
                    self.pool1_heater_turn_off = "http://192.168.1." + str(i) + "/cm?cmnd=Power%20off"
                    self.pool1_heater = "http://192.168.1." + str(i) + "/cm?cmnd=Power"
                    self.pool1_heater_status = "http://192.168.1." + str(i) + "/cm?cmnd=Status%209"
                # if(data['Status']['FriendlyName'][0] ==u'Pool_2_Temp_and_Cooling'):
                #     print("Found pool 1 temp and cooler at ")
                #     self.pool2_cooler_turn_on = "http://192.168.1." + str(i) + "/cm?cmnd=Power%20On"
                #     self.pool2_cooler_turn_off = "http://192.168.1." + str(i) + "/cm?cmnd=Power%20off"
                #     self.pool2_cooler = "http://192.168.1." + str(i) + "/cm?cmnd=Power"
                #     self.pool2_cooler_status = "http://192.168.1." + str(i) + "/cm?cmnd=Status%209"
                if(data['Status']['FriendlyName'][0] ==u'Pool_2_Heat'):
                    print("Found pool 1 temp and cooler at ")
                    self.pool2_heater_turn_on = "http://192.168.1." + str(i) + "/cm?cmnd=Power%20On"
                    self.pool2_heater_turn_off = "http://192.168.1." + str(i) + "/cm?cmnd=Power%20off"
                    self.pool2_heater = "http://192.168.1." + str(i) + "/cm?cmnd=Power"
                    self.pool2_heater_status = "http://192.168.1." + str(i) + "/cm?cmnd=Status%209"

                # Pool 2.5 Sonoffs
                if(data['Status']['FriendlyName'][0] ==u'Pool 2.5 Heat'):
                    print("Found pool 2.5 heat at ")
                    self.pool2_5_heater_turn_on = "http://192.168.1." + str(i) + "/cm?cmnd=Power%20On"
                    self.pool2_5_heater_turn_off = "http://192.168.1." + str(i) + "/cm?cmnd=Power%20off"
                    self.pool2_5_heater = "http://192.168.1." + str(i) + "/cm?cmnd=Power"
                    self.pool2_5_heater_status = "http://192.168.1." + str(i) + "/cm?cmnd=Status%209"

                if(data['Status']['FriendlyName'][0] ==u'Pool 2.5 Temp and Cooling'):
                    print("Found pool 2.5 Temp and Cooling at ")
                    self.pool2_5_cooler_turn_on = "http://192.168.1." + str(i) + "/cm?cmnd=Power%20On"
                    self.pool2_5_cooler_turn_off = "http://192.168.1." + str(i) + "/cm?cmnd=Power%20off"
                    self.pool2_5_cooler = "http://192.168.1." + str(i) + "/cm?cmnd=Power"
                    self.pool2_5_cooler_status = "http://192.168.1." + str(i) + "/cm?cmnd=Status%209"

            except Exception as e:
                # print(e)
                print("none at this point")


    def Look_For_Sonoffs(self):
        friendly_names = self.gsheets_retrieve_data('Control!E2:E30', self.spreadsheet_id)
        for i in range (3,101):
                try:
                    # Check Ip address and send request to find if it responds
                    URL = "http://192.168.1." +str(i) +"/cm?cmnd=Status%209"
                    r = requests.get(url = URL, timeout=2)
                    data = r.json() 
                    # Search through the current names and compare it to the found sonoff
                    for name in friendly_names:
                        # If sonoff name is in the list then 
                        if(str(data['Status']['FriendlyName'][0]) == name):
                            if(self.check_for_sheet(str(data['Status']['FriendlyName'][0]))):
                                text = "Sheet already exists for " + str(data['Status']['FriendlyName'][0])
                                print()

                            else:
                                # self.gsheets_add_sheet(str(data['Status']['FriendlyName'][0]))
                                print("---------There is no sheet for this make a new one!---------------")



                except Exception as e:
                    print(e)
                    print("No Sonoff")

            
     #---------------------Check For Sheet---------------------
        # @desc:    Passes in a sheet name and looks in the google sheet to see if it already exists
        #           If it exists it returns true, if not it returns false
        # @param:  (str(sheet_name))
        # @return: (boolean)
    #----------------------------------------------------     
    def check_for_sheet(self, sheet_name):
        try:
            sheet = str(sheet_name) + '!A1:A1'
            check_first_cell = self.gsheets_retrieve_data(sheet, self.spreadsheet_id)
            print(check_first_cell)
            print("sheet exists")
            return(True)
        except:
            print("No Sheet")
            return(False)
    #---------------------Control Pool Temp--------------------
        # @desc:    Passes in a sheet name and looks in the google sheet to see if it already exists
        #           If it exists it returns true, if not it returns false
        # @param:  (str(sheet_name))
        # @return: (boolean)
    #----------------------------------------------------  

    def check_sensor(self):
        print("Checking Sensors")
        # 
        if(self.pool_3_active):
            if(self.entities.sensor.pool3_temp.state != "unknown" ):
                self.pool3_sensor_off_count = 0
                self.pool3_sensor_off_text = False

            elif(self.entities.sensor.pool3_temp.state == "unknown" and self.pool3_sensor_off_count>3 and self.pool3_sensor_off_text != True):
                text = "Pool 3 Sensor is Not Recording Please Check"
                self.text_notification(text)
                self.pool3_sensor_off_text = True

            else:
                print("Pool 3 Sensor not logging")
                self.pool3_sensor_off_count = self.pool3_sensor_off_count + 1
                print(self.pool3_sensor_off_count)

        
        # Check if heater or cooler is on and log
        if(self.pool_4_active):
            if(self.entities.sensor.pool4_temp.state != "unknown"):
                self.pool4_sensor_off_count = 0
                self.pool4_sensor_off_text = False

            elif(self.entities.sensor.pool4_temp.state == "unknown" and self.pool4_sensor_off_count>3 and self.pool4_sensor_off_text != True):
                text = "Pool 4 Sensor is Not Recording Please Check"
                self.text_notification(text)
                self.pool4_sensor_off_text = True

            else:
                self.pool4_sensor_off_count = self.pool4_sensor_off_count + 1

       
        if(self.pool_1_active):

            if(self.entities.sensor.pool_1_temp.state != "unknown"):
                self.pool1_sensor_off_count = 0
                self.pool1_sensor_off_text = False
                
            elif(self.entities.sensor.pool_1_temp.state == "unknown" and self.pool1_sensor_off_count>3 and self.pool1_sensor_off_text != True):
                text = "Pool 1 Sensor is Not Recording Please Check"
                self.text_notification(text)
                self.pool1_sensor_off_text = True

            else:
                self.pool1_sensor_off_count = self.pool1_sensor_off_count + 1

        if(self.pool_2_active):
            if(self.entities.sensor.pool_2_temp.state != "unknown"):
                self.pool2_sensor_off_count = 0
                self.pool2_sensor_off_text = False
                

            elif(self.entities.sensor.pool_2_temp.state == "unknown" and self.pool2_sensor_off_count>3 and self.pool2_sensor_off_text != True):
                text = "Pool 2 Sensor is Not Recording Please Check"
                self.text_notification(text)
                self.pool2_sensor_off_text = True

            else:
                self.pool2_sensor_off_count = self.pool2_sensor_off_count + 1

        # Pool 2.5
        if(self.pool_2_point_five_active):
            try:
                if(self.entities.sensor.pool_2_5_temp.state != "unknown"):
                    self.pool2_5_sensor_off_count = 0
                    self.pool2_5_sensor_off_text = False

                elif(self.entities.sensor.pool_2_5_temp.state == "unknown" and self.pool2_5_sensor_off_count>3 and self.pool2_5_sensor_off_text != True):
                    text = "Pool 2.5 Sensor is Not Recording Please Check"
                    self.text_notification(text)
                    self.pool2_5_sensor_off_text = True

                else:
                    self.pool2_5_sensor_off_count = self.pool2_5_sensor_off_count + 1

            except Exception as e:
                print(e)

    #---------------------Data Buffer---------------------
        # @desc:    Uses Http requests to check if the sonoffs relays are active and thus
        #           check if the heaters or coolers are currently running and update the booleans
        #           that indicate if any of these are on.

        # @param: (none)
        # @return: none
    #-----------------------------------------------------
    def data_buffer(self):
        print("TEST")
        fmt = '%Y-%m-%d %H:%M:%S'
        d = datetime.now()
        cur_time = d.strftime(fmt)
        data_list = []
        self.log("Data Buffer storing data currently.")
        # Check relays for their current status
        try:
            self.check_relays()
        except:
            print("Failed to check relays.")
        self.log("Greenhouse temp =%s" % self.entities.sensor.greenhouse_temp.state)

        # Insert Greenhouse data
        if(self.entities.sensor.greenhouse_temp.state != "unknown"):
            greenhouse_data = str(cur_time) + "," + str(self.entities.sensor.greenhouse_temp.last_updated) + "," +str(self.entities.sensor.greenhouse_temp.attributes.friendly_name) + "," + str(self.entities.sensor.greenhouse_temp.state) + "," + str(self.entities.sensor.greenhouse_humidity.state) + "," + "Null"+ "," + "Null" + "," + "Null"+","+ "Null"+","+ "Null"
            data_list.append(greenhouse_data)

        # Check if heater or cooler is on and log 
        self.log("Pool 3 temp =%s" % self.entities.sensor.pool3_temp.state)
        if(self.pool_3_active):
            if(self.entities.sensor.pool3_temp.state != "unknown" ):
                self.pool3_sensor_off_text = False
                self.pool3_sensor_off_count = 0
                if(self.pool3_heater_on == True):
                    p3_heat = "5"
                else:
                    p3_heat = "0"
                if(self.pool3_cooler_on == True):
                    p3_cool = "5"
                else:
                    p3_cool = "0"
            
                p3_data = str(cur_time) + "," + str(self.entities.sensor.pool3_temp.last_updated) + "," +str(self.entities.sensor.pool3_temp.attributes.friendly_name) +"," + str(self.entities.sensor.pool3_temp.state) + "," + "Null" + "," + "Null"+ "," + str(p3_heat) + "," + str(p3_cool) +","+ "Null"+","+ "Null"
                data_list.append(p3_data)
            elif(self.entities.sensor.pool3_temp.state == "unknown" and self.pool3_sensor_off_count>1 and self.pool3_sensor_off_text != True):
                text = "Pool 3 Sensor is Not Recording Please Check"
                self.text_notification(text)
                self.pool3_sensor_off_text = True

            else:
                print("Pool 3 Sensor not logging")
                self.pool3_sensor_off_count = self.pool3_sensor_off_count + 1
                print(self.pool3_sensor_off_count)

        self.log("Pool 4 temp =%s" % self.entities.sensor.pool4_temp.state)
        # Check if heater or cooler is on and log
        if(self.pool_4_active):
            if(self.entities.sensor.pool4_temp.state != "unknown"):
                self.pool4_sensor_off_text = False
                self.pool4_sensor_off_count = 0
                if(self.pool4_heater_on == True):
                    p4_heat = "10"
                else:
                    p4_heat = "0"
                if(self.pool4_cooler_on == True):
                    p4_cool = "10"
                else:
                    p4_cool = "0"
            # Insert Pool 4 Data
                # self.gsheets_insert(cur_time,
                #                     self.spreadsheet_id,
                #                     self.entities.sensor.pool4_temp.last_updated,
                #                     self.entities.sensor.pool4_temp.attributes.friendly_name,
                #                     self.entities.sensor.pool4_temp.state, "Null", "Null", p4_heat, p4_cool, "Null", "Null")

                p4_data = str(cur_time) + "," + str(self.entities.sensor.pool4_temp.last_updated) + "," +str(self.entities.sensor.pool4_temp.attributes.friendly_name) +"," + str(self.entities.sensor.pool4_temp.state) + "," + "Null" + "," + "Null"+ "," + str(p4_heat) + "," + str(p4_cool) +","+ "Null"+","+ "Null"
                data_list.append(p4_data)
            elif(self.entities.sensor.pool4_temp.state == "unknown" and self.pool4_sensor_off_count>1 and self.pool4_sensor_off_text != True):
                try:
                    text = "Pool 4 Sensor is Not Recording Please Check"
                    self.text_notification(text)
                    self.pool4_sensor_off_text = True
                except:
                    print("Texts not working")

            else:
                self.pool4_sensor_off_count = self.pool4_sensor_off_count + 1

        self.log("Outside temp =%s" % self.entities.sensor.outside_temp.state)
        # Insert Outside Data
        if(self.entities.sensor.outside_temp.state != "unknown"):
            

            outside_data = str(cur_time) + "," + str(self.entities.sensor.outside_temp.last_updated) + "," +str(self.entities.sensor.outside_temp.attributes.friendly_name) +"," + str(self.entities.sensor.outside_temp.state) + "," + str(self.entities.sensor.outside_humidity.state) + "," + "Null"+ "," + "Null" + "," + "Null"+","+ "Null"+","+ "Null"
            data_list.append(outside_data)
        self.log("Light Lux =%s" % self.entities.sensor.light_illuminance.state)
        # Insert Light Data
        try:
            if(self.entities.sensor.light_illuminance.state != "unknown"):
                
                light_data = str(cur_time) + "," + str(self.entities.sensor.light_illumiminance.last_updated) + "," +str(self.entities.sensor.light_illumance.attributes.friendly_name) +"," + str(self.entities.sensor.light_illumance.state) + "," + str(self.entities.sensor.light_infrared.state) + "," + str(self.entities.sensor.light_uv.state)+ "," + "Null" + "," + "Null"+","+ "Null"+","+ "Null"
                data_list.append(light_data)
        except Exception as e:
            print(e)
        # if(self.entities.sensor.pool_4_airpump_heat.state != "unknown"):
        try:
            
            if(self.pool_1_active):

                if(self.entities.sensor.pool_1_temp.state != "unknown"):
                    self.pool1_sensor_off_text = False
                    self.pool1_sensor_off_count = 0
                    if(self.pool1_heater_on == True):
                        p1_heat = "10"
                    else:
                        p1_heat = "0"
                    if(self.pool1_cooler_on == True):
                        p1_cool = "10"
                    else:
                        p1_cool = "0"
                

                    p1_data = str(cur_time) + "," + str(self.entities.sensor.pool_1_temp.last_updated) + "," +"pool_1_temp" +"," + str(self.entities.sensor.pool_1_temp.state) + "," + "Null" + "," + "Null"+ "," + str(p1_heat) + "," + str(p1_cool) +","+ "Null"+","+ "Null"
                    data_list.append(p1_data)
                elif(self.entities.sensor.pool_1_temp.state == "unknown" and self.pool1_sensor_off_count>1 and self.pool1_sensor_off_text != True):
                    try:
                        text = "Pool 1 Sensor is Not Recording Please Check"

                        self.text_notification(text)
                        self.pool1_sensor_off_text = True
                    except:
                        print("Texts not working")

                else:
                    self.pool1_sensor_off_count = self.pool1_sensor_off_count + 1

            if(self.pool_2_active):
                if(self.entities.sensor.pool_2_temp.state != "unknown"):
                    self.pool2_sensor_off_count = 0
                    self.pool2_sensor_off_text = False
                    if(self.pool2_heater_on == True):
                        p2_heat = "5"
                    else:
                        p2_heat = "0"
                    # Only one cooling Implement so basing it all off pool 1
                    if(self.pool1_cooler_on == True):
                        p2_cool = "5"
                    else:
                        p2_cool = "0"
                

                    p2_data = str(cur_time) + "," + str(self.entities.sensor.pool_2_temp.last_updated) + "," +"pool_2_temp" +"," + str(self.entities.sensor.pool_2_temp.state) + "," + "Null" + "," + "Null"+ "," + str(p2_heat) + "," + str(p2_cool) +","+ "Null"+","+ "Null"
                    data_list.append(p2_data)

                elif(self.entities.sensor.pool_2_temp.state == "unknown" and self.pool2_sensor_off_count>1 and self.pool2_sensor_off_text != True):
                    try:

                        text = "Pool 2 Sensor is Not Recording Please Check"
                        self.text_notification(text)
                        self.pool2_sensor_off_text = True
                    except:
                            print("Texts not working")

                else:
                    self.pool2_sensor_off_count = self.pool2_sensor_off_count + 1
        except Exception as e:
            print(e)

        # Pool 2.5
        if(self.pool_2_point_five_active):
            try:
                if(self.entities.sensor.pool_2_5_temp.state != "unknown"):
                    self.pool2_5_sensor_off_count = 0
                    self.pool2_5_sensor_off_text = False
                    if(self.pool2_5_heater_on == True):
                        p2_5_heat = "5"
                    else:
                        p2_5_heat = "0"
                    # Only one cooling Implement so basing it all off pool 1
                    if(self.pool2_5_cooler_on == True):
                        p2_5_cool = "5"
                    else:
                        p2_5_cool = "0"
                

                    p2_5_data = str(cur_time) + "," + str(self.entities.sensor.pool_2_5_temp.last_updated) + "," +"pool_2.5_temp" +"," + str(self.entities.sensor.pool_2_5_temp.state) + "," + "Null" + "," + "Null"+ "," + str(p2_5_heat) + "," + str(p2_5_cool) +","+ "Null"+","+ "Null"
                    data_list.append(p2_5_data)

                elif(self.entities.sensor.pool_2_5_temp.state == "unknown" and self.pool2_5_sensor_off_count>1 and self.pool2_5_sensor_off_text != True):
                    try:
                        text = "Pool 2.5 Sensor is Not Recording Please Check"
                        self.text_notification(text)
                        self.pool2_5_sensor_off_text = True
                    except:
                        print("Texts not working")

                else:
                    self.pool2_5_sensor_off_count = self.pool2_5_sensor_off_count + 1


            except Exception as e:
                print(e)
                print("no pool 2.5")
        print("Got to end of data")
        self.data_buffer_write(data_list)

        return(cur_time)

    def is_file_there(self):
        try:
            f = open("/home/homeassistant/conf/bufferdata.txt")
            self.file_exists = True
            f.close()
        except:
            self.file_exists = False

    def data_buffer_write(self, text):
        # f= open("bufferdata.txt","w+")
        # if(os.path.exists('bufferdata.txt')):
        # file_exists = False
        print("In data_buffer_write")
        try:
            f = open("/home/homeassistant/conf/bufferdata.txt")
            file_exists = True
            f.close()

            # If it exists then append to the end of it
            f = open("/home/homeassistant/conf/bufferdata.txt", "a")
            for x in text:
                modified_text = x +"\n"
                print(modified_text)
                f.write(modified_text)
            print("bufferdata.txt exists, append to end")

        except Exception as e:
            print(e)
            print('File does not exist')
            try:
                print("Before open")
                f = open("/home/homeassistant/conf/bufferdata.txt", "w+")
                for x in text:
                    modified_text = x + "\n"
                    print(modified_text)
                    f.write(modified_text)
                f.close() 
                print("After Opening")
                print("Succesfully made a txt file.")
            except Exception as e:
                print("Failed to make file")
                print(e)

        # else:
        #     # if(file_exists == True):
        #     for i in range(10):
        #         f.write("%s\r\n" % (text))
        #     f.close() 
    def empty_data_buffer(self):
        print("TEST")
        try:
            f = open('/home/homeassistant/conf/bufferdata.txt', "r")
            file_exists = True
            line_count = 0

            for x in f:
                print(x)
                data = x.replace("\n","")
                list = data.split(",")
                if(list[2] == "greenhouse_temp"):
                    print(list)
                    self.gsheets_insert(list[0], self.spreadsheet_id, list[1], list[2],list[3],
                                        list[4], list[5], list[6], list[7], list[8], list[9])
                if(list[2] == "pool3_temp"):
                    print(list)
                    self.gsheets_insert(list[0], self.spreadsheet_id, list[1], list[2],list[3],
                                        list[4], list[5], list[6], list[7], list[8], list[9])
                if(list[2] == "pool4_temp"):
                    print(list)
                    self.gsheets_insert(list[0], self.spreadsheet_id, list[1], list[2],list[3],
                                        list[4], list[5], list[6], list[7], list[8], list[9])
                if(list[2] == "outside_temp"):
                    print(list)
                    self.gsheets_insert(list[0], self.spreadsheet_id, list[1], list[2],list[3],
                                        list[4], list[5], list[6], list[7], list[8], list[9])
                if(list[2] == "light_illuminance"):
                    print(list)
                    self.gsheets_insert(list[0], self.spreadsheet_id, list[1], list[2],list[3],
                                        list[4], list[5], list[6], list[7], list[8], list[9])
                if(list[2] == "pool_1_temp"):
                    print(list)
                    self.gsheets_insert(list[0], self.spreadsheet_id, list[1], list[2],list[3],
                                        list[4], list[5], list[6], list[7], list[8], list[9])
                if(list[2] == "pool_2_temp"):
                    print(list)
                    self.gsheets_insert(list[0], self.spreadsheet_id, list[1], list[2],list[3],
                                        list[4], list[5], list[6], list[7], list[8], list[9])
                if(list[2] == "pool2_5_temp"):
                    print(list)
                    self.gsheets_insert(list[0], self.spreadsheet_id, list[1], list[2],list[3],
                                        list[4], list[5], list[6], list[7], list[8], list[9])

            print("Removing Buffer File")
            os.remove("/home/homeassistant/conf/bufferdata.txt")
        except Exception as e:
            print("Failed Buffer for Some reason")
            print(e)



    def dynamic_pool_control(self, pool_number):
        if(self.pool_1_active):
            try:
                if(self.entities.sensor.pool_1_temp.state != "unknown"):
                    pool1_conv = float(self.entities.sensor.pool_1_temp.state)
                    if(pool1_conv > float(pool1_high) and self.pool1_cooler_on != True and self.pool1_heater_on != True):
                        self.log("Pool 1 Cooler Turned On. Too Hot Temp: %s" % self.entities.sensor.pool_1_temp.state)
                        self.pool1_cooler_on = True 
                        try:
                            self.send_http(self.pool1_cooler_turn_on)
                            # textout = 'Pool 1 Cooler Turned on at ' + str(self.entities.sensor.pool_1_temp.state)
                            # self.send_text(textout, "Conrad")
                        # Pool 4 Cooler is not responding
                        except:
                            self.log("Failed to http get request to the site.")
                            if(self.p1_cooler_broken_on_checked == False):
                                self.check_sonoff_status()
                                self.p1_cooler_broken_on_checked = True
                            elif(self.p1_cooler_broken_on_text == False):
                                testtext = 'Pool 1 Turn Cooler On Failed, Please Check'
                                self.text_notification(testtext)
                                self.p1_cooler_broken_on_text = True
                    if(pool1_conv < float(pool1_low) and self.pool1_heater_on != True and self.pool1_cooler_on != True):
                        self.log("Pool 1 Heater Turned On. Too Cool Temp: %s"% self.entities.sensor.pool_1_temp.state)
                        self.pool1_heater_on = True
                        try:

                            self.send_http(self.pool1_heater_turn_on)
                            print("Pool 1 heater successfully turned on")
                        # Pool 1 Heater is not responding
                        except Exception as e:
                            print(e)
                            if(self.p1_heater_broken_on_checked == False):
                                self.check_sonoff_status()
                                self.p1_heater_broken_on_checked = True
                            elif(self.p1_heater_broken_on_text == False):
                                self.log("Failed to http get request to the site.")
                                testtext = 'Pool 1 Turn Heater On Failed, Please Check'
                                self.text_notification(testtext)
                                self.p1_heater_broken_on_text==True
                    if(pool1_conv < float(pool1_high) and self.pool1_cooler_on == True):
                        self.log("Pool 1 Cooler Turned Off. Current Temp: %s"% self.entities.sensor.pool_1_temp.state)
                        self.pool1_cooler_on = False
                        try:
                            self.send_http(self.pool1_cooler_turn_off)
                        except:
                            if(self.p1_cooler_broken_off_checked == False):
                                self.check_sonoff_status()
                                self.p1_cooler_broken_off_checked = True
                            elif(self.p1_cooler_broken_off_text == False): 
                                self.log("Failed to http get request to the site.")
                                testtext = 'Pool 1 Turn Cooler Off Failed, Please Check'
                                self.text_notification(testtext)
                    if(pool1_conv > float(pool1_low) and self.pool1_heater_on == True):
                        self.log("Pool 1 Heater Turned Off. Current Temp: %s"% self.entities.sensor.pool_1_temp.state)
                        self.pool1_heater_on = False
                        try:
                            self.send_http(self.pool1_heater_turn_off)
                        except:
                            if(self.p1_heater_broken_off_checked == False):
                                self.check_sonoff_status()
                                self.p1_heater_broken_off_checked = True
                            elif(self.p1_heater_broken_off_text == False): 
                                self.log("Failed to http get request to the site.")
                                testtext = 'Pool 1 Turn Heater Off Failed, Please Check'
                                self.text_notification(testtext)
            except Exception as e:
                print(e)
                testtext = 'Pool 1 Turn Cooler is off'
                self.send_text(testtext, "Conrad")
    def check_ping(self):

        try:
            response = subprocess.check_output(
                ['ping', '-c', '1', '8.8.8.8'],
                stderr=subprocess.STDOUT,  # get all output
                universal_newlines=True  # return string not bytes
            )
            # print(response)
            return(True)
        except subprocess.CalledProcessError:
            print("Failed ping")
            response = None
            return(False)

        # hostname = "8.8.8.8"
        # response = os.system("ping -c 1 " + hostname)
        # # and then check the response...
        # if response == 0:
        #     pingstatus = True
        # else:
        #     pingstatus = False
        if(response==0):
            return(True)
        else:
            return(False)

        # return pingstatus

    def check_ip(self):
        hostname = socket.gethostname()    
        IPAddr = socket.gethostbyname(hostname + ".local")
        print("Your Computer Name is:" + hostname)    
        print("Your Computer IP Address is:" + IPAddr) 
        if(IPAddr != "192.168.1.20"):
            print("Ip address is wrong")
            self.restart_pi()
        else:
            print("Ip is correct")

    def notification_start(self):
        # notification text Timing
        time = self.get_time()
        send_notification_text = False

        # print("Checking Time")
        # print(time)
        notification_time_10_am = datetime.utcfromtimestamp(1594720800).strftime('%H:%M:%S')
        notification_time_11_am = datetime.utcfromtimestamp(1594724400).strftime('%H:%M:%S')
        notification_time_3_pm = datetime.utcfromtimestamp(1594738800).strftime('%H:%M:%S')
        notification_time_4_pm = datetime.utcfromtimestamp(1594742400).strftime('%H:%M:%S')
        #1594742400
        # notification_time_10_am = datetime.utcfromtimestamp(1594720800).strftime('%H:%M:%S')
        # notification_time_11_am = datetime.utcfromtimestamp(1594724400).strftime('%H:%M:%S')

        # Between 10 an and 11 am notification
        # print(time)
        # print (notification_time_3_pm)
        # if(time>notification_time_3_pm and time<notification_time_4_pm):
        #     print("Past 3pm")
        # if(time<notification_time_4_pm):
        #     print("Before  4pm")
        # if(time>notification_time_3_pm and time<notification_time_4_pm):
        #     print("Past 3pm and before 4 pm")

        if(time>notification_time_10_am and time <notification_time_11_am):
            if(self.notification_text_sent_out == False):
                send_notification_text = True
        elif(time>notification_time_11_am and time< notification_time_3_pm and self.notification_text_sent_out == True):
            self.notification_text_sent_out = False
            send_notification_text=False
            print("between 11 am and 3 pm")
        # Between 3pm and 4pm notification
        if(time>notification_time_3_pm and time <notification_time_4_pm):
            if(self.notification_text_sent_out == False):
                send_notification_text = True
        elif(time>notification_time_4_pm  and self.notification_text_sent_out == True):
            self.notification_text_sent_out = False
            send_notification_text=False
            print("between 4 pm and 10 am")

        # send_notifcation_text= self.check_notification_time(time)
        
        if(send_notification_text == True and self.notification_text_sent_out == False):
            text = "Greenspring Farm Notification Update: Current Time: " + str(time)
            self.send_text(text, 'Conrad')
            self.send_text(text, 'Tarah')
            self.notification_text_sent_out = True

    # def check_notifcation_time(self, time):
    #     print("Checking Time")
    #     print(time)
    #     notification_time_10_am = datetime.utcfromtimestamp(1594720800).strftime('%H:%M:%S')
    #     notification_time_11_am = datetime.utcfromtimestamp(1594724400).strftime('%H:%M:%S')
    #     notification_time_3_pm = datetime.utcfromtimestamp(1594738800).strftime('%H:%M:%S')
    #     notification_time_4_pm = datetime.utcfromtimestamp(1594742400).strftime('%H:%M:%S')
    #     # notification_time_10_am = datetime.utcfromtimestamp(1594720800).strftime('%H:%M:%S')
    #     # notification_time_11_am = datetime.utcfromtimestamp(1594724400).strftime('%H:%M:%S')

    #     # Between 10 an and 11 am notification
    #     if(time>notification_time_10_am and time <notification_time_11_am):
    #         if(self.notification_text_sent_out):
    #             send_text = True
    #     elif(time>notification_time_11_am and time< notification_time_3_pm and self.notification_text_sent_out == True):
    #         self.notification_text_sent_out = False
    #         send_text=False
    #     # Between 3pm and 4pm notification
    #     if(time>notification_time_3_pm and time <notification_time_4_pm):
    #         if(self.notification_text_sent_out):
    #             send_text = True
    #     elif(time>notification_time_4_pm and time< notification_time_10_am and self.notification_text_sent_out == True):
    #         self.notification_text_sent_out = False
    #         send_text=False

    #     return(send_text)



    # def store_data_locally(self):
    #      self.log("***** inside log_sensor_data *****")
    #     #self.log("***** last_updated:%s, last_changed:%s *****" % (self.entities.sensor.greenhouse_temp.last_updated,
    #     #                                                            self.entities.sensor.greenhouse_temp.last_changed))
    #     self.log("***** last_updated:%s, last_changed:%s *****" % (self.entities.sensor.outside_temp.last_updated,
    #                                                                 self.entities.sensor.outside_temp.last_changed))
    #     # Get Current Time for Log input
    #     fmt = '%Y-%m-%d %H:%M:%S'
    #     d = datetime.now()
    #     cur_time = d.strftime(fmt)
    #     # Check relays for their current status
    #     try:
    #         self.check_relays()
    #     except:
    #         print("Failed to check relays.")
    #     self.log("Greenhouse temp =%s" % self.entities.sensor.greenhouse_temp.state)
    #     # Insert Greenhouse data
    #     if(self.entities.sensor.greenhouse_temp.state != "unknown"):
    #         self.gsheets_insert(cur_time,
    #                             self.spreadsheet_id,
    #                             self.entities.sensor.greenhouse_temp.last_updated,
    #                             self.entities.sensor.greenhouse_temp.attributes.friendly_name,
    #                             #self.get_state(self.entities.sensor.greenhouse_temp, attribute="friendly_name"),
    #                             self.entities.sensor.greenhouse_temp.state,
    #                             self.entities.sensor.greenhouse_humidity.state, "Null", "Null", "Null", "Null", "Null")
    #     # Check if heater or cooler is on and log 
    #     self.log("Pool 3 temp =%s" % self.entities.sensor.pool3_temp.state)
    #     if(self.entities.sensor.pool3_temp.state != "unknown"):
    #         if(self.pool3_heater_on == True):
    #             p3_heat = "5"
    #         else:
    #             p3_heat = "0"
    #         if(self.pool3_cooler_on == True):
    #             p3_cool = "5"
    #         else:
    #             p3_cool = "0"
    #     # Insert Pool 3 Data
    #         self.gsheets_insert(cur_time,
    #                             self.spreadsheet_id,
    #                             self.entities.sensor.pool3_temp.last_updated,
    #                             self.entities.sensor.pool3_temp.attributes.friendly_name,
    #                             self.entities.sensor.pool3_temp.state, "Null", "Null",p3_heat, p3_cool, "Null", "Null")

    #     self.log("Pool 4 temp =%s" % self.entities.sensor.pool4_temp.state)
    #     # Check if heater or cooler is on and log
    #     if(self.entities.sensor.pool4_temp.state != "unknown"):
    #         if(self.pool4_heater_on == True):
    #             p4_heat = "10"
    #         else:
    #             p4_heat = "0"
    #         if(self.pool4_cooler_on == True):
    #             p4_cool = "10"
    #         else:
    #             p4_cool = "0"
    #     # Insert Pool 4 Data
    #         self.gsheets_insert(cur_time,
    #                             self.spreadsheet_id,
    #                             self.entities.sensor.pool4_temp.last_updated,
    #                             self.entities.sensor.pool4_temp.attributes.friendly_name,
    #                             self.entities.sensor.pool4_temp.state, "Null", "Null", p4_heat, p4_cool, "Null", "Null")

    #     self.log("Outisde temp =%s" % self.entities.sensor.outside_temp.state)
    #     # Insert Outside Data
    #     if(self.entities.sensor.outside_temp.state != "unknown"):
    #         self.gsheets_insert(cur_time,
    #                             self.spreadsheet_id,
    #                             self.entities.sensor.outside_temp.last_updated,
    #                             self.entities.sensor.outside_temp.attributes.friendly_name,
    #                             self.entities.sensor.outside_temp.state,
    #                             self.entities.sensor.outside_humidity.state, "Null", "Null", "Null", "Null", "Null")
    #     self.log("Light Lux =%s" % self.entities.sensor.light_illuminance.state)
    #     # Insert Light Data
    #     if(self.entities.sensor.light_illuminance.state != "unknown"):
    #         self.gsheets_insert(cur_time,
    #                             self.spreadsheet_id,
    #                             self.entities.sensor.light_illuminance.last_updated,
    #                             self.entities.sensor.light_illuminance.attributes.friendly_name,
    #                             self.entities.sensor.light_illuminance.state,
    #                             self.entities.sensor.light_infrared.state,
    #                             self.entities.sensor.light_uv.state, "Null", "Null", "Null", "Null")
    #     # if(self.entities.sensor.pool_4_airpump_heat.state != "unknown"):

    #     # # Insert Pool 3 Data
    #     #     self.gsheets_insert(cur_time,
    #     #                         self.spreadsheet_id,
    #     #                         self.entities.sensor.pool_4_airpump_heat.last_updated,
    #     #                         "pool_4_airpump_temp",
    #     #                         self.entities.sensor.pool_4_airpump_heat.state, "Null", "Null", "Null", "Null", "Null", "Null")

    #     if(self.entities.sensor.pool_1_temp.state != "unknown"):
    #         if(self.pool1_heater_on == True):
    #             p1_heat = "10"
    #         else:
    #             p1_heat = "0"
    #         if(self.pool1_cooler_on == True):
    #             p1_cool = "10"
    #         else:
    #             p1_cool = "0"
    #     # Insert Pool 3 Data
    #         self.gsheets_insert(cur_time,
    #                             self.spreadsheet_id,
    #                             self.entities.sensor.pool_1_temp.last_updated,
    #                             "pool_1_temp",
    #                             self.entities.sensor.pool_1_temp.state, "Null", "Null", p1_heat, p1_cool, "Null", "Null")

    #     if(self.entities.sensor.pool_2_temp.state != "unknown"):
    #         if(self.pool2_heater_on == True):
    #             p2_heat = "5"
    #         else:
    #             p2_heat = "0"
    #         # Only one cooling Implement so basing it all off pool 1
    #         if(self.pool1_cooler_on == True):
    #             p2_cool = "5"
    #         else:
    #             p2_cool = "0"
    #     # Insert Pool 3 Data
    #         self.gsheets_insert(cur_time,
    #                             self.spreadsheet_id,
    #                             self.entities.sensor.pool_2_temp.last_updated,
    #                             "pool_2_temp",
    #                             self.entities.sensor.pool_2_temp.state, "Null", "Null", p2_heat, p2_cool, "Null", "Null")
    #     # return(cur_time)

class Pool(hass.Hass):
    def initialize(self):
        self.pool_heater_turn_on = "http://192.168.1.0/cm?cmnd=Power%20On"
        self.pool_heater_turn_off = "http://192.168.1.0/cm?cmnd=Power%20off"
        self.pool_cooler_turn_on = "http://192.168.1.0/cm?cmnd=Power%20On"
        self.pool_cooler_turn_off = "http://192.168.1.0/cm?cmnd=Power%20off"

        self.pool_lights_turn_on = "http://192.168.1.115/cm?cmnd=Power%20On"
        self.pool_lights_turn_off = "http://192.168.1.115/cm?cmnd=Power%20off"
        
        # MQTT Check Relay Status
        self.pool_cooler = "http://192.168.1.22/cm?cmnd=Power"
        self.pool_heater = "http://192.168.1.11/cm?cmnd=Power"
        
        # Status
        self.pool_heater_status = "http://192.168.1.11/cm?cmnd=Status%209"
        self.pool_heater_status = "http://192.168.1.8/cm?cmnd=Status%209"
        
        # Broken Relays Boolean
        self.p_cooler_broken = False
        self.p_heater_broken = False

        # Broken Relay Text Boolean
        self.p_cooler_broken_on_text=False
        self.p_cooler_broken_off_text=False
        self.p_heater_broken_on_text=False
        self.p_heater_broken_off_text=False

        self.p_heater_broken_on_checked = False
        self.p_heater_broken_off_checked = False
        self.p_cooler_broken_on_checked = False
        self.p_cooler_broken_off_checked = False


# class TimeOutException(Exception):
#    pass
 
# def alarm_handler(signum, frame):
#     print("ALARM signal received")
#     raise TimeOutException()
        


