ISTP_RULES = []
_REFERENCES = set()


def register_istp_rule(class_):
    global ISTP_RULES
    global _REFERENCES
    rule = class_()
    if rule.reference not in _REFERENCES:
        _REFERENCES.add(rule.reference)
    else:
        raise ValueError(f"Duplicate reference found: {rule.reference}, each rule must have a unique reference.")
    ISTP_RULES.append(rule)
    return class_
