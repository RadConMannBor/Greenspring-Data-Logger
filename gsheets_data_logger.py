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
import re
import smtplib
import pyowm
import requests 
import traceback
import photosynq_py as ps
import environment_variables


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
#

class GSheetsDataLogger(hass.Hass):
    def initialize(self):
        self.log("******* Hello from GSheetsDataLogger ********")
#        self.log("temp =%s" % self.entities.sensor.greenhouse_temp.state)

        

        self.SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
        self.CLIENT_SECRET_FILE = 'client_secret.json'
        self.CLIENT_TOKEN_FILE_NAME = 'gsheets_write_token.json' #Copied from token.json
        self.APPLICATION_NAME = 'GsheetsDataLogger' 
        self.spreadsheet_id = os.getenv('SPREADSHEET_ID') # FARM
        
        # These flags determine if temperature went over expected levels and to watch for when it returns
        self.pool3_flag = False
        self.pool4_flag = False
        self.greenhouse_flag = False
        self.farm_flag = False
        self.light_flag = False
        self.pool3_heater_on = False
        self.pool3_cooler_on = False

        self.pool4_heater_on = False
        self.pool4_cooler_on = False
        # MQTT heating and cooling commands
        self.pool3_heater1_turn_on = "http://192.168.1.27/cm?cmnd=Power%20On"
        self.pool3_heater1_turn_off = "http://192.168.1.27/cm?cmnd=Power%20off"
        self.pool3_heater2_turn_on = "http://192.168.1.100/cm?cmnd=Power%20On"
        self.pool3_heater2_turn_off = "http://192.168.1.100/cm?cmnd=Power%20off"
        self.pool3_cooler_turn_on = "http://192.168.1.42/cm?cmnd=Power%20On"
        self.pool3_cooler_turn_off = "http://192.168.1.42/cm?cmnd=Power%20off"
        self.pool3_lights_turn_on = "http://192.168.1.115/cm?cmnd=Power%20On"
        self.pool3_lights_turn_off = "http://192.168.1.115/cm?cmnd=Power%20off"
        self.pool4_heater_turn_on = "http://192.168.1.47/cm?cmnd=Power%20On"
        self.pool4_heater_turn_off = "http://192.168.1.47/cm?cmnd=Power%20off"
        self.pool4_cooler_turn_on = "http://192.168.1.46/cm?cmnd=Power%20On"
        self.pool4_cooler_turn_off = "http://192.168.1.46/cm?cmnd=Power%20off"
        self.pool4_lights_turn_on = "http://192.168.1.115/cm?cmnd=Power%20On"
        self.pool4_lights_turn_off = "http://192.168.1.115/cm?cmnd=Power%20off"
        # MQTT Check Relay Status
        self.pool3_heater1 = "http://192.168.1.27/cm?cmnd=Power"
        self.pool3_heater2 = "http://192.168.1.100/cm?cmnd=Power"
        self.pool3_cooler = "http://192.168.1.42/cm?cmnd=Power"
        self.pool3_lights = "http://192.168.1.115/cm?cmnd=Power"
        self.pool4_heater = "http://192.168.1.47/cm?cmnd=Power"
        self.pool4_cooler = "http://192.168.1.46/cm?cmnd=Power"
        self.pool4_lights = "http://192.168.1.115/cm?cmnd=Power"
        # Broken Relays Boolean
        self.p3_heater1_broken=False
        self.p3_heater2_broken=False
        self.p4_heater_broken=False
        self.p3_cooler_broken=False
        self.p4_heater_broken=False
        self.p4_cooler_broken=False
        # Broken Relay Text Boolean
        self.p3_heater1_broken_text=False
        self.p3_heater2_broken_text=False
        self.p4_heater_broken_text=False
        self.p3_cooler_broken_text=False
        self.p4_heater_broken_text=False
        self.p4_cooler_broken_text=False

        self.pool3_heater_count = 0
        self.pool3_cooler_count = 0

        self.forecast_trigger = False
        self.photosynq_trigger = True
        # Google Sheet Spreadsheet id's
        self.photosynq_p3_spreadsheet_id = 1809622314
        self.photosynq_p4_spreadsheet_id = 633728140
        self.outside_spreadsheet_id =1139064985
        self.data_summary_spreadsheet_id =1
        self.pool_4_spreadsheet_id =114357400
        self.pool_3_spreadsheet_id =1889372714
        self.greenhouse_spreadsheet_id =894214581
        self.sunlight_spreadsheet_id =202215001
        self.weather_forecast_sheet = 1366405747

        self.row_1 = 1
        self.row_2 = 2
        self.row_42 = 42
        self.row_43 = 43
        
        self.brentwood_id = 5330642

        self.wind_speed_limit = 12
        self.wind_gust_limit = 16
        # Counters
        self.restart_counter = 0
        self.three_hours = 3
        self.six_ten_minutes = 6
        self.four_failure_cycles = 4
     

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
        # self.get_photosynq()
        # self.log("After photosynq TEST")    
        try:
            # Credentials for Google sheets interface
            self.credentials = self.get_credentials()
            self.http = self.credentials.authorize(httplib2.Http())
            self.service = discovery.build('sheets', 'v4', http=self.http, discoveryServiceUrl=self.discoveryUrl)

            # try:
            #     self.get_photosynq()
            #     self.log("After photosynq TEST")
            # except Exception as e:
            #     print("Photosynq Failed!")
            #     print(e)

            self.log("after services - discover.build")
            ten_minutes = 6
            forecast_counter = 0
            loop = 10
            error_count = 0
            
            
            
            self.log("***** Trying to run every 10 minute...")
            while True:
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
                    try:
                        # make only one retreive for control values
                        control_values = self.gsheets_retrieve_data('Control!B2:B7', self.spreadsheet_id)
                    except Exception as e:
                    # except Exception as e, e:
                    #     logger.error('Failed retrieve Data: '+ str(e))
                        self.log("!!!!!!!!!!!!!!!Failed Retrieve Data!!!!!!!!!!!!!!!!!!!")
                        traceback.print_exc()
                        print(e)
                    try:
                        # control_values = self.gsheets_retrieve_data('Control!B2:B7', self.spreadsheet_id)
                        self.check_sensors_text(control_values[0], control_values[1], control_values[2], control_values[3], control_values[4], control_values[5])
                    except Exception as e:
                        self.log("!!!!!!!!!!!!!!!Failed Text Notification. (BIG Problem)!!!!!!!!!!!!!!!!!!!")
                        traceback.print_exc()
                        print(e)
                    try:
                        time_store = self.log_sensor_data()
                    except Exception as e:
                        self.log("!!!!!!!!!!Failed Log Sensor Data. (Internet Failed Likely)!!!!!!!!!!!!")
                        traceback.print_exc()
                        print(e)
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
                    photosynq_start_time = datetime.utcfromtimestamp(1577444400).strftime('%H:%M:%S')
                    photosynq_end_time = datetime.utcfromtimestamp(1577448000).strftime('%H:%M:%S')
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
                    #---------------------Pool Temperature Control Loop---------------------
                    # @desc Retrieve Control Values from the google sheets that will determine temperature for 
                    #       Controlling the Pools heating and cooling system.
                   #  
                    try:
                        control_values2 = self.gsheets_retrieve_data('Control!B9:B22', self.spreadsheet_id)
                        # Check for restart
                        if(control_values2[13] =='1'):
                            self.restart_pi()



                    except Exception as e:
                        self.log("Retrieve Data Failed.")
                        traceback.print_exc()
                        print(e)
                    # Pool Temperature control loop that will check every minute the status of the temperature and control heating and cooling based on the sensor data
                    while n < 10:
                        try:
                            try:
                                self.control_pool_temp(control_values2[1], control_values2[2], control_values2[3], control_values2[4], control_values2[5], control_values2[6], control_values2[7], control_values2[8], control_values2[9], control_values2[10], control_values2[11], control_values2[12], sunrise, sunset)
                            except Exception as e:
                                # Control values for temperature control in case of internet failure.  I chose to keep these readable so 
                                # It would be easier to alter them
                                self.control_pool_temp(35, 33.3, 26, 35, 33.3, 26, 35, 30, 22, 35, 30, 22, sunrise, sunset)
                                traceback.print_exc()
                                print(e)

                        except Exception as e:
                            self.log("!!!!!!!!!!!-----Cooling and Heating Control FAILED first one use standard values----!!!!!!!!!!!!!!")
                            traceback.print_exc()
                            print(e)
                        n = n + 1
                        time.sleep(55)
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
                            self.control_pool_temp(control_values2[1], control_values2[2], control_values2[3], control_values2[4], control_values2[5], control_values2[6], control_values2[7], control_values2[8], control_values2[9], control_values2[10], control_values2[11], control_values2[12], sunrise, sunset)
                            # self.log("*****! Made it Past Control Pool Temp !*****")
                        except Exception as e:
                            try:
                                self.log("!!!!!!!!!!!-----Cooling and Heating Control use standard values----!!!!!!!!!!!!!!")
                                self.control_pool_temp(35, 33.3, 26, 35, 33.3, 26, 35, 30, 22, 35, 30, 22, 0,0)
                                traceback.print_exc()
                                print(e)
                            except:
                                # Final Failur point and if it reaches this point a second time it should restart the pi
                                restart_counter = restart_counter+1
                                print("Got to final failure point")
                                if(restart_counter == 2):
                                    self.restart_pi()
                        n = n + 1
                        time.sleep(55)
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
        if(self.entities.sensor.greenhouse_temp.state != "unknown"):
            self.gsheets_insert(cur_time,
                                self.spreadsheet_id,
                                self.entities.sensor.greenhouse_temp.last_updated,
                                self.entities.sensor.greenhouse_temp.attributes.friendly_name,
                                #self.get_state(self.entities.sensor.greenhouse_temp, attribute="friendly_name"),
                                self.entities.sensor.greenhouse_temp.state,
                                self.entities.sensor.greenhouse_humidity.state, "Null", "Null", "Null", "Null", "Null")
        # Check if heater or cooler is on and log 
        self.log("Pool 3 temp =%s" % self.entities.sensor.pool3_temp.state)
        if(self.entities.sensor.pool3_temp.state != "unknown"):
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
                                self.entities.sensor.pool3_temp.last_updated,
                                self.entities.sensor.pool3_temp.attributes.friendly_name,
                                self.entities.sensor.pool3_temp.state, "Null", "Null",p3_heat, p3_cool, "Null", "Null")

        self.log("Pool 4 temp =%s" % self.entities.sensor.pool4_temp.state)
        # Check if heater or cooler is on and log
        if(self.entities.sensor.pool4_temp.state != "unknown"):
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
                                self.entities.sensor.pool4_temp.last_updated,
                                self.entities.sensor.pool4_temp.attributes.friendly_name,
                                self.entities.sensor.pool4_temp.state, "Null", "Null", p4_heat, p4_cool, "Null", "Null")

        self.log("Outisde temp =%s" % self.entities.sensor.outside_temp.state)
        # Insert Outside Data
        if(self.entities.sensor.outside_temp.state != "unknown"):
            self.gsheets_insert(cur_time,
                                self.spreadsheet_id,
                                self.entities.sensor.outside_temp.last_updated,
                                self.entities.sensor.outside_temp.attributes.friendly_name,
                                self.entities.sensor.outside_temp.state,
                                self.entities.sensor.outside_humidity.state, "Null", "Null", "Null", "Null", "Null")
        self.log("Light Lux =%s" % self.entities.sensor.light_illuminance.state)
        # Insert Light Data
        if(self.entities.sensor.light_illuminance.state != "unknown"):
            self.gsheets_insert(cur_time,
                                self.spreadsheet_id,
                                self.entities.sensor.light_illuminance.last_updated,
                                self.entities.sensor.light_illuminance.attributes.friendly_name,
                                self.entities.sensor.light_illuminance.state,
                                self.entities.sensor.light_infrared.state,
                                self.entities.sensor.light_uv.state, "Null", "Null", "Null", "Null")
        # weather = self.get_weather()    
        # self.weather_insert(cur_time, self.spreadsheet_id,  weather[0], weather[1], weather[2],
        #                     weather[3], weather[4],weather[5], weather[6], weather[7], weather[8])
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
        # self.log('***** gsheets_insert local_str:%s' % local_str)

        # fmt = '%Y-%m-%d %H:%M:%S'
        # d = datetime.now()
        # cur_time = d.strftime(fmt)

        spreadsheet_str = str(spreadsheet_id)
        # Pools
        if (val2 == "Null" and val3 == "Null"):
            data = log_time + "," + local_str + "," + val1 + "," + val4 + "," + val5
        # Temp & Humidity
        elif(val3 == "Null"):
            data = log_time + "," + local_str + "," + val1 + "," + val2
        # Light
        elif(val4 =="Null" and val5 == "Null"):
            data = log_time + "," + local_str + "," + val1 + "," + val2 + "," + val3
        # PHotosynq
        else:
            data =  val1 + "," + val2 + "," + val3 + "," + val4 + "," + val5 + "," + val6 + "," + val7


        if(sheet_name ==  "outside_temp"):
            #sheet = o #TEST
            sheet = self.outside_spreadsheet_id
        # elif(sheet_name ==  "pool1_temp"):
        #     #sheet = 813402084 #TEST
        #     sheet = 1
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
        else:
            #sheet = 1077133875 #TEST
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

    # def gsheets_draw_chart(self, spreadsheet_id, sheet_id, chart_name):

    #     spreadsheet_str = str(spreadsheet_id)

    #     # self.log("*****In Chart Try 2 *****")

    #     if(chart_name == "Pool_3"):
    #         left_axis = "Temperature C"
    #         batch_update_spreadsheet_request_body = {
    #           "requests": [
    #             {
    #               "addChart": {
    #                 "chart": {
    #                   "spec": {
    #                     "title": chart_name,
    #                     "basicChart": {
    #                       "chartType": "SCATTER",
    #                       "legendPosition": "BOTTOM_LEGEND",
    #                       "axis": [
    #                         {
    #                           "position": "BOTTOM_AXIS",
    #                           "title": "Date & Time"
    #                         },
    #                         {
    #                           "position": "LEFT_AXIS",
    #                           "title": left_axis
    #                         }
    #                       ],
    #                       "domains": [
    #                         {
    #                           "domain": {
    #                             "sourceRange": {
    #                               "sources": [
    #                                 {
    #                                   "sheetId": sheet_id,
    #                                   "startRowIndex": 1,
    #                                   "endRowIndex": 300,
    #                                   "startColumnIndex": 1,
    #                                   "endColumnIndex": 2
    #                                 }
    #                               ]
    #                             }
    #                           }
    #                         }
    #                       ],
    #                       "series": [
    #                         {
    #                           "series": {
    #                             "sourceRange": {
    #                               "sources": [
    #                                 {
    #                                   "sheetId": sheet_id,
    #                                   "startRowIndex": 1,
    #                                   "endRowIndex": 300,
    #                                   "startColumnIndex": 2,
    #                                   "endColumnIndex": 3
    #                                 }
    #                               ]
    #                             }
    #                           },
    #                           "targetAxis": "LEFT_AXIS"
    #                         }
    #                       ],
    #                       "headercount": 1
    #                     }
    #                   },
    #                   "position": {
    #                     "overlayPosition": {
    #                       "anchorCell": {
    #                         "sheetId": sheet_id,
    #                         "rowIndex": 4,
    #                         "columnIndex": 2
    #                       },
    #                       "offsetXPixels": 80,
    #                       "offsetYPixels": 30
    #                     }
    #                   }
    #                 }
    #               }
    #             }
    #           ]
    #         }

    #     else:
    #         left_axis = "Temperature & Humidity"
    #         batch_update_spreadsheet_request_body = {
    #           "requests": [
    #             {
    #               "addChart": {
    #                 "chart": {
    #                   "spec": {
    #                     "title": chart_name,
    #                     "basicChart": {
    #                       "chartType": "SCATTER",
    #                       "legendPosition": "BOTTOM_LEGEND",
    #                       "axis": [
    #                         {
    #                           "position": "BOTTOM_AXIS",
    #                           "title": "Date & Time"
    #                         },
    #                         {
    #                           "position": "LEFT_AXIS",
    #                           "title": left_axis
    #                         }
    #                       ],
    #                       "domains": [
    #                         {
    #                           "domain": {
    #                             "sourceRange": {
    #                               "sources": [
    #                                 {
    #                                   "sheetId": sheet_id,
    #                                   "startRowIndex": 1,
    #                                   "endRowIndex": 300,
    #                                   "startColumnIndex": 1,
    #                                   "endColumnIndex": 2
    #                                 }
    #                               ]
    #                             }
    #                           }
    #                         }
    #                       ],
    #                       "series": [
    #                         {
    #                           "series": {
    #                             "sourceRange": {
    #                               "sources": [
    #                                 {
    #                                   "sheetId": sheet_id,
    #                                   "startRowIndex": 1,
    #                                   "endRowIndex": 300,
    #                                   "startColumnIndex": 2,
    #                                   "endColumnIndex": 3
    #                                 }
    #                               ]
    #                             }
    #                           },
    #                           "targetAxis": "LEFT_AXIS"
    #                         }
    #                       ],
    #                       "headercount": 1
    #                     }
    #                   },
    #                   "position": {
    #                     "overlayPosition": {
    #                       "anchorCell": {
    #                         "sheetId": sheet_id,
    #                         "rowIndex": 4,
    #                         "columnIndex": 2
    #                       },
    #                       "offsetXPixels": 80,
    #                       "offsetYPixels": 30
    #                     }
    #                   }
    #                 }
    #               }
    #             }
    #           ]
    #         }

    #     request = self.service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=batch_update_spreadsheet_request_body)
    #     try :
    #         response = request.execute()
    #     except Exception as e:
    #         self.log("google-api ERROR: %s" % response)
    #         print(e)
    #     else :
    #         # TODO: Change code below to process the `response` dict:
    #         self.log("google-api response: %s" % response)


    #---------------------Retrieve Data From Google Sheet---------------------
        # @desc:    Retrieve data from data sheet and use the sheet range and spreadsheet id
        #           to Grab the data and return it as a list.        

        # @param:  string(sheet_range), string(spreadsheet_id)
        # @return: none
    #-------------------------------------------------------------------------
    def gsheets_retrieve_data(self, sheet_range, spreadsheet_id):

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

    #---------------------Send Text---------------------
        # @desc:    Send a text message to a specific person
        # @param:  string(message), string(person)
        # @return: none
    #---------------------------------------------------
    def send_text(self, message, person):
        # Replace the number with your own, or consider using an argument\dict for multiple people.
        message_subject = '--Greenspring Text Notification System--'
        auth = ('Greenspringtextnotifications@gmail.com', 'GSTextSMS')

        aaron_phone= os.getenv('AARON_PHONE')
        sasha_phone= os.getenv('SASHA_PHONE')
        tarah_phone= os.getenv('TARAH_PHONE')
        conrad_phone= os.getenv('CONRAD_PHONE')
        elle_phone= os.getenv('ELLE_PHONE')

        if(person == "Aaron"):
            to_number = aaron_phone.format(carriers['verizon'])
            message = "From: %s\r\n" % auth[0] + "To: %s\r\n" % to_number + "Subject: %s\r\n" % message_subject + "\r\n" + message
        elif(person == "Sasha"):
            to_number = sasha_phone.format(carriers['tmobile'])
            message = "From: %s\r\n" % auth[0] + "To: %s\r\n" % to_number + "Subject: %s\r\n" % message_subject + "\r\n" + message
        elif(person == "Tarah"):
            to_number = tarah_phone.format(carriers['sprint'])
            message = "From: %s\r\n" % auth[0] + "To: %s\r\n" % to_number + "Subject: %s\r\n" % message_subject + "\r\n" + message
        elif(person == "Conrad"):
            to_number = conrad_phone.format(carriers['att'])
            message = "From: %s\r\n" % auth[0] + "To: %s\r\n" % to_number + "Subject: %s\r\n" % message_subject + "\r\n" + message
        elif(person == "Elle"):
            to_number = elle_phone.format(carriers['att'])
            message = "From: %s\r\n" % auth[0] + "To: %s\r\n" % to_number + "Subject: %s\r\n" % message_subject + "\r\n" + message
        # to_number = '2099147599{}'.format(carriers['att'])
        # auth = ('greenspringtext@yahoo.com', 'GSTextSMS')
        # auth = ('greenspringtext@outlook.com', 'GreenspringText')
        
        self.log('***** Gsheets Text to be sent: %s' % message)

        server = smtplib.SMTP( "smtp.gmail.com", 587)
        server.starttls()
        server.login(auth[0], auth[1])
        text = str(message)

        # Send text message through SMS gateway of destination number
        server.sendmail( auth[0], to_number, message)

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

        #************************* Check if values returned to Normal ************************* 
        if(self.entities.sensor.outside_temp.state != "unknown"):
            if((float(farm_high) > float(self.entities.sensor.outside_temp.state) > float(farm_low)) and self.farm_flag == True):
                # outside_conv = float(self.entities.sensor.outside_temp.state)
                testtext = '__Outside Temperature Returned to Acceptable Level__ ' + str(self.entities.sensor.outside_temp.state)+ ' C'
                self.text_notification(testtext)
                self.farm_flag = False

        if(self.entities.sensor.pool3_temp.state != "unknown"):
            if((float(pool_high) > float(self.entities.sensor.pool3_temp.state) > float(pool_low)) and self.pool3_flag == True):
                # pool3_conv = float(self.entities.sensor.pool3_temp.state)
                testtext = '__Pool3 Temperature Returned to Acceptable Level__ ' + str(self.entities.sensor.pool3_temp.state) + ' C' 
                self.text_notification(testtext)
                self.pool3_flag = False

        if(self.entities.sensor.pool4_temp.state != "unknown"):
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


    def text_notification(self, textout):
        textout = textout + "                                                                                                                                                                                                                                                                                                          "
        self.send_text(textout, "Conrad")
        self.send_text(textout, "Aaron")
        self.send_text(textout, "Elle")
        self.send_text(textout, "Tarah")
        self.send_text(textout, "Sasha")
        
        
        
    #---------------------Get Weather---------------------
        # @desc:    Function for the obtaining weather information from the pywom 

        # @param: time, sheet_id, spreadsheet_id, wind_speed,wind_deg, wind_gust, humidity, temp, temp_max, temp_min, rain, clouds
        # @return: none
    #-----------------------------------------------------
    def get_weather(self):
        pyowm_api_key = os.environ.get('PYOWM_API_KEY')
        print(pyowm_api_key)
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
                if(wind["gust"] >16):
                    self.text_notification("Wind gust is very High at the Farm, please take precautions.")

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
        # self.log('***** gsheets_insert last_updated:%s' % last_updated)

        spreadsheet_str = str(spreadsheet_id)

        
        sheet = sheet_id
        if(sheet == self.weather_forecast_sheet):
            start_row_index = 1
            end_row_index = 2
        else:
            start_row_index = 41
            end_row_index = 42
        #1300964882
        data = time + "," + str(temp) + "," + str(temp_min) + "," + str(temp_max) + "," + str(wind_speed) + "," + str(wind_deg) + "," + str(wind_gust) + "," + str(rain) + "," + str(clouds) + "," + str(humidity)

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
    def control_pool_temp(self,pool1_high, pool1_low_day, pool1_low_night , pool2_high,pool2_low_day, pool2_low_night, pool3_high, pool3_low_day, pool3_low_night, pool4_high, pool4_low_day, pool4_low_night, sunrise, sunset):
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

        # peak_energy_start = datetime.utcfromtimestamp(1572966000).strftime('%H:%M:%S')
        # peak_energy_end = datetime.utcfromtimestamp(1572984000).strftime('%H:%M:%S')
        peak_energy_start = datetime.utcfromtimestamp(1573029000).strftime('%H:%M:%S')
        peak_energy_end = datetime.utcfromtimestamp(1573075800).strftime('%H:%M:%S')
        # self.log("Peak Energy Start: %s"%str(peak_energy_start))
        # self.log("Peak Energy End: %s"%str(peak_energy_end))

        # if(time > peak_energy_start and time < peak_energy_end):
        #     self.log("Peak Energy Cost Time, Turn off Heaters unless dangerously low")
        #     pool3_low = pool3_low_night
        #     pool4_low = pool4_low_night

        if(time > sunrise_use and time < sunset_use):
            self.log("Its Day: %s"%str(time))
            # pool1_low = pool1_low_day
            # pool2_low = pool2_low_day
            pool3_low = pool3_low_day
            pool4_low = pool4_low_day

        elif(time < sunrise_use or time > sunset_use):
            self.log("Its Night: %s"%str(time))
            # pool1_low = pool_1_low_night
            # pool2_low = pool_2_low_night
            pool3_low = pool3_low_night
            pool4_low =  pool4_low_night
        self.check_relays()
        #-----------------Pool 3-------------------------
        if(self.entities.sensor.pool3_temp.state != "unknown"):
            pool3_conv = float(self.entities.sensor.pool3_temp.state)
            if(pool3_conv > float(pool3_high) and self.pool3_cooler_on != True and self.pool3_heater_on != True):
                self.log("Pool 3 Cooler Turned On. Too Hot Temp: %s" % self.entities.sensor.pool3_temp.state)
                self.pool3_cooler_on = True 
                try:
                    self.send_http(self.pool3_cooler_turn_on)
                    textout = 'Pool 3 Cooler Turned on at ' + str(self.entities.sensor.pool3_temp.state)
                    try:
                        self.send_text(textout, "Conrad")
                    except:
                        self.log("text didnt work")
                except:
                    time.sleep(20)
                    try:
                        self.send_http(self.pool3_cooler_turn_on)
                        textout = 'Pool 3 Cooler Turned on at ' + str(self.entities.sensor.pool3_temp.state)
                        self.send_text(textout, "Conrad")
                    except:
                        self.log("Failed to http get request to the site.")
                        testtext = 'Pool 3 Turn Cooler On Failed, Please Check'
                        self.text_notification(testtext)
                        # self.send_text(testtext, "Conrad")
                    
            if(pool3_conv < float(pool3_low) and self.pool3_heater_on != True and self.pool3_cooler_on != True):
                self.log("Pool 3 Heater Turned On. Too Cool Temp: %s"% self.entities.sensor.pool3_temp.state)
                self.pool3_heater_on = True
                try:
                    self.send_http(self.pool3_heater1_turn_on)
                    self.send_http(self.pool3_heater2_turn_on)
                    
                    

                except:
                    self.log("Failed to http get request to the site.")
                    if(self.p3_heater1_broken==True and self.p3_heater2_broken==True and self.p3_heater1_broken_text ==False):
                        testtext = 'Pool 3 Both Heaters failed to turn on, Please Check'  
                        self.text_notification(testtext)
                        # self.send_text( testtext,"Conrad")
                        self.p3_heater1_broken_text ==True
                    if(self.p3_heater1_broken==True and self.p3_heater1_broken_text ==False):
                        testtext = 'Pool 3 Turn heater on failed , Please Check'  
                        # self.send_text(testtext,"Conrad")
                        self.text_notification(testtext)
                        self.p3_heater1_broken_text ==True
                    if(self.p3_heater2_broken==True and self.p3_heater2_broken_text ==False):
                        testtext = 'Pool 3 Turn heater on failed , Please Check'  
                        self.text_notification(testtext)
                        # self.send_text(testtext,"Conrad")
                        self.p3_heater1_broken_text ==True
                    
                    
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
        try:
            if(self.entities.sensor.pool4_temp.state != "unknown"):
                pool4_conv = float(self.entities.sensor.pool4_temp.state)
                if(pool4_conv > float(pool4_high) and self.pool4_cooler_on != True and self.pool4_heater_on != True):
                    self.log("Pool 4 Cooler Turned On. Too Hot Temp: %s" % self.entities.sensor.pool4_temp.state)
                    self.pool4_cooler_on = True 
                    try:
                        self.send_http(self.pool4_cooler_turn_on)
                        textout = 'Pool 4 Cooler Turned on at ' + str(self.entities.sensor.pool4_temp.state)
                        self.send_text(textout, "Conrad")
                    except:
                        self.log("Failed to http get request to the site.")
                        testtext = 'Pool 4 Turn Cooler On Failed, Please Check'
                        self.text_notification(testtext)
                if(pool4_conv < float(pool4_low) and self.pool4_heater_on != True and self.pool4_cooler_on != True):
                    self.log("Pool 4 Heater Turned On. Too Cool Temp: %s"% self.entities.sensor.pool4_temp.state)
                    self.pool4_heater_on = True
                    try:
                        self.send_http(self.pool4_heater_turn_on)
                    except:
                        self.log("Failed to http get request to the site.")
                        testtext = 'Pool 4 Turn Heater On Failed, Please Check'
                        self.text_notification(testtext)
                if(pool4_conv < float(pool4_high) and self.pool4_cooler_on == True):
                    self.log("Pool 4 Cooler Turned Off. Current Temp: %s"% self.entities.sensor.pool4_temp.state)
                    self.pool4_cooler_on = False
                    try:
                        self.send_http(self.pool4_cooler_turn_off)
                    except:
                        self.log("Failed to http get request to the site.")
                        testtext = 'Pool 4 Turn Cooler Off Failed, Please Check'
                        self.text_notification(testtext)
                if(pool4_conv > float(pool4_low) and self.pool4_heater_on == True):
                    self.log("Pool 4 Heater Turned Off. Current Temp: %s"% self.entities.sensor.pool4_temp.state)
                    self.pool4_heater_on = False
                    try:
                        self.send_http(self.pool4_heater_turn_off)
                    except:
                        self.log("Failed to http get request to the site.")
                        testtext = 'Pool 4 Turn Heater Off Failed, Please Check'
                        self.text_notification(testtext)
        except:
            testtext = 'Pool 4 Turn Cooler is off'
            self.send_text(testtext, "Conrad")
            self.log("pool 4 turn cooler is off did not work") 
        
   #---------------------Check Relays---------------------
        # @desc:    Uses Http requests to check if the sonoffs relays are active and thus
        #           check if the heaters or coolers are currently running and update the booleans
        #           that indicate if any of these are on.

        # @param: (none)
        # @return: none
    #-----------------------------------------------------
    def check_relays(self):
        # Heaters
        #Need to add try excepts to get around these issues and make it known that there is a problem.

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
        except:
            self.p3_cooler_broken = True
            self.log("Pool 3 cooler failed to turn on.")

        if(self.p3_heater1_broken==True and self.p3_heater2_broken==True and self.p3_heater1_broken_text==False and self.p3_heater2_broken_text==False):
            testtext='Pool 3 both heaters are not responding please check.'
            self.p3_heater1_broken_text=True
            self.p3_heater1_broken_text=True
            self.send_text(testtext,"Conrad")
        elif(self.p3_heater1_broken==True and self.p3_heater1_broken_text==False):
            self.p3_heater1_broken_text=True
            testtext='Pool 3 heater 1 is not responding please check.'
            self.send_text(testtext,"Conrad")
        elif(self.p3_heater2_broken==True and self.p3_heater2_broken_text==False):
            self.p3_heater2_broken_text=True
            testtext='Pool 3 heater 2 is not responding please check.'
            self.send_text(testtext,"Conrad")
        
        # Lights
        # r = requests.get(url = pool3_lights)
        # data1 = r.json() 
        # if(data1["POWER"] == "ON"):
        #     pool3_lights_on = True
        # else:
        #     pool3_lights_on = False
        #Pool 4 Relays
        # Heater
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
        except:
            self.p4_cooler_broken
            self.log("Pool 4 cooler has failed and needs to be checked")
            self.pool4_cooler_on = False
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
        fc = owm.forecast_counter_forecast_at_id(self.brentwood_id)
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

        for x in range(0, 40):
            collection = str(time_list[x]) + ',' +  str(temp_list[x]) + ',' + str(temp_min_list[x]) + ',' + str(temp_max_list[x]) + ',' + str(humidity_list[x]) + ',' + str(wind_speed_list[x]) + ',' +str(wind_deg_list[x]) + ',' + str(wind_gust_list[x]) + ',' + str(clouds_list[x])
            final_data.append(collection)
            print(collection)
            # Insert the data into the google sheet
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
            self.text_notification()

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
            p3_most_recent_time = self.gsheets_retrieve_data('Photosynq P3!A2:A2', self.spreadsheet_id)
            p4_most_recent_time = self.gsheets_retrieve_data('Photosynq P4!A2:A2', self.spreadsheet_id)
            print(p3_most_recent_time)
        except Exception as e:
            self.log("Failed Retrieving most recent photosynq data.")
            print(e)
        # Convert Time of most recently input value to a datetime object to be compared against
        p3_recent_time = datetime.strptime(p3_most_recent_time[0], '%Y-%m-%d %H:%M:%S')
        p4_recent_time = datetime.strptime(p4_most_recent_time[0], '%Y-%m-%d %H:%M:%S')
        #login to PHotosynq
        ps.login(email,password)

        # retrieve a dataframe with data from the given project ID
        projectId = 2005
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
            print("Measurement Time:")
            print(datetime_object)

            # if(cur_time == time): #doing it once a day and taking all the info from that day.
            if(p3_recent_time < datetime_object and df["Algae Photosynthesis MultispeQ V1.0"]["Which pool is being tested?"][key] == "Pool 3"):
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
                self.gsheets_photosynq_insert(self.spreadsheet_id, self.photosynq_p3_spreadsheet_id, str(p3_time), str(p3_phi2), str(p3_phinpq), str(p3_relative_chlorophyll))
                    
            if(p4_recent_time < datetime_object and df["Algae Photosynthesis MultispeQ V1.0"]["Which pool is being tested?"][key] == "Pool 4"):
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
                self.gsheets_photosynq_insert(self.spreadsheet_id, self.photosynq_p4_spreadsheet_id, str(p4_time), str(p4_phi2), str(p4_phinpq), str(p4_relative_chlorophyll))
                    


        # self.gsheets_insert(cur_time,
        #                         self.spreadsheet_id, cur_time, "Photosynq",test_time,
        #                         p3_phi2, p3_phinpq, p3_relative_chlorophyll, p4_phi2, p4_phinpq, p4_relative_chlorophyll)


        # logout
        ps.logout();

    #---------------------Gsheets Photosynq Insert---------------------
        # @desc Takes in the Different photosynq data and inserts it into the Google sheets document
        # @param (int(spreadsheet_id), int(sheet_name_id), str(val1), str(val2), str(val3), str(val4))
    #-------------------------------------------------------------------------
    def gsheets_photosynq_insert(self, spreadsheet_id, sheet_name_id, val1, val2, val3, val4):

        spreadsheet_str = str(spreadsheet_id)
        
        data =  val1 + "," + val2 + "," + val3 + "," + val4

        
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
        # @param: (none)
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



        


