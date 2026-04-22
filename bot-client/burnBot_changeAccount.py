# selenium 4
from burnBot_imports import *
from burnBot_utils import close_windows, has_internet_connection, process_exception, delay

def changeAccount(driver, targetAccount):
    moduleErrorsLog = ""
    module_status = None
    try:
        print(f"{targetAccount}:[<account>]", end="")
        time.sleep(2)
        driver.get('https://www.instagram.com/')
        WebDriverWait(driver, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        current_ActiveAccount = driver.find_element(By.CSS_SELECTOR, "a.xwhw2v2").text
        
        time.sleep(random.randint(4, 6))
        
        print(f" -current:[<{current_ActiveAccount}>] ")
        if targetAccount in current_ActiveAccount:  ##already in account
            print(f"{targetAccount}:[<account>] -change:[<unnecessary>] ")

        else: ## not in target account
            print(f"{targetAccount}:[<account>] -change:[<needed>] ")


            ## find the switch account link for drop-down
            switchLink = driver.find_element(By.XPATH, "//div[contains(text(), 'Switch')]")
            actions = ActionChains(driver);actions.move_to_element(switchLink);actions.click(switchLink);actions.perform()
            time.sleep(random.randint(2, 4))

            ## read list in switch account drop-down
            switchBox = driver.find_element(By.CLASS_NAME, "x71s49j")  ##issue###
            switchBoxList = switchBox.find_elements(By.CLASS_NAME, "xuxw1ft")
            for switchCount, SwitchAccount in enumerate(switchBoxList):
                try:
                    if SwitchAccount.text == targetAccount:
                        #print(f"{targetAccount}:[<account>] attempt[<{targetAccount}>]")
                        actions = ActionChains(driver) ; actions.move_to_element(switchBoxList[switchCount]) ; actions.click(switchBoxList[switchCount]) ; actions.perform()
                        time.sleep(random.randint(5, 7))
                        break
                except (NoSuchElementException, StaleElementReferenceException):
                    pass

        #### do the double check..
        try:
            elem = WebDriverWait(driver, 6).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.xwhw2v2")))
            current_ActiveAccount = elem.text
            if targetAccount in current_ActiveAccount:
                module_status = True
            else:
                module_status = False

        except Exception as error:  ### catch all errors
            noteError = "check current account"
            printError = False; logError = False; debugError = False
            moduleErrorsLog += process_exception(printError, noteError, logError, debugError)


    except Exception as error:  ### catch all errors
        noteError = "changeAccount catch all"
        printError = False; logError = True; debugError = False
        moduleErrorsLog += process_exception(printError, noteError, logError, debugError)
    
    return module_status, moduleErrorsLog