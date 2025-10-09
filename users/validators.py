import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class ComplexityValidator:
    """
    Require at least:
    - one lowercase
    - one uppercase
    - one digit
    - one symbol (e.g. !@#$%)
    """
    pattern = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).+$')

    def validate(self, password, user=None):
        if not self.pattern.search(password or ""):
            raise ValidationError(
                _("Password has to include uppercase, lowercase, a digit, and a symbol."),
                code="password_no_complexity",
            )

    def get_help_text(self):
        return _("Your password must include uppercase, lowercase, a digit, and a symbol.")