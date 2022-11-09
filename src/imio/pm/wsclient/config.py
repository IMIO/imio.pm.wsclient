from imio.pm.wsclient import WS4PMClientMessageFactory as _

# suffix used when adding our actions to portal_actions
ACTION_SUFFIX = 'plonemeeting_wsclient_action_'

# taken from imio.pm.ws
DEFAULT_NO_WARNING_MESSAGE = _('There was NO WARNING message during item creation.')

# messages
CAN_NOT_SEE_LINKED_ITEMS_INFO = _(u"This element is linked to item(s) in PloneMeeting but your are not allowed to see it.")
CORRECTLY_SENT_TO_PM_INFO = _(u"The item has been correctly sent to PloneMeeting.")
CONFIG_UNABLE_TO_CONNECT_ERROR = _(u"Unable to connect to PloneMeeting! The error message was : ${error}!")
UNABLE_TO_CONNECT_ERROR = _(u"Unable to connect to PloneMeeting! Please contact system administrator!")
ALREADY_SENT_TO_PM_ERROR = _(u"This element has already been sent to PloneMeeting!")
TAL_EVAL_FIELD_ERROR = _(
    u"There was an error evaluating the TAL expression '${expr}' for the field '${field_name}'! "
    "The error was : ${error}. Please contact system administrator."
)
UNABLE_TO_DETECT_MIMETYPE_ERROR = _(
    u"Could not detect correct mimetype for item template! "
    "Please contact system administrator!"
)
FILENAME_MANDATORY_ERROR = _(
    u"A filename is mandatory while generating a document! "
    "Please contact system administrator!"
)
UNABLE_TO_DISPLAY_VIEWLET_ERROR = _(
    u"Unable to display informations about the potentially linked item "
    "in PloneMeeting because there was an error evaluating the TAL expression '${expr}' "
    "for the field '${field_name}'! The error was : '${error}'.  Please contact system administrator."
)
CONFIG_CREATE_ITEM_PM_ERROR = _(
    u"An error occured during the item creation in PloneMeeting! "
    "The error message was : ${error}"
)
NO_PROPOSING_GROUP_ERROR = _(
    u"An error occured during the item creation in PloneMeeting! The error message was "
    u": [{'field': 'proposingGroup', 'message': u'Proposing group is not available for "
    u"user.', 'error': 'ValidationError'}]"
)
NO_USER_INFOS_ERROR = _(u"Could not get userInfos in PloneMeeting for user '${userId}'!")
NO_FIELD_MAPPINGS_ERROR = _(u"No field_mappings defined in the WS4PMClient configuration!")
CAN_NOT_CREATE_FOR_PROPOSING_GROUP_ERROR = _(
    u"The current user can not create an item with the proposingGroup forced "
    "thru the configuration! Please contact system administrator!"
)
NO_CONFIG_INFOS_ERROR = _(u"No configuration informations found!")
CAN_NOT_CREATE_WITH_CATEGORY_ERROR = _(
    u"The current user can not create an item with the category forced "
    "thru the configuration! Please contact system administrator!"
)
SEND_WITHOUT_SUFFICIENT_FIELD_MAPPINGS_DEFINED_WARNING = _(
    u"No sufficient field mappings are defined in the "
    "configuration. It is recommended to define at least the "
    "'title' mapping, but 'description' and 'decision' should "
    "also be defined. It will ne be possible to create the "
    "item in PloneMeeting."
)
ANNEXID_MANDATORY_ERROR = _(u"An annex id is mandatory to download an annex!")
MISSING_FILE_ERROR = _(u"The requested file could not be found on the item")

# annotations key
WS4PMCLIENT_ANNOTATION_KEY = "imio.pm.wsclient-sent_to"
