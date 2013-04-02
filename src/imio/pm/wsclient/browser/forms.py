import logging
logger = logging.getLogger('imio.pm.wsclient')
from collections import OrderedDict

from AccessControl import Unauthorized

from zope.annotation import IAnnotations
from zope.component.hooks import getSite
from zope.component import queryUtility, getMultiAdapter
from zope.contentprovider.provider import ContentProviderBase
from zope import interface, schema
from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory
from z3c.form import form, field, button
from z3c.form.interfaces import HIDDEN_MODE
from z3c.form.interfaces import IFieldsAndContentProvidersForm
from z3c.form.contentprovider import ContentProviders

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from Products.statusmessages.interfaces import IStatusMessage

from imio.pm.wsclient import WS4PMClientMessageFactory as _
from imio.pm.wsclient import PMMessageFactory as _PM
from imio.pm.wsclient.config import ALREADY_SENT_TO_PM_ERROR, UNABLE_TO_CONNECT_ERROR, \
    NO_USERINFOS_ERROR, NO_PROPOSING_GROUP_ERROR, CORRECTLY_SENT_TO_PM_INFO, DEFAULT_NO_WARNING_MESSAGE, \
    WS4PMCLIENT_ANNOTATION_KEY, TAL_EVAL_FIELD_ERROR
from imio.pm.wsclient.interfaces import IRedirect


class ISendToPloneMeeting(interface.Interface):
    meetingConfigId = schema.TextLine(title=_(u"Meeting config id"))
    proposingGroup = schema.Choice(title=_PM(u"PloneMeeting_label_proposingGroup"),
                                   description=_(u"Select the proposing group to use "
                                                 "for the created item in PloneMeeting"),
                                   required=True,
                                   vocabulary=u'imio.pm.wsclient.proposing_groups_for_user_vocabulary')
    category = schema.Choice(title=_PM(u"PloneMeeting_label_category"),
                             description=_(u"Select the category to use for the created item item in PloneMeeting"),
                             required=True,
                             vocabulary=u'imio.pm.wsclient.categories_for_user_vocabulary')


class DisplayDataToSendProvider(ContentProviderBase):
    """
    """
    template = ViewPageTemplateFile('templates/display_data_to_send.pt')

    def __init__(self, context, request, view):
        super(DisplayDataToSendProvider, self).__init__(context, request, view)
        self.__parent__ = view

    def getDisplayableData(self):
        """
          Returns data to be displayed in the resume form
          Do not display :
          - externalIdentifier
          - empty values
        """
        data = self.__parent__.form._buildDataDict()
        if 'externalIdentifier' in data:
            data.pop('externalIdentifier')
        for elt in data:
            # keep category and proposingGroup even if empty
            if not data[elt].strip() and not elt in ['category', 'proposingGroup', ]:
                data.pop(elt)
        return data

    def render(self):
        return self.template()


class SendToPloneMeetingForm(form.Form):
    implements(IFieldsAndContentProvidersForm)

    fields = field.Fields(ISendToPloneMeeting)
    ignoreContext = True  # don't use context to get widget data

    contentProviders = ContentProviders()
    contentProviders['dataToSend'] = DisplayDataToSendProvider
    # put the 'dataToSend' in last position
    contentProviders['dataToSend'].position = 3
    label = u"Send to PloneMeeting"
    description = u''
    _finishedSent = False
    _displayErrorsInOverlay = False

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.meetingConfigId = self._findMeetingConfigId()
        self.proposingGroupId = self.request.form.get('form.widgets.proposingGroupId', [''])[0]
        self.portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = self.portal_state.portal()
        self.ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')

    @button.buttonAndHandler(_('Send to PloneMeeting'), name='send_to_plonemeeting')
    def handleSendToPloneMeeting(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        self.proposingGroupId = self.request.form.get('form.widgets.proposingGroup')[0]
        # do send to PloneMeeting
        self._doSendToPloneMeeting()

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self._finishedSent = True

    def update(self):
        """ """
        # use checkAlreadySentToPloneMeeting that will return :
        # None if could not connect
        # True if already sent
        # False if not already sent, in this case we can proceed...
        alreadySent = self.ws4pmSettings.checkAlreadySentToPloneMeeting(self.context, (self.meetingConfigId,))
        if alreadySent:
            IStatusMessage(self.request).addStatusMessage(_(ALREADY_SENT_TO_PM_ERROR), "error")
            self._changeFormForErrors()
            return
        elif alreadySent in (None, False):
            # None means that it was already sent but that it could not connect to PloneMeeting
            # False means that is was not sent, so no connection test is made to PloneMeeting for performance reason
            if alreadySent is False:
                # now connect to PloneMeeting
                client = self.ws4pmSettings._soap_connectToPloneMeeting()
            if alreadySent is None or not client:
                IStatusMessage(self.request).addStatusMessage(_(UNABLE_TO_CONNECT_ERROR), "error")
                self._changeFormForErrors()
                return

        # do not go further if current user can not create an item in
        # PloneMeeting with any proposingGroup
        userInfos = self.ws4pmSettings._soap_getUserInfos(showGroups=True, suffix='creators')
        if not userInfos or not 'groups' in userInfos:
            userThatWillCreate = self.ws4pmSettings._getUserIdToUseInTheNameOfWith()
            if not userInfos:
                IStatusMessage(self.request).addStatusMessage(_(NO_USERINFOS_ERROR % userThatWillCreate), "error")
            else:
                IStatusMessage(self.request).addStatusMessage(_(NO_PROPOSING_GROUP_ERROR % userThatWillCreate), "error")
            self._changeFormForErrors()
            return

        # now that we can connect to the webservice, check that the user can actually trigger that action
        # indeed parameters are sent thru the request, and so someone could do nasty things...
        # check that the real currentUrl is on available in object_buttons actions for the user
        availableActions = self.portal.portal_actions.listFilteredActionsFor(self.context).get('object_buttons', [])
        # rebuild real url called by the action
        currentUrl = unicode(self.request['ACTUAL_URL'] + '?meetingConfigId=' + self.meetingConfigId, 'utf-8')
        # now check if this url is available in the actions for the user
        mayDoAction = False
        for action in availableActions:
            if action['url'] == currentUrl:
                mayDoAction = True
                break
        if not mayDoAction:
            raise Unauthorized

        super(SendToPloneMeetingForm, self).update()
        # while calling parent's update, vocabularies are initialized
        # if there where errors in the vocabularies, hide the form
        if self.request.get('error_in_vocabularies', False):
            self._changeFormForErrors()
        # after calling parent's update, self.actions are available
        self.actions.get('cancel').addClass('standalone')

    def updateWidgets(self):
        portal = getSite()
        # this is also called by the kss inline_validation, avoid too much work...
        if not portal.__module__ == 'Products.CMFPlone.Portal':
            return
        # hide the meetingConfigId field
        self.fields.get('meetingConfigId').mode = HIDDEN_MODE
        # hide the widget if the linked vocabulary is empty, it means that
        # the linked meetingConfig does not use categories...
        # hide it and set it to required=False
        category_field = self.fields.get('category')
        category_field.mode = not bool(self._getCategoriesVocab()) and HIDDEN_MODE or None
        # as category is a required field, hidding it is not enough...
        category_field.field.required = bool(self._getCategoriesVocab()) and True or False
        # XXX manipulate self.fields BEFORE doing form.Form.updateWidgets
        form.Form.updateWidgets(self)
        # add a 'Choose a value...'
        self.widgets.get('proposingGroup').prompt = True
        self.widgets.get('category').prompt = True
        # initialize the value of the meetingConfigId field to what is found in the request
        self.widgets.get('meetingConfigId').value = self._findMeetingConfigId()
        # add the class 'standalone' on the 'Cancel' button

    def render(self):
        if self._finishedSent:
            IRedirect(self.request).redirect(self.context.absolute_url())
            return ""
        return super(SendToPloneMeetingForm, self).render()

    def _findMeetingConfigId(self):
        """
          Find the meetingConfigId wherever it is...
        """
        return self.request.get('meetingConfigId', '') or \
            self.request.form.get('form.widgets.meetingConfigId')

    def _doSendToPloneMeeting(self):
        """
          The method actually called while sending to PloneMeeting
        """
        # check again if already sent before sending
        # this avoid double sent from 2 opened form to send
        if self.ws4pmSettings.checkAlreadySentToPloneMeeting(self.context, (self.meetingConfigId,)):
            return False
        # build the creationData
        client = self.ws4pmSettings._soap_connectToPloneMeeting()
        creation_data = self._getCreationData(client)
        # call the SOAP method actually creating the item
        res = self.ws4pmSettings._soap_createItem(self.meetingConfigId,
                                                  self.proposingGroupId,
                                                  creation_data)
        if res:
            uid, warnings = res
            self.request.set('show_send_to_pm_form', False)
            self.portal.plone_utils.addPortalMessage(_(CORRECTLY_SENT_TO_PM_INFO), 'info')
            if warnings:
                for warning in warnings[1]:
                    # show warnings in the web interface and add it to the Zope log
                    # do not show the DEFAULT_NO_WARNING_MESSAGE
                    if warning == DEFAULT_NO_WARNING_MESSAGE:
                        continue
                    else:
                        type = "warning"
                        logger.warning(warning)
                        IStatusMessage(self.request).addStatusMessage(_(warning), type)
            # finally save in the self.context annotation that the item has been sent
            annotations = IAnnotations(self.context)
            if not WS4PMCLIENT_ANNOTATION_KEY in annotations:
                annotations[WS4PMCLIENT_ANNOTATION_KEY] = [self.meetingConfigId, ]
            else:
                # do not use .append directly on the annotations or it does not save
                # correctly and when Zope restarts, the added annotation is lost???
                existingAnnotations = list(annotations[WS4PMCLIENT_ANNOTATION_KEY])
                existingAnnotations.append(self.meetingConfigId)
                annotations[WS4PMCLIENT_ANNOTATION_KEY] = existingAnnotations
            self._finishedSent = True
            return True
        return False

    def _getCreationData(self, client):
        """
          Build creationData dict that will be used to actually create
          the item in PloneMeeting thru SOAP createItem call
        """
        data = self._buildDataDict()
        # now that every values are evaluated, build the CreationData
        creation_data = client.factory.create('CreationData')
        # not using categories?
        if not 'category' in data:
            # make sure we do not pass a 'None' !
            creation_data.category = u''

        for elt in data:
            # proposingGroup is managed apart
            if elt == u'proposingGroup':
                continue
            if not isinstance(data[elt], unicode):
                data[elt] = unicode(data[elt], 'utf-8')
            creation_data[elt] = data[elt]
        # initialize the externalIdentifier to the context UID
        creation_data['externalIdentifier'] = self.context.UID()
        return creation_data

    def _buildDataDict(self):
        """
        """
        data = OrderedDict()
        settings = self.ws4pmSettings.settings()
        for availableData in settings.field_mappings:
            field_name = availableData['field_name']
            if field_name == 'category':
                # check that the meetingConfig we want to send the item to
                # actually use categories
                if not self._getCategoriesVocab():
                    continue
                else:
                    #if we receive a category, use it
                    if self.request.form.get('form.widgets.category'):
                        data[field_name] = self.request.form.get('form.widgets.category')[0]
                        continue
            expr = availableData['expression']
            # make the meetingConfigId available in the expression
            vars = {}
            vars['meetingConfigId'] = self.meetingConfigId
            vars['proposingGroupId'] = self.proposingGroupId
            # evaluate the expression
            try:
                data[field_name] = self.ws4pmSettings.renderTALExpression(self.context,
                                                                          self.portal,
                                                                          expr,
                                                                          vars)
            except Exception, e:
                IStatusMessage(self.request).addStatusMessage(
                    _(TAL_EVAL_FIELD_ERROR %
                      (settings.viewlet_display_condition, 'viewlet_display_condition', e)),
                    "error")
                return self.request.RESPONSE.redirect(self.context.absolute_url())
        return data

    def _getCategoriesVocab(self):
        """Return the vocabulary used for the categories field"""
        portal = getSite()
        factory = queryUtility(IVocabularyFactory, u'imio.pm.wsclient.categories_for_user_vocabulary')
        return factory(portal)

    def _getProposingGroupsVocab(self):
        """Return the vocabulary used for the proposingGroup field"""
        portal = getSite()
        factory = queryUtility(IVocabularyFactory, u'imio.pm.wsclient.proposing_groups_for_user_vocabulary')
        return factory(portal)

    def _changeFormForErrors(self):
        """
        """
        # if we use an overlay popup do some nasty things...
        if 'ajax_load' in self.request.form:
            self.template = ViewPageTemplateFile('templates/show_errors_in_overlay_form.pt').__get__(self, '')
        else:
            self._finishedSent = True
        super(SendToPloneMeetingForm, self).update()


from plone.z3cform.layout import wrap_form
SendToPloneMeetingWrapper = wrap_form(SendToPloneMeetingForm)
