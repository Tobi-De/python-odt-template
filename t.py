import IPython
import lxml.etree as ET  # noqa
from python_odt_template import ODTTemplate

with ODTTemplate("samples/template.odt") as template:
    # enter Ipython shell
    IPython.embed()
    template.pack("samples/template.odt")
