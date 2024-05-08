__all__ = ["Contains", "StartsWith", "EndsWith"]

SAFE_REGEX_DICTIONARY = {
    "(": "\\(",
    ")": "\\)",
    "!": "\\!",
    "^": "\\^",
    "$": "\\$",
    "[": "\\[",
    "]": "\\]",
    "*": "\\*",
    "+": "\\+",
    "?": "\\?",
    "{": "\\{",
    "}": "\\}",
    "/": "\\/",
    "|": "\\|",
    "<": "\\<",
    ">": "\\>",
    ".": "\\.",
    "\\": "\\\\",
}


class Contains(dict):
    def __init__(self, value: str, case_sensitive: bool = True):
        safe_value = value.translate(value.maketrans(SAFE_REGEX_DICTIONARY))
        if case_sensitive:
            super().__init__({"$regex": safe_value})
        else:
            super().__init__({"$regex": safe_value, "$options": "i"})


class StartsWith(dict):
    def __init__(self, value: str, case_sensitive: bool = True):
        safe_value = value.translate(value.maketrans(SAFE_REGEX_DICTIONARY))
        if case_sensitive:
            super().__init__({"$regex": f"^{safe_value}"})
        else:
            super().__init__({"$regex": f"^{safe_value}", "$options": "i"})


class EndsWith(dict):
    def __init__(self, value: str, case_sensitive: bool = True):
        safe_value = value.translate(value.maketrans(SAFE_REGEX_DICTIONARY))
        if case_sensitive:
            super().__init__({"$regex": f"{safe_value}$"})
        else:
            super().__init__({"$regex": f"{safe_value}$", "$options": "i"})
