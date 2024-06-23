from markupsafe import Markup


def pad_string(value, length=5):
    value = str(value)
    return value.zfill(length)


def finalize_value(value):
    """Escapes variables values."""
    if isinstance(value, Markup):
        return value

    """
        Encodes XML reserved chars in value (eg. &, <, >) and also replaces
        the control chars \n and \t control chars to their ODF counterparts.
        """
    value = Markup.escape(value)
    return Markup(
        value.replace("\n", Markup("<text:line-break/>"))
        .replace("\t", Markup("<text:tab/>"))
        .replace("\x0b", "<text:space/>")
        .replace("\x0c", "<text:space/>")
    )
