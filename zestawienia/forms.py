from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, HTML, Button, Row, Field
from crispy_forms.bootstrap import AppendedText, PrependedText, FormActions

from .models import Ustawienia

class UstawieniaForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(UstawieniaForm, self).__init__(*args, **kwargs)

        # If you pass FormHelper constructor a form instance
        # It builds a default layout with all its fields
        self.helper = FormHelper(self)

        # You can dynamically adjust your layout
        self.helper.layout = Layout(
            Field('data_start', ),
            Field('data_koniec',),
            Field('serwer',),
            #Field('usunac_baze',),
            FormActions(Submit('ustawienia', 'Sprawdź zestawienia'))
            )
        #self.helper.layout.append(Submit('save', 'save'))

    class Meta:
        model = Ustawienia
        fields = ["data_start", 
                "data_koniec", 
                "serwer", 
                #"usunac_baze"
                ]
