*** Settings ***
Documentation  Control panel of the connection to PloneMeeting (F2).
Resource  imio_pm_wsclient.robot
Test Setup  Open test browser
Test Teardown  Close all browsers


*** Test Cases ***
The settings are in the control panel
    Enable autologin as  Manager
    Go to  ${PLONE_URL}/@@overview-controlpanel
    Click link  css=#content a[href$="/@@ws4pmclient-settings"]:not(.dropdown-item)
    Wait until page contains element  css=#form-widgets-pm_url
    Textfield value should be  css=#form-widgets-pm_url  http://pm.example.org/plone
    The page is not an error

Save the settings
    Enable autologin as  Manager
    Open the settings
    Input text  css=#form-widgets-pm_timeout  20
    Save the settings
    The status message contains  Changes saved
    Textfield value should be  css=#form-widgets-pm_timeout  20
    # the generated actions are kept
    A document
    The content action is available  plonemeeting_wsclient_action_1

A wrong URL shows the connection error
    Enable autologin as  Manager
    Open the settings
    Input text  css=#form-widgets-pm_url  http://wrong.example.org
    Save the settings
    The status message contains  Unable to connect to PloneMeeting! The error message was : Failed to establish a new connection
