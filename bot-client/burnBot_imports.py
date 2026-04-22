# burnBot_imports.py
# Selenium 4 - Cleaned and Organized

# === Standard Libraries ===
import os
import sys
import time
import threading
import shutil
import json
import random
import traceback
import urllib.request
import builtins
import inspect
import re
import configparser
import psutil
import atexit
import socket
import subprocess

from datetime import date, datetime, timedelta

# === Third-Party Libraries ===
import pandas as pd
import requests

from pandas.core.algorithms import safe_sort
from pprint import pprint

# === Selenium and WebDriver Manager ===
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException,TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common import exceptions
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# === Email (SMTP) ===
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# === burnBot Project Modules ===

#import burnBot_changeAccount  # Not used
#import burnBot_likePostsHome
#import burnBot_likePostsTopic
#import burnBot_followAccount
#import burnBot_unfollowAccount
#import burnBot_followSuggested

#import burnBot_sendMail  # Removed - using burnBot_notifications instead
import burnBot_login
#import burnBot_setDriver
import burnBot_utils
import burnBot_config

#from burnBot_setDriver import InstaBot_Driver
