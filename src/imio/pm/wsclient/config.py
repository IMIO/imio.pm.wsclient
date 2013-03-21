# suffix used when adding our actions to portal_actions
ACTION_SUFFIX = 'plonemeeting_wsclient_action_'

# taken from imio.pm.ws
DEFAULT_NO_WARNING_MESSAGE = 'There was NO WARNING message during item creation.'

# messages
CAN_NOT_SEE_LINKED_ITEMS_INFO = u"This element is linked to item(s) in PloneMeeting but your are not allowed to see it."
CORRECTLY_SENT_TO_PM_INFO = u"The item has been correctly sent to PloneMeeting."
CONFIG_UNABLE_TO_CONNECT_ERROR = u"Unable to connect to PloneMeeting!  The error message was : '%s'! "
UNABLE_TO_CONNECT_ERROR = u"Unable to connect to PloneMeeting!  Please contact system administrator! "
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
CONFIG_CREATE_ITEM_PM_ERROR = u"An error occured during the item creation in PloneMeeting!  The error message was : %s"
NO_PROPOSING_GROUP_ERROR = u"The configuration specify that user '%s' will create the item in PloneMeeting but this " \
                           "user can not create item for any proposingGroup in PloneMeeting!"
NO_USERINFOS_ERROR = u"Could not get userInfos in PloneMeeting for user '%s'!"
# annotations key
WS4PMCLIENT_ANNOTATION_KEY = "imio.pm.wsclient-sent_to"
