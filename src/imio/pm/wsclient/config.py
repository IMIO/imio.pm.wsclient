# suffix used when adding our actions to portal_actions
ACTION_SUFFIX = 'plonemeeting_wsclient_action_'

# taken from imio.pm.ws
DEFAULT_NO_WARNING_MESSAGE = 'There was NO WARNING message during item creation.'

# messages
CORRECTLY_SENT_TO_PM_INFO = u"The item has been correctly sent to PloneMeeting."
UNABLE_TO_CONNECT_ERROR = u"Unable to connect to PloneMeeting, check the 'WS4PM Client settings'! "\
                          "Please contact system administrator!"
ALREADY_SENT_TO_PM_ERROR = u"This element has already been sent to PloneMeeting!"
TAL_EVAL_FIELD_ERROR = u"There was an error evaluating the TAL expression '%s' for the field '%s'!  " \
                       "The error was : '%s'.  Please contact system administrator."
UNABLE_TO_DETECT_MIMETYPE_ERROR = u"Could not detect correct mimetype for item template! "\
                          "Please contact system administrator!"
FILENAME_MANDATORY_ERROR = u"A filename is mandatory while generating a document! "\
                          "Please contact system administrator!"
UNABLE_TO_DISPLAY_VIEWLET_ERROR = u"Unable to display informations about the potentially linked item " \
            "in PloneMeeting because there was an error evaluating the TAL expression '%s' for the field '%s'!  " \
            "The error was : '%s'.  Please contact system administrator."
CONFIG_UNABLE_TO_CONNECT_TO_PM_ERROR = u"Unable to connect with given url/username/password!"
CONFIG_CREATE_ITEM_PM_ERROR = u"An error occured during the item creation in PloneMeeting!  The error message was : %s"

# annotations key
WS4PMCLIENT_ANNOTATION_KEY = "imio.pm.wsclient-sent_to"
