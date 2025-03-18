from datetime import datetime
from z3c.form import interfaces
from z3c.form.browser.select import SelectWidget
from z3c.form.widget import FieldWidget

import zope.component
import zope.interface
import zope.schema
import zope.schema.interfaces


class DateSelectWidget(SelectWidget):
    @property
    def items(self):
        items = super(DateSelectWidget, self).items
        for item in items:
            # "content": "2025-01-13 10:00:00+01:00"
            try:
                item["content"] = datetime.strptime(item["content"][:-6], "%Y-%m-%d %H:%M:%S")
                item["content"] = datetime.strftime(item["content"], "%d/%m/%Y %H:%M")
            except ValueError:
                pass
        return items


@zope.component.adapter(zope.schema.interfaces.IChoice, zope.interface.Interface, interfaces.IFormLayer)
@zope.interface.implementer(interfaces.IFieldWidget)
def DateSelectFieldWidget(field, source, request=None):
    """IFieldWidget factory for SelectWidget."""
    # BBB: emulate our pre-2.0 signature (field, request)
    if request is None:
        real_request = source
    else:
        real_request = request
    return FieldWidget(field, DateSelectWidget(real_request))
