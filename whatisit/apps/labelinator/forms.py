from crispy_forms.layout import Layout, Div, Submit, HTML, Button, Row, Field, Hidden
from crispy_forms.bootstrap import AppendedText, PrependedText, FormActions, TabHolder, Tab
from crispy_forms.bootstrap import StrictButton
from crispy_forms.helper import FormHelper

from django.forms import ModelForm, Form
from django import forms

from whatisit.apps.labelinator.utils import format_report_name

from glob import glob
import os

from whatisit.apps.labelinator.models import (Report, ReportCollection)


class ReportForm(ModelForm):

    class Meta:
        model = Report
        fields = ("uid","text",)

    def clean(self):
        cleaned_data = super(ReportForm, self).clean()

        # The "name" must be lowercase, no invalid characters or numbers
        name = cleaned_data.get("name")
        cleaned_data['name'] = format_container_name(name,special_characters=['-'])            
        return cleaned_data

    def __init__(self, *args, **kwargs):

        super(ContainerForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout()
        tab_holder = TabHolder()
        self.helper.add_input(Submit("submit", "Save"))


class ReportCollectionForm(ModelForm):

    class Meta:
        model = ReportCollection
        fields = ("name",)

    def clean(self):
        cleaned_data = super(ReportCollectionForm, self).clean()

        # The "name" must be lowercase, no invalid characters or numbers
        name = cleaned_data.get("name")
        cleaned_data['name'] = format_report_name(name,special_characters=['-'])            
        return cleaned_data

    def __init__(self, *args, **kwargs):

        super(ReportCollectionForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout()
        tab_holder = TabHolder()
        self.helper.add_input(Submit("submit", "Save"))


#######################################################################################
# FORM HELPER FUNCTIONS ###############################################################
#######################################################################################

def update_form(form,updates):
    '''update_form will update a query dict for a form
    :param form: should be the form object generated from the request.POST
    :param updates: should be a dictionary of {field:value} to update
    '''
    qd = form.data.copy()
    for field,value in updates.iteritems():
        qd[field] = value
    form.data = qd
    return form
