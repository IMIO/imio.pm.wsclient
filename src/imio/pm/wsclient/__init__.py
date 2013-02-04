from zope.i18nmessageid import MessageFactory

WS4PMClientMessageFactory = MessageFactory("imio.pm.wsclient")

def initialize(context):
    """Initializer called when used as a Zope 2 product."""