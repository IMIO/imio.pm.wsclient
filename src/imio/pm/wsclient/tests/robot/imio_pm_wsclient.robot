*** Settings ***
Documentation  imio.pm.wsclient keywords, built on the ui_plone${PLONE_MAJOR}.robot keywords.
...            The testing layer configures the connection to the fake PloneMeeting and 2 generated
...            actions: "Send to PloneMeeting assembly" (action 1) and "Send to PloneGov assembly".
Resource  ui_plone${PLONE_MAJOR}.robot


*** Variables ***
${SEND_ACTION}  plonemeeting_wsclient_action_1
${SETTINGS_URL}  ${PLONE_URL}/@@ws4pmclient-settings


*** Keywords ***
Log in as the PloneMeeting creator
    [Documentation]  A Manager mapped to pmCreator1 in PloneMeeting (user_mappings of the testing layer)
    Enable autologin as  Manager
    Set autologin username  ${TEST_USER_ID}

A document
    Log in as the PloneMeeting creator
    Create content  type=Document  id=my-document  title=My document  description=Sent to PloneMeeting
    Go to  ${PLONE_URL}/my-document

Open the send form
    Click the content action  ${SEND_ACTION}
    The modal is open

Send the document
    Open the send form
    ${proposing_group}=  Modal element  form-widgets-proposingGroup
    Select from list by label  ${proposing_group}  Developers
    Click the modal button  form-buttons-send_to_plonemeeting
    The status message contains  The item has been correctly sent to PloneMeeting.

The send form shows the error
    [Documentation]  The form is replaced by the error message
    [Arguments]  ${text}
    Wait until element contains  ${MODAL}  ${text}

The PloneMeeting informations are shown
    Wait until page contains  PloneMeeting informations
    Page should contain link  My document

Open the settings
    Go to  ${SETTINGS_URL}
    Wait until page contains element  css=#form-widgets-pm_url

Save the settings
    [Documentation]  The password is not shown, it is entered again
    Input password  css=#form-widgets-pm_password  Meeting_12
    Click button  css=#form-buttons-save
