*** Settings ***
Documentation  Send an element to PloneMeeting from the generated actions (F3, F5, F7, F11).
Resource  imio_pm_wsclient.robot
Test Setup  Open test browser
Test Teardown  Close all browsers


*** Test Cases ***
The generated actions are in the Actions menu
    A document
    The content action is available  plonemeeting_wsclient_action_1
    Element should contain  css=[id="plone-contentmenu-actions-plonemeeting_wsclient_action_1"]  Send to PloneMeeting assembly
    Element should contain  css=[id="plone-contentmenu-actions-plonemeeting_wsclient_action_2"]  Send to PloneGov assembly

Send the element from the send form
    A document
    Send the document
    The PloneMeeting informations are shown
    Page should contain  M. PMCreator One
    Page should contain  PloneMeeting assembly

Cancel the send form
    A document
    Open the send form
    Cancel the modal
    The modal is closed
    Page should not contain  PloneMeeting informations

An element is sent once only
    A document
    Send the document
    Open the send form
    The send form shows the error  This element has already been sent to PloneMeeting!
    Page should not contain element  css=[id="form-widgets-proposingGroup"]

The PloneMeeting informations link to the documents of the item
    A document
    Send the document
    Page should contain element  css=a[href*="@@generate_document_from_plonemeeting"][href*="templateFormat=odt"]
    Page should contain element  css=a[href*="@@generate_document_from_plonemeeting"][href*="templateFormat=pdf"]
