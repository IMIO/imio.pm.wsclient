# -*- coding: utf-8 -*-

from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield.registry import DictRow
from datetime import datetime
from functools import wraps
from imio.pm.wsclient import WS4PMClientMessageFactory as _
from imio.pm.wsclient.config import ACTION_SUFFIX
from imio.pm.wsclient.config import CONFIG_CREATE_ITEM_PM_ERROR
from imio.pm.wsclient.config import CONFIG_UNABLE_TO_CONNECT_ERROR
from imio.pm.wsclient.config import UNABLE_TO_CONNECT_ERROR
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.memoize.view import memoize
from plone.registry.interfaces import IRecordModifiedEvent
from plone.registry.interfaces import IRegistry
from Products.CMFCore.ActionInformation import Action
from Products.CMFPlone.utils import base_hasattr
from Products.statusmessages.interfaces import IStatusMessage
from z3c.form import button
from z3c.form import field
from zope import schema
from zope.component import getMultiAdapter
from zope.component import queryUtility
from zope.component.hooks import getSite
from zope.i18n import translate
from zope.interface import Interface
from zope.schema.interfaces import IVocabularyFactory

import logging
import requests
import six


logger = logging.getLogger('imio.pm.wsclient')


class IGeneratedActionsSchema(Interface):
    """Schema used for the datagrid field 'generated_actions' of IWS4PMClientSettings."""
    condition = schema.TextLine(
        title=_("TAL Condition"),
        required=False, )
    permissions = schema.Choice(
        title=_("Permissions"),
        required=False,
        vocabulary=u'imio.pm.wsclient.possible_permissions_vocabulary')
    pm_meeting_config_id = schema.Choice(
        title=_("PloneMeeting meetingConfig id"),
        required=True,
        vocabulary=u'imio.pm.wsclient.pm_meeting_config_id_vocabulary')


class IFieldMappingsSchema(Interface):
    """Schema used for the datagrid field 'field_mappings' of IWS4PMClientSettings."""
    field_name = schema.Choice(
        title=_("PloneMeeting field name"),
        required=True,
        vocabulary=u'imio.pm.wsclient.pm_item_data_vocabulary')
    expression = schema.TextLine(
        title=_("TAL expression to evaluate for the corresponding PloneMeeting field name"),
        required=True, )


class IAllowedAnnexTypesSchema(Interface):
    """Schema used for the datagrid field 'allowed_annex_type' of IWS4PMClientSettings."""
    annex_type = schema.TextLine(
        title=_("Annex type"),
        required=True)


class IUserMappingsSchema(Interface):
    """Schema used for the datagrid field 'user_mappings' of IWS4PMClientSettings."""
    local_userid = schema.TextLine(
        title=_("Local user id"),
        required=True)
    pm_userid = schema.TextLine(
        title=_("PloneMeeting corresponding user id"),
        required=True, )


class IWS4PMClientSettings(Interface):
    """
    Configuration of the WS4PM Client
    """
    pm_url = schema.TextLine(
        title=_(u"PloneMeeting URL"),
        required=True, )
    pm_timeout = schema.Int(
        title=_(u"PloneMeeting connection timeout"),
        description=_(u"Enter the timeout while connecting to PloneMeeting. Do not set a too high timeout because it "
                      "will impact the load of the viewlet showing PM infos on a sent element if PM is not available. "
                      "Default is '10' seconds."),
        default=10,
        required=True, )
    pm_username = schema.TextLine(
        title=_("PloneMeeting username to use"),
        description=_(u"The user must be at least a 'MeetingManager'. Nevertheless, items will be created regarding "
                      "the <i>User ids mappings</i> defined here under."),
        required=True, )
    pm_password = schema.Password(
        title=_("PloneMeeting password to use"),
        required=False, )
    only_one_sending = schema.Bool(
        title=_("An element can be sent one time only"),
        default=True,
        required=True, )
    viewlet_display_condition = schema.TextLine(
        title=_("Viewlet display condition"),
        description=_("Enter a TAL expression that will be evaluated to check if the viewlet displaying "
                      "informations about the created items in PloneMeeting should be displayed. "
                      "If empty, the viewlet will only be displayed if an item is actually linked to it. "
                      "The 'isLinked' variable representing this default behaviour is available "
                      "in the TAL expression."),
        required=False, )
    field_mappings = schema.List(
        title=_("Field accessor mappings"),
        description=_("For every available data you can send, define in the mapping a TAL expression that will be "
                      "executed to obtain the correct value to send. The 'meetingConfigId' and 'proposingGroupId' "
                      "variables are also available for the expression. Special case for the 'proposingGroup' and "
                      "'category' fields, you can 'force' the use of a particular value by defining it here. If not "
                      "defined the user will be able to use every 'proposingGroup' or 'category' he is allowed to "
                      "use in PloneMeeting."),
        value_type=DictRow(title=_("Field mappings"),
                           schema=IFieldMappingsSchema,
                           required=False),
        required=False, )
    allowed_annexes_types = schema.List(
        title=_("Allowed annexes types"),
        description=_("List here the annexes types allowed to be display in the linked meeting item viewlet"),
        value_type=DictRow(title=_("Allowed annex type"),
                           schema=IAllowedAnnexTypesSchema,
                           required=False),
        default=[],
        required=False, )
    user_mappings = schema.List(
        title=_("User ids mappings"),
        description=_("By default, while sending an element to PloneMeeting, the user id of the logged in user "
                      "is used and a binding is made to the same user id in PloneMeeting. "
                      "If the local user id does not exist in PloneMeeting, you can define here the user mappings "
                      "to use. For example : 'jdoe' in 'Local user id' of the current application correspond to "
                      "'johndoe' in PloneMeeting."),
        value_type=DictRow(title=_("User mappings"),
                           schema=IUserMappingsSchema,
                           required=False),
        required=False, )
    generated_actions = schema.List(
        title=_("Generated actions"),
        description=_("Actions to send an item to PloneMeeting can be generated. First enter a 'TAL condition' "
                      "evaluated to show the action then choose permission(s) the user must have to see the action. "
                      "Finally, choose the meetingConfig the item will be sent to."),
        value_type=DictRow(title=_("Actions"),
                           schema=IGeneratedActionsSchema,
                           required=False),
        required=False, )
    select_all_attachments_by_default = schema.Bool(
        title=_("Select all attachments by default"),
        description=_("When enabled, all attachments are selected by default. "
                      "Users can still manually deselect individual attachments if needed."),
        default=True,
        required=False, )


class WS4PMClientSettingsEditForm(RegistryEditForm):
    """
    Define form logic
    """
    schema = IWS4PMClientSettings
    label = _(u"WS4PM Client settings")
    description = _(u"""""")

    fields = field.Fields(IWS4PMClientSettings)
    fields['generated_actions'].widgetFactory = DataGridFieldFactory
    fields['field_mappings'].widgetFactory = DataGridFieldFactory
    fields['allowed_annexes_types'].widgetFactory = DataGridFieldFactory
    fields['user_mappings'].widgetFactory = DataGridFieldFactory

    def updateFields(self):
        super(WS4PMClientSettingsEditForm, self).updateFields()
        portal = getSite()
        # this is also called by the kss inline_validation, avoid too much work...
        if not portal.__module__ == 'Products.CMFPlone.Portal':
            return
        ctrl = getMultiAdapter((portal, portal.REQUEST), name='ws4pmclient-settings')
        # if we can not getConfigInfos from the given pm_url, we do not permit to edit other parameters
        generated_actions_field = self.fields.get('generated_actions')
        field_mappings = self.fields.get('field_mappings')
        if not ctrl._rest_getConfigInfos():
            generated_actions_field.mode = 'display'
            field_mappings.mode = 'display'
        else:
            if generated_actions_field.mode == 'display' and \
                    'form.buttons.save' not in self.request.form.keys():
                # only change mode while not in the "saving" process (that calls updateFields, but why?)
                # because it leads to loosing generated_actions because a [] is returned by extractDate here above
                self.fields.get('generated_actions').mode = 'input'
                self.fields.get('field_mappings').mode = 'input'

    def updateWidgets(self):
        super(WS4PMClientSettingsEditForm, self).updateWidgets()

    @button.buttonAndHandler(_('Save'), name=None)
    def handleSave(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        self.applyChanges(data)
        IStatusMessage(self.request).addStatusMessage(_(u"Changes saved"),
                                                      "info")
        portal = getSite()
        ctrl = getMultiAdapter((portal, portal.REQUEST), name='ws4pmclient-settings')
        ctrl._rest_checkConnection()
        self.context.REQUEST.RESPONSE.redirect("@@ws4pmclient-settings")

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        IStatusMessage(self.request).addStatusMessage(_(u"Edit cancelled"),
                                                      "info")
        self.request.response.redirect("%s/%s" % (self.context.absolute_url(),
                                                  self.control_panel_view))


def with_pm_session(empty_return=None):
    """Decorator that injects an authenticated PM session as the first argument.

    Handles the session-is-None guard and wraps the call in a try/except so
    network errors are surfaced via _handle_rest_error rather than propagating.
    Stack with @memoize as the OUTER decorator so the final result is cached.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            session = self._rest_connectToPloneMeeting()
            if session is None:
                return empty_return
            try:
                return func(self, session, *args, **kwargs)
            except requests.RequestException as e:
                logger.exception("Error during PloneMeeting REST call in %s", func.__name__)
                self._handle_rest_error(e)
                return empty_return
        return wrapper
    return decorator


class WS4PMClientSettings(ControlPanelFormWrapper):
    form = WS4PMClientSettingsEditForm

    @memoize
    def settings(self):
        """ """
        registry = queryUtility(IRegistry)
        settings = registry.forInterface(IWS4PMClientSettings, check=False)
        return settings

    @property
    def url(self):
        """Return PloneMeeting App URL"""
        settings = self.settings()
        return self.request.form.get('form.widgets.pm_url') or settings.pm_url or ''

    @property
    def username(self):
        """Return username used for REST calls"""
        settings = self.settings()
        return self.request.form.get('form.widgets.pm_username') or settings.pm_username or ''

    @property
    def timeout(self):
        """Return connection timeout in seconds for REST calls"""
        settings = self.settings()
        raw = self.request.form.get('form.widgets.pm_timeout')
        try:
            return int(raw)
        except (TypeError, ValueError):
            return settings.pm_timeout

    def is_configured(self):
        """Check if the WS4PM Client is activated by checking if the connection fields are filled in."""
        settings = self.settings()
        return bool(settings.pm_url and settings.pm_username and settings.pm_password)

    @memoize
    def _rest_connectToPloneMeeting(self):
        """Return an authenticated requests.Session for PloneMeeting REST calls.
        Returns None if connection settings are not configured.
        """
        if not self.is_configured():
            return None
        settings = self.settings()
        password = self.request.form.get('form.widgets.pm_password') or settings.pm_password
        session = requests.Session()
        session.auth = (self.username, password)
        session.headers.update({'Accept': 'application/json', 'Content-Type': 'application/json'})
        return session

    def _rest_checkConnection(self):
        """Probe PloneMeeting to validate credentials."""
        session = self._rest_connectToPloneMeeting()
        if session is None:
            return
        url = "{0}/@users/{1}".format(self.url, self.username)
        try:
            response = session.get(url, timeout=self.timeout)
        except requests.RequestException as exc:
            self._handle_rest_error(exc)
            return
        if response.status_code != 200:
            error_body = response.json() if response.content else {}
            msg = (error_body.get('message') or
                   error_body.get('error', {}).get('message') or
                   "HTTP {0}".format(response.status_code))
            self._handle_rest_error(requests.ConnectionError(msg))

    def _handle_rest_error(self, exc):
        """Show a connection error status message when on the settings panel or not."""
        if self.request.get('URL', '').endswith('@@ws4pmclient-settings'):
            msg = getattr(exc, 'message', None) or getattr(exc, 'reason', None) or str(exc)
            IStatusMessage(self.request).addStatusMessage(
                _(CONFIG_UNABLE_TO_CONNECT_ERROR, mapping={'error': msg}), "error")
        else:
            IStatusMessage(self.request).addStatusMessage(_(UNABLE_TO_CONNECT_ERROR), "error")

    def _format_rest_query_url(self, endpoint, **kwargs):
        """Return a rest query URL formatted for the given endpoint and arguments"""
        arguments = []
        for k, v in kwargs.items():
            if isinstance(v, six.string_types) and "," in v:
                for v in v.split(","):
                    arguments.append("{0}={1}".format(k, v))
            else:
                if v:
                    arguments.append("{0}={1}".format(k, v))
                elif k in ("fullobjects",):
                    arguments.append(k)
        if arguments:
            return "{url}/{endpoint}?{arguments}".format(
                url=self.url,
                endpoint=endpoint,
                arguments="&".join(arguments),
            )
        return "{url}/{endpoint}".format(url=self.url, endpoint=endpoint)

    @with_pm_session(empty_return=None)
    def _rest_checkIsLinked(self, session, data):
        """Query the checkIsLinked REST server method."""
        if 'inTheNameOf' not in data:
            data["inTheNameOf"] = self._getUserIdToUseInTheNameOfWith()
        url = self._format_rest_query_url(
            "@get",
            # extra_include="linked_items",  # why this ?
            **data
        )
        response = session.get(url)
        # first 2 tests for plonemeeting.restapi 2.12+
        if response.status_code == 403:
            # forbidden item
            return True
        elif response.status_code == 404:
            # item not found
            return False
        elif response.status_code != 200:
            return False
        elif response.json().get("items_total") == 0:
            return False
        return response.json()

    @memoize
    @with_pm_session(empty_return=None)
    def _rest_getConfigInfos(self, session, showCategories=False):
        """Query the getConfigInfos REST server method."""
        # XXX to reimplements once @configs endpoint is implemented in plonemeeting.restapi
        config_url = "{}/@users/{}?extra_include=configs".format(self.url, self.username)
        user_infos = session.get(config_url, timeout=self.timeout)
        if user_infos.status_code != 200:
            return None
        configs_info = user_infos.json()['extra_include_configs']
        if showCategories:
            config_url = '{}&extra_include=categories'.format(config_url)
            for config_info in configs_info:
                config_url = '{}&extra_include_categories_configs={}'.format(
                    config_url,
                    config_info['id']
                )
            user_infos = session.get(config_url, timeout=self.timeout)
            content = user_infos.json()
            configs_info = content['extra_include_configs']
            for config_info in configs_info:
                config_info['categories'] = content['extra_include_categories'][config_info['id']]
        return configs_info

    @memoize
    @with_pm_session(empty_return=None)
    def _rest_getUserInfos(self, session, showGroups=False, suffix=''):
        """Query the getUserInfos REST server method."""
        # get the inTheNameOf userid if it was not already set
        userId = self._getUserIdToUseInTheNameOfWith(mandatory=True)
        parameters = {}
        if showGroups is True:
            parameters["extra_include"] = "groups"
            if suffix:
                parameters["extra_include_groups_suffixes"] = suffix
        url = self._format_rest_query_url(
            "@users/{0}".format(userId),
            **parameters
        )
        response = session.get(url, timeout=self.timeout)
        if response.status_code == 200:
            return response.json()
        return None

    @with_pm_session(empty_return=[])
    def _rest_searchItems(self, session, data):
        """Query the searchItems REST server method."""
        # get the inTheNameOf userid if it was not already set
        if 'inTheNameOf' not in data:
            data["inTheNameOf"] = self._getUserIdToUseInTheNameOfWith()
        if "type" not in data:
            # we want item by default
            data["type"] = "item"
        url = self._format_rest_query_url(
            "@search",
            in_name_of=data["inTheNameOf"],
            **{k: v for k, v in data.items() if k != "inTheNameOf"}
        )
        response = session.get(url, timeout=self.timeout)
        if response.status_code == 200:
            return response.json().get("items", [])
        return []

    @with_pm_session(empty_return=[])
    def _rest_getItemInfos(self, session, data):
        """Query the getItemInfos REST server method."""
        # get the inTheNameOf userid if it was not already set
        if 'inTheNameOf' not in data:
            data["inTheNameOf"] = self._getUserIdToUseInTheNameOfWith()
        url = self._format_rest_query_url(
            "@get",
            uid=data["UID"],
            in_name_of=data["inTheNameOf"],
            **{k: v for k, v in data.items() if k not in ("UID", "inTheNameOf")}
        )
        response = session.get(url, timeout=self.timeout)
        if response.status_code == 200:
            # Expect a list even for a single result
            return [response.json()]
        return []

    @with_pm_session(empty_return=None)
    def _rest_getAnnex(self, session, url):
        """Return an annex based on his download url. !!! WARNING !!! this must only
        used inside code that validate before that the user can access the annex"""
        response = session.get(url, timeout=self.timeout)
        if response.status_code == 200:
            return response.content

    @with_pm_session(empty_return=[])
    def _rest_getMeetingsAcceptingItems(self, session, data):
        """Query the getMeetingsAcceptingItems REST server method."""
        if 'inTheNameOf' not in data:
            data["inTheNameOf"] = self._getUserIdToUseInTheNameOfWith()
        url = self._format_rest_query_url(
            "@search",
            config_id=data["meetingConfigId"],
            in_name_of=data["inTheNameOf"],
            type="meeting",
            meetings_accepting_items="true",
            additional_values="formatted_date",
            # fullobjects=1,
        )
        response = session.get(url)
        if response.status_code == 200:
            return response.json()["items"]
        return []

    def _rest_getDecidedMeetingDate(self,
                                    data,
                                    item_portal_type,
                                    decided_states=('accepted', 'accepted_but_modified', 'accepted_and_returned')):
        """
        Get the actual decided meeting date. It handles delayed and sentTo items appropriately.
        Use item_portal_type parameter to get the decided meeting date for this portal_type.
        It returns a datetime object if a meeting has been found, or None otherwise.
        TODO: handle decided_states correctly, fetching decided states from PloneMeeting configuration
        """
        query = {
            'extra_include': 'meeting,linked_items',
            'extra_include_linked_items_mode': 'every_successors',
            'extra_include_linked_items_extra_include': 'meeting',
        }
        query.update(data)
        items = self._rest_searchItems(query)
        if not items:
            return  # Item has been deleted or has not been sent to PloneMeeting
        item = items[0]
        if item_portal_type == item["@type"] and item['review_state'] in decided_states:
            return datetime.strptime(item['extra_include_meeting']['date'], "%Y-%m-%dT%H:%M:%S")
        elif item['extra_include_linked_items']:
            for linked_item in item['extra_include_linked_items']:
                if item_portal_type == linked_item["@type"] and linked_item['review_state'] in decided_states:
                    return datetime.strptime(linked_item['extra_include_meeting']['date'], "%Y-%m-%dT%H:%M:%S")

    @with_pm_session(empty_return=None)
    def _rest_getItemTemplate(self, session, data):
        """Query the getItemTemplate REST server method."""
        if 'inTheNameOf' not in data:
            data["inTheNameOf"] = self._getUserIdToUseInTheNameOfWith()
        try:
            if not data["itemUID"]:
                raise ValueError(
                    "Server raised fault: 'You can not access this item!'"
                )
            url = self._format_rest_query_url(
                "@get",
                uid=data["itemUID"],
                in_name_of=data["inTheNameOf"],
                extra_include="pod_templates",
            )
            response = session.get(url, timeout=self.timeout)
            if not data["templateId"]:
                raise ValueError(
                    "Server raised fault: 'You can not access this template!'"
                )
            template_id, output_format = data["templateId"].split("__format__")
            # Iterate over possible templates to find the right one
            template = [t for t in response.json()["extra_include_pod_templates"]
                        if t["id"] == template_id]
            if not template:
                raise ValueError("Unkown template id '{0}'".format(template_id))
            # Iterate over possible output format to find the expected one
            output = [o for o in template[0]["outputs"]
                      if o["format"] == output_format]
            if not output:
                raise ValueError(
                    "Unknown output format '{0}' for template id '{1}'".format(
                        output_format, template_id
                    )
                )
            response = session.get(output[0]["url"], timeout=self.timeout)
            if response.status_code == 200:
                return response
        except Exception as exc:
            logger.exception("Error generating PloneMeeting document: %s", exc)
            IStatusMessage(self.request).addStatusMessage(
                _(u"An error occured while generating the document in PloneMeeting! "
                  "The error message was : %s" % exc), "error")

    @memoize
    @with_pm_session(empty_return=[])
    def _rest_getItemCreationAvailableData(self, session):
        """Query REST to obtain the list of available fields useable while creating an item."""
        available_data = [
            u"annexes",
            u"associatedGroups",
            u"category",
            u"decision",
            u"externalIdentifier",
            u"extraAttrs",
            u"groupsInCharge",
            u"ignore_validation_for",
            u"ignore_not_used_data",
            u"motivation",
            u"optionalAdvisers",
            u"preferredMeeting",
            u"proposingGroup",
            u"title",
        ]
        ignored_data = [
            u"itemIsSigned",
            u"itemTags",
        ]
        configs_url = "{0}/@users/{1}?extra_include=configs".format(self.url, self.username)
        configs = session.get(configs_url, timeout=self.timeout)
        if configs.status_code != 200:
            return []
        for config in configs.json()["extra_include_configs"]:
            url = self._format_rest_query_url(
                "@config",
                config_id=config["id"],
                metadata_fields="usedItemAttributes",
            )
            response = session.get(url, timeout=self.timeout)
            if response.status_code != 200:
                continue
            attributes = response.json()["usedItemAttributes"]
            map(
                available_data.append,
                [k["token"] for k in attributes
                 if k["token"] not in available_data
                 and k["token"] not in ignored_data],
            )
        return sorted(available_data)

    @with_pm_session(empty_return=None)
    def _rest_createItem(self, session, meetingConfigId, proposingGroupId, creationData):
        """Query the createItem REST server method."""
        try:
            # we create an item inTheNameOf the currently connected member
            # _getUserIdToCreateWith returns None if the settings defined username creates the item
            inTheNameOf = self._getUserIdToUseInTheNameOfWith()
            data = {
                "config_id": meetingConfigId,
                "proposingGroup": proposingGroupId,
                "in_name_of": inTheNameOf,
            }
            # For backward compatibility
            if "ignore_validation_for" in creationData:
                ignored = creationData.pop("ignore_validation_for")
                creationData["ignore_validation_for"] = ignored.split(",")
            if "extraAttrs" in creationData:
                extra_attrs = creationData.pop("extraAttrs")
                for value in extra_attrs:
                    creationData[value["key"]] = value["value"]
            data.update(creationData)
            response = session.post("{0}/@item".format(self.url), json=data, timeout=self.timeout)
            if response.status_code != 201:
                if response.content:
                    error = response.json()["message"]
                else:
                    error = "Unexcepted response ({0})".format(response.status_code)
                IStatusMessage(self.request).addStatusMessage(
                    _(CONFIG_CREATE_ITEM_PM_ERROR, mapping={"error": error})
                )
                return
            # return 'UID' and 'warnings' if any current user is a Manager
            warnings = []
            response_json = response.json()
            if self.context.portal_membership.getAuthenticatedMember().has_role('Manager'):
                warnings = response_json.get('warnings', [])
            return response_json['UID'], warnings
        except Exception as exc:
            logger.exception("Error creating item in PloneMeeting: %s", exc)
            IStatusMessage(self.request).addStatusMessage(
                _(CONFIG_CREATE_ITEM_PM_ERROR, mapping={'error': getattr(exc, 'message', None) or str(exc)}), "error"
            )

    def _getUserIdToUseInTheNameOfWith(self, mandatory=False):
        """
          Returns the userId that will actually create the item.
          Returns None if we found out that it is the defined settings.pm_username
          that will create the item : either it is the currently connected user,
          or there is an existing user_mapping between currently connected user
          and settings.pm_username user.
          If p_mandatory is True, returns mndatorily a userId.
        """
        member = self.context.portal_membership.getAuthenticatedMember()
        memberId = member.getId()
        # get username specified to connect to the REST distant site
        settings = self.settings()
        restUsername = settings.pm_username and settings.pm_username.strip()
        # if current user is the user defined in the settings, return None
        if memberId == restUsername:
            if mandatory:
                return restUsername
            else:
                return None
        # check if a user_mapping exists
        if settings.user_mappings:
            for user_mapping in settings.user_mappings:
                localUserId, distantUserId = user_mapping['local_userid'], user_mapping['pm_userid']
                # if we found a mapping for the current user, check also
                # that the distantUserId the mapping is linking to, is not the restUsername
                if memberId == localUserId.strip():
                    if not restUsername == distantUserId.strip():
                        return distantUserId.strip()
                    else:
                        if mandatory:
                            return restUsername
                        else:
                            return None
        return memberId

    def checkAlreadySentToPloneMeeting(self, context, meetingConfigId=None):
        """
          Check if the element has already been sent to PloneMeeting to avoid double sents
          If an item needs to be doubled in PloneMeeting, it is PloneMeeting's duty
          The script will return :
          - 'None' if could not connect to PloneMeeting
          - True if the p_context is linked to an item of p_meetingConfigId
          - False if p_context is not linked to an item of p_meetingConfigId
        """
        isLinked = False
        if not base_hasattr(context, "UID"):  # for plone site
            return False
        data = {"externalIdentifier": context.UID()}
        if meetingConfigId:
            data["config_id"] = meetingConfigId
        res = self._rest_checkIsLinked(data)
        # if res is None, it means that it could not connect to PloneMeeting
        if res is None:
            return None
        # we found at least one linked item
        elif res:
            isLinked = True
        return isLinked

    def getMeetingConfigTitle(self, meetingConfigId):
        """
          Return the title of the given p_meetingConfigId
          Use the vocabulary u'imio.pm.wsclient.pm_meeting_config_id_vocabulary'
        """
        # get the pm_meeting_config_id_vocabulary so we will be able to displayValue
        factory = queryUtility(IVocabularyFactory, u'imio.pm.wsclient.pm_meeting_config_id_vocabulary')
        # self.context is portal
        meetingConfigVocab = factory(self.context)
        try:
            return meetingConfigVocab.getTerm(meetingConfigId).title
        except LookupError:
            return ''


def notify_configuration_changed(event):
    """Event subscriber that is called every time the configuration changed."""
    portal = getSite()

    if IRecordModifiedEvent.providedBy(event):
        # generated_actions changed, we need to update generated actions in portal_actions
        if event.record.fieldName == 'generated_actions':
            # if generated_actions have been changed, remove every existing generated_actions then recreate them
            # first remove every actions starting with ACTION_SUFFIX
            object_buttons = portal.portal_actions.object_buttons
            for object_button in object_buttons.objectValues():
                if object_button.id.startswith(ACTION_SUFFIX):
                    object_buttons.manage_delObjects([object_button.id])
            # then recreate them
            i = 1
            ws4pmSettings = getMultiAdapter((portal, portal.REQUEST), name='ws4pmclient-settings')
            for actToGen in event.record.value:
                actionId = "%s%d" % (ACTION_SUFFIX, i)
                action = Action(
                    actionId,
                    title=translate(
                        'Send to ${meetingConfigTitle}',
                        domain='imio.pm.wsclient',
                        mapping={
                            'meetingConfigTitle':
                                ws4pmSettings.getMeetingConfigTitle(actToGen['pm_meeting_config_id']),
                        },
                        context=portal.REQUEST),
                    description='', i18n_domain='imio.pm.wsclient',
                    url_expr='string:${object_url}/@@send_to_plonemeeting_form?meetingConfigId=%s'
                             % actToGen['pm_meeting_config_id'],
                    icon_expr='string:${portal_url}/++resource++imio.pm.wsclient.images/send_to_plonemeeting.png',
                    available_expr=actToGen['condition'] or '',
                    # make sure we have a tuple as permissions value
                    permissions=actToGen['permissions'] and (actToGen['permissions'],) or ('View',),
                    visible=True)
                object_buttons._setObject(actionId, action)
                i = i + 1
