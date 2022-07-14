# -*- coding: utf-8 -*-
#
# Copyright (c) 2013 by Imio.be
#
# GNU General Public License (GPL)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#

from Acquisition import aq_base
from plonemeeting.restapi.tests.base import BaseTestCase as WS4PMTestCase
from imio.pm.wsclient.testing import WS4PMCLIENT_PM_TESTING_PROFILE_FUNCTIONAL
from Products.PloneMeeting.config import DEFAULT_USER_PASSWORD
from zope.annotation.interfaces import IAnnotations
from zope.component import getMultiAdapter

import transaction


SEND_TO_PM_VIEW_NAME = '@@send_to_plonemeeting_form'


class WS4PMCLIENTTestCase(WS4PMTestCase):
    '''Base class for defining WS4PMCLIENT test cases.'''

    # define PM base TestCase test file that we will not launch from here
    subproductIgnoredTestFiles = ['testMeetingCategory.py', 'testVotes.py', 'testWFAdaptations.py',
                                  'testPodTemplates.py', 'testAdvices.py', 'testMeetingFileType.py',
                                  'testMeeting.py', 'testChangeItemOrderView.py', 'testMeetingGroup.py',
                                  'testWorkflows.py', 'testMeetingConfig.py', 'testToolPloneMeeting.py',
                                  'testPortlets.py', 'testMeetingItem.py', 'testConversionWithDocumentViewer.py',
                                  'testPerformances.py']

    layer = WS4PMCLIENT_PM_TESTING_PROFILE_FUNCTIONAL

    def setUp(self):
        """ """
        WS4PMTestCase.setUp(self)

    def _sendToPloneMeeting(self, obj, user='pmCreator1', proposingGroup='developers',
                            meetingConfigId='plonemeeting-assembly', category=''):
        """
          Helper method for sending an element to PloneMeeting
        """
        # set correct config
        setCorrectSettingsConfig(self.portal)
        # create the 'pmCreator1' member area to be able to create an item
        self.tool.getPloneMeetingFolder(meetingConfigId, user)
        # we have to commit() here or portal used behing the SOAP call
        # does not have the freshly created item...
        transaction.commit()
        # use the 'send_to_plonemeeting' view
        self.request.set('URL', obj.absolute_url())
        self.request.set('ACTUAL_URL', obj.absolute_url() + '/%s' % SEND_TO_PM_VIEW_NAME)
        self.request.set('meetingConfigId', meetingConfigId)
        view = obj.restrictedTraverse(SEND_TO_PM_VIEW_NAME).form_instance
        view.proposingGroupId = proposingGroup
        # call the view so relevant status messages are displayed
        view()
        # we start a new transaction because view._doSendToPloneMeeting creates the
        # item using a suds SOAP subprocess call and the item is actually created when the transaction is committed
        # if not, the item is not really created and not found here under by the portal_catalog query
        transaction.begin()
        view._doSendToPloneMeeting()
        transaction.commit()
        brains = self.portal.portal_catalog(portal_type='MeetingItemPma', externalIdentifier=obj.UID())
        return brains and brains[0].getObject() or None


def setCorrectSettingsConfig(portal, setConnectionParams=True, minimal=False, withValidation=True, **kwargs):
    """Set a workable set of settings for tests.
       If p_withValidation is False, remove validation because we want
       to force to set some values and relevant vocabularies for example do not contain that value.
       If p_minimal is True, only minimal settings are set to be able to connect."""
    if not withValidation:
        # disable validation when forcing some values to set
        from zope.schema._field import AbstractCollection
        old_validate = AbstractCollection._validate

        def _validate(self, value):
            return
        AbstractCollection._validate = _validate
    ws4pmSettings = getMultiAdapter((portal, portal.REQUEST), name='ws4pmclient-settings')
    settings = ws4pmSettings.settings()
    if setConnectionParams:
        settings.pm_url = kwargs.get('pm_url', None) or portal.absolute_url().decode('utf-8')
        settings.pm_username = kwargs.get('pm_username', None) or u'pmManager'
        settings.pm_password = kwargs.get('pm_password', None) or DEFAULT_USER_PASSWORD
    settings.user_mappings = kwargs.get('user_mappings', None) or \
        [{'local_userid': u'localUserId',
          'pm_userid': u'pmCreator1'},
         {'local_userid': u'localUserId2',
          'pm_userid': u'pmCreator2'},
         {'local_userid': u'admin',
          'pm_userid': u'pmCreator1'}, ]
    settings.viewlet_display_condition = kwargs.get('viewlet_display_condition', None) or u''
    if not minimal:
        # these parameters are only available while correctly connected
        # to PloneMeeting webservices, either use withValidation=False
        # these fields mappings make it work if classic Document content_type
        settings.field_mappings = kwargs.get('field_mappings', None) or [
            {'field_name': u'title',
             'expression': u'object/Title'},
            {'field_name': u'description',
             'expression': u'object/Description'},
            # 'plonemeeting-assembly' does not use categories but 'plonegov-assembly' does
            {'field_name': u'category',
             'expression':
                u'python: object.REQUEST.get("meetingConfigId") != "plonemeeting-assembly" and "deployment" or ""'},
            {'field_name': u'decision',
             'expression': u'object/getText'},
            {'field_name': u'externalIdentifier',
             'expression': u'object/UID'},
        ]
        settings.allowed_annexes_types = kwargs.get('allowed_annexes_types', None) or []
        settings.generated_actions = kwargs.get('generated_actions', None) or [
            {'pm_meeting_config_id': 'plonegov-assembly',
             'condition': u'python:True',
             'permissions': u'View'},
            {'pm_meeting_config_id': 'plonegov-assembly',
             'condition': u'python:True',
             'permissions': u'View'},
            {'pm_meeting_config_id': 'plonemeeting-assembly',
             'condition': u'python:True',
             'permissions': u'View'},
            {'pm_meeting_config_id': 'plonemeeting-assembly',
             'condition': u'python:False',
             'permissions': u'View'},
            {'pm_meeting_config_id': 'plonemeeting-assembly',
             'condition': u'python:True',
             'permissions': u'Manage portal'}

        ]
    if not withValidation:
        AbstractCollection._validate = old_validate


def createDocument(placeToCreate):
    """
      Helper method for creating a document object
    """
    data = {'title': 'Document title',
            'description': 'Document description',
            'text': '<p>Document rich text</p>'}
    documentId = placeToCreate.invokeFactory('Document', id='document', **data)
    document = getattr(placeToCreate, documentId)
    document.reindexObject()
    return document


def createAnnex(placeToCreate):
    """
      Helper method for creating an annex object
    """
    data = {'title': 'Annexe oubliée',
            'file': 'hello\n'}
    annexId = placeToCreate.invokeFactory('File', id='annex', **data)
    annex = getattr(placeToCreate, annexId)
    annex.getFile().setFilename('annexe oubliée.txt')
    annex.reindexObject()
    return annex


def cleanMemoize(request, obj=None):
    """
      Remove every memoized informations : memoize on the REQUEST and on the object
    """
    annotations = IAnnotations(request)
    if 'plone.memoize' in annotations:
        annotations['plone.memoize'].clear()
    if obj and hasattr(aq_base(obj), '_memojito_'):
        delattr(obj, '_memojito_')
