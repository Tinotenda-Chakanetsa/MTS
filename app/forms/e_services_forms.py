from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired

class AddAccountForm(FlaskForm):
    name = StringField('Account Name', validators=[DataRequired()])
    account_number = StringField('Account Number', validators=[DataRequired()])
    submit = SubmitField('Create Account')
