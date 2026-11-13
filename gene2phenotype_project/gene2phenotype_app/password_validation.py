from string import punctuation

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class PasswordComplexityValidator:
    def validate(self, password, user=None):
        errors = []
        if not any(character.isupper() for character in password):
            errors.append(
                ValidationError(
                    _("This password must contain at least one uppercase letter."),
                    code="password_no_uppercase",
                )
            )
        if not any(character in punctuation for character in password):
            errors.append(
                ValidationError(
                    _("This password must contain at least one special character."),
                    code="password_no_special_character",
                )
            )
        if not any(character.isdigit() for character in password):
            errors.append(
                ValidationError(
                    _("This password must contain at least one digit."),
                    code="password_no_digit",
                )
            )
        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return _(
            "Your password must contain at least one uppercase letter, "
            "one special character and one digit."
        )
