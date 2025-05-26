# -*- coding: utf-8 -*-

from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield.registry import DictRow
from datetime import datetime
from imio.pm.wsclient import WS4PMClientMessageFactory as _
from imio.pm.wsclient.config import ACTION_SUFFIX
from imio.pm.wsclient.config import CONFIG_CREATE_ITEM_PM_ERROR
from imio.pm.wsclient.config import CONFIG_UNABLE_TO_CONNECT_ERROR
from imio.pm.wsclient.config import WS4PMCLIENT_ANNOTATION_KEY
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.memoize.view import memoize
from plone.registry.interfaces import IRecordModifiedEvent
from plone.registry.interfaces import IRegistry
from Products.CMFCore.ActionInformation import Action
from Products.CMFCore.Expression import createExprContext
from Products.CMFCore.Expression import Expression
from Products.statusmessages.interfaces import IStatusMessage
from StringIO import StringIO
from z3c.form import button
from z3c.form import field
from zope import schema
from zope.annotation import IAnnotations
from zope.component import getMultiAdapter
from zope.component import queryUtility
from zope.component.hooks import getSite
from zope.i18n import translate
from zope.interface import Interface
from zope.schema.interfaces import IVocabularyFactory

import json
import requests
import six


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
        required=True, )
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
        self.context.REQUEST.RESPONSE.redirect("@@ws4pmclient-settings")

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        IStatusMessage(self.request).addStatusMessage(_(u"Edit cancelled"),
                                                      "info")
        self.request.response.redirect("%s/%s" % (self.context.absolute_url(),
                                                  self.control_panel_view))


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

    @memoize
    def _rest_connectToPloneMeeting(self):
        """
          Connect to distant PloneMeeting.
          Either return None or the session
        """
        settings = self.settings()
        password = self.request.form.get('form.widgets.pm_password') or settings.pm_password or ''
        timeout = self.request.form.get('form.widgets.pm_timeout') or settings.pm_timeout or ''
        try:
            infos_url = "{}/@infos".format(self.url)
            session = requests.Session()
            session.auth = (self.username, password)
            session.headers.update({'Accept': 'application/json', 'Content-Type': 'application/json'})
            login = session.get(infos_url, timeout=int(timeout))
            if login.status_code != 200:
                response = json.load(StringIO(login.content))
                raise ConnectionError(response['error']['message'])
        except Exception as e:
            # if we are really on the configuration panel, display relevant message
            if self.request.get('URL', '').endswith('@@ws4pmclient-settings'):
                IStatusMessage(self.request).addStatusMessage(
                    _(CONFIG_UNABLE_TO_CONNECT_ERROR, mapping={'error': (e.message or str(e.reason))}), "error")
            return None
        return session

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

    def _rest_checkIsLinked(self, data):
        """Query the checkIsLinked REST server method."""
        session = self._rest_connectToPloneMeeting()
        if session is not None:
            if 'inTheNameOf' not in data:
                data["inTheNameOf"] = self._getUserIdToUseInTheNameOfWith()
            url = self._format_rest_query_url(
                "@get",
                extra_include="linked_items",
                **{k: v for k, v in data.items() if k != "inTheNameOf"}
            )
            response = session.get(url)
            if response.status_code != 200:
                return False
            if response.json().get("items_total") == 0:
                # When there is no item found, we still get a response but items_total is 0
                return False
            return response.json()

    @memoize
    def _rest_getConfigInfos(self, showCategories=False):
        """Query the getConfigInfos REST server method."""
        session = self._rest_connectToPloneMeeting()
        if session is not None:
            # XXX to reimplements once @configs endpoint is implemented in plonemeeting.restapi
            config_url = "{}/@users/{}?extra_include=configs".format(self.url, session.auth[0])
            user_infos = session.get(config_url)
            if user_infos.status_code == 200:
                configs_info = user_infos.json()['extra_include_configs']
                if showCategories:
                    config_url = '{}&extra_include=categories'.format(config_url)
                    for config_info in configs_info:
                        config_url = '{}&extra_include_categories_configs={}'.format(
                            config_url,
                            config_info['id']
                        )
                    user_infos = session.get(config_url)
                    content = user_infos.json()
                    configs_info = content['extra_include_configs']
                    for config_info in configs_info:
                        config_info['categories'] = content['extra_include_categories'][config_info['id']]
            return configs_info

    @memoize
    def _rest_getUserInfos(self, showGroups=False, suffix=''):
        """Query the getUserInfos REST server method."""
        session = self._rest_connectToPloneMeeting()
        if session is not None:
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
            response = session.get(url)
            if response.status_code == 200:
                return response.json()

    def _rest_searchItems(self, data):
        """Query the searchItems REST server method."""
        session = self._rest_connectToPloneMeeting()
        if session is not None:
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
            response = session.get(url)
            if response.status_code == 200:
                return response.json().get("items", [])
            return []

    def _rest_getItemInfos(self, data):
        """Query the getItemInfos REST server method."""
        session = self._rest_connectToPloneMeeting()
        if session is not None:
            # get the inTheNameOf userid if it was not already set
            if 'inTheNameOf' not in data:
                data["inTheNameOf"] = self._getUserIdToUseInTheNameOfWith()
            url = self._format_rest_query_url(
                "@get",
                uid=data["UID"],
                in_name_of=data["inTheNameOf"],
                **{k: v for k, v in data.items() if k not in ("UID", "inTheNameOf")}
            )
            response = session.get(url)
            if response.status_code == 200:
                # Expect a list even for a single result
                return [response.json()]
            return []

    def _rest_getAnnex(self, url):
        """Return an annex based on his download url. !!! WARNING !!! this must only
        used inside code that validate before that the user can access the annex"""
        session = self._rest_connectToPloneMeeting()
        if session is not None:
            response = session.get(url)
            if response.status_code == 200:
                return response.content
        return ''

    def _rest_getMeetingsAcceptingItems(self, data):
        """Query the getItemInfos REST server method."""
        session = self._rest_connectToPloneMeeting()
        if session is not None:
            if 'inTheNameOf' not in data:
                data["inTheNameOf"] = self._getUserIdToUseInTheNameOfWith()
            url = self._format_rest_query_url(
                "@search",
                config_id=data["meetingConfigId"],
                in_name_of=data["inTheNameOf"],
                type="meeting",
                meetings_accepting_items="true",
                fullobjects=1,
            )
            response = session.get(url)
            if response.status_code == 200:
                return response.json()["items"]

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

    def _rest_getItemTemplate(self, data):
        """Query the getItemTemplate REST server method."""
        session = self._rest_connectToPloneMeeting()
        if session is not None:
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
                response = session.get(url)
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
                response = session.get(output[0]["url"])
                if response.status_code == 200:
                    return response
            except Exception as exc:
                IStatusMessage(self.request).addStatusMessage(
                    _(u"An error occured while generating the document in PloneMeeting! "
                      "The error message was : %s" % exc), "error")

    @memoize
    def _rest_getItemCreationAvailableData(self):
        """Query REST to obtain the list of available fields useable while creating an item."""
        session = self._rest_connectToPloneMeeting()
        if session is not None:
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
            configs_url = "{0}/@users/{1}?extra_include=configs".format(
                self.url,
                self.username,
            )
            configs = session.get(configs_url)
            for config in configs.json()["extra_include_configs"]:
                url = self._format_rest_query_url(
                    "@config",
                    config_id=config["id"],
                    metadata_fields="usedItemAttributes",
                )
                response = session.get(url)
                attributes = response.json()["usedItemAttributes"]
                map(
                    available_data.append,
                    [k["token"] for k in attributes
                     if k["token"] not in available_data
                     and k["token"] not in ignored_data],
                )
            return sorted(available_data)

    def _rest_createItem(self, meetingConfigId, proposingGroupId, creationData):
        """Query the createItem REST server method."""
        session = self._rest_connectToPloneMeeting()
        if session is not None:
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
                response = session.post("{0}/@item".format(self.url), json=data)
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
                    warnings = 'warnings' in response_json and response_json['warnings'] or []
                return response_json['UID'], warnings
            except Exception as exc:
                IStatusMessage(self.request).addStatusMessage(
                    _(CONFIG_CREATE_ITEM_PM_ERROR, mapping={'error': exc}), "error"
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

    def checkAlreadySentToPloneMeeting(self, context, meetingConfigIds=[]):
        """
          Check if the element has already been sent to PloneMeeting to avoid double sents
          If an item needs to be doubled in PloneMeeting, it is PloneMeeting's duty
          If p_meetingConfigIds is empty (), then it checks every available meetingConfigId it was sent to...
          The script will return :
          - 'None' if could not connect to PloneMeeting
          - True if the p_context is linked to an item of p_meetingConfigIds
          - False if p_context is not linked to an item of p_meetingConfigIds
          This script also wipe out every meetingConfigIds for wich the item does not exist anymore in PloneMeeting
        """
        annotations = IAnnotations(context)
        # for performance reason (avoid to connect to REST if no annotations)
        # if there are no relevant annotations, it means that the p_context
        # is not linked and we return False
        isLinked = False
        if WS4PMCLIENT_ANNOTATION_KEY in annotations:
            # the item seems to have been sent, but double check in case it was
            # deleted in PloneMeeting after having been sent
            # warning, here searchItems inTheNameOf the super user to be sure
            # that we can access it in PloneMeeting
            if not meetingConfigIds:
                # evaluate the meetingConfigIds in the annotation
                # this will wipe out the entire annotation
                meetingConfigIds = list(annotations[WS4PMCLIENT_ANNOTATION_KEY])
            for meetingConfigId in meetingConfigIds:
                res = self._rest_checkIsLinked({'externalIdentifier': context.UID(),
                                                'config_id': meetingConfigId, })
                # if res is None, it means that it could not connect to PloneMeeting
                if res is None:
                    return None
                # we found at least one linked item
                elif res:
                    isLinked = True
                # could connect to PM but did not find a result
                elif not res:
                    # either the item was deleted in PloneMeeting
                    # or it was never send, wipe out if it was deleted in PloneMeeting
                    if meetingConfigId in annotations[WS4PMCLIENT_ANNOTATION_KEY]:
                        # do not use .remove directly on the annotations or it does not save
                        # correctly and when Zope restarts, the removed annotation is still there???
                        existingAnnotations = list(annotations[WS4PMCLIENT_ANNOTATION_KEY])
                        existingAnnotations.remove(meetingConfigId)
                        annotations[WS4PMCLIENT_ANNOTATION_KEY] = existingAnnotations
                    if not annotations[WS4PMCLIENT_ANNOTATION_KEY]:
                        # remove the entire annotation key if empty
                        del annotations[WS4PMCLIENT_ANNOTATION_KEY]
        return isLinked

    def renderTALExpression(self, context, portal, expression, vars={}):
        """
          Renders given TAL expression in p_expression.
          p_vars contains extra variables that will be done available in the TAL expression to render
        """
        res = ''
        if expression:
            expression = expression.strip()
            ctx = createExprContext(context.aq_inner.aq_parent, portal, context)
            vars['context'] = context
            ctx.vars.update(vars)
            for k, v in vars.items():
                ctx.setContext(k, v)
            res = Expression(expression)(ctx)
        # make sure we do not return None because it breaks REST call
        if res is None:
            return u''
        else:
            return res

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
                        'Send to',
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
