from marshmallow import Schema, fields, validate, validates_schema, ValidationError

Username = fields.Str(
    required=True,
    validate=validate.Regexp(r"^[a-zA-Z0-9_]+$", error="Username must be alphanumeric/underscre.")
)
Email = fields.Email(required=True, error_messages={"invalid": "Invalid email address."})
Password = fields.Str(required=True)

class RegisterSchema(Schema):
    username = Username
    email = Email
    password = Password

class LoginSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)

class ChangePasswordSchema(Schema):
    old_password = fields.Str(required=True)
    new_password = Password
    new_password_again = Password

    @validates_schema
    def ensure_diff(self, data, **kwargs):
        if data.get("old_password") == data.get("new_password"):
            raise ValidationError("New password cannot be the same as old password.", field_name="new_password")

class TokensResponseSchema(Schema):
    access_token = fields.Str()
    refresh_token = fields.Str()

class MessageSchema(Schema):
    msg = fields.Str()

class ForgotPasswordSchema(Schema):
    email = fields.Email(required=True)

class ResetPasswordSchema(Schema):
    email = fields.Str(required=True)
    digit_code = fields.Str(required=True)
    new_password = fields.Str(required=True)
    new_password_again = fields.Str(required=True)