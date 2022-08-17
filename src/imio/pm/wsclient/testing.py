# -*- coding: utf-8 -*-

from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.testing import z2
from plone.testing import zca
from Products.PloneMeeting.testing import PMLayer

import imio.pm.ws


class WSCLIENTLayer(PMLayer):
    """ """


WS4PMCLIENT_ZCML = zca.ZCMLSandbox(filename="testing.zcml",
                                   package=imio.pm.wsclient,
                                   name='WS4PMCLIENT_ZCML')

WS4PMCLIENT_Z2 = z2.IntegrationTesting(bases=(z2.STARTUP, WS4PMCLIENT_ZCML),
                                       name='WS4PMCLIENT_Z2')

WS4PMCLIENT = WSCLIENTLayer(
    zcml_filename="testing-settings.zcml",
    zcml_package=imio.pm.wsclient,
    additional_z2_products=('imio.dashboard',
                            'imio.pm.wsclient',
                            'Products.PasswordStrength'),
    gs_profile_id='imio.pm.wsclient:testing',
    name="WS4PMCLIENT")

WS4PMCLIENT_PM_TESTING_PROFILE = WSCLIENTLayer(
    zcml_filename="testing-settings.zcml",
    zcml_package=imio.pm.wsclient,
    additional_z2_products=('imio.dashboard',
                            'Products.PloneMeeting',
                            'Products.CMFPlacefulWorkflow',
                            'imio.pm.wsclient',
                            'Products.PasswordStrength'),
    gs_profile_id='imio.pm.wsclient:testing',
    name="WS4PMCLIENT_PM_TESTING_PROFILE")

WS4PMCLIENT_PM_TESTING_PROFILE_INTEGRATION = IntegrationTesting(
    bases=(WS4PMCLIENT_PM_TESTING_PROFILE,), name="WS4PMCLIENT_PM_TESTING_PROFILE_INTEGRATION")

WS4PMCLIENT_PROFILE_FUNCTIONAL = FunctionalTesting(
    bases=(WS4PMCLIENT,), name="WS4PMCLIENT_PROFILE_FUNCTIONAL")

WS4PMCLIENT_PM_TESTING_PROFILE_FUNCTIONAL = FunctionalTesting(
    bases=(
        WS4PMCLIENT_PM_TESTING_PROFILE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        z2.ZSERVER_FIXTURE,
    ),
    name="WS4PMCLIENT_PM_TESTING_PROFILE_FUNCTIONAL",
)
