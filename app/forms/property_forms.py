from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired

from app.models.user import Account
from flask_login import current_user

class PropertyRegistrationForm(FlaskForm):
    account_id = SelectField('Account', coerce=int)
    owner_name = StringField('Owner Name', validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired()])
    type = StringField('Property Type', validators=[DataRequired()])
    status = SelectField('Status', choices=[('Active', 'Active'), ('Suspended', 'Suspended'), ('Transferred', 'Transferred')], validators=[DataRequired()])
    submit = SubmitField('Register Property')
